"""Establish the versioned application schema.

Revision ID: d3ca3c532cd6
Revises:
Create Date: 2026-07-17

The first revision is deliberately adoptive: it creates a new database in full,
and it upgrades an existing pre-Alembic database without dropping application
data. Future revisions can assume this complete baseline.
"""

from alembic import op
import sqlalchemy as sa


revision = "d3ca3c532cd6"
down_revision = None
branch_labels = None
depends_on = None


def _table_exists(table_name):
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _column_exists(table_name, column_name):
    return column_name in {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)
    }


def _index_exists(table_name, index_name):
    return index_name in {
        index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)
    }


def _create_table_if_missing(table_name, *elements):
    if not _table_exists(table_name):
        op.create_table(table_name, *elements)


def _add_column_if_missing(table_name, column):
    if not _column_exists(table_name, column.name):
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            batch_op.add_column(column)


def _create_index_if_missing(index_name, table_name, columns, unique=False, **kwargs):
    if not _index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=unique, **kwargs)


def _ensure_unique_columns(table_name, constraint_name, columns):
    expected_columns = tuple(columns)
    inspector = sa.inspect(op.get_bind())
    unique_constraints = inspector.get_unique_constraints(table_name)
    indexes = inspector.get_indexes(table_name)
    if any(tuple(item.get("column_names") or ()) == expected_columns for item in unique_constraints):
        return
    if any(
        item.get("unique") and tuple(item.get("column_names") or ()) == expected_columns
        for item in indexes
    ):
        return
    op.create_index(constraint_name, table_name, columns, unique=True)


def _ensure_foreign_key(table_name, constraint_name, columns, remote_table, remote_columns):
    expected_columns = tuple(columns)
    expected_remote = tuple(remote_columns)
    foreign_keys = sa.inspect(op.get_bind()).get_foreign_keys(table_name)
    if any(
        tuple(item.get("constrained_columns") or ()) == expected_columns
        and item.get("referred_table") == remote_table
        and tuple(item.get("referred_columns") or ()) == expected_remote
        for item in foreign_keys
    ):
        return

    with op.batch_alter_table(table_name, schema=None) as batch_op:
        batch_op.create_foreign_key(
            constraint_name,
            remote_table,
            columns,
            remote_columns,
        )


