"""harden strava dedup indexes

Revision ID: 005
Revises: 004
Create Date: 2026-07-13
"""
import sqlalchemy as sa
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def _index_exists(name: str) -> bool:
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='index' AND name=:name"),
        {"name": name},
    ).fetchall()
    return bool(rows)


def upgrade() -> None:
    conn = op.get_bind()

    if not _index_exists("ix_users_strava_athlete_id"):
        conn.execute(sa.text(
            "CREATE INDEX ix_users_strava_athlete_id ON users (strava_athlete_id)"
        ))

    # Per-user dedupe policy: the same Strava activity can exist for different
    # app users, but not more than once for the same user. SQLite allows many
    # NULL values in unique indexes, so manual/non-Strava workouts are unaffected.
    if not _index_exists("uq_workouts_user_strava_activity_id"):
        conn.execute(sa.text(
            "CREATE UNIQUE INDEX uq_workouts_user_strava_activity_id "
            "ON workouts (user_id, strava_activity_id) "
            "WHERE strava_activity_id IS NOT NULL"
        ))


def downgrade() -> None:
    conn = op.get_bind()
    if _index_exists("uq_workouts_user_strava_activity_id"):
        conn.execute(sa.text("DROP INDEX uq_workouts_user_strava_activity_id"))
    if _index_exists("ix_users_strava_athlete_id"):
        conn.execute(sa.text("DROP INDEX ix_users_strava_athlete_id"))
