from flask import Blueprint, jsonify, request

from ..models import get_db


jugadores_bp = Blueprint("jugadores", __name__)


@jugadores_bp.get("/")
def listar_jugadores():
    team_id = request.args.get("team_id", type=int)
    if not team_id:
        return jsonify([])
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT id, number, name, role, libero FROM players WHERE team_id=? ORDER BY (libero DESC), number",
        (team_id,),
    )
    rows = [
        {"id": r[0], "number": r[1], "name": r[2], "role": r[3], "libero": bool(r[4])}
        for r in c.fetchall()
    ]
    conn.close()
    return jsonify(rows)
