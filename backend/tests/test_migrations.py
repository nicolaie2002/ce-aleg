import os
from pathlib import Path
import subprocess
import sys

from sqlalchemy import create_engine, inspect, text

from database import db
from migration import assert_database_at_head, run_migrations, run_release


BACKEND_DIR = Path(__file__).resolve().parents[1]
HEAD_REVISION = "a84f5c6e9d21"


def sqlite_url(database_path):
    return f"sqlite:///{database_path.as_posix()}"


def test_empty_database_upgrade_downgrade_and_upgrade(tmp_path):
    database_path = tmp_path / "migration-cycle.db"
    database_url = sqlite_url(database_path)

    run_release(
        database_url=database_url,
        environ={"APP_ENV": "testing"},
    )

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        assert set(db.metadata.tables).issubset(inspector.get_table_names())
        assert "alembic_version" in inspector.get_table_names()
        assert {
            index["name"] for index in inspector.get_indexes("products")
        }.issuperset({
            "ix_products_barcode",
            "ix_products_category",
            "ix_products_store",
            "ix_products_score",
        })
        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one() == HEAD_REVISION
    finally:
        engine.dispose()

    run_migrations("downgrade", "base", database_url=database_url)

    engine = create_engine(database_url)
    try:
        remaining_tables = set(inspect(engine).get_table_names())
        assert not set(db.metadata.tables).intersection(remaining_tables)
        assert remaining_tables == {"alembic_version"}
    finally:
        engine.dispose()

    run_migrations("upgrade", database_url=database_url)
    engine = create_engine(database_url)
    try:
        assert set(db.metadata.tables).issubset(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_upgrade_adopts_legacy_database_without_losing_users(tmp_path):
    database_path = tmp_path / "legacy.db"
    database_url = sqlite_url(database_path)
    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(120) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    is_admin BOOLEAN NOT NULL DEFAULT 0,
                    created_at DATETIME
                )
            """))
            connection.execute(
                text("""
                    INSERT INTO users (id, name, email, password_hash)
                    VALUES (7, 'Legacy User', 'legacy@example.com', 'hash')
                """)
            )
    finally:
        engine.dispose()

    run_release(
        database_url=database_url,
        environ={"APP_ENV": "testing"},
    )

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        assert {
            "email_verified",
            "invite_code",
            "referred_by_user_id",
            "bonus_scan_credits",
            "auth_version",
            "processing_restricted",
            "analytics_consent",
        }.issubset(user_columns)
        assert set(db.metadata.tables).issubset(inspector.get_table_names())
        with engine.connect() as connection:
            legacy_user = connection.execute(
                text("SELECT id, email FROM users WHERE id = 7")
            ).one()
            assert legacy_user == (7, "legacy@example.com")
    finally:
        engine.dispose()


def test_release_data_operations_are_idempotent(tmp_path):
    database_path = tmp_path / "release.db"
    database_url = sqlite_url(database_path)
    run_migrations("upgrade", database_url=database_url)

    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text("""
                    INSERT INTO users (name, email, password_hash, created_at)
                    VALUES ('Release Owner', 'owner@example.com', 'hash', CURRENT_TIMESTAMP)
                """)
            )
    finally:
        engine.dispose()

    release_environ = {"ADMIN_EMAIL": "owner@example.com", "APP_ENV": "testing"}
    run_release(database_url=database_url, environ=release_environ)

    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            first_result = connection.execute(
                text("SELECT is_admin, invite_code FROM users WHERE email = :email"),
                {"email": "owner@example.com"},
            ).one()
        assert bool(first_result.is_admin) is True
        assert first_result.invite_code.startswith("CEA")
    finally:
        engine.dispose()

    run_release(database_url=database_url, environ=release_environ)
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            second_result = connection.execute(
                text("SELECT is_admin, invite_code FROM users WHERE email = :email"),
                {"email": "owner@example.com"},
            ).one()
        assert bool(second_result.is_admin) is True
        assert second_result.invite_code == first_result.invite_code
    finally:
        engine.dispose()


def test_application_import_does_not_create_database_schema(tmp_path):
    database_path = tmp_path / "startup-read-only.db"
    environment = os.environ.copy()
    environment.update({
        "APP_ENV": "testing",
        "AUTH_SECRET": "migration-test-auth-secret-with-at-least-32-characters",
        "DATABASE_URL": sqlite_url(database_path),
        "EXTERNAL_CATALOG_ENABLED": "false",
        "OPEN_PRICES_ENABLED": "false",
    })

    result = subprocess.run(
        [sys.executable, "-c", "import app"],
        cwd=BACKEND_DIR,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    if database_path.exists():
        engine = create_engine(sqlite_url(database_path))
        try:
            assert inspect(engine).get_table_names() == []
        finally:
            engine.dispose()


def test_production_startup_fails_when_database_is_not_migrated(tmp_path):
    database_path = tmp_path / "unversioned-production.db"
    environment = os.environ.copy()
    environment.update({
        "APP_ENV": "production",
        "AUTH_SECRET": "migration-test-auth-secret-with-at-least-32-characters",
        "DATABASE_URL": sqlite_url(database_path),
        "EXTERNAL_CATALOG_ENABLED": "false",
        "OPEN_PRICES_ENABLED": "false",
    })

    result = subprocess.run(
        [sys.executable, "-c", "import app"],
        cwd=BACKEND_DIR,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert result.returncode != 0
    assert "Database migration revision mismatch" in result.stderr


def test_head_assertion_accepts_migrated_database(tmp_path):
    database_url = sqlite_url(tmp_path / "migrated-production.db")
    run_migrations("upgrade", database_url=database_url)

    assert_database_at_head(database_url=database_url)


def test_migration_cli_fails_closed_on_database_error(tmp_path):
    database_path = tmp_path / "corrupt.db"
    database_path.write_text("this is not a sqlite database", encoding="ascii")
    environment = os.environ.copy()
    environment.update({
        "APP_ENV": "testing",
        "DATABASE_URL": sqlite_url(database_path),
    })

    result = subprocess.run(
        [sys.executable, "migration.py", "upgrade"],
        cwd=BACKEND_DIR,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert result.returncode != 0
    assert "Database migration failed" in result.stderr


def test_production_start_commands_release_before_gunicorn():
    repository_root = BACKEND_DIR.parent
    render_config = (repository_root / "render.yaml").read_text(encoding="utf-8")
    dockerfile = (BACKEND_DIR / "Dockerfile").read_text(encoding="utf-8")

    expected_order = "python migration.py release && exec gunicorn"
    assert expected_order in render_config
    assert expected_order in dockerfile
