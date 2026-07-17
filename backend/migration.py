"""Versioned database migration and release commands.

Production releases use ``python migration.py release`` before triggering the
Render deploy. The command exits non-zero on every connection, migration, or
data-release failure, so the deployment workflow remains fail-closed.

Useful local commands::

    python migration.py upgrade
    python migration.py downgrade -1
    python migration.py current
"""

import argparse
import logging
import os
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from config import normalize_database_url


BACKEND_DIR = Path(__file__).resolve().parent
MIGRATIONS_DIR = BACKEND_DIR / "migrations"
POSTGRES_MIGRATION_LOCK_ID = 1_018_012_026
LOGGER = logging.getLogger("cealeg.migrations")


def resolve_database_url(database_url=None, environ=None):
    source = environ if environ is not None else os.environ
    raw_url = source.get("DATABASE_URL", "") if database_url is None else database_url
    resolved_url = normalize_database_url(raw_url)
    app_env = str(source.get("APP_ENV", "development") or "development").lower()

    if not resolved_url:
        if app_env in {"production", "prod"}:
            raise RuntimeError(
                "DATABASE_URL is required for production migrations; refusing SQLite fallback."
            )
        resolved_url = f"sqlite:///{(BACKEND_DIR / 'instance' / 'cealeg.db').as_posix()}"

    parsed_url = make_url(resolved_url)
    if parsed_url.get_backend_name() == "sqlite":
        database = parsed_url.database
        if database and database != ":memory:":
            database_path = Path(database)
            if not database_path.is_absolute():
                database_path = BACKEND_DIR / "instance" / database_path
            database_path.parent.mkdir(parents=True, exist_ok=True)
            parsed_url = parsed_url.set(database=str(database_path.resolve()))

    return parsed_url


def build_alembic_config(database_url):
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR).replace("%", "%%"))
    rendered_url = database_url.render_as_string(hide_password=False).replace("%", "%%")
    config.set_main_option("sqlalchemy.url", rendered_url)
    return config


def create_migration_engine(database_url, environ=None):
    source = environ if environ is not None else os.environ
    connect_args = {}

    if database_url.get_backend_name() == "postgresql":
        sslmode = str(source.get("DATABASE_SSLMODE", "") or "").strip()
        if sslmode and "sslmode" not in database_url.query:
            connect_args["sslmode"] = sslmode

    return create_engine(
        database_url,
        connect_args=connect_args,
        pool_pre_ping=True,
        poolclass=NullPool,
    )


def _run_alembic(connection, action, revision):
    config = build_alembic_config(connection.engine.url)
    config.attributes["connection"] = connection

    if action == "upgrade":
        command.upgrade(config, revision)
    elif action == "downgrade":
        command.downgrade(config, revision)
    elif action == "current":
        command.current(config, verbose=True)
    else:
        raise ValueError(f"Unsupported migration action: {action}")


def _backfill_invite_codes(connection):
    rows = connection.execute(
        text("SELECT id, invite_code FROM users ORDER BY id")
    ).mappings().all()
    existing_codes = {
        str(row["invite_code"]).upper()
        for row in rows
        if str(row["invite_code"] or "").strip()
    }
    updated = 0

    for row in rows:
        if str(row["invite_code"] or "").strip():
            continue

        invite_code = None
        for _attempt in range(12):
            candidate = f"CEA{uuid4().hex[:8].upper()}"
            if candidate not in existing_codes:
                invite_code = candidate
                existing_codes.add(candidate)
                break

        if invite_code is None:
            raise RuntimeError(f"Could not allocate a unique invite code for user {row['id']}")

        connection.execute(
            text("UPDATE users SET invite_code = :invite_code WHERE id = :user_id"),
            {"invite_code": invite_code, "user_id": row["id"]},
        )
        updated += 1

    return updated


