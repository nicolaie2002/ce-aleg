import os
import secrets
from dataclasses import dataclass


DEFAULT_AUTH_SECRET = "local-development-change-this-secret"
PRODUCTION_ENVIRONMENTS = frozenset({"production", "prod"})


def read_secret_env(name, default="", environ=None):
    source = environ if environ is not None else os.environ
    value = str(source.get(name, default) or "").strip().strip("\"'")
    prefixed_name = f"{name}="

    if value.startswith(prefixed_name):
        value = value[len(prefixed_name):].strip().strip("\"'")

    return value


def normalize_database_url(value):
    database_url = str(value or "").strip()

    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    return database_url


@dataclass(frozen=True)
class RuntimeConfig:
    app_env: str
    production_mode: bool
    database_url: str
    database_sslmode: str
    auth_secret: str
    max_upload_bytes: int
    max_image_pixels: int

    @property
    def sqlalchemy_database_uri(self):
        return self.database_url or "sqlite:///cealeg.db"

    @property
    def sqlalchemy_engine_options(self):
        if not self.database_url.startswith("postgresql+psycopg://"):
            return {}

        options = {
            "pool_pre_ping": True,
            "pool_recycle": 240,
        }
        if self.database_sslmode:
            options["connect_args"] = {"sslmode": self.database_sslmode}
        return options

    def apply_to(self, flask_app):
        flask_app.config.update(
            SQLALCHEMY_DATABASE_URI=self.sqlalchemy_database_uri,
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            SQLALCHEMY_ENGINE_OPTIONS=self.sqlalchemy_engine_options,
            MAX_CONTENT_LENGTH=self.max_upload_bytes,
            AUTH_SECRET=self.auth_secret,
        )

    @classmethod
    def from_env(cls, environ=None):
        source = environ if environ is not None else os.environ
        app_env = str(source.get("APP_ENV", "development") or "development").strip().lower()
        production_mode = app_env in PRODUCTION_ENVIRONMENTS
        database_url = normalize_database_url(source.get("DATABASE_URL", ""))
        database_sslmode = str(
            source.get("DATABASE_SSLMODE", "require" if production_mode else "") or ""
        ).strip()
        auth_secret = read_secret_env("AUTH_SECRET", environ=source)

        if production_mode and not database_url:
            raise RuntimeError(
                "DATABASE_URL is required in production. "
                "Refusing to use ephemeral SQLite storage."
            )

        if production_mode and (
            not auth_secret
            or auth_secret == DEFAULT_AUTH_SECRET
            or len(auth_secret) < 32
        ):
            raise RuntimeError(
                "AUTH_SECRET must be a unique value of at least 32 characters in production."
            )

        try:
            max_upload_mb = max(1, int(source.get("MAX_UPLOAD_MB", "8")))
            max_image_pixels = max(1, int(source.get("MAX_IMAGE_PIXELS", "24000000")))
        except (TypeError, ValueError) as error:
            raise RuntimeError("Upload limits must be positive integers.") from error

        return cls(
            app_env=app_env,
            production_mode=production_mode,
            database_url=database_url,
            database_sslmode=database_sslmode,
            auth_secret=auth_secret or secrets.token_urlsafe(48),
            max_upload_bytes=max_upload_mb * 1024 * 1024,
            max_image_pixels=max_image_pixels,
        )


class DevelopmentConfig(RuntimeConfig):
    """Named configuration type for local development and tooling."""


class TestConfig(RuntimeConfig):
    """Named configuration type for isolated test environments."""


class ProductionConfig(RuntimeConfig):
    """Named configuration type for hosted production environments."""
