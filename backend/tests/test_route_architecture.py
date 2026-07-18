import app as app_module
from types import SimpleNamespace

from config import RuntimeConfig
from routes.registry import (
    ROUTE_ACCESS_POLICIES,
    ROUTE_OWNERS,
    VALID_ACCESS_POLICIES,
)


PUBLIC_MUTATION_ENDPOINTS = {
    "confirm_account_deletion",
    "contact_support",
    "forgot_password",
    "get_password_strength",
    "log_consent",
    "login",
    "register",
    "resend_email_verification",
    "reset_password",
    "track_analytics_event",
    "verify_email",
}


def _route_endpoint(rule):
    return str(rule.endpoint).rsplit(".", 1)[-1]


def _runtime_config(database_url, auth_secret):
    return RuntimeConfig.from_env(
        {
            "APP_ENV": "test",
            "DATABASE_URL": database_url,
            "AUTH_SECRET": auth_secret,
            "MAX_UPLOAD_MB": "8",
            "MAX_IMAGE_PIXELS": "24000000",
        }
    )


def test_every_application_route_has_explicit_owner_and_access_policy(app):
    failures = []

    for rule in app.url_map.iter_rules():
        endpoint = _route_endpoint(rule)

        if endpoint == "static":
            continue

        policy = ROUTE_ACCESS_POLICIES.get(endpoint)
        owner = ROUTE_OWNERS.get(endpoint)

        if policy not in VALID_ACCESS_POLICIES or not owner:
            failures.append(f"{rule.rule} -> {endpoint}: policy={policy}, owner={owner}")

    assert failures == []


def test_public_mutations_are_a_small_reviewed_allowlist(app):
    public_mutations = {
        _route_endpoint(rule)
        for rule in app.url_map.iter_rules()
        if ROUTE_ACCESS_POLICIES.get(_route_endpoint(rule)) == "public"
        and set(rule.methods or ()) & {"POST", "PUT", "PATCH", "DELETE"}
    }

    assert public_mutations == PUBLIC_MUTATION_ENDPOINTS
    assert ROUTE_ACCESS_POLICIES["stripe_webhook"] == "signed-webhook"
    assert ROUTE_ACCESS_POLICIES["run_cron_maintenance"] == "internal-secret"


def test_missing_route_policy_fails_closed(client, monkeypatch):
    monkeypatch.setattr(app_module, "get_route_access_policy", lambda _endpoint: None)

    response = client.get("/version")

    assert response.status_code == 503
    assert response.get_json()["code"] == "route_policy_missing"


def test_factory_creates_isolated_fully_registered_apps():
    first = app_module.create_application(
        runtime_config=_runtime_config(
            "sqlite:///:memory:", "first-isolated-auth-secret-with-32-characters"
        ),
        config_overrides={"TESTING": True, "FACTORY_MARKER": "first"},
    )
    second = app_module.create_application(
        runtime_config=_runtime_config(
            "sqlite:///second-factory.db", "second-isolated-auth-secret-with-32-characters"
        ),
        config_overrides={"TESTING": True, "FACTORY_MARKER": "second"},
    )

    assert first is not second
    assert first.config["FACTORY_MARKER"] == "first"
    assert second.config["FACTORY_MARKER"] == "second"
    assert first.config["SQLALCHEMY_DATABASE_URI"] != second.config["SQLALCHEMY_DATABASE_URI"]
    assert len(list(first.url_map.iter_rules())) == len(list(second.url_map.iter_rules()))
    assert first.test_client().get("/health").status_code == 200
    assert second.test_client().get("/health").status_code == 200


def test_legacy_database_initializer_cannot_mutate_production_schema(app, monkeypatch):
    create_all_called = False

    def record_create_all():
        nonlocal create_all_called
        create_all_called = True

    original_runtime = app.extensions["cealeg_runtime_config"]
    app.extensions["cealeg_runtime_config"] = SimpleNamespace(production_mode=True)
    monkeypatch.setattr(app_module.db, "create_all", record_create_all)

    try:
        with app.test_request_context("/init-db"):
            response, status = app_module.init_db()
    finally:
        app.extensions["cealeg_runtime_config"] = original_runtime

    assert status == 409
    assert response.get_json()["code"] == "release_migration_required"
    assert create_all_called is False
