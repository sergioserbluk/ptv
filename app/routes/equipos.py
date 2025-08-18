from flask import Blueprint, jsonify, request

from ..services import teams as team_service
from ..errors import APIError


equipos_bp = Blueprint("equipos", __name__)


def _validate_team_payload(data):
    if "name" not in data or not isinstance(data["name"], str):
        raise APIError("'name' is required", 400)
    for field in ("short", "colors", "logo_url"):
        if field in data and data[field] is not None and not isinstance(data[field], str):
            raise APIError(f"'{field}' must be a string", 400)


@equipos_bp.get("/")
def listar_equipos():
    return jsonify({"data": team_service.list_teams()})


@equipos_bp.post("/")
def crear_equipo():
    data = request.get_json() or {}
    _validate_team_payload(data)
    team = team_service.create_team(data)
    return jsonify({"data": team}), 201


@equipos_bp.put("/<int:team_id>")
def actualizar_equipo(team_id: int):
    data = request.get_json() or {}
    _validate_team_payload(data)
    team = team_service.update_team(team_id, data)
    return jsonify({"data": team})


@equipos_bp.delete("/<int:team_id>")
def eliminar_equipo(team_id: int):
    team_service.delete_team(team_id)
    return jsonify({"status": "success", "message": "deleted"})
