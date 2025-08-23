import json
from .util_db import get_db
from .state import rules_for_match, log_event

def get_team_players(team_id):
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT id, number, name, role, libero
                 FROM players
                 WHERE team_id=? ORDER BY (libero DESC), number""", (team_id,))
    rows = [{"id":r[0], "number":r[1], "name":r[2], "role":r[3], "libero": bool(r[4])} for r in c.fetchall()]
    conn.close()
    return rows

def get_lineup(match_id, set_number, team):
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT players_json, libero_id
                 FROM lineups
                 WHERE match_id=? AND set_number=? AND team=?""",
              (match_id, set_number, team))
    row = c.fetchone()
    players = json.loads(row[0]) if row else []
    libero_id = row[1] if row else None

    c.execute("""SELECT used FROM subs_counter
                 WHERE match_id=? AND set_number=? AND team=?""",
              (match_id, set_number, team))
    r2 = c.fetchone()
    used = r2[0] if r2 else 0
    limit = rules_for_match(match_id).get("subs_per_set", 6)

    conn.close()
    return {"players": players, "libero_id": libero_id, "subs_used": used, "subs_limit": limit}

def set_lineup(match_id, set_number, team, players, libero_id):
    # players debe tener 6 ids de jugador
    conn = get_db(); c = conn.cursor()
    c.execute("""INSERT INTO lineups(match_id,set_number,team,players_json,libero_id)
                 VALUES (?,?,?,?,?)
                 ON CONFLICT(match_id,set_number,team)
                 DO UPDATE SET players_json=excluded.players_json, libero_id=excluded.libero_id""",
              (match_id, set_number, team, json.dumps(players), libero_id))
    # contador de sustituciones (si no existe)
    c.execute("""INSERT INTO subs_counter(match_id,set_number,team,used)
                 VALUES (?,?,?,0)
                 ON CONFLICT(match_id,set_number,team) DO NOTHING""",
              (match_id, set_number, team))
    conn.commit(); conn.close()

    log_event(match_id, set_number, "LINEUP_SET",
              {"team": team, "players": players, "libero_id": libero_id})
    return {"ok": True}

def do_sub(match_id, set_number, team, out_id, in_id):
    conn = get_db(); c = conn.cursor()
    # lineup actual
    c.execute("""SELECT players_json FROM lineups
                 WHERE match_id=? AND set_number=? AND team=?""",
              (match_id, set_number, team))
    row = c.fetchone()
    if not row:
        conn.close(); return {"ok": False, "error": "no hay sexteto cargado"}
    players = json.loads(row[0])

    if out_id not in players:
        conn.close(); return {"ok": False, "error": "el que sale no está en cancha"}
    if in_id in players:
        conn.close(); return {"ok": False, "error": "el que entra ya está en cancha"}

    # límite de sustituciones
    c.execute("""SELECT used FROM subs_counter
                 WHERE match_id=? AND set_number=? AND team=?""",
              (match_id, set_number, team))
    r2 = c.fetchone()
    used = r2[0] if r2 else 0
    limit = rules_for_match(match_id).get("subs_per_set", 6)
    if used >= limit:
        conn.close(); return {"ok": False, "error": "límite de sustituciones alcanzado"}

    # aplicar cambio
    players = [in_id if pid == out_id else pid for pid in players]
    c.execute("""UPDATE lineups SET players_json=?
                 WHERE match_id=? AND set_number=? AND team=?""",
              (json.dumps(players), match_id, set_number, team))
    c.execute("""INSERT INTO subs_counter(match_id,set_number,team,used) VALUES (?,?,?,1)
                 ON CONFLICT(match_id,set_number,team) DO UPDATE SET used=used+1""",
              (match_id, set_number, team))
    conn.commit(); conn.close()

    log_event(match_id, set_number, "SUB",
              {"team": team, "out": out_id, "in": in_id})
    return {"ok": True, "subs_used": used+1, "subs_limit": limit}
