from flask import Blueprint, request, jsonify
from ..services.util_db import get_db
from ..services.lineup_service import get_team_players, get_lineup, set_lineup, do_sub

bp = Blueprint("lineup", __name__)

@bp.get("/match_teams")
def match_teams():
    mid = request.args.get("match_id", type=int)
    if not mid: return jsonify({"error":"match_id requerido"}), 400
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT home_id,away_id FROM matches WHERE id=?", (mid,))
    r = c.fetchone(); conn.close()
    if not r: return jsonify({"error":"partido no encontrado"}), 404
    return jsonify({"home_id": r[0], "away_id": r[1]})

@bp.get("/team_players")
def team_players():
    tid = request.args.get("team_id", type=int)
    return jsonify(get_team_players(tid) if tid else [])

@bp.get("/lineup")
def lineup_get():
    mid = request.args.get("match_id", type=int)
    setn = request.args.get("set_number", type=int)
    team = request.args.get("team")
    if not (mid and setn and team in ("home","away")): return jsonify({"error":"params"}), 400
    return jsonify(get_lineup(mid, setn, team))

@bp.post("/lineup")
def lineup_set():
    d = request.get_json(force=True)
    mid = d.get("match_id"); setn = d.get("set_number")
    team = d.get("team"); players = d.get("players") or []; libero_id = d.get("libero_id")
    if not (mid and setn and team in ("home","away") and isinstance(players,list) and len(players)==6):
        return jsonify({"error":"params"}), 400
    return jsonify(set_lineup(mid, setn, team, players, libero_id))

@bp.post("/sub")
def sub_do():
    d = request.get_json(force=True)
    mid = d.get("match_id"); setn = d.get("set_number"); team = d.get("team")
    out_id = d.get("out_id"); in_id = d.get("in_id")
    if not all([mid,setn,team in ("home","away"),out_id,in_id]):
        return jsonify({"error":"params"}), 400
    res = do_sub(mid, setn, team, out_id, in_id)
    return (jsonify(res), 200) if res.get("ok") else (jsonify(res), 400)
