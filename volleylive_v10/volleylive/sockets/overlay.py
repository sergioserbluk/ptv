from ..services.state import STATE, broadcast, log_event, load_match_names

def register_socketio(socketio):
    @socketio.on("connect")
    def on_connect():
        socketio.emit("state_update", STATE)

    @socketio.on("select_context")
    def on_select_context(data):
        STATE["tournament_id"] = data.get("tournament_id")
        STATE["match_id"] = data.get("match_id")
        if STATE["match_id"]:
            load_match_names(STATE["match_id"])
        broadcast()

    @socketio.on("mode")
    def on_mode(data):
        mode = data.get("mode")
        if mode in ("intro","partido","tiempo_fuera","entre_sets","publicidad"):
            STATE["mode"] = mode
            log_event(STATE["match_id"], STATE["set_number"], f"MODE_{mode.upper()}", {})
            broadcast()

    @socketio.on("theme")
    def on_theme(data):
        theme = data.get("theme")
        if theme in ("light","dark"):
            STATE["theme"] = theme
            broadcast()

    @socketio.on("update_names")
    def on_update_names(data):
        STATE["home_name"] = (data.get("home_name") or STATE["home_name"])[:24]
        STATE["away_name"] = (data.get("away_name") or STATE["away_name"])[:24]
        broadcast()

    @socketio.on("point")
    def on_point(data):
        team = data.get("team")
        amt = int(data.get("amount", 1))
        if team == "home":
            STATE["home_points"] = max(0, STATE["home_points"] + amt)
            log_event(STATE["match_id"], STATE["set_number"], "POINT_HOME", {"delta": amt})
        elif team == "away":
            STATE["away_points"] = max(0, STATE["away_points"] + amt)
            log_event(STATE["match_id"], STATE["set_number"], "POINT_AWAY", {"delta": amt})
        broadcast()

    @socketio.on("set_point")
    def on_set_point(data):
        team = data.get("team")
        amt = int(data.get("amount", 1))
        if team == "home":
            STATE["home_sets"] = max(0, STATE["home_sets"] + amt)
        elif team == "away":
            STATE["away_sets"] = max(0, STATE["away_sets"] + amt)
        broadcast()

    @socketio.on("next_set")
    def on_next_set():
        hp, ap = STATE["home_points"], STATE["away_points"]
        if hp == ap:
            socketio.emit("tie_on_set_end", {"home_points": hp, "away_points": ap})
            return
        winner = "home" if hp > ap else "away"
        if winner == "home":
            STATE["home_sets"] += 1
        else:
            STATE["away_sets"] += 1
        log_event(STATE["match_id"], STATE["set_number"], "END_SET",
                  {"winner": winner, "home_points": hp, "away_points": ap})
        STATE["home_points"] = 0
        STATE["away_points"] = 0
        STATE["set_number"] += 1
        log_event(STATE["match_id"], STATE["set_number"], "START_SET", {})
        broadcast()

    @socketio.on("timer")
    def on_timer(data):
        action = data.get("action")
        if action == "start":
            STATE["timer_running"] = True
        elif action == "stop":
            STATE["timer_running"] = False
        elif action == "reset":
            STATE["timer_running"] = False
            STATE["timer_seconds"] = 0
        elif action == "set":
            try:
                STATE["timer_seconds"] = max(0, int(data.get("seconds", 0)))
            except Exception:
                pass
        broadcast()

    @socketio.on("tick")
    def on_tick():
        if STATE["timer_running"] and STATE["timer_seconds"] > 0:
            STATE["timer_seconds"] -= 1
            broadcast()

    @socketio.on("ads_toggle")
    def on_ads_toggle(data):
        STATE["ads_enabled"] = bool(data.get("enabled", False))
        broadcast()

    @socketio.on("intro_update")
    def on_intro_update(data):
        STATE["intro_title"] = (data.get("intro_title") or STATE["intro_title"])[:120]
        STATE["intro_subtitle"] = (data.get("intro_subtitle") or STATE["intro_subtitle"])[:160]
        STATE["intro_extra"] = (data.get("intro_extra") or STATE["intro_extra"])[:200]
        broadcast()

    @socketio.on("clock")
    def on_clock(data):
        act = data.get("action")
        if act == "start":
            STATE["match_clock_running"] = True
            log_event(STATE["match_id"], STATE["set_number"], "CLOCK_START", {})
        elif act == "stop":
            STATE["match_clock_running"] = False
            log_event(STATE["match_id"], STATE["set_number"], "CLOCK_STOP", {})
        elif act == "reset":
            STATE["match_clock_running"] = False
            STATE["match_clock_seconds"] = 0
            log_event(STATE["match_id"], STATE["set_number"], "CLOCK_RESET", {})
        broadcast()

    @socketio.on("timeout")
    def on_timeout(data):
        act = data.get("action")
        if act == "start":
            team = data.get("team")
            seconds = int(data.get("seconds", 60))
            if team in ("home","away") and seconds > 0:
                STATE["timeout_active"] = True
                STATE["timeout_team"] = team
                STATE["timeout_seconds"] = seconds
                timeout_event("TIMEOUT_START")
        elif act == "stop":
            if STATE["timeout_active"]:
                timeout_event("TIMEOUT_STOP")
            STATE["timeout_active"] = False
            STATE["timeout_team"] = None
            STATE["timeout_seconds"] = 0
        broadcast()

    @socketio.on("tick")
    def on_tick():
        # llamado 1 vez por segundo desde el control
        changed = False
    
        if STATE["match_clock_running"]:
            STATE["match_clock_seconds"] += 1
            changed = True
    
        if STATE["timeout_active"] and STATE["timeout_seconds"] > 0:
            STATE["timeout_seconds"] -= 1
            changed = True
            if STATE["timeout_seconds"] <= 0:
                # terminó el TO
                timeout_event("TIMEOUT_END")
                STATE["timeout_active"] = False
                STATE["timeout_team"] = None
                STATE["timeout_seconds"] = 0
    
        if changed:
            broadcast()