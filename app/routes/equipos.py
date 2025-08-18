from flask import Blueprint, jsonify

from ..models import get_db


equipos_bp = Blueprint("equipos", __name__)


@equipos_bp.get("/")
def listar_equipos():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, short FROM teams ORDER BY name ASC")
    rows = [{"id": r[0], "name": r[1], "short": r[2]} for r in c.fetchall()]
    conn.close()
    return jsonify(rows)
