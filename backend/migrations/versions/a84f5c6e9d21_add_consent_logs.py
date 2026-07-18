"""Add the granular consent audit log.

Revision ID: a84f5c6e9d21
Revises: d3ca3c532cd6
Create Date: 2026-07-18
"""

from alembic import op
import sqlalchemy as sa


revision = "a84f5c6e9d21"
down_revision = "d3ca3c532cd6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "consent_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("categories", sa.JSON(), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_consent_logs_user_id", "consent_logs", ["user_id"])
    op.create_index("ix_consent_logs_session_id", "consent_logs", ["session_id"])
    op.create_index("ix_consent_logs_created_at", "consent_logs", ["created_at"])


def downgrade():
    op.drop_index("ix_consent_logs_created_at", table_name="consent_logs")
    op.drop_index("ix_consent_logs_session_id", table_name="consent_logs")
    op.drop_index("ix_consent_logs_user_id", table_name="consent_logs")
    op.drop_table("consent_logs")
