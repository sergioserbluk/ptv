
import os, sqlite3, json, csv, io, datetime
from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit

DB_PATH = os.path.join(os.path.dirname(__file__), "matches.db")

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SECRET_KEY"] = "change-me"

# optional eventlet, fallback to threading
try:
    import eventlet  # noqa: F401
    async_mode = "eventlet"
except Exception:
    async_mode = "threading"

socketio = SocketIO(app, cors_allowed_origins="*", async_mode=async_mode)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db(); c = conn.cursor()
    c.executescript("""
    PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS rulesets (id INTEGER PRIMARY KEY, name TEXT NOT NULL, json TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS tournaments (id INTEGER PRIMARY KEY, name TEXT NOT NULL, season TEXT, ruleset_id INTEGER NOT NULL, type TEXT NOT NULL, meta_json TEXT, FOREIGN KEY (ruleset_id) REFERENCES rulesets(id));
    CREATE TABLE IF NOT EXISTS teams (id INTEGER PRIMARY KEY, name TEXT NOT NULL, short TEXT, colors TEXT, logo_url TEXT);
    CREATE TABLE IF NOT EXISTS tournament_teams (id INTEGER PRIMARY KEY, tournament_id INTEGER NOT NULL, team_id INTEGER NOT NULL, group_name TEXT, FOREIGN KEY (tournament_id) REFERENCES tournaments(id), FOREIGN KEY (team_id) REFERENCES teams(id));
    CREATE TABLE IF NOT EXISTS matches (id INTEGER PRIMARY KEY, tournament_id INTEGER NOT NULL, home_id INTEGER NOT NULL, away_id INTEGER NOT NULL, date TEXT, gym TEXT, status TEXT, rules_snapshot_json TEXT, result_json TEXT, FOREIGN KEY (tournament_id) REFERENCES tournaments(id), FOREIGN KEY (home_id) REFERENCES teams(id), FOREIGN KEY (away_id) REFERENCES teams(id));
    CREATE TABLE IF NOT EXISTS players (id INTEGER PRIMARY KEY, team_id INTEGER NOT NULL, number INTEGER, name TEXT NOT NULL, role TEXT, libero INTEGER NOT NULL DEFAULT 0, FOREIGN KEY (team_id) REFERENCES teams(id));

    CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, match_id INTEGER NOT NULL, set_number INTEGER, ts TEXT NOT NULL, type TEXT NOT NULL, payload_json TEXT, FOREIGN KEY (match_id) REFERENCES matches(id));

    -- v9: alineaciones y contador de sustituciones
    CREATE TABLE IF NOT EXISTS lineups (
      id INTEGER PRIMARY KEY,
      match_id INTEGER NOT NULL,
      set_number INTEGER NOT NULL,
      team TEXT NOT NULL,               -- 'home' | 'away'
      players_json TEXT NOT NULL,       -- [player_id,...] (6)
      libero_id INTEGER,
      UNIQUE(match_id,set_number,team)
    );
    CREATE TABLE IF NOT EXISTS subs_counter (
      id INTEGER PRIMARY KEY,
      match_id INTEGER NOT NULL,
      set_number INTEGER NOT NULL,
      team TEXT NOT NULL,               -- 'home' | 'away'
      used INTEGER NOT NULL DEFAULT 0,
      UNIQUE(match_id,set_number,team)
    );
    """)

    # seed
    c.execute("SELECT COUNT(*) FROM rulesets")
    if c.fetchone()[0] == 0:
        rules = {
            "best_of": 5, "sets_to_win": 3,
            "set_points_regular": 25, "set_points_tiebreak": 15,
            "win_by_two": True, "timeouts_per_set": 2, "timeout_seconds": 60,
            "subs_per_set": 6, "libero_rules": {"count": 1, "free_replacements": True},
            "standings_scoring": {"mode": "by_result", "by_result": {"win_3_0_or_3_1": 3, "win_3_2": 2, "loss_2_3": 1, "loss_other": 0}},
            "track_points_diff": True, "tiebreakers_order": ["points_total","matches_won","set_ratio","points_ratio","head_to_head"],
            "tournament_type": "round_robin"
        }
        c.execute("INSERT INTO rulesets(name, json) VALUES (?,?)", ("Liga 2025 - Std (Bo5)", json.dumps(rules)))
        ruleset_id = c.lastrowid

        # teams
        c.execute("INSERT INTO teams(name, short) VALUES (?,?)", ("Iberá V.C.", "IBR"))
        home_id = c.lastrowid
        c.execute("INSERT INTO teams(name, short) VALUES (?,?)", ("Independiente", "IND"))
        away_id = c.lastrowid

        # tournament
        c.execute("INSERT INTO tournaments(name, season, ruleset_id, type, meta_json) VALUES (?,?,?,?,?)",
                  ("Liga Local 2025", "2025", ruleset_id, "round_robin", "{}"))
        tournament_id = c.lastrowid
        c.execute("INSERT INTO tournament_teams(tournament_id, team_id) VALUES (?,?)", (tournament_id, home_id))
        c.execute("INSERT INTO tournament_teams(tournament_id, team_id) VALUES (?,?)", (tournament_id, away_id))

        # match
        c.execute("""INSERT INTO matches(tournament_id, home_id, away_id, date, gym, status, rules_snapshot_json)
                     VALUES (?,?,?,?,?,?,?)""",
                  (tournament_id, home_id, away_id, "2025-08-16T18:00:00", "Polideportivo", "scheduled", json.dumps(rules)))
        mid = c.lastrowid

        # players (home)
        home_players = [
            (home_id, 1, "Local 1", "OH", 0),
            (home_id, 2, "Local 2", "MB", 0),
            (home_id, 3, "Local 3", "S",  0),
            (home_id, 4, "Local 4", "OP", 0),
            (home_id, 5, "Local 5", "OH", 0),
            (home_id, 6, "Local 6", "MB", 0),
            (home_id, 12, "Líbero Local", "L", 1),
            (home_id, 7, "Local 7", "OH", 0),
            (home_id, 8, "Local 8", "MB", 0),
        ]
        c.executemany("INSERT INTO players(team_id, number, name, role, libero) VALUES (?,?,?,?,?)", home_players)

        # players (away)
        away_players = [
            (away_id, 1, "Visita 1", "OH", 0),
            (away_id, 2, "Visita 2", "MB", 0),
            (away_id, 3, "Visita 3", "S",  0),
            (away_id, 4, "Visita 4", "OP", 0),
            (away_id, 5, "Visita 5", "OH", 0),
            (away_id, 6, "Visita 6", "MB", 0),
            (away_id, 10, "Líbero Visita", "L", 1),
            (away_id, 7, "Visita 7", "OH", 0),
            (away_id, 8, "Visita 8", "MB", 0),
        ]
        c.executemany("INSERT INTO players(team_id, number, name, role, libero) VALUES (?,?,?,?,?)", away_players)

    conn.commit(); conn.close()

