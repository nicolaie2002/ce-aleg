import json
from datetime import timedelta
from types import SimpleNamespace

import requests
from werkzeug.security import generate_password_hash

import app as app_module
from database import db
from models import Product, ScanHistory, Subscription, UsageEvent, User
from time_utils import utcnow


def create_user(email="mail@example.com", *, verified=True):
    user = User(
        name="Mail User",
        email=email,
        password_hash=generate_password_hash("A-secure-password-123!"),
        email_verified=verified,
    )
    db.session.add(user)
    db.session.commit()
    return user


class FakeHttpResponse:
    def __init__(self, status_code=201, text="ok"):
        self.status_code = status_code
        self.text = text


def test_brevo_and_resend_transports_send_expected_payloads(monkeypatch):
    calls = []
    responses = iter([FakeHttpResponse(201), FakeHttpResponse(202)])
    monkeypatch.setattr(app_module, "EMAIL_FROM", "contact@cealeg.shop")
    monkeypatch.setattr(app_module, "CONTACT_EMAIL", "contact@cealeg.shop")
    monkeypatch.setattr(app_module, "BREVO_API_KEY", "brevo-local-test")
    monkeypatch.setattr(app_module, "RESEND_API_KEY", "resend-local-test")
    monkeypatch.setattr(
        app_module.requests,
        "post",
        lambda *args, **kwargs: calls.append((args, kwargs)) or next(responses),
    )

    assert app_module.send_brevo_email(
        "member@example.com", "Brevo subject", "Text", "<p>HTML</p>"
    ) is True
    assert app_module.send_resend_email(
        "member@example.com", "Resend subject", "Text", "<p>HTML</p>"
    ) is True

    brevo_payload = calls[0][1]["json"]
    resend_payload = calls[1][1]["json"]
    assert brevo_payload["sender"]["email"] == "contact@cealeg.shop"
    assert brevo_payload["replyTo"]["email"] == "contact@cealeg.shop"
    assert resend_payload["from"].endswith("<contact@cealeg.shop>")
    assert resend_payload["reply_to"] == "contact@cealeg.shop"
    assert app_module.LAST_EMAIL_PROVIDER_ERROR == ""


def test_http_email_transports_report_provider_and_network_failures(monkeypatch):
    monkeypatch.setattr(app_module, "EMAIL_FROM", "contact@cealeg.shop")
    monkeypatch.setattr(app_module, "CONTACT_EMAIL", "contact@cealeg.shop")
    monkeypatch.setattr(app_module, "EMAIL_HTTP_RETRY_DELAY_SECONDS", 0)
    monkeypatch.setattr(
        app_module.requests,
        "post",
        lambda *_args, **_kwargs: FakeHttpResponse(429, "quota reached"),
    )

    assert app_module.send_brevo_email("member@example.com", "Subject", "Text") is False
    assert "Brevo HTTP 429" in app_module.LAST_EMAIL_PROVIDER_ERROR

    monkeypatch.setattr(
        app_module.requests,
        "post",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(requests.RequestException("offline")),
    )
    assert app_module.send_resend_email("member@example.com", "Subject", "Text") is False
    assert "Resend network error after 2 attempts" in app_module.LAST_EMAIL_PROVIDER_ERROR


