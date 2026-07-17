import io
from types import SimpleNamespace
from datetime import timedelta

from werkzeug.security import generate_password_hash

import app as app_module
from database import db
from models import ConsentRecord, Product, SearchEvent, User
from time_utils import utcnow
from ai_provider import extract_response_text


def create_user(email="user@example.com", admin=False):
    user = User(
        name="Test User",
        email=email,
        password_hash=generate_password_hash("A-secure-password-123"),
        email_verified=True,
        is_admin=admin,
    )
    db.session.add(user)
    db.session.commit()
    return user


def auth_cookie_for(user):
    return app_module.get_auth_serializer().dumps({
        "user_id": user.id,
        "auth_version": int(user.auth_version or 0),
    })


def test_admin_monitoring_requires_authentication(app, client):
    response = client.get("/admin/monitoring")

    assert response.status_code == 401
    assert response.get_json()["code"] == "auth_required"


def test_openapi_contract_lists_protected_admin_route(app, client):
    response = client.get("/api/openapi.json")

    assert response.status_code == 200
    document = response.get_json()
    assert document["openapi"] == "3.1.0"
    operation = document["paths"]["/admin/monitoring"]["get"]
    assert operation["security"] == [{"sessionCookie": []}]
    assert "403" in operation["responses"]


def test_runtime_openapi_combines_explicit_schemas_with_every_flask_route(app, client):
    response = client.get("/api/openapi.json")

    assert response.status_code == 200
    document = response.get_json()
    assert document["jsonSchemaDialect"].endswith("2020-12/schema")
    assert "RegisterRequest" in document["components"]["schemas"]
    assert (
        document["paths"]["/support/contact"]["post"]["x-validation-helper"]
        == "validate_support_payload"
    )
    assert "/admin/catalog/quality" in document["paths"]
    assert "/internal/cron/maintenance" in document["paths"]

    operation_ids = [
        operation["operationId"]
        for path_item in document["paths"].values()
        for operation in path_item.values()
        if isinstance(operation, dict) and "operationId" in operation
    ]
    assert len(operation_ids) == len(set(operation_ids))


def test_admin_monitoring_rejects_regular_user(app, client):
    with app.app_context():
        user = create_user()
        cookie = auth_cookie_for(user)

    client.set_cookie(app_module.AUTH_COOKIE_NAME, cookie)
    response = client.get("/admin/monitoring")

    assert response.status_code == 403
    assert response.get_json()["code"] == "admin_required"


def test_auth_version_revokes_existing_session(app, client):
    with app.app_context():
        user = create_user()
        old_cookie = auth_cookie_for(user)
        user.password_hash = generate_password_hash("A-new-secure-password-456")
        user.auth_version += 1
        db.session.commit()

    client.set_cookie(app_module.AUTH_COOKIE_NAME, old_cookie)
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_invite_lookup_accepts_display_separators(app):
    with app.app_context():
        inviter = create_user(email="inviter@example.com")
        inviter.invite_code = "CE-PRO001"
        db.session.commit()

        assert app_module.find_inviter_by_code("cepro001").id == inviter.id
        assert app_module.find_inviter_by_code("CE-PRO001").id == inviter.id


def test_account_export_excludes_credentials_and_restriction_blocks_processing(app, client):
    with app.app_context():
        user = create_user()
        cookie = auth_cookie_for(user)

    client.set_cookie(app_module.AUTH_COOKIE_NAME, cookie)
    export_response = client.get("/account/data-export")

    assert export_response.status_code == 200
    assert "password" not in export_response.get_data(as_text=True).lower()
    restriction_response = client.post("/account/restriction", json={"restricted": True})
    assert restriction_response.status_code == 200

    blocked_response = client.post(
        "/analyze",
        data={"image": (io.BytesIO(b"not an image"), "fake.jpg")},
        content_type="multipart/form-data",
    )
    assert blocked_response.status_code == 423
    assert blocked_response.get_json()["code"] == "processing_restricted"


def test_non_finite_numeric_values_are_rejected():
    assert app_module.parse_optional_float("NaN") is None
    assert app_module.parse_optional_float("Infinity") is None
    assert app_module.parse_optional_float("-Infinity") is None


def test_vision_provider_extracts_structured_output_text():
    payload = {"output": [{"content": [{"type": "output_text", "text": "{\"identified\": false}"}]}]}

    assert extract_response_text(payload) == '{"identified": false}'


def test_csv_formula_cells_are_neutralized():
    response = app_module.csv_response(
        "test.csv",
        ["query"],
        [{"query": "=HYPERLINK(\"https://example.test\")"}],
    )

    assert "'=HYPERLINK" in response.get_data(as_text=True)


def test_barcode_import_uses_verified_source_data(app, client, monkeypatch):
    verified_product = {
        "product_name": "Verified yogurt",
        "brands": "Verified Brand",
        "categories_tags": ["en:yogurts"],
        "nutriments": {"energy-kcal_100g": 60, "sugars_100g": 4},
    }

    with app.app_context():
        user = create_user()
        cookie = auth_cookie_for(user)

    monkeypatch.setattr(app_module, "fetch_off_product_by_barcode", lambda barcode: verified_product)
    client.set_cookie(app_module.AUTH_COOKIE_NAME, cookie)
    response = client.post("/barcode/import", json={
        "barcode": "5941238013309",
        "name": "Attacker supplied name",
        "score": 10,
    })

    assert response.status_code == 201
    with app.app_context():
        product = Product.query.filter_by(barcode="5941238013309").one()
        assert product.name == "Verified yogurt"
        assert product.name != "Attacker supplied name"


