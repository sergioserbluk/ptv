from flask import Blueprint, jsonify

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/ping')
def ping():
    return jsonify({"msg": "pong"})
