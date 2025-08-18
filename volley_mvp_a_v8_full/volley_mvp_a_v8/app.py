
import os, sqlite3, json, csv, io, datetime
from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit

DB_PATH = os.path.join(os.path.dirname(__file__), "matches.db")

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SECRET_KEY"] = "change-me"

try:
    import eventlet  # noqa: F401
    async_mode = "eventlet"
except Exception:
    async_mode = "threading"

socketio = SocketIO(app, cors_allowed_origins="*", async_mode=async_mode)

def get_db():
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row; return conn

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
    CREATE TABLE IF NOT EXISTS lineups (
        id INTEGER PRIMARY KEY,
        match_id INTEGER NOT NULL,
        set_number INTEGER NOT NULL,
        team_id INTEGER NOT NULL,
        p1 INTEGER, p2 INTEGER, p3 INTEGER, p4 INTEGER, p5 INTEGER, p6 INTEGER,
        libero_id INTEGER,
        UNIQUE(match_id, set_number, team_id)
    );
    """)
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
        c.execute("INSERT INTO teams(name, short) VALUES (?,?)", ("Iberá V.C.", "IBR"))
        home_id = c.lastrowid
        c.execute("INSERT INTO teams(name, short) VALUES (?,?)", ("Independiente", "IND"))
        away_id = c.lastrowid
        c.execute("INSERT INTO tournaments(name, season, ruleset_id, type, meta_json) VALUES (?,?,?,?,?)",
                  ("Liga Local 2025", "2025", ruleset_id, "round_robin", "{}"))
        tournament_id = c.lastrowid
        c.execute("INSERT INTO tournament_teams(tournament_id, team_id) VALUES (?,?)", (tournament_id, home_id))
        c.execute("INSERT INTO tournament_teams(tournament_id, team_id) VALUES (?,?)", (tournament_id, away_id))
        c.execute("""INSERT INTO matches(tournament_id, home_id, away_id, date, gym, status, rules_snapshot_json)
                     VALUES (?,?,?,?,?,?,?)""",
                  (tournament_id, home_id, away_id, "2025-08-16T18:00:00", "Polideportivo", "scheduled", json.dumps(rules)))
        for num, name in [(1,"Local 1"),(2,"Local 2"),(3,"Local 3"),(4,"Local 4"),(5,"Local 5"),(6,"Local 6"),(12,"Líbero Local")]:
            c.execute("INSERT INTO players(team_id, number, name, role, libero) VALUES (?,?,?,?,?)",
                      (home_id, num, name, None, 1 if num==12 else 0))
        for num, name in [(7,"Visita 1"),(8,"Visita 2"),(9,"Visita 3"),(10,"Visita 4"),(11,"Visita 5"),(13,"Visita 6"),(14,"Líbero Visita")]:
            c.execute("INSERT INTO players(team_id, number, name, role, libero) VALUES (?,?,?,?,?)",
                      (away_id, num, name, None, 1 if num==14 else 0))
    conn.commit(); conn.close()

init_db()

state = {
    "mode": "intro","theme":"dark",
    "home_name":"Local","away_name":"Visitante",
    "home_points":0,"away_points":0,
    "home_sets":0,"away_sets":0,"set_number":1,
    "timer_running":False,"timer_seconds":0,
    "ads_enabled":True,
    "intro_title":"Fecha 5 - Liga Local",
    "intro_subtitle":"Iberá V.C. vs Independiente",
    "intro_extra":"Cancha: Polideportivo · 20:00",
    "match_id":None,"tournament_id":None,
    "home_team_id":None,"away_team_id":None,
    "on_court":{"home":[],"away":[]},
    "liberos":{"home":None,"away":None},
    "subs_count":{"home":0,"away":0},
    "rules":{}
}

def broadcast(): socketio.emit("state_update", state)

def log_event(match_id, set_number, ev_type, payload):
    if not match_id: return
    conn = get_db(); c = conn.cursor()
    c.execute("""INSERT INTO events(match_id, set_number, ts, type, payload_json)
                 VALUES (?,?,?,?,?)""", (match_id, set_number, datetime.datetime.now().isoformat(), ev_type, json.dumps(payload or {})))
    conn.commit(); conn.close()

def load_match_basics(match_id):
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT m.home_id, m.away_id, th.name, ta.name, m.rules_snapshot_json
                 FROM matches m
                 JOIN teams th ON th.id=m.home_id
                 JOIN teams ta ON ta.id=m.away_id
                 WHERE m.id=?""", (match_id,))
    r = c.fetchone(); conn.close()
    if not r: return None
    state["home_team_id"], state["away_team_id"], state["home_name"], state["away_name"] = r[0], r[1], r[2], r[3]
    try: state["rules"] = json.loads(r[4]) if r[4] else {}
    except: state["rules"] = {}
    return True

