from typing import Any, Dict, List

from ..models import get_db
from ..errors import APIError


def list_teams() -> List[Dict[str, Any]]:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, short, colors, logo_url FROM teams ORDER BY name ASC")
    rows = [
        {"id": r[0], "name": r[1], "short": r[2], "colors": r[3], "logo_url": r[4]}
        for r in c.fetchall()
    ]
    conn.close()
    return rows


def create_team(data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO teams(name, short, colors, logo_url) VALUES (?,?,?,?)",
        (data["name"], data.get("short"), data.get("colors"), data.get("logo_url")),
    )
    conn.commit()
    team_id = c.lastrowid
    conn.close()
    return {"id": team_id, **data}


def update_team(team_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "UPDATE teams SET name=?, short=?, colors=?, logo_url=? WHERE id=?",
        (
            data["name"],
            data.get("short"),
            data.get("colors"),
            data.get("logo_url"),
            team_id,
        ),
    )
    if c.rowcount == 0:
        conn.close()
        raise APIError("Team not found", 404)
    conn.commit()
    conn.close()
    return {"id": team_id, **data}


def delete_team(team_id: int) -> None:
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM teams WHERE id=?", (team_id,))
    if c.rowcount == 0:
        conn.close()
        raise APIError("Team not found", 404)
    conn.commit()
    conn.close()
