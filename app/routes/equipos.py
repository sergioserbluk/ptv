from flask import Blueprint, jsonify

from ..models import get_session, Team


equipos_bp = Blueprint("equipos", __name__)


@equipos_bp.get("/")
def listar_equipos():
    with get_session() as session:
        teams = session.query(Team).order_by(Team.name.asc()).all()
        rows = [
            {"id": t.id, "name": t.name, "short": t.short}
            for t in teams
        ]
    return jsonify(rows)