def get_rules_value(key, default=None):
    return (state.get("rules") or {}).get(key, default)

def save_lineup(match_id, set_number, team_id, players6, libero_id):
    conn = get_db(); c = conn.cursor()
    c.execute("""INSERT INTO lineups(match_id,set_number,team_id,p1,p2,p3,p4,p5,p6,libero_id)
                 VALUES (?,?,?,?,?,?,?,?,?,?)
                 ON CONFLICT(match_id,set_number,team_id) DO UPDATE SET
                   p1=excluded.p1,p2=excluded.p2,p3=excluded.p3,p4=excluded.p4,p5=excluded.p5,p6=excluded.p6,libero_id=excluded.libero_id"""
                 , (match_id,set_number,team_id,*(players6+[libero_id])))
    conn.commit(); conn.close()

def load_lineup(match_id, set_number, team_id):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT p1,p2,p3,p4,p5,p6,libero_id FROM lineups WHERE match_id=? AND set_number=? AND team_id=?",
              (match_id,set_number,team_id))
    r = c.fetchone(); conn.close()
    if not r: return None
    return {"players":[r[0],r[1],r[2],r[3],r[4],r[5]], "libero_id": r[6]}

def players_by_team(team_id):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id, number, name, role, libero FROM players WHERE team_id=? ORDER BY number IS NULL, number", (team_id,))
    rows = [{"id": rr[0], "number": rr[1], "name": rr[2], "role": rr[3], "libero": bool(rr[4])} for rr in c.fetchall()]
    conn.close(); return rows

def count_subs_in_set(match_id, set_number, team_key):
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT COUNT(*) FROM events
                 WHERE match_id=? AND set_number=? AND type='SUB' AND json_extract(payload_json,'$.team')=?""",
              (match_id,set_number,team_key))
    n = c.fetchone()[0]; conn.close(); return n

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

@app.route("/api/tournaments")
def api_tournaments():
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT t.id, t.name, t.season, r.name, t.type
                 FROM tournaments t JOIN rulesets r ON r.id=t.ruleset_id
                 ORDER BY t.id DESC""")
    rows = [{"id": r[0], "name": r[1], "season": r[2], "ruleset": r[3], "type": r[4]} for r in c.fetchall()]
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

