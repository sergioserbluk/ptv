import datetime
import json
from typing import Any, Dict

from ..models import get_session, Event, Match, Team

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


def load_match_names(match_id):
    try:
        with get_session() as session:
            home = (
                session.query(Team.name)
                .join(Match, Match.home_id == Team.id)
                .filter(Match.id == match_id)
                .scalar()
            )
            away = (
                session.query(Team.name)
                .join(Match, Match.away_id == Team.id)
                .filter(Match.id == match_id)
                .scalar()
            )
            if home and away:
                state["home_name"], state["away_name"] = home, away
    except Exception:
        pass


def rules_for_match(match_id):
    with get_session() as session:
        match = session.get(Match, match_id)
    if not match or not match.rules_snapshot_json:
        return {"subs_per_set": 6}
    try:
        return json.loads(match.rules_snapshot_json)
    except Exception:
        return {"subs_per_set": 6}