def test_analyze_rejects_fake_image_without_persisting(app, client):
    with app.app_context():
        user = create_user()
        cookie = auth_cookie_for(user)

    client.set_cookie(app_module.AUTH_COOKIE_NAME, cookie)
    response = client.post(
        "/analyze",
        data={
            "image": (io.BytesIO(b"not an image"), "fake.jpg"),
            "product_query": "test",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json()["code"] == "invalid_scan_image"


def test_stripe_webhook_is_processed_once(app, client, monkeypatch):
    event = {
        "id": "evt_idempotent_test",
        "type": "checkout.session.completed",
        "data": {"object": {"id": "cs_test", "metadata": {}}},
    }
    calls = []
    stripe_stub = SimpleNamespace(
        Webhook=SimpleNamespace(construct_event=lambda **_kwargs: event),
    )

    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setattr(app_module, "stripe", stripe_stub)
    monkeypatch.setattr(
        app_module,
        "handle_stripe_checkout_completed",
        lambda payload: calls.append(payload["id"]),
    )

    first = client.post(
        "/billing/stripe/webhook",
        data=b"{}",
        headers={"Stripe-Signature": "test"},
    )
    second = client.post(
        "/billing/stripe/webhook",
        data=b"{}",
        headers={"Stripe-Signature": "test"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.get_json()["duplicate"] is True
    assert calls == ["cs_test"]


def test_stripe_checkout_uses_scoped_idempotency_keys(app, monkeypatch):
    calls = []

    def create_session(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(id="cs_test_idempotent", url="https://checkout.example.test")

    monkeypatch.setattr(
        app_module,
        "stripe",
        SimpleNamespace(
            checkout=SimpleNamespace(
                Session=SimpleNamespace(create=create_session),
            ),
        ),
    )
    user = SimpleNamespace(id=42, email="checkout@example.com")

    with app.test_request_context(
        "/billing/checkout",
        method="POST",
        headers={"Idempotency-Key": "client-operation-123"},
    ):
        first_key = app_module.build_stripe_idempotency_key(
            "subscription-checkout",
            user.id,
            "pro",
            "monthly",
        )
        repeated_key = app_module.build_stripe_idempotency_key(
            "subscription-checkout",
            user.id,
            "pro",
            "monthly",
        )
        other_user_key = app_module.build_stripe_idempotency_key(
            "subscription-checkout",
            43,
            "pro",
            "monthly",
        )
        result = app_module.create_checkout_session_with_stale_customer_retry(
            {"mode": "subscription"},
            None,
            user,
            first_key,
        )

    assert first_key == repeated_key
    assert first_key != other_user_key
    assert calls[0]["idempotency_key"] == first_key
    assert result.id == "cs_test_idempotent"


def test_sentry_sanitizer_removes_request_secrets():
    event = {
        "request": {
            "data": {"password": "secret"},
            "cookies": {"session": "secret"},
            "query_string": "token=secret",
            "headers": {
                "Authorization": "Bearer secret",
                "Cookie": "session=secret",
                "Accept": "application/json",
            },
        },
        "user": {"id": "12", "email": "private@example.com", "ip_address": "127.0.0.1"},
    }

    sanitized = app_module.sanitize_sentry_event(event, None)

    assert "data" not in sanitized["request"]
    assert "cookies" not in sanitized["request"]
    assert sanitized["request"]["query_string"] == ""
    assert "Authorization" not in sanitized["request"]["headers"]
    assert "Cookie" not in sanitized["request"]["headers"]
    assert sanitized["user"] == {"id": "12"}


def test_account_export_excludes_auth_secrets_and_other_users(app, client):
    with app.app_context():
        user = create_user("owner@example.com")
        create_user("other@example.com")
        cookie = auth_cookie_for(user)

    client.set_cookie(app_module.AUTH_COOKIE_NAME, cookie)
    response = client.get("/account/export")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["account"]["email"] == "owner@example.com"
    assert "password_hash" not in response.get_data(as_text=True)
    assert "other@example.com" not in response.get_data(as_text=True)


def test_processing_restriction_blocks_mutations_until_lifted(app, client):
    with app.app_context():
        user = create_user()
        user_id = user.id
        cookie = auth_cookie_for(user)

    client.set_cookie(app_module.AUTH_COOKIE_NAME, cookie)
    restricted = client.post("/account/restriction", json={"restricted": True})
    blocked = client.post("/favorites/add", json={"user_id": user_id, "name": "Test"})
    lifted = client.post("/account/restriction", json={"restricted": False})

    assert restricted.status_code == 200
    assert blocked.status_code == 423
    assert blocked.get_json()["code"] == "processing_restricted"
    assert lifted.status_code == 200


def test_authenticated_consent_is_logged(app, client):
    with app.app_context():
        user = create_user()
        user_id = user.id
        cookie = auth_cookie_for(user)

    client.set_cookie(app_module.AUTH_COOKIE_NAME, cookie)
    response = client.post("/privacy/consent", json={
        "type": "analytics",
        "granted": False,
        "policyVersion": "2026-07",
    })

    assert response.status_code == 201
    with app.app_context():
        record = ConsentRecord.query.filter_by(user_id=user_id).one()
        assert record.granted is False


def test_retention_supports_dry_run_and_apply(app):
    with app.app_context():
        user = create_user()
        old_search = SearchEvent(
            user_id=user.id,
            search_text="old query",
            result_count=0,
            source="test",
            created_at=utcnow() - timedelta(days=500),
        )
        db.session.add(old_search)
        db.session.commit()

        preview = app_module.run_retention_cleanup(apply_changes=False)
        assert preview["searchEvents"] == 1
        assert SearchEvent.query.count() == 1

        applied = app_module.run_retention_cleanup(apply_changes=True)
        assert applied["searchEvents"] == 1
        assert SearchEvent.query.count() == 0
