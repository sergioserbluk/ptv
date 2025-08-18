import os
import json
from contextlib import contextmanager

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    Boolean,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

DB_PATH = os.path.join(os.path.dirname(__file__), "matches.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


class Ruleset(Base):
    __tablename__ = "rulesets"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    json = Column(Text, nullable=False)

    tournaments = relationship("Tournament", back_populates="ruleset")


class Tournament(Base):
    __tablename__ = "tournaments"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    season = Column(String)
    ruleset_id = Column(Integer, ForeignKey("rulesets.id"), nullable=False)
    type = Column(String, nullable=False)
    meta_json = Column(Text)

    ruleset = relationship("Ruleset", back_populates="tournaments")
    teams = relationship("TournamentTeam", back_populates="tournament")
    matches = relationship("Match", back_populates="tournament")


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    short = Column(String)
    colors = Column(String)
    logo_url = Column(String)

    players = relationship("Player", back_populates="team")
    tournaments = relationship("TournamentTeam", back_populates="team")
    home_matches = relationship("Match", foreign_keys="Match.home_id", back_populates="home_team")
    away_matches = relationship("Match", foreign_keys="Match.away_id", back_populates="away_team")


class TournamentTeam(Base):
    __tablename__ = "tournament_teams"

    id = Column(Integer, primary_key=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    group_name = Column(String)

    tournament = relationship("Tournament", back_populates="teams")
    team = relationship("Team", back_populates="tournaments")


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"), nullable=False)
    home_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    away_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    date = Column(String)
    gym = Column(String)
    status = Column(String)
    rules_snapshot_json = Column(Text)
    result_json = Column(Text)

    tournament = relationship("Tournament", back_populates="matches")
    home_team = relationship("Team", foreign_keys=[home_id], back_populates="home_matches")
    away_team = relationship("Team", foreign_keys=[away_id], back_populates="away_matches")
    events = relationship("Event", back_populates="match")
    lineups = relationship("Lineup", back_populates="match")
    subs_counter = relationship("SubsCounter", back_populates="match")


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    number = Column(Integer)
    name = Column(String, nullable=False)
    role = Column(String)
    libero = Column(Boolean, nullable=False, default=False)

    team = relationship("Team", back_populates="players")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    set_number = Column(Integer)
    ts = Column(String, nullable=False)
    type = Column(String, nullable=False)
    payload_json = Column(Text)

    match = relationship("Match", back_populates="events")


class Lineup(Base):
    __tablename__ = "lineups"

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    set_number = Column(Integer, nullable=False)
    team = Column(String, nullable=False)
    players_json = Column(Text, nullable=False)
    libero_id = Column(Integer)

    __table_args__ = (UniqueConstraint("match_id", "set_number", "team"),)

    match = relationship("Match", back_populates="lineups")


class SubsCounter(Base):
    __tablename__ = "subs_counter"

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    set_number = Column(Integer, nullable=False)
    team = Column(String, nullable=False)
    used = Column(Integer, nullable=False, default=0)

    __table_args__ = (UniqueConstraint("match_id", "set_number", "team"),)

    match = relationship("Match", back_populates="subs_counter")


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    with get_session() as session:
        if session.query(Ruleset).count() == 0:
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
            ruleset = Ruleset(name="Liga 2025 - Std (Bo5)", json=json.dumps(rules))
            session.add(ruleset)
            session.flush()

            home = Team(name="Iberá V.C.", short="IBR")
            away = Team(name="Independiente", short="IND")
            session.add_all([home, away])
            session.flush()

            tournament = Tournament(
                name="Liga Local 2025",
                season="2025",
                ruleset_id=ruleset.id,
                type="round_robin",
                meta_json="{}",
            )
            session.add(tournament)
            session.flush()

            session.add_all(
                [
                    TournamentTeam(tournament_id=tournament.id, team_id=home.id),
                    TournamentTeam(tournament_id=tournament.id, team_id=away.id),
                ]
            )
            session.flush()

            match = Match(
                tournament_id=tournament.id,
                home_id=home.id,
                away_id=away.id,
                date="2025-08-16T18:00:00",
                gym="Polideportivo",
                status="scheduled",
                rules_snapshot_json=json.dumps(rules),
            )
            session.add(match)
            session.flush()

            home_players = [
                Player(team_id=home.id, number=1, name="Local 1", role="OH"),
                Player(team_id=home.id, number=2, name="Local 2", role="MB"),
                Player(team_id=home.id, number=3, name="Local 3", role="S"),
                Player(team_id=home.id, number=4, name="Local 4", role="OP"),
                Player(team_id=home.id, number=5, name="Local 5", role="OH"),
                Player(team_id=home.id, number=6, name="Local 6", role="MB"),
                Player(team_id=home.id, number=12, name="Líbero Local", role="L", libero=True),
                Player(team_id=home.id, number=7, name="Local 7", role="OH"),
                Player(team_id=home.id, number=8, name="Local 8", role="MB"),
            ]
            away_players = [
                Player(team_id=away.id, number=1, name="Visita 1", role="OH"),
                Player(team_id=away.id, number=2, name="Visita 2", role="MB"),
                Player(team_id=away.id, number=3, name="Visita 3", role="S"),
                Player(team_id=away.id, number=4, name="Visita 4", role="OP"),
                Player(team_id=away.id, number=5, name="Visita 5", role="OH"),
                Player(team_id=away.id, number=6, name="Visita 6", role="MB"),
                Player(team_id=away.id, number=10, name="Líbero Visita", role="L", libero=True),
                Player(team_id=away.id, number=7, name="Visita 7", role="OH"),
                Player(team_id=away.id, number=8, name="Visita 8", role="MB"),
            ]
            session.add_all(home_players + away_players)
        session.commit()