def test_http_email_transport_retries_only_transient_failures(monkeypatch):
    calls = []
    responses = iter([
        FakeHttpResponse(503, "temporarily unavailable"),
        FakeHttpResponse(202, "accepted"),
    ])
    monkeypatch.setattr(app_module, "EMAIL_FROM", "contact@cealeg.shop")
    monkeypatch.setattr(app_module, "CONTACT_EMAIL", "contact@cealeg.shop")
    monkeypatch.setattr(app_module, "EMAIL_HTTP_MAX_ATTEMPTS", 2)
    monkeypatch.setattr(app_module, "EMAIL_HTTP_RETRY_DELAY_SECONDS", 0)
    monkeypatch.setattr(
        app_module.requests,
        "post",
        lambda *_args, **_kwargs: calls.append(True) or next(responses),
    )

    assert app_module.send_brevo_email(
        "member@example.com", "Subject", "Text"
    ) is True
    assert len(calls) == 2
    assert app_module.LAST_EMAIL_PROVIDER_ERROR == ""

    calls.clear()
    monkeypatch.setattr(
        app_module.requests,
        "post",
        lambda *_args, **_kwargs: calls.append(True)
        or FakeHttpResponse(400, "sender not verified"),
    )

    assert app_module.send_brevo_email(
        "member@example.com", "Subject", "Text"
    ) is False
    assert len(calls) == 1
    assert "senderul contact@cealeg.shop" in app_module.LAST_EMAIL_PROVIDER_ERROR

    monkeypatch.setattr(
        app_module.requests,
        "post",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("client bug")),
    )

    assert app_module.send_resend_email(
        "member@example.com", "Subject", "Text"
    ) is False
    assert "unexpected client error" in app_module.LAST_EMAIL_PROVIDER_ERROR


def test_email_diagnostics_reject_invalid_sender_and_reply_to(monkeypatch):
    monkeypatch.setattr(app_module, "EMAIL_PROVIDER", "brevo")
    monkeypatch.setattr(app_module, "BREVO_API_KEY", "brevo-local-test")
    monkeypatch.setattr(app_module, "EMAIL_FROM", "not-an-email")
    monkeypatch.setattr(app_module, "CONTACT_EMAIL", "also-invalid")

    diagnostics = app_module.get_email_configuration_diagnostics()

    assert diagnostics["configured"] is False
    assert "EMAIL_FROM nu este o adresa de email valida." in diagnostics["issues"]
    assert any("CONTACT_EMAIL" in issue for issue in diagnostics["issues"])


class FakeSmtpClient:
    def __init__(self):
        self.started_tls = False
        self.login_args = None
        self.messages = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def starttls(self):
        self.started_tls = True

    def login(self, username, password):
        self.login_args = (username, password)

    def send_message(self, message):
        self.messages.append(message)


def test_smtp_transport_uses_tls_auth_reply_to_and_html(monkeypatch):
    smtp = FakeSmtpClient()
    monkeypatch.setattr(app_module, "EMAIL_FROM", "contact@cealeg.shop")
    monkeypatch.setattr(app_module, "CONTACT_EMAIL", "contact@cealeg.shop")
    monkeypatch.setattr(app_module, "EMAIL_SMTP_HOST", "smtp.example.test")
    monkeypatch.setattr(app_module, "EMAIL_SMTP_PORT", 587)
    monkeypatch.setattr(app_module, "EMAIL_SMTP_USERNAME", "smtp-user")
    monkeypatch.setattr(app_module, "EMAIL_SMTP_PASSWORD", "smtp-password")
    monkeypatch.setattr(app_module, "EMAIL_USE_SSL", False)
    monkeypatch.setattr(app_module, "EMAIL_USE_TLS", True)
    monkeypatch.setattr(app_module.smtplib, "SMTP", lambda *_args, **_kwargs: smtp)

    sent = app_module.send_smtp_email(
        "member@example.com", "SMTP subject", "Text body", "<p>HTML body</p>"
    )

    assert sent is True
    assert smtp.started_tls is True
    assert smtp.login_args == ("smtp-user", "smtp-password")
    assert smtp.messages[0]["Reply-To"] == "contact@cealeg.shop"
    assert smtp.messages[0].is_multipart()