init_db()

# ---------------- Overlay State ----------------
state = {
    "mode": "intro", "theme": "dark",
    "home_name": "Local", "away_name": "Visitante",
    "home_points": 0, "away_points": 0,
    "home_sets": 0, "away_sets": 0, "set_number": 1,
    "timer_running": False, "timer_seconds": 0,
    "ads_enabled": True,
    "intro_title": "Fecha 5 - Liga Local",
    "intro_subtitle": "Iberá V.C. vs Independiente",
    "intro_extra": "Cancha: Polideportivo · 20:00",
    "match_id": None, "tournament_id": None
}

def broadcast(): socketio.emit("state_update", state)

def log_event(match_id, set_number, ev_type, payload):
    if not match_id: return
    conn = get_db(); c = conn.cursor()
    c.execute("""INSERT INTO events(match_id, set_number, ts, type, payload_json)
                 VALUES (?,?,?,?,?)""",
              (match_id, set_number, datetime.datetime.now().isoformat(), ev_type, json.dumps(payload or {})))
    conn.commit(); conn.close()

def load_match_names(match_id):
    try:
        conn = get_db(); c = conn.cursor()
        c.execute("""SELECT th.name, ta.name FROM matches m
                     JOIN teams th ON th.id=m.home_id
                     JOIN teams ta ON ta.id=m.away_id
                     WHERE m.id=?""", (match_id,))
        r = c.fetchone()
        if r: state["home_name"], state["away_name"] = r[0], r[1]
        conn.close()
    except Exception:
        pass

