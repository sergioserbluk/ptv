from flask_socketio import SocketIO, emit

from .services import (
    broadcast,
    load_match_names,
    log_event,
    state,
)


def register_socketio_events(socketio: SocketIO):
    @socketio.on("connect")
    def on_connect():
        emit("state_update", state)

    @socketio.on("select_context")
    def on_select_context(data):
        state["tournament_id"] = data.get("tournament_id")
        state["match_id"] = data.get("match_id")
        if state["match_id"]:
            load_match_names(state["match_id"])
        broadcast()

    @socketio.on("mode")
    def on_mode(data):
        mode = data.get("mode")
        if mode in ("intro", "partido", "tiempo_fuera", "entre_sets", "publicidad"):
            state["mode"] = mode
            log_event(state["match_id"], state["set_number"], f"MODE_{mode.upper()}", {})
            broadcast()

    @socketio.on("theme")
    def on_theme(data):
        theme = data.get("theme")
        if theme in ("light", "dark"):
            state["theme"] = theme
            broadcast()

    @socketio.on("update_names")
    def on_update_names(data):
        state["home_name"] = (data.get("home_name") or state["home_name"])[:24]
        state["away_name"] = (data.get("away_name") or state["away_name"])[:24]
        broadcast()

    @socketio.on("point")
    def on_point(data):
        team = data.get("team")
        amt = int(data.get("amount", 1))
        if team == "home":
            state["home_points"] = max(0, state["home_points"] + amt)
            log_event(state["match_id"], state["set_number"], "POINT_HOME", {"delta": amt})
        elif team == "away":
            state["away_points"] = max(0, state["away_points"] + amt)
            log_event(state["match_id"], state["set_number"], "POINT_AWAY", {"delta": amt})
        broadcast()

    @socketio.on("set_point")
    def on_set_point(data):
        team = data.get("team")
        amt = int(data.get("amount", 1))
        if team == "home":
            state["home_sets"] = max(0, state["home_sets"] + amt)
        elif team == "away":
            state["away_sets"] = max(0, state["away_sets"] + amt)
        broadcast()

    @socketio.on("next_set")
    def on_next_set():
        hp, ap = state["home_points"], state["away_points"]
        if hp == ap:
            emit("tie_on_set_end", {"home_points": hp, "away_points": ap})
            return
        winner = "home" if hp > ap else "away"
        if winner == "home":
            state["home_sets"] += 1
        else:
            state["away_sets"] += 1
        log_event(
            state["match_id"],
            state["set_number"],
            "END_SET",
            {"winner": winner, "home_points": hp, "away_points": ap},
        )
        state["home_points"] = 0
        state["away_points"] = 0
        state["set_number"] += 1
        log_event(state["match_id"], state["set_number"], "START_SET", {})
        broadcast()

    @socketio.on("timer")
    def on_timer(data):
        action = data.get("action")
        if action == "start":
            state["timer_running"] = True
        elif action == "stop":
            state["timer_running"] = False
        elif action == "reset":
            state["timer_running"] = False
            state["timer_seconds"] = 0
        elif action == "set":
            try:
                state["timer_seconds"] = max(0, int(data.get("seconds", 0)))
            except Exception:
                pass
        broadcast()

    @socketio.on("tick")
    def on_tick():
        if state["timer_running"] and state["timer_seconds"] > 0:
            state["timer_seconds"] -= 1
            broadcast()

    @socketio.on("ads_toggle")
    def on_ads_toggle(data):
        state["ads_enabled"] = bool(data.get("enabled", False))
        broadcast()

    @socketio.on("intro_update")
    def on_intro_update(data):
        state["intro_title"] = (data.get("intro_title") or state["intro_title"])[:120]
        state["intro_subtitle"] = (data.get("intro_subtitle") or state["intro_subtitle"])[:160]
        state["intro_extra"] = (data.get("intro_extra") or state["intro_extra"])[:200]
        broadcast()
