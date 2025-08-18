from flask import Blueprint, jsonify

from ..models import get_db


torneos_bp = Blueprint("torneos", __name__)


@torneos_bp.get("/")
def listar_torneos():
    conn = get_db()
    c = conn.cursor()
    c.execute(
        """SELECT t.id, t.name, t.season, r.name, t.type
                 FROM tournaments t JOIN rulesets r ON r.id=t.ruleset_id
                 ORDER BY t.id DESC"""
    )
    rows = [
        {"id": r[0], "name": r[1], "season": r[2], "ruleset": r[3], "type": r[4]}
        for r in c.fetchall()
    ]
    conn.close()
    return jsonify(rows)
