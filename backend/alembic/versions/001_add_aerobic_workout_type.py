"""add aerobic workout type

Revision ID: 001
Revises:
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite stores enums as VARCHAR — no schema change needed.
    # PostgreSQL requires ALTER TYPE to add the new enum value.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE workouttype ADD VALUE IF NOT EXISTS 'aerobic'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values without recreating the type.
    pass
