import os
import sqlite3
import json

DB_PATH = os.path.join(os.path.dirname(__file__), "matches.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript(
        """
    PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS rulesets (id INTEGER PRIMARY KEY, name TEXT NOT NULL, json TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS tournaments (id INTEGER PRIMARY KEY, name TEXT NOT NULL, season TEXT, ruleset_id INTEGER NOT NULL,
    type TEXT NOT NULL, meta_json TEXT, FOREIGN KEY (ruleset_id) REFERENCES rulesets(id));
    CREATE TABLE IF NOT EXISTS teams (id INTEGER PRIMARY KEY, name TEXT NOT NULL, short TEXT, colors TEXT, logo_url TEXT);
    CREATE TABLE IF NOT EXISTS tournament_teams (id INTEGER PRIMARY KEY, tournament_id INTEGER NOT NULL, team_id INTEGER NOT NULL,
    group_name TEXT, FOREIGN KEY (tournament_id) REFERENCES tournaments(id), FOREIGN KEY (team_id) REFERENCES teams(id));
    CREATE TABLE IF NOT EXISTS matches (id INTEGER PRIMARY KEY, tournament_id INTEGER NOT NULL, home_id INTEGER NOT NULL, away_id INTEGER NOT NULL,
    date TEXT, gym TEXT, status TEXT, rules_snapshot_json TEXT, result_json TEXT, FOREIGN KEY (tournament_id) REFERENCES tournaments(id),
    FOREIGN KEY (home_id) REFERENCES teams(id), FOREIGN KEY (away_id) REFERENCES teams(id));
    CREATE TABLE IF NOT EXISTS players (id INTEGER PRIMARY KEY, team_id INTEGER NOT NULL, number INTEGER, name TEXT NOT NULL,
    role TEXT, libero INTEGER NOT NULL DEFAULT 0, FOREIGN KEY (team_id) REFERENCES teams(id));

    CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, match_id INTEGER NOT NULL, set_number INTEGER, ts TEXT NOT NULL,
    type TEXT NOT NULL, payload_json TEXT, FOREIGN KEY (match_id) REFERENCES matches(id));

    CREATE TABLE IF NOT EXISTS lineups (
      id INTEGER PRIMARY KEY,
      match_id INTEGER NOT NULL,
      set_number INTEGER NOT NULL,
      team TEXT NOT NULL,
      players_json TEXT NOT NULL,
      libero_id INTEGER,
      UNIQUE(match_id,set_number,team)
    );
    CREATE TABLE IF NOT EXISTS subs_counter (
      id INTEGER PRIMARY KEY,
      match_id INTEGER NOT NULL,
      set_number INTEGER NOT NULL,
      team TEXT NOT NULL,
      used INTEGER NOT NULL DEFAULT 0,
      UNIQUE(match_id,set_number,team)
    );
    """
    )

    # seed
    c.execute("SELECT COUNT(*) FROM rulesets")
    if c.fetchone()[0] == 0:
        rules = {
            "best_of": 5,
            "sets_to_win": 3,
            "set_points_regular": 25,
            "set_points_tiebreak": 15,
            "win_by_two": True,
            "timeouts_per_set": 2,
            "timeout_seconds": 60,
            "subs_per_set": 6,
            "libero_rules": {"count": 1, "free_replacements": True},
            "standings_scoring": {
                "mode": "by_result",
                "by_result": {
                    "win_3_0_or_3_1": 3,
                    "win_3_2": 2,
                    "loss_2_3": 1,
                    "loss_other": 0,
                },
            },
            "track_points_diff": True,
            "tiebreakers_order": [
                "points_total",
                "matches_won",
                "set_ratio",
                "points_ratio",
                "head_to_head",
            ],
            "tournament_type": "round_robin",
        }
        c.execute(
            "INSERT INTO rulesets(name, json) VALUES (?,?)",
            ("Liga 2025 - Std (Bo5)", json.dumps(rules)),
        )
        ruleset_id = c.lastrowid

        # teams
        c.execute(
            "INSERT INTO teams(name, short) VALUES (?,?)",
            ("Iberá V.C.", "IBR"),
        )
        home_id = c.lastrowid
        c.execute(
            "INSERT INTO teams(name, short) VALUES (?,?)",
            ("Independiente", "IND"),
        )
        away_id = c.lastrowid

        # tournament
        c.execute(
            "INSERT INTO tournaments(name, season, ruleset_id, type, meta_json) VALUES (?,?,?,?,?)",
            ("Liga Local 2025", "2025", ruleset_id, "round_robin", "{}"),
        )
        tournament_id = c.lastrowid
        c.execute(
            "INSERT INTO tournament_teams(tournament_id, team_id) VALUES (?,?)",
            (tournament_id, home_id),
        )
        c.execute(
            "INSERT INTO tournament_teams(tournament_id, team_id) VALUES (?,?)",
            (tournament_id, away_id),
        )

        # match
        c.execute(
            """INSERT INTO matches(tournament_id, home_id, away_id, date, gym, status, rules_snapshot_json)
                     VALUES (?,?,?,?,?,?,?)""",
            (
                tournament_id,
                home_id,
                away_id,
                "2025-08-16T18:00:00",
                "Polideportivo",
                "scheduled",
                json.dumps(rules),
            ),
        )
        mid = c.lastrowid  # noqa: F841

        # players (home)
        home_players = [
            (home_id, 1, "Local 1", "OH", 0),
            (home_id, 2, "Local 2", "MB", 0),
            (home_id, 3, "Local 3", "S", 0),
            (home_id, 4, "Local 4", "OP", 0),
            (home_id, 5, "Local 5", "OH", 0),
            (home_id, 6, "Local 6", "MB", 0),
            (home_id, 12, "Líbero Local", "L", 1),
            (home_id, 7, "Local 7", "OH", 0),
            (home_id, 8, "Local 8", "MB", 0),
        ]
        c.executemany(
            "INSERT INTO players(team_id, number, name, role, libero) VALUES (?,?,?,?,?)",
            home_players,
        )

        # players (away)
        away_players = [
            (away_id, 1, "Visita 1", "OH", 0),
            (away_id, 2, "Visita 2", "MB", 0),
            (away_id, 3, "Visita 3", "S", 0),
            (away_id, 4, "Visita 4", "OP", 0),
            (away_id, 5, "Visita 5", "OH", 0),
            (away_id, 6, "Visita 6", "MB", 0),
            (away_id, 10, "Líbero Visita", "L", 1),
            (away_id, 7, "Visita 7", "OH", 0),
            (away_id, 8, "Visita 8", "MB", 0),
        ]
        c.executemany(
            "INSERT INTO players(team_id, number, name, role, libero) VALUES (?,?,?,?,?)",
            away_players,
        )

    conn.commit()
    conn.close()
