"""Add trigram indexes for catalog category and store search.

Revision ID: c19f3a7b2e64
Revises: a84f5c6e9d21
Create Date: 2026-07-18
"""

from alembic import op


revision = "c19f3a7b2e64"
down_revision = "a84f5c6e9d21"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_products_category_trgm "
        "ON products USING gin (category gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_products_store_trgm "
        "ON products USING gin (store gin_trgm_ops)"
    )


def downgrade():
    if op.get_bind().dialect.name != "postgresql":
        return

    op.execute("DROP INDEX IF EXISTS ix_products_store_trgm")
    op.execute("DROP INDEX IF EXISTS ix_products_category_trgm")
