"""add strava integration fields

Revision ID: 004
Revises: 003
Create Date: 2026-04-12
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- users table: Strava OAuth fields ---
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("strava_athlete_id", sa.BigInteger(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("strava_access_token", sa.String(512), nullable=True)
        )
        batch_op.add_column(
            sa.Column("strava_refresh_token", sa.String(512), nullable=True)
        )
        # Unix timestamp when the access token expires
        batch_op.add_column(
            sa.Column("strava_token_expires_at", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("strava_connected", sa.Boolean(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("strava_scope", sa.String(255), nullable=True)
        )
        # Human-readable athlete name from Strava profile
        batch_op.add_column(
            sa.Column("strava_athlete_name", sa.String(255), nullable=True)
        )

    # --- workouts table: Strava activity deduplication ---
    with op.batch_alter_table("workouts") as batch_op:
        batch_op.add_column(
            sa.Column("strava_activity_id", sa.BigInteger(), nullable=True)
        )
        batch_op.create_index("ix_workouts_strava_activity_id", ["strava_activity_id"])


def downgrade() -> None:
    with op.batch_alter_table("workouts") as batch_op:
        batch_op.drop_index("ix_workouts_strava_activity_id")
        batch_op.drop_column("strava_activity_id")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("strava_athlete_name")
        batch_op.drop_column("strava_scope")
        batch_op.drop_column("strava_connected")
        batch_op.drop_column("strava_token_expires_at")
        batch_op.drop_column("strava_refresh_token")
        batch_op.drop_column("strava_access_token")
        batch_op.drop_column("strava_athlete_id")