def rules_for_match(match_id):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT rules_snapshot_json FROM matches WHERE id=?", (match_id,))
    r = c.fetchone(); conn.close()
    if not r or not r[0]: return {"subs_per_set": 6}
    try: return json.loads(r[0])
    except: return {"subs_per_set": 6}

# ---------------- Routes ----------------
@app.route("/")
def index(): return "OK · Control: /control · Display: /display · Admin: /admin"

@app.route("/control")
def control(): return render_template("control.html")

@app.route("/display")
def display(): return render_template("display.html", theme=state.get("theme","dark"))

@app.route("/admin")
def admin(): return render_template("admin.html")

@app.route("/ads")
def ads_list():
    files = []
    base = os.path.join(app.static_folder, "ads")
    if os.path.isdir(base):
        for f in sorted(os.listdir(base)):
            if f.lower().endswith((".png",".jpg",".jpeg",".gif",".webp")):
                files.append(f"/static/ads/{f}")
    return {"images": files}

# ---- APIs lectura ----
@app.route("/api/rulesets")
def api_rulesets():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id, name FROM rulesets ORDER BY id DESC")
    rows = [{"id": r[0], "name": r[1]} for r in c.fetchall()]
    conn.close(); return jsonify(rows)

@app.route("/api/tournaments")
def api_tournaments():
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT t.id, t.name, t.season, r.name, t.type
                 FROM tournaments t JOIN rulesets r ON r.id=t.ruleset_id
                 ORDER BY t.id DESC""")
    rows = [{"id": r[0], "name": r[1], "season": r[2], "ruleset": r[3], "type": r[4]} for r in c.fetchall()]
    conn.close(); return jsonify(rows)

@app.route("/api/teams")
def api_teams():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id, name, short FROM teams ORDER BY name ASC")
    rows = [{"id": r[0], "name": r[1], "short": r[2]} for r in c.fetchall()]
    conn.close(); return jsonify(rows)

@app.route("/api/players")
def api_players():
    team_id = request.args.get("team_id", type=int)
    if not team_id: return jsonify([])
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id, number, name, role, libero FROM players WHERE team_id=? ORDER BY (libero DESC), number", (team_id,))
    rows = [{"id": r[0], "number": r[1], "name": r[2], "role": r[3], "libero": bool(r[4])} for r in c.fetchall()]
    conn.close(); return jsonify(rows)

@app.route("/api/matches")
def api_matches():
    tid = request.args.get("tournament_id", type=int)
    conn = get_db(); c = conn.cursor()
    if tid:
        c.execute("""SELECT m.id, th.name, ta.name, m.status, m.date FROM matches m
                     JOIN teams th ON th.id=m.home_id
                     JOIN teams ta ON ta.id=m.away_id
                     WHERE m.tournament_id=? ORDER BY m.id DESC""", (tid,))
    else:
        c.execute("""SELECT m.id, th.name, ta.name, m.status, m.date FROM matches m
                     JOIN teams th ON th.id=m.home_id
                     JOIN teams ta ON ta.id=m.away_id
                     ORDER BY m.id DESC""")
    rows = [{"id": r[0], "label": f"{r[1]} vs {r[2]}", "status": r[3], "date": r[4]} for r in c.fetchall()]
    conn.close(); return jsonify(rows)

@app.route("/api/match_teams")
def api_match_teams():
    mid = request.args.get("match_id", type=int)
    if not mid: return jsonify({"error":"match_id requerido"}), 400
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT home_id, away_id FROM matches WHERE id=?", (mid,))
    r = c.fetchone(); conn.close()
    if not r: return jsonify({"error":"partido no encontrado"}), 404
    return jsonify({"home_id": r[0], "away_id": r[1]})

# ---- Export CSV ----
@app.route("/api/events/export.csv")
def api_export_csv():
    match_id = request.args.get("match_id", type=int)
    if not match_id: return ("match_id requerido", 400)
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id, set_number, ts, type, payload_json FROM events WHERE match_id=? ORDER BY id", (match_id,))
    out = io.StringIO(); w = csv.writer(out)
    w.writerow(["id","set","timestamp","type","payload_json"])
    for r in c.fetchall():
        w.writerow([r[0], r[1], r[2], r[3], r[4]])
    data = out.getvalue().encode("utf-8")
    return send_file(io.BytesIO(data), mimetype="text/csv", as_attachment=True, download_name=f"match_{match_id}_events.csv")

# ---- Admin minimal (crear/editar/borrar) ----
@app.route("/api/admin/team", methods=["POST"])
def api_admin_team():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    short = (data.get("short") or "").strip() or None
    if not name: return jsonify({"error":"name requerido"}), 400
    conn = get_db(); c = conn.cursor()
    c.execute("INSERT INTO teams(name, short) VALUES (?,?)", (name, short))
    team_id = c.lastrowid
    conn.commit(); conn.close()
    return jsonify({"ok": True, "id": team_id})

@app.route("/api/admin/match", methods=["POST"])
def api_admin_match():
    data = request.get_json(force=True)
    tournament_id = data.get("tournament_id")
    home_id = data.get("home_id")
    away_id = data.get("away_id")
    date = data.get("date") or datetime.datetime.now().isoformat()
    gym = (data.get("gym") or "").strip() or None
    if not (tournament_id and home_id and away_id): return jsonify({"error":"tournament_id, home_id, away_id requeridos"}), 400
    if home_id == away_id: return jsonify({"error":"home y away no pueden ser el mismo equipo"}), 400
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT r.json FROM tournaments t JOIN rulesets r ON r.id=t.ruleset_id WHERE t.id=?", (tournament_id,))
    r = c.fetchone()
    if not r: conn.close(); return jsonify({"error":"tournament inválido"}), 400
    snap = r[0]
    c.execute("""INSERT INTO matches(tournament_id, home_id, away_id, date, gym, status, rules_snapshot_json)
                 VALUES (?,?,?,?,?,?,?)""", (tournament_id, home_id, away_id, date, gym, "scheduled", snap))
    mid = c.lastrowid
    for tid_team in (home_id, away_id):
        c.execute("SELECT 1 FROM tournament_teams WHERE tournament_id=? AND team_id=?", (tournament_id, tid_team))
        if c.fetchone() is None:
            c.execute("INSERT INTO tournament_teams(tournament_id, team_id) VALUES (?,?)", (tournament_id, tid_team))
    conn.commit(); conn.close()
    return jsonify({"ok": True, "id": mid})

@app.route("/api/admin/player", methods=["POST"])
def api_admin_player():
    d = request.get_json(force=True)
    team_id = d.get("team_id"); name = (d.get("name") or "").strip()
    number = d.get("number"); role = (d.get("role") or "").strip() or None
    libero = 1 if d.get("libero") else 0
    if not (team_id and name): return jsonify({"error":"team_id y name requeridos"}), 400
    conn = get_db(); c = conn.cursor()
    c.execute("INSERT INTO players(team_id, number, name, role, libero) VALUES (?,?,?,?,?)", (team_id, number, name, role, libero))
    pid = c.lastrowid
    conn.commit(); conn.close()
    return jsonify({"ok": True, "id": pid})

# ---- Lineup APIs ----
@app.route("/api/team_players")
def api_team_players():
    tid = request.args.get("team_id", type=int)
    if not tid: return jsonify([])
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT id, number, name, role, libero
                 FROM players WHERE team_id=? ORDER BY (libero DESC), number""", (tid,))
    rows = [{"id":r[0], "number":r[1], "name":r[2], "role":r[3], "libero": bool(r[4])} for r in c.fetchall()]
    conn.close(); return jsonify(rows)