@app.route("/api/match/<int:match_id>")
def api_match_info(match_id):
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT m.id, m.home_id, m.away_id, th.name, ta.name, m.rules_snapshot_json
                 FROM matches m
                 JOIN teams th ON th.id=m.home_id
                 JOIN teams ta ON ta.id=m.away_id
                 WHERE m.id=?""", (match_id,))
    r = c.fetchone(); conn.close()
    if not r: return jsonify({"error":"match no encontrado"}), 404
    return jsonify({"id": r[0], "home_id": r[1], "away_id": r[2], "home_name": r[3], "away_name": r[4], "rules": json.loads(r[5]) if r[5] else {}})

@app.route("/api/players")
def api_players():
    team_id = request.args.get("team_id", type=int)
    if not team_id: return jsonify([])
    return jsonify(players_by_team(team_id))

@app.route("/api/lineup")
def api_get_lineup():
    match_id = request.args.get("match_id", type=int)
    set_number = request.args.get("set_number", type=int)
    team_id = request.args.get("team_id", type=int)
    if not (match_id and set_number and team_id): return jsonify({"error":"params requeridos"}), 400
    lu = load_lineup(match_id, set_number, team_id)
    if not lu: return jsonify({"players": [], "libero_id": None})
    return jsonify(lu)

@app.route("/api/subs_count")
def api_subs_count():
    match_id = request.args.get("match_id", type=int)
    set_number = request.args.get("set_number", type=int)
    team = request.args.get("team")
    if not (match_id and set_number and team): return jsonify({"error":"params requeridos"}), 400
    n = count_subs_in_set(match_id, set_number, team)
    limit = get_rules_value("subs_per_set", 6)
    return jsonify({"count": n, "limit": limit})

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

@socketio.on("connect")
def on_connect(): emit("state_update", state)

@socketio.on("select_context")
def on_select_context(data):
    state["tournament_id"] = data.get("tournament_id")
    state["match_id"] = data.get("match_id")
    if state["match_id"]:
        load_match_basics(state["match_id"])
        # cargar lineup guardado para set actual si existe
        hlu = load_lineup(state["match_id"], state["set_number"], state["home_team_id"])
        alu = load_lineup(state["match_id"], state["set_number"], state["away_team_id"])
        state["on_court"]["home"] = (hlu["players"] if hlu else [])
        state["on_court"]["away"] = (alu["players"] if alu else [])
        state["liberos"]["home"] = (hlu["libero_id"] if hlu else None)
        state["liberos"]["away"] = (alu["libero_id"] if alu else None)
        state["subs_count"]["home"] = count_subs_in_set(state["match_id"], state["set_number"], "home")
        state["subs_count"]["away"] = count_subs_in_set(state["match_id"], state["set_number"], "away")
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
    state["on_court"]["home"] = []; state["on_court"]["away"] = []
    state["liberos"]["home"] = None; state["liberos"]["away"] = None
    state["subs_count"]["home"] = 0; state["subs_count"]["away"] = 0
    log_event(state["match_id"], state["set_number"], "START_SET", {})
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

@socketio.on("set_lineup")
def on_set_lineup(data):
    team_key = data.get("team")
    players = data.get("players") or []
    libero_id = data.get("libero_id")
    set_number = int(data.get("set_number") or state["set_number"])
    if team_key not in ("home","away"): return
    if len(players) != 6:
        emit("error_msg", {"msg": "Debe seleccionar 6 jugadores para el sexteto"}); return
    team_id = state["home_team_id"] if team_key=="home" else state["away_team_id"]
    match_id = state["match_id"]
    # validar pertenencia
    team_players = {p["id"] for p in players_by_team(team_id)}
    if not all(pid in team_players for pid in players):
        emit("error_msg", {"msg": "Hay jugadores que no pertenecen al equipo"}); return
    if libero_id and libero_id not in team_players:
        emit("error_msg", {"msg": "El líbero no pertenece al equipo"}); return
    save_lineup(match_id, set_number, team_id, players, libero_id)
    state["on_court"][team_key] = players[:]
    state["liberos"][team_key] = libero_id
    log_event(match_id, set_number, "LINEUP_SET", {"team": team_key, "players": players, "libero_id": libero_id})
    broadcast()

@socketio.on("substitution")
def on_substitution(data):
    team_key = data.get("team")
    out_id = data.get("out_id")
    in_id = data.get("in_id")
    set_number = state["set_number"]
    match_id = state["match_id"]
    if team_key not in ("home","away"): return
    on_court = state["on_court"][team_key]
    if out_id not in on_court:
        emit("error_msg", {"msg": "El jugador que sale no está en cancha"}); return
    if in_id in on_court:
        emit("error_msg", {"msg": "El jugador que entra ya está en cancha"}); return
    limit = get_rules_value("subs_per_set", 6)
    current = count_subs_in_set(match_id, set_number, team_key)
    if current >= limit:
        emit("error_msg", {"msg": f"Límite de sustituciones alcanzado ({limit})"}); return
    # pertenencia
    team_id = state["home_team_id"] if team_key=="home" else state["away_team_id"]
    tplayers = {p["id"] for p in players_by_team(team_id)}
    if in_id not in tplayers or out_id not in tplayers:
        emit("error_msg", {"msg": "IDs de jugador inválidos para el equipo"}); return
    state["on_court"][team_key] = [in_id if pid==out_id else pid for pid in on_court]
    state["subs_count"][team_key] = current + 1
    log_event(match_id, set_number, "SUB", {"team": team_key, "out": out_id, "in": in_id})
    broadcast()

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
