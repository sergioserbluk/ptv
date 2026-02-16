from flask import Blueprint, jsonify, request
from sqlalchemy.orm import aliased

from ..models import get_session, Team, Tournament, Match, Player
from ..errors import APIError

admin_bp = Blueprint("admin", __name__)


# GET endpoints - List data
@admin_bp.get("/teams")
def list_teams():
    """List all teams."""
    with get_session() as session:
        teams = session.query(Team).all()
        return jsonify([{
            "id": t.id,
            "name": t.name,
            "short": t.short,
            "colors": t.colors,
            "logo_url": t.logo_url,
        } for t in teams])


@admin_bp.get("/tournaments")
def list_tournaments():
    """List all tournaments."""
    with get_session() as session:
        tournaments = session.query(Tournament).all()
        return jsonify([{
            "id": t.id,
            "name": t.name,
            "season": t.season,
            "type": t.type,
        } for t in tournaments])


@admin_bp.get("/matches")
def list_matches():
    """List matches, optionally filtered by tournament_id."""
    tournament_id = request.args.get("tournament_id", type=int)
    with get_session() as session:
        home = aliased(Team)
        away = aliased(Team)
        query = (
            session.query(Match, home, away)
            .join(home, Match.home_id == home.id)
            .join(away, Match.away_id == away.id)
        )
        if tournament_id:
            query = query.filter(Match.tournament_id == tournament_id)
        
        matches = query.order_by(Match.id.desc()).all()
        return jsonify([{
            "id": m[0].id,
            "label": f"{m[1].name} vs {m[2].name}",
            "status": m[0].status,
            "date": m[0].date,
        } for m in matches])


@admin_bp.get("/players")
def list_players():
    """List players, optionally filtered by team_id."""
    team_id = request.args.get("team_id", type=int)
    with get_session() as session:
        query = session.query(Player)
        if team_id:
            query = query.filter(Player.team_id == team_id)
        
        players = query.order_by(Player.libero.desc(), Player.number).all()
        return jsonify([{
            "id": p.id,
            "number": p.number,
            "name": p.name,
            "role": p.role,
            "libero": bool(p.libero),
        } for p in players])


# POST endpoints - Create data
@admin_bp.post("/admin/team")
def create_team():
    """Create a new team."""
    data = request.get_json() or {}
    
    if "name" not in data or not isinstance(data["name"], str):
        return jsonify({"ok": False, "error": "'name' is required"})
    
    name = data["name"].strip()
    short = data.get("short", "").strip() or None
    colors = data.get("colors", "").strip() or None
    logo_url = data.get("logo_url", "").strip() or None
    
    try:
        with get_session() as session:
            team = Team(name=name, short=short, colors=colors, logo_url=logo_url)
            session.add(team)
            session.commit()
            return jsonify({"ok": True, "id": team.id})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@admin_bp.post("/admin/player")
def create_player():
    """Create a new player."""
    data = request.get_json() or {}
    
    if "team_id" not in data or not isinstance(data["team_id"], int):
        return jsonify({"ok": False, "error": "'team_id' is required and must be int"})
    
    if "name" not in data or not isinstance(data["name"], str):
        return jsonify({"ok": False, "error": "'name' is required"})
    
    team_id = data["team_id"]
    number = data.get("number")
    name = data["name"].strip()
    role = data.get("role", "").strip() or None
    libero = data.get("libero", False)
    
    try:
        with get_session() as session:
            # Verify team exists
            team = session.query(Team).filter(Team.id == team_id).first()
            if not team:
                return jsonify({"ok": False, "error": "Team not found"})
            
            player = Player(team_id=team_id, number=number, name=name, role=role, libero=libero)
            session.add(player)
            session.commit()
            return jsonify({"ok": True, "id": player.id})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@admin_bp.post("/admin/match")
def create_match():
    """Create a new match."""
    data = request.get_json() or {}
    
    if "tournament_id" not in data or not isinstance(data["tournament_id"], int):
        return jsonify({"ok": False, "error": "'tournament_id' is required and must be int"})
    
    if "home_id" not in data or not isinstance(data["home_id"], int):
        return jsonify({"ok": False, "error": "'home_id' is required and must be int"})
    
    if "away_id" not in data or not isinstance(data["away_id"], int):
        return jsonify({"ok": False, "error": "'away_id' is required and must be int"})
    
    tournament_id = data["tournament_id"]
    home_id = data["home_id"]
    away_id = data["away_id"]
    date = data.get("date", "").strip() or None
    gym = data.get("gym", "").strip() or None
    status = data.get("status", "pending")
    
    try:
        with get_session() as session:
            # Verify tournament exists
            tournament = session.query(Tournament).filter(Tournament.id == tournament_id).first()
            if not tournament:
                return jsonify({"ok": False, "error": "Tournament not found"})
            
            # Verify teams exist
            home_team = session.query(Team).filter(Team.id == home_id).first()
            away_team = session.query(Team).filter(Team.id == away_id).first()
            if not home_team or not away_team:
                return jsonify({"ok": False, "error": "Team not found"})
            
            match = Match(
                tournament_id=tournament_id,
                home_id=home_id,
                away_id=away_id,
                date=date,
                gym=gym,
                status=status
            )
            session.add(match)
            session.commit()
            return jsonify({"ok": True, "id": match.id})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})
