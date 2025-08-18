from typing import Any, Dict, List
import json

from ..models import get_db
from ..errors import APIError


def list_tournaments() -> List[Dict[str, Any]]:
    conn = get_db()
    c = conn.cursor()
    c.execute(
        """SELECT t.id, t.name, t.season, r.name, t.type, t.meta_json, t.ruleset_id
                 FROM tournaments t JOIN rulesets r ON r.id=t.ruleset_id
                 ORDER BY t.id DESC"""
    )
    rows = [
        {
            "id": r[0],
            "name": r[1],
            "season": r[2],
            "ruleset": r[3],
            "type": r[4],
            "meta_json": json.loads(r[5] or "{}"),
            "ruleset_id": r[6],
        }
        for r in c.fetchall()
    ]
    conn.close()
    return rows


def create_tournament(data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_db()
    c = conn.cursor()
    c.execute(
        """INSERT INTO tournaments(name, season, ruleset_id, type, meta_json)
                 VALUES (?,?,?,?,?)""",
        (
            data["name"],
            data.get("season"),
            data["ruleset_id"],
            data["type"],
            json.dumps(data.get("meta_json") or {}),
        ),
    )
    conn.commit()
    tid = c.lastrowid
    conn.close()
    return {"id": tid, **data}


def update_tournament(tid: int, data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_db()
    c = conn.cursor()
    c.execute(
        """UPDATE tournaments
                 SET name=?, season=?, ruleset_id=?, type=?, meta_json=?
                 WHERE id=?""",
        (
            data["name"],
            data.get("season"),
            data["ruleset_id"],
            data["type"],
            json.dumps(data.get("meta_json") or {}),
            tid,
        ),
    )
    if c.rowcount == 0:
        conn.close()
        raise APIError("Tournament not found", 404)
    conn.commit()
    conn.close()
    return {"id": tid, **data}


def delete_tournament(tid: int) -> None:
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM tournaments WHERE id=?", (tid,))
    if c.rowcount == 0:
        conn.close()
        raise APIError("Tournament not found", 404)
    conn.commit()
    conn.close()
