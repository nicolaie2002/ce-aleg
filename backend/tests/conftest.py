import os


os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUTH_SECRET", "pytest-auth-secret-with-at-least-32-characters")
os.environ.setdefault("COOKIE_SECURE", "false")
os.environ.setdefault("EXPOSE_DEV_AUTH_LINKS", "false")
os.environ.setdefault("EMAIL_PROVIDER", "smtp")
os.environ.setdefault("EMAIL_SMTP_HOST", "")
os.environ.setdefault("EXTERNAL_CATALOG_ENABLED", "false")
os.environ.setdefault("OPEN_PRICES_ENABLED", "false")

import pytest

from app import app as flask_app
from database import db


@pytest.fixture()
def app():
    flask_app.config.update(TESTING=True)

    with flask_app.app_context():
        db.drop_all()
        db.create_all()

    yield flask_app

    with flask_app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
