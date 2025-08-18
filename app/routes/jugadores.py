from flask import Blueprint, jsonify, request

from ..models import get_session, Player


jugadores_bp = Blueprint("jugadores", __name__)


@jugadores_bp.get("/")
def listar_jugadores():
    team_id = request.args.get("team_id", type=int)
    if not team_id:
        return jsonify([])
    with get_session() as session:
        players = (
            session.query(Player)
            .filter(Player.team_id == team_id)
            .order_by(Player.libero.desc(), Player.number)
            .all()
        )
        rows = [
            {
                "id": p.id,
                "number": p.number,
                "name": p.name,
                "role": p.role,
                "libero": bool(p.libero),
            }
            for p in players
        ]
    return jsonify(rows)