def test_transactional_email_routes_to_selected_provider_or_fails_closed(monkeypatch):
    monkeypatch.setattr(app_module, "is_email_configured", lambda: False)
    assert app_module.send_transactional_email(
        "member@example.com", "Subject", "Text"
    ) is False
    assert "not configured" in app_module.LAST_EMAIL_PROVIDER_ERROR

    monkeypatch.setattr(app_module, "is_email_configured", lambda: True)
    monkeypatch.setattr(app_module, "EMAIL_PROVIDER", "brevo")
    monkeypatch.setattr(app_module, "send_brevo_email", lambda *_args, **_kwargs: True)
    assert app_module.send_transactional_email("member@example.com", "Subject", "Text") is True

    monkeypatch.setattr(app_module, "EMAIL_PROVIDER", "resend")
    monkeypatch.setattr(app_module, "send_resend_email", lambda *_args, **_kwargs: True)
    assert app_module.send_transactional_email("member@example.com", "Subject", "Text") is True

    monkeypatch.setattr(app_module, "EMAIL_PROVIDER", "smtp")
    monkeypatch.setattr(app_module, "send_smtp_email", lambda *_args, **_kwargs: True)
    assert app_module.send_transactional_email("member@example.com", "Subject", "Text") is True


def test_brand_template_escapes_user_content():
    html = app_module.render_brand_email(
        "<script>preheader</script>",
        "Title <unsafe>",
        "Intro & details",
        "Open <now>",
        "https://example.test/?x=1&y=2",
        ["Detail <unsafe>"],
        tone="danger",
    )

    assert "<script>" not in html
    assert "&lt;unsafe&gt;" in html
    assert "Intro &amp; details" in html
    assert "https://example.test/?x=1&amp;y=2" in html


def test_all_transactional_templates_target_the_account_email(app, monkeypatch):
    deliveries = []

    def capture(to_email, subject, text_body, html_body=None):
        deliveries.append({
            "to": to_email,
            "subject": subject,
            "text": text_body,
            "html": html_body,
        })
        return True

    with app.app_context():
        user = create_user(verified=False)
        inviter = create_user("inviter@example.com")
        product = Product(
            name="Iaurt natural",
            store="Lidl",
            category="Lactate",
            barcode="5941238013309",
            score=8.8,
        )
        db.session.add(product)
        db.session.commit()
        subscription = Subscription(
            user_id=user.id,
            plan="pro",
            status="active",
            current_period_end=utcnow() + timedelta(days=30),
        )
        db.session.add(subscription)
        db.session.commit()
        submission = SimpleNamespace(
            product_name="Iaurt natural",
            store="Lidl",
        )
        monkeypatch.setattr(app_module, "send_transactional_email", capture)

        assert app_module.send_welcome_email(user) is True
        verification_sent, verification_url = app_module.send_email_verification_email(user)
        reset_sent, reset_url = app_module.send_password_reset_email(user)
        deletion_sent, deletion_url = app_module.send_account_deletion_email(user)
        assert app_module.send_referral_bonus_email(user, inviter) is True
        assert app_module.send_referral_inviter_email(inviter, user) is True
        assert app_module.send_cecoins_purchase_email(
            user,
            {"title": "Bronze", "coins": 500},
            {"amount_total": 999, "currency": "ron"},
        ) is True
        assert app_module.send_cecoin_reward_email(
            user,
            {"title": "5 scanari bonus", "cost": 350, "bonusScans": 5, "bonusDays": 1},
        ) is True
        assert app_module.send_product_submission_approved_email(
            user,
            submission,
            product,
            duplicate=False,
            reward={"claimed": True, "coins": 10},
        ) is True
        assert app_module.send_alternative_report_fixed_email(
            user,
            {"name": "Iaurt scanat"},
            {"name": "Alternativa"},
            "Altele",
            "Lactate",
        ) is True
        assert app_module.send_product_corrected_email(
            user,
            product,
            {"category": "Altele"},
        ) is True
        assert app_module.send_subscription_activated_email(
            user,
            "pro",
            subscription,
        ) is True
        assert app_module.send_mission_digest_email(user, [{
            "title": "Scaneaza 3 produse",
            "remaining": 1,
            "rewardText": "10 CeCoins",
        }]) is True

    assert verification_sent is True
    assert reset_sent is True
    assert deletion_sent is True
    assert "/verify-email?token=" in verification_url
    assert "/reset-password?token=" in reset_url
    assert "/delete-account?token=" in deletion_url
    assert len(deliveries) == 13
    assert all(item["html"] and "<!doctype html>" in item["html"] for item in deliveries)
    assert {item["to"] for item in deliveries} == {
        "mail@example.com",
        "inviter@example.com",
    }


