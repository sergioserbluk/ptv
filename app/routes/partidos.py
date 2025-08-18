from flask import Blueprint, jsonify, request

from ..models import get_db


partidos_bp = Blueprint("partidos", __name__)


@partidos_bp.get("/")
def listar_partidos():
    tid = request.args.get("tournament_id", type=int)
    conn = get_db()
    c = conn.cursor()
    if tid:
        c.execute(
            """SELECT m.id, th.name, ta.name, m.status, m.date FROM matches m
                     JOIN teams th ON th.id=m.home_id
                     JOIN teams ta ON ta.id=m.away_id
                     WHERE m.tournament_id=? ORDER BY m.id DESC""",
            (tid,),
        )
    else:
        c.execute(
            """SELECT m.id, th.name, ta.name, m.status, m.date FROM matches m
                     JOIN teams th ON th.id=m.home_id
                     JOIN teams ta ON ta.id=m.away_id
                     ORDER BY m.id DESC"""
        )
    rows = [
        {"id": r[0], "label": f"{r[1]} vs {r[2]}", "status": r[3], "date": r[4]}
        for r in c.fetchall()
    ]
    conn.close()
    return jsonify(rows)


@partidos_bp.get("/equipos")
def obtener_equipos_partido():
    mid = request.args.get("match_id", type=int)
    if not mid:
        return jsonify({"error": "match_id requerido"}), 400
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT home_id, away_id FROM matches WHERE id=?", (mid,))
    r = c.fetchone()
    conn.close()
    if not r:
        return jsonify({"error": "partido no encontrado"}), 404
    return jsonify({"home_id": r[0], "away_id": r[1]})