@app.route("/api/lineup")
def api_lineup_get():
    mid = request.args.get("match_id", type=int)
    setn = request.args.get("set_number", type=int)
    team = request.args.get("team")
    if not (mid and setn and team in ("home","away")): return jsonify({"error":"params"}), 400
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT players_json, libero_id FROM lineups WHERE match_id=? AND set_number=? AND team=?", (mid,setn,team))
    row = c.fetchone()
    players = json.loads(row[0]) if row else []
    libero_id = row[1] if row else None
    c.execute("SELECT used FROM subs_counter WHERE match_id=? AND set_number=? AND team=?", (mid,setn,team))
    r2 = c.fetchone(); used = r2[0] if r2 else 0
    limit = rules_for_match(mid).get("subs_per_set", 6)
    conn.close()
    return jsonify({"players": players, "libero_id": libero_id, "subs_used": used, "subs_limit": limit})

@app.route("/api/lineup", methods=["POST"])
def api_lineup_set():
    d = request.get_json(force=True)
    mid = d.get("match_id")
    setn = d.get("set_number")
    team = d.get("team")
    players = d.get("players") or []
    libero_id = d.get("libero_id")
    if not (mid and setn and team in ("home","away") and isinstance(players, list) and len(players) == 6):
        return jsonify({"error":"params"}), 400
    conn = get_db(); c = conn.cursor()
    c.execute("""INSERT INTO lineups(match_id,set_number,team,players_json,libero_id)
                 VALUES (?,?,?,?,?)
                 ON CONFLICT(match_id,set_number,team)
                 DO UPDATE SET players_json=excluded.players_json, libero_id=excluded.libero_id""",
              (mid, setn, team, json.dumps(players), libero_id))
    c.execute("""INSERT INTO subs_counter(match_id,set_number,team,used) VALUES (?,?,?,0)
                 ON CONFLICT(match_id,set_number,team) DO NOTHING""", (mid,setn,team))
    conn.commit(); conn.close()
    log_event(mid, setn, "LINEUP_SET", {"team": team, "players": players, "libero_id": libero_id})
    return jsonify({"ok": True})

