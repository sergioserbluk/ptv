"""initial tables

Revision ID: 0001
Revises: 
Create Date: 2024-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'rulesets',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('json', sa.Text(), nullable=False)
    )
    op.create_table(
        'teams',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('short', sa.String()),
        sa.Column('colors', sa.String()),
        sa.Column('logo_url', sa.String())
    )
    op.create_table(
        'tournaments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('season', sa.String()),
        sa.Column('ruleset_id', sa.Integer(), sa.ForeignKey('rulesets.id'), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('meta_json', sa.Text())
    )
    op.create_table(
        'tournament_teams',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tournament_id', sa.Integer(), sa.ForeignKey('tournaments.id'), nullable=False),
        sa.Column('team_id', sa.Integer(), sa.ForeignKey('teams.id'), nullable=False),
        sa.Column('group_name', sa.String())
    )
    op.create_table(
        'matches',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tournament_id', sa.Integer(), sa.ForeignKey('tournaments.id'), nullable=False),
        sa.Column('home_id', sa.Integer(), sa.ForeignKey('teams.id'), nullable=False),
        sa.Column('away_id', sa.Integer(), sa.ForeignKey('teams.id'), nullable=False),
        sa.Column('date', sa.String()),
        sa.Column('gym', sa.String()),
        sa.Column('status', sa.String()),
        sa.Column('rules_snapshot_json', sa.Text()),
        sa.Column('result_json', sa.Text())
    )
    op.create_table(
        'players',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('team_id', sa.Integer(), sa.ForeignKey('teams.id'), nullable=False),
        sa.Column('number', sa.Integer()),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('role', sa.String()),
        sa.Column('libero', sa.Boolean(), nullable=False, server_default=sa.text('0'))
    )
    op.create_table(
        'events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('match_id', sa.Integer(), sa.ForeignKey('matches.id'), nullable=False),
        sa.Column('set_number', sa.Integer()),
        sa.Column('ts', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('payload_json', sa.Text())
    )
    op.create_table(
        'lineups',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('match_id', sa.Integer(), sa.ForeignKey('matches.id'), nullable=False),
        sa.Column('set_number', sa.Integer(), nullable=False),
        sa.Column('team', sa.String(), nullable=False),
        sa.Column('players_json', sa.Text(), nullable=False),
        sa.Column('libero_id', sa.Integer()),
        sa.UniqueConstraint('match_id', 'set_number', 'team')
    )
    op.create_table(
        'subs_counter',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('match_id', sa.Integer(), sa.ForeignKey('matches.id'), nullable=False),
        sa.Column('set_number', sa.Integer(), nullable=False),
        sa.Column('team', sa.String(), nullable=False),
        sa.Column('used', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.UniqueConstraint('match_id', 'set_number', 'team')
    )

def downgrade():
    op.drop_table('subs_counter')
    op.drop_table('lineups')
    op.drop_table('events')
    op.drop_table('players')
    op.drop_table('matches')
    op.drop_table('tournament_teams')
    op.drop_table('tournaments')
    op.drop_table('teams')
    op.drop_table('rulesets')
