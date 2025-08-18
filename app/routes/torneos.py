from flask import Blueprint, jsonify

from ..models import get_session, Tournament, Ruleset


torneos_bp = Blueprint("torneos", __name__)


@torneos_bp.get("/")
def listar_torneos():
    with get_session() as session:
        torneos = (
            session.query(Tournament)
            .join(Ruleset)
            .order_by(Tournament.id.desc())
            .all()
        )
        rows = [
            {
                "id": t.id,
                "name": t.name,
                "season": t.season,
                "ruleset": t.ruleset.name,
                "type": t.type,
            }
            for t in torneos
        ]
    return jsonify(rows)
