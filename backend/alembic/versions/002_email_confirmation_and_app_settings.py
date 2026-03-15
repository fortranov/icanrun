"""email confirmation fields and app_settings table

Revision ID: 002
Revises: 001
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # 1. Add email confirmation columns to users table                    #
    # ------------------------------------------------------------------ #
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("email_confirmed", sa.Boolean(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("email_confirmation_token", sa.String(512), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "email_confirmation_sent_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )

    # ------------------------------------------------------------------ #
    # 2. Create app_settings table                                        #
    # ------------------------------------------------------------------ #
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ------------------------------------------------------------------ #
    # 3. Seed default app settings                                        #
    # ------------------------------------------------------------------ #
    op.bulk_insert(
        sa.table(
            "app_settings",
            sa.column("key", sa.String),
            sa.column("value", sa.Text),
        ),
        [
            {"key": "email_confirmation_enabled", "value": "false"},
            {"key": "smtp_host", "value": ""},
            {"key": "smtp_port", "value": "587"},
            {"key": "smtp_user", "value": ""},
            {"key": "smtp_password", "value": ""},
            {"key": "smtp_from_email", "value": ""},
            {"key": "smtp_from_name", "value": "ICanRun"},
            {"key": "confirmation_token_hours", "value": "24"},
        ],
    )


def downgrade() -> None:
    op.drop_table("app_settings")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("email_confirmation_sent_at")
        batch_op.drop_column("email_confirmation_token")
        batch_op.drop_column("email_confirmed")
