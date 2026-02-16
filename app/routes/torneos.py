from flask import Blueprint, jsonify, request




torneos_bp = Blueprint("torneos", __name__)


def _validate_tournament_payload(data):
    for field in ("name", "type"):
        if field not in data or not isinstance(data[field], str):
            raise APIError(f"'{field}' is required", 400)
    if "ruleset_id" not in data or not isinstance(data["ruleset_id"], int):
        raise APIError("'ruleset_id' is required and must be int", 400)
    if "season" in data and data["season"] is not None and not isinstance(data["season"], str):
        raise APIError("'season' must be a string", 400)
    if "meta_json" in data and data["meta_json"] is not None and not isinstance(data["meta_json"], dict):
        raise APIError("'meta_json' must be an object", 400)


@torneos_bp.get("/")
def listar_torneos():
    return jsonify({"torneos": []})
