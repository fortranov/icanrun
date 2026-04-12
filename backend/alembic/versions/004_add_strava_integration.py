"""add strava integration fields

Revision ID: 004
Revises: 003
Create Date: 2026-04-12

NOTE: Uses PRAGMA table_info to check existing columns so this migration
is idempotent and safe to run multiple times (SQLite does not support
ALTER TABLE ... ADD COLUMN IF NOT EXISTS).
"""
import sqlalchemy as sa
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def _existing_columns(table: str) -> set:
    conn = op.get_bind()
    rows = conn.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
    return {row[1] for row in rows}


def upgrade() -> None:
    # --- users table: Strava OAuth fields ---
    users_cols = _existing_columns("users")
    with op.batch_alter_table("users") as batch_op:
        if "strava_athlete_id" not in users_cols:
            batch_op.add_column(sa.Column("strava_athlete_id", sa.BigInteger(), nullable=True))
        if "strava_access_token" not in users_cols:
            batch_op.add_column(sa.Column("strava_access_token", sa.String(512), nullable=True))
        if "strava_refresh_token" not in users_cols:
            batch_op.add_column(sa.Column("strava_refresh_token", sa.String(512), nullable=True))
        if "strava_token_expires_at" not in users_cols:
            batch_op.add_column(sa.Column("strava_token_expires_at", sa.Integer(), nullable=True))
        if "strava_connected" not in users_cols:
            batch_op.add_column(
                sa.Column("strava_connected", sa.Boolean(), nullable=False, server_default="0")
            )
        if "strava_scope" not in users_cols:
            batch_op.add_column(sa.Column("strava_scope", sa.String(255), nullable=True))
        if "strava_athlete_name" not in users_cols:
            batch_op.add_column(sa.Column("strava_athlete_name", sa.String(255), nullable=True))

    # --- workouts table: Strava activity deduplication ---
    workout_cols = _existing_columns("workouts")
    with op.batch_alter_table("workouts") as batch_op:
        if "strava_activity_id" not in workout_cols:
            batch_op.add_column(sa.Column("strava_activity_id", sa.BigInteger(), nullable=True))
        # Create index only if not yet present
        conn = op.get_bind()
        idx_rows = conn.execute(
            sa.text("SELECT name FROM sqlite_master WHERE type='index' AND name='ix_workouts_strava_activity_id'")
        ).fetchall()
        if not idx_rows:
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
