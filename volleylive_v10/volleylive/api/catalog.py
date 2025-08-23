from flask import Blueprint, jsonify, request
from ..services.util_db import get_db

bp = Blueprint("catalog", __name__)

@bp.get("/rulesets")
def rulesets():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id, name FROM rulesets ORDER BY id DESC")
    out = [{"id":r[0], "name":r[1]} for r in c.fetchall()]
    conn.close(); return jsonify(out)

@bp.get("/tournaments")
def tournaments():
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT t.id, t.name, t.season, r.name, t.type
                 FROM tournaments t JOIN rulesets r ON r.id=t.ruleset_id
                 ORDER BY t.id DESC""")
    out = [{"id":r[0],"name":r[1],"season":r[2],"ruleset":r[3],"type":r[4]} for r in c.fetchall()]
    conn.close(); return jsonify(out)

@bp.get("/teams")
def teams():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id,name,short FROM teams ORDER BY name")
    out = [{"id":r[0],"name":r[1],"short":r[2]} for r in c.fetchall()]
    conn.close(); return jsonify(out)

@bp.get("/players")
def players():
    team_id = request.args.get("team_id", type=int)
    if not team_id: return jsonify([])
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id,number,name,role,libero FROM players WHERE team_id=? ORDER BY (libero DESC), number", (team_id,))
    out = [{"id":r[0],"number":r[1],"name":r[2],"role":r[3],"libero":bool(r[4])} for r in c.fetchall()]
    conn.close(); return jsonify(out)

@bp.get("/matches")
def matches():
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
    out = [{"id":r[0], "label": f"{r[1]} vs {r[2]}", "status": r[3], "date": r[4]} for r in c.fetchall()]
    conn.close(); return jsonify(out)