def _create_application_tables():
    _create_table_if_missing(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("store", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("barcode", sa.String(length=80), nullable=True),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("tag", sa.String(length=100), nullable=True),
        sa.Column("image", sa.String(length=255), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("price_text", sa.String(length=100), nullable=True),
        sa.Column("calories", sa.Float(), nullable=True),
        sa.Column("protein", sa.Float(), nullable=True),
        sa.Column("sugar", sa.Float(), nullable=True),
        sa.Column("fat", sa.Float(), nullable=True),
        sa.Column("vegan", sa.Boolean(), nullable=True, server_default=sa.false()),
        sa.Column("lactose_free", sa.Boolean(), nullable=True, server_default=sa.false()),
        sa.Column("natural", sa.Boolean(), nullable=True, server_default=sa.false()),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("ingredients", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    _create_table_if_missing(
        "stripe_webhook_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider_event_id", sa.String(length=180), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default="processing",
        ),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    _create_table_if_missing(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("email_verified_at", sa.DateTime(), nullable=True),
        sa.Column("invite_code", sa.String(length=30), nullable=True),
        sa.Column("referred_by_user_id", sa.Integer(), nullable=True),
        sa.Column("bonus_unlimited_until", sa.DateTime(), nullable=True),
        sa.Column("bonus_scan_credits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("auth_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "processing_restricted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("processing_restricted_at", sa.DateTime(), nullable=True),
        sa.Column("processing_restriction_reason", sa.String(length=500), nullable=True),
        sa.Column("terms_version", sa.String(length=30), nullable=True),
        sa.Column("terms_accepted_at", sa.DateTime(), nullable=True),
        sa.Column("age_confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("analytics_consent", sa.Boolean(), nullable=True),
        sa.Column("analytics_consent_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["referred_by_user_id"],
            ["users.id"],
            name="fk_users_referred_by_user_id_users",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    _create_table_if_missing(
        "consent_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("consent_type", sa.String(length=80), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column("policy_version", sa.String(length=40), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False, server_default="web"),
        sa.Column("request_identity_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _create_table_if_missing(
        "family_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("color", sa.String(length=30), nullable=False, server_default="teal"),
        sa.Column("avatar", sa.String(length=20), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _create_table_if_missing(
        "favorites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(length=150), nullable=False),
        sa.Column("store", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("price", sa.String(length=100), nullable=True),
        sa.Column("image", sa.String(length=255), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _create_table_if_missing(
        "price_observations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("product_barcode", sa.String(length=80), nullable=False),
        sa.Column("store", sa.String(length=100), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="RON"),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _create_table_if_missing(
        "product_submissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(length=150), nullable=False),
        sa.Column("brand", sa.String(length=100), nullable=True),
        sa.Column("store", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("quantity", sa.String(length=100), nullable=True),
        sa.Column("barcode", sa.String(length=80), nullable=True),
        sa.Column("price", sa.String(length=100), nullable=True),
        sa.Column("front_image", sa.String(length=255), nullable=True),
        sa.Column("nutrition_image", sa.String(length=255), nullable=True),
        sa.Column("calories", sa.Float(), nullable=True),
        sa.Column("protein", sa.Float(), nullable=True),
        sa.Column("sugar", sa.Float(), nullable=True),
        sa.Column("fat", sa.Float(), nullable=True),
        sa.Column("ingredients", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=True, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _create_table_if_missing(
        "scan_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(length=150), nullable=False),
        sa.Column("store", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("price", sa.String(length=100), nullable=True),
        sa.Column("image", sa.String(length=255), nullable=True),
        sa.Column("verdict", sa.Text(), nullable=True),
        sa.Column("short_advice", sa.Text(), nullable=True),
        sa.Column("scanned_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _create_table_if_missing(
        "search_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("query", sa.String(length=250), nullable=False),
        sa.Column("store", sa.String(length=100), nullable=True),
        sa.Column("result_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "source",
            sa.String(length=40),
            nullable=False,
            server_default="product_search",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _create_table_if_missing(
        "subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("plan", sa.String(length=30), nullable=False, server_default="free"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("provider_customer_id", sa.String(length=120), nullable=True),
        sa.Column("provider_subscription_id", sa.String(length=120), nullable=True),
        sa.Column("current_period_start", sa.DateTime(), nullable=True),
        sa.Column("current_period_end", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_subscriptions_user_id"),
    )
    _create_table_if_missing(
        "usage_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=True),
        sa.Column("idempotency_key", sa.String(length=180), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _create_table_if_missing(
        "cart_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("family_profile_id", sa.Integer(), nullable=True),
        sa.Column("product_name", sa.String(length=150), nullable=False),
        sa.Column("store", sa.String(length=100), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("price", sa.String(length=100), nullable=True),
        sa.Column("image", sa.String(length=255), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True, server_default="1"),
        sa.Column("bought", sa.Boolean(), nullable=True, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["family_profile_id"], ["family_profiles.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def _upgrade_legacy_columns():
    evolved_columns = {
        "users": [
            sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("email_verified_at", sa.DateTime(), nullable=True),
            sa.Column("invite_code", sa.String(length=30), nullable=True),
            sa.Column("referred_by_user_id", sa.Integer(), nullable=True),
            sa.Column("bonus_unlimited_until", sa.DateTime(), nullable=True),
            sa.Column("bonus_scan_credits", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("auth_version", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "processing_restricted",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
            sa.Column("processing_restricted_at", sa.DateTime(), nullable=True),
            sa.Column("processing_restriction_reason", sa.String(length=500), nullable=True),
            sa.Column("terms_version", sa.String(length=30), nullable=True),
            sa.Column("terms_accepted_at", sa.DateTime(), nullable=True),
            sa.Column("age_confirmed_at", sa.DateTime(), nullable=True),
            sa.Column("analytics_consent", sa.Boolean(), nullable=True),
            sa.Column("analytics_consent_at", sa.DateTime(), nullable=True),
        ],
        "products": [
            sa.Column("barcode", sa.String(length=80), nullable=True),
            sa.Column("ingredients", sa.Text(), nullable=True),
        ],
        "product_submissions": [
            sa.Column("barcode", sa.String(length=80), nullable=True),
        ],
        "usage_events": [
            sa.Column("idempotency_key", sa.String(length=180), nullable=True),
        ],
        "cart_items": [
            sa.Column("family_profile_id", sa.Integer(), nullable=True),
        ],
    }
    for table_name, columns in evolved_columns.items():
        for column in columns:
            _add_column_if_missing(table_name, column)

    _ensure_foreign_key(
        "users",
        "fk_users_referred_by_user_id_users",
        ["referred_by_user_id"],
        "users",
        ["id"],
    )
    _ensure_foreign_key(
        "cart_items",
        "fk_cart_items_family_profile_id_family_profiles",
        ["family_profile_id"],
        "family_profiles",
        ["id"],
    )


def _create_application_indexes():
    indexes = [
        ("ix_products_barcode", "products", ["barcode"], False),
        ("ix_products_category", "products", ["category"], False),
        ("ix_products_store", "products", ["store"], False),
        ("ix_products_score", "products", ["score"], False),
        ("ix_scan_history_user_scanned_at", "scan_history", ["user_id", "scanned_at"], False),
        ("ix_favorites_user_id", "favorites", ["user_id"], False),
        ("ix_cart_items_user_id", "cart_items", ["user_id"], False),
        ("ix_cart_items_family_profile_id", "cart_items", ["family_profile_id"], False),
        ("ix_cart_items_user_profile", "cart_items", ["user_id", "family_profile_id"], False),
        (
            "ix_cart_items_user_profile_product_store",
            "cart_items",
            ["user_id", "family_profile_id", "product_name", "store"],
            False,
        ),
        (
            "ix_price_observations_product_barcode",
            "price_observations",
            ["product_barcode"],
            False,
        ),
        ("ix_price_observations_barcode", "price_observations", ["product_barcode"], False),
        (
            "ix_search_events_result_created",
            "search_events",
            ["result_count", "created_at"],
            False,
        ),
        ("ix_search_events_query", "search_events", ["query"], False),
        ("ix_search_events_user_created", "search_events", ["user_id", "created_at"], False),
        ("ix_users_invite_code", "users", ["invite_code"], True),
        ("ix_usage_events_created_at", "usage_events", ["created_at"], False),
        ("ix_usage_events_event_type", "usage_events", ["event_type"], False),
        ("ix_usage_events_idempotency_key", "usage_events", ["idempotency_key"], True),
        ("ix_usage_events_user_id", "usage_events", ["user_id"], False),
        (
            "ix_usage_events_user_type_created",
            "usage_events",
            ["user_id", "event_type", "created_at"],
            False,
        ),
        (
            "ix_usage_events_user_type_source",
            "usage_events",
            ["user_id", "event_type", "source"],
            False,
        ),
        (
            "ix_product_submissions_user_status_created",
            "product_submissions",
            ["user_id", "status", "created_at"],
            False,
        ),
        (
            "ix_product_submissions_barcode_status",
            "product_submissions",
            ["barcode", "status"],
            False,
        ),
        (
            "ix_subscriptions_provider_customer",
            "subscriptions",
            ["provider", "provider_customer_id"],
            False,
        ),
        (
            "ix_subscriptions_provider_subscription",
            "subscriptions",
            ["provider", "provider_subscription_id"],
            False,
        ),
        (
            "ix_stripe_webhook_events_provider_event_id",
            "stripe_webhook_events",
            ["provider_event_id"],
            True,
        ),
        ("ix_stripe_webhook_events_status", "stripe_webhook_events", ["status"], False),
        ("ix_consent_records_consent_type", "consent_records", ["consent_type"], False),
        ("ix_consent_records_created_at", "consent_records", ["created_at"], False),
        ("ix_consent_records_user_id", "consent_records", ["user_id"], False),
        ("ix_family_profiles_user_id", "family_profiles", ["user_id"], False),
    ]
    for index_name, table_name, columns, unique in indexes:
        _create_index_if_missing(index_name, table_name, columns, unique=unique)

    idempotency_not_null = sa.column("idempotency_key").is_not(None)
    _create_index_if_missing(
        "ux_usage_events_idempotency_key",
        "usage_events",
        ["idempotency_key"],
        unique=True,
        postgresql_where=idempotency_not_null,
        sqlite_where=idempotency_not_null,
    )
    _ensure_unique_columns("users", "ux_users_email", ["email"])
    _ensure_unique_columns("subscriptions", "ux_subscriptions_user_id", ["user_id"])

    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        _create_index_if_missing(
            "ix_products_name_trgm",
            "products",
            ["name"],
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        )


def upgrade():
    _create_application_tables()
    _upgrade_legacy_columns()
    _create_application_indexes()


def downgrade():
    table_order = [
        "cart_items",
        "usage_events",
        "subscriptions",
        "search_events",
        "scan_history",
        "product_submissions",
        "price_observations",
        "favorites",
        "family_profiles",
        "consent_records",
        "users",
        "stripe_webhook_events",
        "products",
    ]
    for table_name in table_order:
        if _table_exists(table_name):
            op.drop_table(table_name)
