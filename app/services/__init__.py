import datetime
import json
from typing import Any, Dict

from ..models import get_db

socketio = None

state: Dict[str, Any] = {
    "mode": "intro",
    "theme": "dark",
    "home_name": "Local",
    "away_name": "Visitante",
    "home_points": 0,
    "away_points": 0,
    "home_sets": 0,
    "away_sets": 0,
    "set_number": 1,
    "timer_running": False,
    "timer_seconds": 0,
    "ads_enabled": True,
    "intro_title": "Fecha 5 - Liga Local",
    "intro_subtitle": "Iberá V.C. vs Independiente",
    "intro_extra": "Cancha: Polideportivo · 20:00",
    "match_id": None,
    "tournament_id": None,
}


def set_socketio(sock):
    global socketio
    socketio = sock


def broadcast():
    if socketio:
        socketio.emit("state_update", state)


def log_event(match_id, set_number, ev_type, payload):
    if not match_id:
        return
    conn = get_db()
    c = conn.cursor()
    c.execute(
        """INSERT INTO events(match_id, set_number, ts, type, payload_json)
                 VALUES (?,?,?,?,?)""",
        (
            match_id,
            set_number,
            datetime.datetime.now().isoformat(),
            ev_type,
            json.dumps(payload or {}),
        ),
    )
    conn.commit()
    conn.close()


def load_match_names(match_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute(
            """SELECT th.name, ta.name FROM matches m
                     JOIN teams th ON th.id=m.home_id
                     JOIN teams ta ON ta.id=m.away_id
                     WHERE m.id=?""",
            (match_id,),
        )
        r = c.fetchone()
        if r:
            state["home_name"], state["away_name"] = r[0], r[1]
        conn.close()
    except Exception:
        pass


def rules_for_match(match_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT rules_snapshot_json FROM matches WHERE id=?", (match_id,))
    r = c.fetchone()
    conn.close()
    if not r or not r[0]:
        return {"subs_per_set": 6}
    try:
        return json.loads(r[0])
    except Exception:
        return {"subs_per_set": 6}