@app.route("/api/sub", methods=["POST"])
def api_sub():
    d = request.get_json(force=True)
    mid = d.get("match_id"); setn = d.get("set_number"); team = d.get("team")
    out_id = d.get("out_id"); in_id = d.get("in_id")
    if not all([mid, setn, team in ("home","away"), out_id, in_id]): return jsonify({"error":"params"}), 400
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT players_json FROM lineups WHERE match_id=? AND set_number=? AND team=?", (mid,setn,team))
    row = c.fetchone()
    if not row: conn.close(); return jsonify({"error":"sin lineup"}), 400
    players = json.loads(row[0])
    if out_id not in players: conn.close(); return jsonify({"error":"sale no está en cancha"}), 400
    if in_id in players: conn.close(); return jsonify({"error":"entra ya está en cancha"}), 400
    c.execute("SELECT used FROM subs_counter WHERE match_id=? AND set_number=? AND team=?", (mid,setn,team))
    r2 = c.fetchone(); used = r2[0] if r2 else 0
    limit = rules_for_match(mid).get("subs_per_set", 6)
    if used >= limit:
        conn.close(); return jsonify({"error":"límite de sustituciones alcanzado"}), 400
    players = [in_id if pid == out_id else pid for pid in players]
    c.execute("UPDATE lineups SET players_json=? WHERE match_id=? AND set_number=? AND team=?", (json.dumps(players), mid, setn, team))
    c.execute("""INSERT INTO subs_counter(match_id,set_number,team,used) VALUES (?,?,?,1)
                 ON CONFLICT(match_id,set_number,team) DO UPDATE SET used=used+1""", (mid,setn,team))
    conn.commit(); conn.close()
    log_event(mid, setn, "SUB", {"team": team, "out": out_id, "in": in_id})
    return jsonify({"ok": True, "subs_used": used+1, "subs_limit": limit})

