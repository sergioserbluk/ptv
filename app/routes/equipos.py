from flask import Blueprint, jsonify, request




equipos_bp = Blueprint("equipos", __name__)


def _validate_team_payload(data):
    if "name" not in data or not isinstance(data["name"], str):
        raise APIError("'name' is required", 400)
    for field in ("short", "colors", "logo_url"):
        if field in data and data[field] is not None and not isinstance(data[field], str):
            raise APIError(f"'{field}' must be a string", 400)


@equipos_bp.get("/")
def listar_equipos():
    return jsonify({"equipos": []})

