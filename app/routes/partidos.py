from flask import Blueprint, jsonify, request
from sqlalchemy.orm import aliased

from ..models import get_session, Match, Team


partidos_bp = Blueprint("partidos", __name__)


@partidos_bp.get("/")
def listar_partidos():
    tid = request.args.get("tournament_id", type=int)
    with get_session() as session:
        home = aliased(Team)
        away = aliased(Team)
        query = (
            session.query(Match, home, away)
            .join(home, Match.home_id == home.id)
            .join(away, Match.away_id == away.id)
        )
        if tid:
            query = query.filter(Match.tournament_id == tid)
        matches = query.order_by(Match.id.desc()).all()
        rows = [
            {
                "id": m.id,
                "label": f"{h.name} vs {a.name}",
                "status": m.status,
                "date": m.date,
            }
            for m, h, a in matches
        ]
    return jsonify(rows)


@partidos_bp.get("/equipos")
def obtener_equipos_partido():
    mid = request.args.get("match_id", type=int)
    if not mid:
        return jsonify({"error": "match_id requerido"}), 400
    with get_session() as session:
        match = session.get(Match, mid)
        if not match:
            return jsonify({"error": "partido no encontrado"}), 404
        return jsonify({"home_id": match.home_id, "away_id": match.away_id})