def _promote_configured_admin(connection, environ=None):
    source = environ if environ is not None else os.environ
    admin_email = str(source.get("ADMIN_EMAIL", "") or "").strip().lower()
    if not admin_email:
        return 0

    result = connection.execute(
        text(
            "UPDATE users SET is_admin = :is_admin "
            "WHERE lower(email) = :email AND is_admin = :not_admin"
        ),
        {"email": admin_email, "is_admin": True, "not_admin": False},
    )
    return max(0, int(result.rowcount or 0))


def _run_in_transaction(action, revision, database_url=None, environ=None, release=False):
    resolved_url = resolve_database_url(database_url=database_url, environ=environ)
    engine = create_migration_engine(resolved_url, environ=environ)

    try:
        with engine.begin() as connection:
            if connection.dialect.name == "postgresql":
                connection.execute(
                    text("SELECT pg_advisory_xact_lock(:lock_id)"),
                    {"lock_id": POSTGRES_MIGRATION_LOCK_ID},
                )

            _run_alembic(connection, action, revision)

            if release:
                invite_codes = _backfill_invite_codes(connection)
                promoted_admins = _promote_configured_admin(connection, environ=environ)
                LOGGER.info(
                    "Release data operations completed: invite_codes=%s admins_promoted=%s",
                    invite_codes,
                    promoted_admins,
                )
    finally:
        engine.dispose()


def run_migrations(action, revision=None, database_url=None, environ=None):
    if action == "upgrade":
        target_revision = revision or "head"
    elif action == "downgrade":
        target_revision = revision or "-1"
    elif action == "current":
        target_revision = None
    else:
        raise ValueError(f"Unsupported migration action: {action}")

    _run_in_transaction(
        action,
        target_revision,
        database_url=database_url,
        environ=environ,
    )


def run_release(database_url=None, environ=None):
    _run_in_transaction(
        "upgrade",
        "head",
        database_url=database_url,
        environ=environ,
        release=True,
    )


def assert_database_at_head(database_url=None, environ=None):
    """Read the migration ledger and refuse an incompatible production start."""
    resolved_url = resolve_database_url(database_url=database_url, environ=environ)
    config = build_alembic_config(resolved_url)
    expected_heads = set(ScriptDirectory.from_config(config).get_heads())
    engine = create_migration_engine(resolved_url, environ=environ)

    try:
        with engine.connect() as connection:
            current_heads = set(MigrationContext.configure(connection).get_current_heads())
    finally:
        engine.dispose()

    if current_heads != expected_heads:
        current_label = ", ".join(sorted(current_heads)) or "<unversioned>"
        expected_label = ", ".join(sorted(expected_heads)) or "<no migration heads>"
        raise RuntimeError(
            "Database migration revision mismatch: "
            f"current={current_label}, expected={expected_label}. "
            "Run `python migration.py release` before starting the application."
        )


def build_parser():
    parser = argparse.ArgumentParser(
        description="Run the Ce Aleg versioned database migration gate.",
        epilog=(
            "Production: set DATABASE_URL and run `python migration.py release`; "
            "the command is intentionally fail-closed."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrade to a revision.")
    upgrade_parser.add_argument("revision", nargs="?", default="head")

    downgrade_parser = subparsers.add_parser("downgrade", help="Downgrade to a revision.")
    downgrade_parser.add_argument("revision", nargs="?", default="-1")

    subparsers.add_parser("current", help="Print the current database revision.")
    subparsers.add_parser(
        "release",
        help="Upgrade to head and run idempotent release data operations.",
    )
    return parser


def main(argv=None):
    load_dotenv(BACKEND_DIR / ".env")
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    args = build_parser().parse_args(argv)

    try:
        if args.command == "release":
            run_release()
        else:
            run_migrations(args.command, getattr(args, "revision", None))
    except Exception:
        LOGGER.exception(
            "Database migration failed. The application deployment must remain stopped."
        )
        return 1

    LOGGER.info("Database migration command completed: %s", args.command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