def test_subscription_activation_email_is_sent_once_per_checkout(app, monkeypatch):
    sends = []
    with app.app_context():
        user = create_user()
        subscription = Subscription(user_id=user.id, plan="pro", status="active")
        db.session.add(subscription)
        db.session.commit()
        monkeypatch.setattr(
            app_module,
            "send_subscription_activated_email",
            lambda *args: sends.append(args) or True,
        )
        session = {"id": "cs_email_once"}

        assert app_module.send_subscription_checkout_email_once(
            user, "pro", session, subscription
        ) is True
        assert app_module.send_subscription_checkout_email_once(
            user, "pro", session, subscription
        ) is False

        assert len(sends) == 1
        assert UsageEvent.query.filter_by(
            idempotency_key="stripe:subscription-email:cs_email_once"
        ).count() == 1


def test_product_correction_notification_finds_relevant_users_and_deduplicates(
    app, monkeypatch
):
    sent_to = []
    with app.app_context():
        scanner = create_user("scanner@example.com")
        reporter = create_user("reporter@example.com")
        unverified = create_user("unverified@example.com", verified=False)
        product = Product(
            name="Iaurt natural",
            store="Lidl",
            category="Lactate",
            barcode="5941238013309",
            score=8.9,
        )
        db.session.add(product)
        db.session.flush()
        db.session.add_all([
            ScanHistory(user_id=scanner.id, product_name=product.name, store="Lidl"),
            ScanHistory(user_id=unverified.id, product_name=product.name, store="Lidl"),
            UsageEvent(
                user_id=reporter.id,
                event_type="alternative_report",
                source="alternatives",
                metadata_json=json.dumps({
                    "alternativeProduct": {
                        "name": product.name,
                        "barcode": product.barcode,
                    }
                }),
            ),
        ])
        db.session.commit()
        previous = app_module.product_notification_snapshot(product)
        previous["category"] = "Altele"
        monkeypatch.setattr(app_module, "is_email_configured", lambda: True)
        monkeypatch.setattr(
            app_module,
            "send_product_corrected_email",
            lambda user, *_args: sent_to.append(user.email) or True,
        )

        first = app_module.notify_users_about_product_correction(
            product, previous, limit=25
        )
        second = app_module.notify_users_about_product_correction(
            product, previous, limit=25
        )

        assert first == 2
        assert second == 0
        assert set(sent_to) == {"scanner@example.com", "reporter@example.com"}
        assert UsageEvent.query.filter_by(
            event_type=app_module.PRODUCT_CORRECTION_EMAIL_EVENT_TYPE
        ).count() == 2


def test_admin_alert_uses_configured_email_without_external_services(monkeypatch):
    deliveries = []
    app_module.ADMIN_ALERT_THROTTLE.clear()
    monkeypatch.setenv("ADMIN_EMAIL", "contact@cealeg.shop")
    monkeypatch.delenv("ALERT_WEBHOOK_URL", raising=False)
    monkeypatch.setattr(app_module, "SENTRY_DSN", "")
    monkeypatch.setattr(app_module, "is_email_configured", lambda: True)
    monkeypatch.setattr(
        app_module,
        "send_transactional_email",
        lambda *args, **_kwargs: deliveries.append(args) or True,
    )

    first = app_module.send_admin_alert(
        "Catalog warning",
        "Health score dropped.",
        ["Score: 60"],
        alert_key="catalog-health-test",
        min_interval_seconds=3600,
    )
    second = app_module.send_admin_alert(
        "Catalog warning",
        "Health score dropped.",
        alert_key="catalog-health-test",
        min_interval_seconds=3600,
    )

    assert first is True
    assert second is False
    assert deliveries[0][0] == "contact@cealeg.shop"
