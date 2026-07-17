from types import SimpleNamespace

from werkzeug.security import check_password_hash, generate_password_hash

import app as app_module
from database import db
from models import Subscription, User


PASSWORD = "A-secure-password-123!"
NEW_PASSWORD = "A-new-secure-password-456!"


def create_user(email="member@example.com", *, verified=True):
    user = User(
        name="Test Member",
        email=email,
        password_hash=generate_password_hash(PASSWORD),
        email_verified=verified,
    )
    db.session.add(user)
    db.session.commit()
    return user


def auth_cookie_for(user):
    return app_module.get_auth_serializer().dumps({
        "user_id": user.id,
        "auth_version": int(user.auth_version or 0),
    })


def authenticate(client, user):
    client.set_cookie(app_module.AUTH_COOKIE_NAME, auth_cookie_for(user))


def test_registration_verification_and_login_lifecycle(app, client, monkeypatch):
    verification_requests = []
    monkeypatch.setattr(
        app_module,
        "send_email_verification_email",
        lambda user: (verification_requests.append(user.email) or True, "https://example.test/verify"),
    )
    monkeypatch.setattr(app_module, "send_welcome_email", lambda _user: True)

    registration = client.post("/register", json={
        "name": "New Member",
        "email": "NEW@EXAMPLE.COM",
        "password": PASSWORD,
        "ageConfirmed": True,
        "acceptedTerms": True,
    })

    assert registration.status_code == 201
    assert registration.get_json()["user"]["email"] == "new@example.com"
    assert registration.get_json()["user"]["emailVerified"] is False
    assert verification_requests == ["new@example.com"]

    with app.app_context():
        user = User.query.filter_by(email="new@example.com").one()
        token = app_module.create_email_verification_token(user)

    unverified_login = client.post("/login", json={
        "email": "new@example.com",
        "password": PASSWORD,
    })
    assert unverified_login.status_code == 403
    assert unverified_login.get_json()["code"] == "email_not_verified"

    verification = client.post("/auth/verify-email", json={"token": token})
    assert verification.status_code == 200
    assert verification.get_json()["user"]["emailVerified"] is True
    assert app_module.AUTH_COOKIE_NAME in verification.headers.get("Set-Cookie", "")

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.get_json()["user"]["email"] == "new@example.com"

    duplicate = client.post("/register", json={
        "name": "Duplicate",
        "email": "new@example.com",
        "password": PASSWORD,
        "ageConfirmed": True,
        "acceptedTerms": True,
    })
    assert duplicate.status_code == 409


def test_password_reset_rotates_sessions_and_accepts_new_password(app, client, monkeypatch):
    monkeypatch.setattr(app_module, "send_transactional_email", lambda *_args, **_kwargs: True)

    with app.app_context():
        user = create_user()
        old_cookie = auth_cookie_for(user)
        token = app_module.create_password_reset_token(user)
        user_id = user.id

    reset = client.post("/reset-password", json={
        "token": token,
        "password": NEW_PASSWORD,
    })

    assert reset.status_code == 200
    assert app_module.AUTH_COOKIE_NAME in reset.headers.get("Set-Cookie", "")

    with app.app_context():
        updated_user = db.session.get(User, user_id)
        assert check_password_hash(updated_user.password_hash, NEW_PASSWORD)
        assert updated_user.auth_version == 1

    stale_session_client = app.test_client()
    stale_session_client.set_cookie(app_module.AUTH_COOKIE_NAME, old_cookie)
    assert stale_session_client.get("/auth/me").status_code == 401

    login = app.test_client().post("/login", json={
        "email": "member@example.com",
        "password": NEW_PASSWORD,
    })
    assert login.status_code == 200


def test_billing_requires_auth_and_exposes_free_plan_status(app, client):
    assert client.get("/billing/status").status_code == 401
    assert client.post("/billing/checkout", json={"plan": "pro"}).status_code == 401

    with app.app_context():
        user = create_user()
        authenticate(client, user)

    status = client.get("/billing/status")

    assert status.status_code == 200
    payload = status.get_json()
    assert payload["subscription"]["plan"] == "free"
    assert payload["subscription"]["status"] == "active"
    assert {"free", "pro", "family"}.issubset(payload["plans"])


