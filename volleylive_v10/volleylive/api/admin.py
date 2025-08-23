from flask import Blueprint, request, jsonify
from ..services.util_db import get_db

bp = Blueprint("admin", __name__)

@bp.post("/team")
def create_team():
    d = request.get_json(force=True)
    name = (d.get("name") or "").strip()
    short = (d.get("short") or "").strip() or None
    if not name: return jsonify({"error":"name requerido"}), 400
    conn = get_db(); c = conn.cursor()
    c.execute("INSERT INTO teams(name,short) VALUES (?,?)", (name,short))
    team_id = c.lastrowid
    conn.commit(); conn.close()
    return jsonify({"ok": True, "id": team_id})

@bp.post("/player")
def create_player():
    d = request.get_json(force=True)
    team_id = d.get("team_id"); name = (d.get("name") or "").strip()
    number = d.get("number"); role = (d.get("role") or "").strip() or None
    libero = 1 if d.get("libero") else 0
    if not (team_id and name): return jsonify({"error":"team_id y name requeridos"}), 400
    conn = get_db(); c = conn.cursor()
    c.execute("INSERT INTO players(team_id,number,name,role,libero) VALUES (?,?,?,?,?)", (team_id,number,name,role,libero))
    pid = c.lastrowid
    conn.commit(); conn.close()
    return jsonify({"ok": True, "id": pid})

@bp.post("/match")
def create_match():
    import json, datetime
    d = request.get_json(force=True)
    tournament_id = d.get("tournament_id")
    home_id = d.get("home_id")
    away_id = d.get("away_id")
    date = d.get("date") or datetime.datetime.now().isoformat()
    gym = (d.get("gym") or "").strip() or None
    if not (tournament_id and home_id and away_id): return jsonify({"error":"tournament_id, home_id, away_id requeridos"}), 400
    if home_id == away_id: return jsonify({"error":"home y away iguales"}), 400
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT r.json FROM tournaments t JOIN rulesets r ON r.id=t.ruleset_id WHERE t.id=?", (tournament_id,))
    r = c.fetchone()
    if not r: conn.close(); return jsonify({"error":"tournament inválido"}), 400
    snap = r[0]
    c.execute("""INSERT INTO matches(tournament_id,home_id,away_id,date,gym,status,rules_snapshot_json)
                 VALUES (?,?,?,?,?,?,?)""", (tournament_id,home_id,away_id,date,gym,"scheduled",snap))
    mid = c.lastrowid
    for tid_team in (home_id, away_id):
        c.execute("SELECT 1 FROM tournament_teams WHERE tournament_id=? AND team_id=?", (tournament_id, tid_team))
        if c.fetchone() is None:
            c.execute("INSERT INTO tournament_teams(tournament_id,team_id) VALUES (?,?)", (tournament_id, tid_team))
    conn.commit(); conn.close()
    return jsonify({"ok": True, "id": mid})