# ---------------- Socket.IO ----------------
@socketio.on("connect")
def on_connect(): emit("state_update", state)

@socketio.on("select_context")
def on_select_context(data):
    state["tournament_id"] = data.get("tournament_id")
    state["match_id"] = data.get("match_id")
    if state["match_id"]: load_match_names(state["match_id"])
    broadcast()

@socketio.on("mode")
def on_mode(data):
    mode = data.get("mode")
    if mode in ("intro","partido","tiempo_fuera","entre_sets","publicidad"):
        state["mode"] = mode
        log_event(state["match_id"], state["set_number"], f"MODE_{mode.upper()}", {})
        broadcast()

@socketio.on("theme")
def on_theme(data):
    theme = data.get("theme")
    if theme in ("light","dark"): state["theme"] = theme; broadcast()

@socketio.on("update_names")
def on_update_names(data):
    state["home_name"] = (data.get("home_name") or state["home_name"])[:24]
    state["away_name"] = (data.get("away_name") or state["away_name"])[:24]
    broadcast()

@socketio.on("point")
def on_point(data):
    team = data.get("team"); amt = int(data.get("amount",1))
    if team == "home":
        state["home_points"] = max(0, state["home_points"] + amt)
        log_event(state["match_id"], state["set_number"], "POINT_HOME", {"delta": amt})
    elif team == "away":
        state["away_points"] = max(0, state["away_points"] + amt)
        log_event(state["match_id"], state["set_number"], "POINT_AWAY", {"delta": amt})
    broadcast()

@socketio.on("set_point")
def on_set_point(data):
    team = data.get("team"); amt = int(data.get("amount",1))
    if team == "home": state["home_sets"] = max(0, state["home_sets"] + amt)
    elif team == "away": state["away_sets"] = max(0, state["away_sets"] + amt)
    broadcast()

@socketio.on("next_set")
def on_next_set():
    hp, ap = state["home_points"], state["away_points"]
    if hp == ap:
        emit("tie_on_set_end", {"home_points": hp, "away_points": ap}); return
    winner = "home" if hp > ap else "away"
    if winner == "home": state["home_sets"] += 1
    else: state["away_sets"] += 1
    log_event(state["match_id"], state["set_number"], "END_SET", {"winner": winner, "home_points": hp, "away_points": ap})
    state["home_points"] = 0; state["away_points"] = 0; state["set_number"] += 1
    log_event(state["match_id"], state["set_number"], "START_SET", {})
    # nuevo set -> contador de subs se inicia en 0 automáticamente por set_number
    broadcast()

@socketio.on("timer")
def on_timer(data):
    action = data.get("action")
    if action == "start": state["timer_running"] = True
    elif action == "stop": state["timer_running"] = False
    elif action == "reset": state["timer_running"] = False; state["timer_seconds"] = 0
    elif action == "set":
        try: state["timer_seconds"] = max(0, int(data.get("seconds", 0)))
        except Exception: pass
    broadcast()

@socketio.on("tick")
def on_tick():
    if state["timer_running"] and state["timer_seconds"] > 0:
        state["timer_seconds"] -= 1; broadcast()

@socketio.on("ads_toggle")
def on_ads_toggle(data):
    state["ads_enabled"] = bool(data.get("enabled", False)); broadcast()

@socketio.on("intro_update")
def on_intro_update(data):
    state["intro_title"] = (data.get("intro_title") or state["intro_title"])[:120]
    state["intro_subtitle"] = (data.get("intro_subtitle") or state["intro_subtitle"])[:160]
    state["intro_extra"] = (data.get("intro_extra") or state["intro_extra"])[:200]
    broadcast()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f" * Running http://0.0.0.0:{port} (async_mode={async_mode})")
    socketio.run(app, host="0.0.0.0", port=port)