def test_checkout_and_portal_fail_safely_without_stripe_configuration(
    app, client, monkeypatch
):
    with app.app_context():
        user = create_user()
        authenticate(client, user)

    monkeypatch.setattr(app_module, "PAYMENT_PROVIDER", "stripe")
    monkeypatch.setattr(app_module, "configure_stripe", lambda: False)

    invalid_plan = client.post("/billing/checkout", json={"plan": "enterprise"})
    checkout = client.post("/billing/checkout", json={
        "plan": "pro",
        "billingInterval": "monthly",
    })
    portal = client.post("/billing/portal", json={})

    assert invalid_plan.status_code == 400
    assert checkout.status_code == 503
    assert checkout.get_json()["code"] == "stripe_not_configured"
    assert portal.status_code == 503
    assert portal.get_json()["code"] == "stripe_not_configured"


def test_active_subscription_cannot_start_a_second_checkout(app, client, monkeypatch):
    with app.app_context():
        user = create_user()
        subscription = Subscription(
            user_id=user.id,
            plan="pro",
            status="active",
            provider="stripe",
        )
        db.session.add(subscription)
        db.session.commit()
        authenticate(client, user)

    monkeypatch.setattr(app_module, "PAYMENT_PROVIDER", "stripe")
    monkeypatch.setattr(app_module, "configure_stripe", lambda: True)
    monkeypatch.setattr(app_module, "get_stripe_price_id", lambda *_args: "price_test")

    response = client.post("/billing/checkout", json={"plan": "family"})

    assert response.status_code == 409
    assert response.get_json()["code"] == "active_subscription_exists"
    assert response.get_json()["currentPlan"] == "pro"


def test_gamification_read_paths_and_invalid_actions_are_stable(app, client):
    with app.app_context():
        user = create_user()
        authenticate(client, user)

    packs = client.get("/gamification/coin-packs")
    summary = client.get("/gamification/summary")
    leaderboard = client.get("/gamification/leaderboard?period=weekly")
    missing_mission = client.post("/gamification/claim", json={"missionId": "missing"})
    invalid_reward = client.post("/gamification/redeem", json={"itemId": "missing"})
    insufficient_coins = client.post(
        "/gamification/redeem",
        json={"itemId": app_module.CECOIN_SHOP_ITEMS[0]["id"]},
    )

    assert packs.status_code == 200
    assert len(packs.get_json()["coinPacks"]) == 3
    assert summary.status_code == 200
    assert summary.get_json()["coins"] == 0
    assert leaderboard.status_code == 200
    assert leaderboard.get_json()["period"] == "weekly"
    assert missing_mission.status_code == 400
    assert invalid_reward.status_code == 400
    assert insufficient_coins.status_code == 402
    assert insufficient_coins.get_json()["coins"] == 0


def test_cecoin_checkout_rejects_bad_pack_and_missing_stripe(app, client, monkeypatch):
    with app.app_context():
        user = create_user()
        authenticate(client, user)

    invalid = client.post("/gamification/coin-checkout", json={"packId": "unknown"})
    monkeypatch.setattr(app_module, "configure_stripe", lambda: False)
    missing_config = client.post("/gamification/coin-checkout", json={"packId": "bronze"})
    invalid_sync = client.post(
        "/gamification/coin-checkout/sync",
        json={"sessionId": "not-a-stripe-session"},
    )

    assert invalid.status_code == 400
    assert missing_config.status_code == 503
    assert missing_config.get_json()["code"] == "cecoins_checkout_not_configured"
    assert invalid_sync.status_code == 400


def test_support_message_is_delivered_to_contact_address(app, client, monkeypatch):
    deliveries = []
    monkeypatch.setattr(app_module, "CONTACT_EMAIL", "contact@cealeg.shop")
    monkeypatch.setattr(app_module, "is_email_configured", lambda: True)
    monkeypatch.setattr(
        app_module,
        "send_transactional_email",
        lambda *args, **_kwargs: deliveries.append(args) or True,
    )

    response = client.post("/support/contact", json={
        "email": "visitor@example.com",
        "topic": "Account help",
        "message": "I need help confirming my account.",
    })

    assert response.status_code == 200
    assert deliveries[0][0] == "contact@cealeg.shop"
    assert "Account help" in deliveries[0][1]


def test_support_message_reports_missing_email_configuration(app, client, monkeypatch):
    monkeypatch.setattr(app_module, "CONTACT_EMAIL", "contact@cealeg.shop")
    monkeypatch.setattr(app_module, "is_email_configured", lambda: False)

    response = client.post("/support/contact", json={
        "email": "visitor@example.com",
        "topic": "Account help",
        "message": "I need help confirming my account.",
    })

    assert response.status_code == 503


def test_stripe_webhook_requires_server_secret(app, client, monkeypatch):
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    monkeypatch.setattr(app_module, "stripe", SimpleNamespace())

    response = client.post(
        "/billing/stripe/webhook",
        data=b"{}",
        headers={"Stripe-Signature": "test"},
    )

    assert response.status_code == 503
