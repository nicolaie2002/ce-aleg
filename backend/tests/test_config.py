import pytest
from flask import Flask

from app_factory import create_app
from config import DEFAULT_AUTH_SECRET, RuntimeConfig, normalize_database_url, read_secret_env
from routes import BLUEPRINTS, blueprint_for_rule


def test_postgres_urls_use_psycopg_driver():
    assert normalize_database_url("postgres://db.example/app") == (
        "postgresql+psycopg://db.example/app"
    )
    assert normalize_database_url("postgresql://db.example/app") == (
        "postgresql+psycopg://db.example/app"
    )


def test_production_config_requires_database_and_strong_auth_secret():
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        RuntimeConfig.from_env({"APP_ENV": "production", "AUTH_SECRET": "x" * 40})

    with pytest.raises(RuntimeError, match="AUTH_SECRET"):
        RuntimeConfig.from_env({
            "APP_ENV": "production",
            "DATABASE_URL": "postgresql://db.example/app",
            "AUTH_SECRET": DEFAULT_AUTH_SECRET,
        })


def test_runtime_config_applies_safe_defaults_to_flask():
    config = RuntimeConfig.from_env({"APP_ENV": "test", "MAX_UPLOAD_MB": "4"})
    flask_app = Flask(__name__)

    config.apply_to(flask_app)

    assert flask_app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///cealeg.db"
    assert flask_app.config["MAX_CONTENT_LENGTH"] == 4 * 1024 * 1024
    assert len(flask_app.config["AUTH_SECRET"]) >= 32


def test_postgres_ssl_is_required_in_production_and_optional_in_ci():
    production = RuntimeConfig.from_env({
        "APP_ENV": "production",
        "DATABASE_URL": "postgresql://db.example/app",
        "AUTH_SECRET": "x" * 40,
    })
    ci = RuntimeConfig.from_env({
        "APP_ENV": "test",
        "DATABASE_URL": "postgresql://localhost/app",
        "DATABASE_SSLMODE": "disable",
    })

    assert production.sqlalchemy_engine_options["connect_args"] == {"sslmode": "require"}
    assert ci.sqlalchemy_engine_options["connect_args"] == {"sslmode": "disable"}


def test_secret_reader_handles_accidentally_prefixed_values():
    assert read_secret_env("CRON_SECRET", environ={"CRON_SECRET": "CRON_SECRET=abc"}) == "abc"


def test_factory_creates_independent_configured_app_shells():
    config = RuntimeConfig.from_env({"APP_ENV": "test", "AUTH_SECRET": "x" * 40})

    first = create_app("first_test_app", config, {"TESTING": True})
    second = create_app("second_test_app", config)

    assert first is not second
    assert first.testing is True
    assert second.testing is False
    assert first.extensions["cealeg_runtime_config"] is config


def test_route_registry_covers_expected_production_domains():
    assert len(BLUEPRINTS) == 13
    assert blueprint_for_rule("/health").name == "system"
    assert blueprint_for_rule("/register").name == "auth"
    assert blueprint_for_rule("/products/search").name == "products"
    assert blueprint_for_rule("/admin/overview").name == "admin"
    assert blueprint_for_rule("/submissions/add").name == "submissions"
