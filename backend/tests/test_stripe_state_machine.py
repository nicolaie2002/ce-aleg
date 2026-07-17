from datetime import datetime
from types import SimpleNamespace

from werkzeug.security import generate_password_hash

import app as app_module
from database import db
from models import Subscription, UsageEvent, User


def create_user(email="billing@example.com"):
    user = User(
        name="Billing User",
        email=email,
        password_hash=generate_password_hash("A-secure-password-123!"),
        email_verified=True,
    )
    db.session.add(user)
    db.session.commit()
    return user


def authenticate(client, user):
    token = app_module.get_auth_serializer().dumps({
        "user_id": user.id,
        "auth_version": int(user.auth_version or 0),
    })
    client.set_cookie(app_module.AUTH_COOKIE_NAME, token)


def stripe_subscription(user, **overrides):
    values = {
        "id": "sub_active",
        "customer": "cus_active",
        "status": "active",
        "metadata": {"user_id": str(user.id)},
        "items": {"data": [{"id": "si_active", "price": {"id": "price_pro"}}]},
        "current_period_start": 1_700_000_000,
        "current_period_end": 1_800_000_000,
        "created": 1_690_000_000,
    }
    values.update(overrides)
    return values


def test_stripe_configuration_price_mapping_and_time_helpers(app, monkeypatch):
    stripe_stub = SimpleNamespace()
    monkeypatch.setattr(app_module, "stripe", stripe_stub)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_local_only")
    monkeypatch.setenv("STRIPE_MAX_NETWORK_RETRIES", "4")
    monkeypatch.setenv("STRIPE_API_VERSION", "2025-01-27.acacia")
    monkeypatch.setenv("STRIPE_PRO_PRICE_ID", "price_pro")
    monkeypatch.setenv("STRIPE_FAMILY_YEARLY_PRICE_ID", "price_family_year")

    assert app_module.configure_stripe() is True
    assert stripe_stub.api_key == "sk_test_local_only"
    assert stripe_stub.max_network_retries == 4
    assert stripe_stub.api_version == "2025-01-27.acacia"
    assert app_module.get_plan_for_stripe_price("price_pro") == "pro"
    assert app_module.get_plan_for_stripe_price("price_family_year") == "family"
    assert app_module.get_plan_for_stripe_price("price_unknown") is None
    assert app_module.normalize_billing_interval("annual") == "yearly"
    assert app_module.normalize_billing_interval("unexpected") == "monthly"
    assert app_module.datetime_from_unix(1_700_000_000) == datetime(2023, 11, 14, 22, 13, 20)
    assert app_module.datetime_from_unix("invalid") is None
    assert app_module.stripe_subscription_status_to_local("trialing") == "active"
    assert app_module.stripe_subscription_status_to_local("unpaid") == "canceled"
    assert app_module.stripe_subscription_status_to_local("past_due") == "inactive"


def test_customer_validation_and_checkout_customer_selection(app, monkeypatch):
    with app.app_context():
        user = create_user()
        subscription = Subscription(
            user_id=user.id,
            plan="pro",
            status="inactive",
            provider="stripe",
            provider_customer_id="cus_valid",
        )
        db.session.add(subscription)
        db.session.commit()

        monkeypatch.setattr(app_module, "configure_stripe", lambda: True)
        monkeypatch.setattr(
            app_module,
            "stripe",
            SimpleNamespace(Customer=SimpleNamespace(retrieve=lambda _id: {"deleted": False})),
        )
        params = {}
        selected = app_module.apply_stripe_customer_to_checkout(
            params,
            subscription,
            user,
            allow_customer_update=True,
        )

        assert selected == "cus_valid"
        assert params["customer"] == "cus_valid"
        assert params["customer_update"] == {"address": "auto", "name": "auto"}

        app_module.stripe.Customer.retrieve = lambda _id: {"deleted": True}
        stale_params = {}
        assert app_module.apply_stripe_customer_to_checkout(
            stale_params, subscription, user
        ) is None
        assert stale_params["customer_email"] == user.email
        assert subscription.provider_customer_id is None


def test_checkout_retries_once_without_stale_customer(app, monkeypatch):
    calls = []

    def create_session(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise RuntimeError("No such customer: cus_stale")
        return SimpleNamespace(id="cs_retry", url="https://checkout.example.test/retry")

    with app.app_context():
        user = create_user()
        subscription = Subscription(
            user_id=user.id,
            plan="free",
            status="active",
            provider="stripe",
            provider_customer_id="cus_stale",
        )
        db.session.add(subscription)
        db.session.commit()
        monkeypatch.setattr(
            app_module,
            "stripe",
            SimpleNamespace(checkout=SimpleNamespace(Session=SimpleNamespace(create=create_session))),
        )

        result = app_module.create_checkout_session_with_stale_customer_retry(
            {"customer": "cus_stale", "customer_update": {"address": "auto"}},
            subscription,
            user,
            "cealeg:test:key",
        )

        assert result.id == "cs_retry"
        assert len(calls) == 2
        assert calls[1]["customer_email"] == user.email
        assert "customer" not in calls[1]
        assert calls[1]["idempotency_key"].endswith(":stale-retry")
        assert subscription.provider_customer_id is None


def test_subscription_sync_updates_active_plan_and_ignores_lower_old_plan(
    app, monkeypatch
):
    monkeypatch.setenv("STRIPE_PRO_PRICE_ID", "price_pro")
    monkeypatch.setenv("STRIPE_FAMILY_PRICE_ID", "price_family")

    with app.app_context():
        user = create_user()
        active = app_module.sync_stripe_subscription(stripe_subscription(user))

        assert active.plan == "pro"
        assert active.status == "active"
        assert active.provider_subscription_id == "sub_active"
        assert active.current_period_end == datetime(2027, 1, 15, 8, 0)

        active.plan = "family"
        active.provider_subscription_id = "sub_family"
        db.session.commit()
        older_pro = stripe_subscription(user, id="sub_old_pro")

        assert app_module.sync_stripe_subscription(older_pro) is None
        assert active.plan == "family"

        deleted_old = app_module.sync_stripe_subscription(older_pro, deleted=True)
        assert deleted_old is None
        assert active.plan == "family"

        deleted_current = stripe_subscription(user, id="sub_family", customer="cus_family")
        canceled = app_module.sync_stripe_subscription(deleted_current, deleted=True)
        assert canceled.plan == "free"
        assert canceled.status == "active"


def test_best_subscription_sync_selects_highest_active_plan(app, monkeypatch):
    monkeypatch.setenv("STRIPE_PRO_PRICE_ID", "price_pro")
    monkeypatch.setenv("STRIPE_FAMILY_PRICE_ID", "price_family")

    with app.app_context():
        user = create_user()
        local = Subscription(
            user_id=user.id,
            plan="free",
            status="active",
            provider="stripe",
            provider_customer_id="cus_active",
        )
        db.session.add(local)
        db.session.commit()
        pro = stripe_subscription(user, id="sub_pro")
        family = stripe_subscription(
            user,
            id="sub_family",
            items={"data": [{"id": "si_family", "price": {"id": "price_family"}}]},
        )
        canceled = stripe_subscription(user, id="sub_old", status="canceled")
        monkeypatch.setattr(app_module, "configure_stripe", lambda: True)
        monkeypatch.setattr(
            app_module,
            "stripe",
            SimpleNamespace(
                Subscription=SimpleNamespace(
                    list=lambda **_kwargs: {"data": [pro, canceled, family]},
                )
            ),
        )

        synced = app_module.sync_best_stripe_subscription_for_user(user)

        assert synced.plan == "family"
        assert synced.provider_subscription_id == "sub_family"


def test_cecoin_checkout_handler_is_paid_and_idempotent(app, monkeypatch):
    emails = []
    with app.app_context():
        user = create_user()
        session = {
            "id": "cs_cecoins_paid",
            "customer": "cus_cecoins",
            "payment_status": "paid",
            "metadata": {
                "type": "cecoins",
                "user_id": str(user.id),
                "pack_id": "bronze",
            },
        }
        monkeypatch.setattr(
            app_module,
            "send_cecoins_purchase_email",
            lambda *args: emails.append(args) or True,
        )

        first = app_module.handle_stripe_cecoin_checkout_completed(session)
        second = app_module.handle_stripe_cecoin_checkout_completed(session)

        assert first.id == user.id
        assert second is None
        event = UsageEvent.query.filter_by(event_type="cecoin_purchase").one()
        assert '"coins": 500' in event.metadata_json
        assert len(emails) == 1
        subscription = Subscription.query.filter_by(user_id=user.id).one()
        assert subscription.provider_customer_id == "cus_cecoins"


def test_subscription_checkout_handler_falls_back_without_remote_sync(app, monkeypatch):
    email_calls = []
    with app.app_context():
        user = create_user()
        monkeypatch.setattr(app_module, "configure_stripe", lambda: False)
        monkeypatch.setattr(
            app_module,
            "send_subscription_checkout_email_once",
            lambda *args: email_calls.append(args) or True,
        )
        session = {
            "id": "cs_subscription_paid",
            "customer": "cus_subscription",
            "subscription": "sub_subscription",
            "payment_status": "paid",
            "metadata": {"user_id": str(user.id), "plan": "family"},
        }

        subscription = app_module.handle_stripe_checkout_completed(session)

        assert subscription.plan == "family"
        assert subscription.status == "active"
        assert subscription.provider_customer_id == "cus_subscription"
        assert len(email_calls) == 1


def test_successful_subscription_checkout_and_portal_routes(app, client, monkeypatch):
    with app.app_context():
        user = create_user()
        authenticate(client, user)

    monkeypatch.setattr(app_module, "PAYMENT_PROVIDER", "stripe")
    monkeypatch.setattr(app_module, "configure_stripe", lambda: True)
    monkeypatch.setattr(app_module, "get_stripe_price_id", lambda *_args: "price_pro")
    monkeypatch.setattr(app_module, "stripe_customer_is_usable", lambda _id: True)
    monkeypatch.setattr(
        app_module,
        "create_checkout_session_with_stale_customer_retry",
        lambda *_args: SimpleNamespace(
            id="cs_subscription",
            url="https://checkout.example.test/subscription",
        ),
    )

    checkout = client.post(
        "/billing/checkout",
        json={"plan": "pro", "billingInterval": "monthly"},
        headers={"Idempotency-Key": "checkout-operation-1"},
    )

    assert checkout.status_code == 200
    assert checkout.get_json()["checkoutUrl"].endswith("/subscription")

    with app.app_context():
        subscription = Subscription.query.filter_by(user_id=user.id).one()
        subscription.provider = "stripe"
        subscription.provider_customer_id = "cus_portal"
        db.session.commit()

    monkeypatch.setattr(
        app_module,
        "stripe",
        SimpleNamespace(
            billing_portal=SimpleNamespace(
                Session=SimpleNamespace(
                    create=lambda **_kwargs: SimpleNamespace(
                        url="https://billing.example.test/portal"
                    )
                )
            )
        ),
    )
    portal = client.post("/billing/portal", json={})

    assert portal.status_code == 200
    assert portal.get_json()["portalUrl"].endswith("/portal")


def test_successful_cecoin_checkout_route(app, client, monkeypatch):
    with app.app_context():
        user = create_user()
        authenticate(client, user)

    monkeypatch.setattr(app_module, "configure_stripe", lambda: True)
    monkeypatch.setattr(app_module, "get_cecoin_pack_price_id", lambda _pack: "price_bronze")
    monkeypatch.setattr(app_module, "validate_cecoin_price_for_checkout", lambda _price: "")
    monkeypatch.setattr(
        app_module,
        "create_checkout_session_with_stale_customer_retry",
        lambda *_args: SimpleNamespace(
            id="cs_cecoins",
            url="https://checkout.example.test/cecoins",
        ),
    )

    response = client.post(
        "/gamification/coin-checkout",
        json={"packId": "bronze"},
        headers={"Idempotency-Key": "cecoin-operation-1"},
    )

    assert response.status_code == 200
    assert response.get_json()["pack"] == "bronze"
    assert response.get_json()["checkoutUrl"].endswith("/cecoins")


def test_webhook_dispatches_subscription_and_invoice_events(app, client, monkeypatch):
    calls = []
    events = iter([
        {
            "id": "evt_subscription_update",
            "type": "customer.subscription.updated",
            "data": {"object": {"id": "sub_updated"}},
        },
        {
            "id": "evt_invoice_paid",
            "type": "invoice.paid",
            "data": {"object": {"subscription": "sub_invoice"}},
        },
    ])
    stripe_stub = SimpleNamespace(
        Webhook=SimpleNamespace(construct_event=lambda **_kwargs: next(events)),
    )
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_local_test")
    monkeypatch.setattr(app_module, "stripe", stripe_stub)
    monkeypatch.setattr(
        app_module,
        "sync_stripe_subscription_by_id",
        lambda subscription_id: calls.append(subscription_id),
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
    assert calls == ["sub_updated", "sub_invoice"]
