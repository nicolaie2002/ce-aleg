import json
from datetime import timedelta

import requests
from werkzeug.security import generate_password_hash

import app as app_module
from database import db
from models import (
    CartItem,
    ConsentRecord,
    FamilyProfile,
    Favorite,
    PriceObservation,
    ProductSubmission,
    ScanHistory,
    SearchEvent,
    Subscription,
    UsageEvent,
    User,
)
from time_utils import utcnow


PASSWORD = "A-secure-password-123!"


def create_user(email="flows@example.com", *, verified=True, name="Flow User"):
    user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(PASSWORD),
        email_verified=verified,
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


def add_scan_streak(user_id, days):
    now = utcnow().replace(hour=12, minute=0, second=0, microsecond=0)

    for offset in range(days):
        db.session.add(UsageEvent(
            user_id=user_id,
            event_type="scan",
            source="barcode",
            metadata_json="{}",
            created_at=now - timedelta(days=offset),
        ))

    db.session.commit()


def add_coin_event(user_id, event_type, metadata, *, source=None):
    db.session.add(UsageEvent(
        user_id=user_id,
        event_type=event_type,
        source=source,
        metadata_json=json.dumps(metadata),
    ))


def off_yogurt(code, name):
    return {
        "code": code,
        "product_name": name,
        "product_name_ro": name,
        "brands": "Brand local",
        "categories": "Dairies, Yogurts",
        "categories_tags": ["en:dairies", "en:yogurts"],
        "stores": "Lidl",
        "ingredients_text_ro": "lapte, culturi lactice",
        "nutriments": {
            "energy-kcal_100g": 62,
            "proteins_100g": 5.2,
            "sugars_100g": 3.8,
            "fat_100g": 2.1,
        },
        "nutrition_grades": "a",
    }


def test_mission_nudges_use_real_streak_progress_and_filter_completed_work(app):
    with app.app_context():
        user = create_user()
        add_scan_streak(user.id, 2)

        nudges = app_module.build_mission_nudge_items(
            user,
            limit=20,
            min_progress=60,
        )

        assert len(nudges) == 1
        assert nudges[0] == {
            **nudges[0],
            "id": "streak_3",
            "seriesId": "streak",
            "current": 2,
            "target": 3,
            "remaining": 1,
            "progress": 67,
            "rewardText": "35 CeCoins + 1 scanari bonus",
            "href": "/barcode-scan",
        }

        add_scan_streak(user.id, 3)
        assert app_module.build_mission_nudge_items(user) == []
        assert app_module.build_mission_nudge_items(None) == []


def test_mission_digest_dry_run_apply_and_cooldown_are_consistent(
    app, monkeypatch
):
    deliveries = []

    with app.app_context():
        eligible = create_user("eligible@example.com", name="Eligible")
        recent = create_user("recent@example.com", name="Recent")
        unverified = create_user(
            "unverified@example.com",
            verified=False,
            name="Unverified",
        )
        create_user("idle@example.com", name="Idle")
        create_user("invalid-email", name="Invalid")

        add_scan_streak(eligible.id, 2)
        add_scan_streak(recent.id, 2)
        add_scan_streak(unverified.id, 2)
        db.session.add(UsageEvent(
            user_id=recent.id,
            event_type=app_module.MISSION_DIGEST_EVENT_TYPE,
            source="admin",
            metadata_json="{}",
        ))
        db.session.commit()

        dry_run = app_module.build_mission_digest_batch(
            limit=1000,
            apply_changes=False,
        )

        assert dry_run["scanned"] == 5
        assert dry_run["eligible"] == 1
        assert dry_run["sent"] == 0
        assert dry_run["failed"] == 0
        assert dry_run["skippedRecent"] == 1
        assert dry_run["skippedUnverified"] == 1
        assert dry_run["applied"] is False
        assert dry_run["recipients"][0]["email"] == "eligible@example.com"
        assert dry_run["recipients"][0]["topProgress"] == 67
        assert UsageEvent.query.filter_by(
            user_id=eligible.id,
            event_type=app_module.MISSION_DIGEST_EVENT_TYPE,
        ).count() == 0

        monkeypatch.setattr(
            app_module,
            "send_transactional_email",
            lambda *args, **kwargs: deliveries.append((args, kwargs)) or True,
        )
        applied = app_module.build_mission_digest_batch(
            limit=1000,
            apply_changes=True,
        )

        assert applied["eligible"] == 1
        assert applied["sent"] == 1
        assert applied["failed"] == 0
        assert applied["applied"] is True
        assert deliveries[0][0][0] == "eligible@example.com"
        assert "misiuni aproape gata" in deliveries[0][0][1].lower()

        event = UsageEvent.query.filter_by(
            user_id=eligible.id,
            event_type=app_module.MISSION_DIGEST_EVENT_TYPE,
        ).one()
        metadata = json.loads(event.metadata_json)
        assert metadata["missionIds"] == ["streak_3"]
        assert metadata["topProgress"] == 67

        repeated = app_module.build_mission_digest_batch(
            limit=1000,
            apply_changes=True,
        )
        assert repeated["eligible"] == 0
        assert repeated["sent"] == 0
        assert repeated["skippedRecent"] == 2
        assert len(deliveries) == 1


def test_mission_digest_records_provider_failure_without_false_success(
    app, monkeypatch
):
    with app.app_context():
        user = create_user()
        add_scan_streak(user.id, 2)
        monkeypatch.setattr(
            app_module,
            "send_transactional_email",
            lambda *_args, **_kwargs: False,
        )

        result = app_module.build_mission_digest_batch(apply_changes=True)

        assert result["eligible"] == 1
        assert result["sent"] == 0
        assert result["failed"] == 1
        assert UsageEvent.query.filter_by(
            user_id=user.id,
            event_type=app_module.MISSION_DIGEST_EVENT_TYPE,
        ).count() == 0


def test_bulk_coin_balance_accounts_for_invites_purchases_and_spending(app):
    with app.app_context():
        primary = create_user("primary@example.com")
        referral_only = create_user("referral@example.com")
        debtor = create_user("debtor@example.com")

        add_coin_event(
            primary.id,
            "mission_claim",
            {"reward": {"coins": 35}, "seriesId": "streak"},
            source="streak_3",
        )
        add_coin_event(
            primary.id,
            "mission_claim",
            {"reward": {"coins": 100}, "seriesId": "invite"},
            source="invite_1",
        )
        add_coin_event(primary.id, "cecoin_purchase", {"coins": 500})
        add_coin_event(primary.id, "referral_cecoin_bonus", {"coins": 150})
        add_coin_event(primary.id, "cecoin_spend", {"cost": 120})
        add_coin_event(debtor.id, "cecoin_spend", {"cost": 50})
        db.session.commit()

        metrics = {
            primary.id: {"confirmedInvites": 2},
            referral_only.id: {"confirmedInvites": 1},
            debtor.id: {"confirmedInvites": 0},
        }
        balances = app_module.calculate_bulk_user_coins(
            [primary.id, referral_only.id, debtor.id],
            metrics,
        )

        assert balances == {
            primary.id: 665,
            referral_only.id: 100,
            debtor.id: 0,
        }
        assert app_module.calculate_referral_cecoin_bonus(
            primary.id,
            metrics[primary.id],
        ) == 150
        assert app_module.calculate_referral_cecoin_bonus(
            referral_only.id,
            metrics[referral_only.id],
        ) == 100
        assert app_module.calculate_bulk_user_coins([]) == {}


def test_referral_bonus_after_verification_is_atomic_and_idempotent(
    app, monkeypatch
):
    sent = []

    with app.app_context():
        inviter = create_user("inviter@example.com", name="Inviter")
        referred = create_user("referred@example.com", name="Referred")
        referred.referred_by_user_id = inviter.id
        db.session.commit()

        monkeypatch.setattr(
            app_module,
            "send_referral_bonus_email",
            lambda user, source: sent.append(("referred", user.id, source.id)) or True,
        )
        monkeypatch.setattr(
            app_module,
            "send_referral_inviter_email",
            lambda user, invited: sent.append(("inviter", user.id, invited.id)) or True,
        )

        assert app_module.apply_referral_bonus_after_verification(referred) is True
        assert app_module.apply_referral_bonus_after_verification(referred) is False

        db.session.refresh(inviter)
        db.session.refresh(referred)
        assert inviter.bonus_unlimited_until > utcnow()
        assert referred.bonus_unlimited_until > utcnow()
        assert sent == [
            ("referred", referred.id, inviter.id),
            ("inviter", inviter.id, referred.id),
        ]
        assert UsageEvent.query.filter_by(
            user_id=inviter.id,
            event_type="referral_cecoin_bonus",
        ).count() == 1
        assert UsageEvent.query.filter_by(event_type="bonus_unlimited").count() == 2
        assert app_module.calculate_user_coins(inviter.id) == 100
        assert app_module.calculate_user_coins(referred.id) == 0


def test_daily_mission_claim_is_persisted_and_cannot_be_claimed_twice(app, client):
    with app.app_context():
        user = create_user()
        user_id = user.id
        db.session.add(Favorite(
            user_id=user.id,
            product_name="Iaurt natural",
            store="Lidl",
        ))
        db.session.commit()
        authenticate(client, user)

    claimed = client.post(
        "/gamification/claim",
        json={"missionId": "favorite_1"},
    )
    duplicate = client.post(
        "/gamification/claim",
        json={"missionId": "favorite_1"},
    )

    assert claimed.status_code == 200
    assert claimed.get_json()["reward"]["coins"] == 10
    assert claimed.get_json()["summary"]["coins"] == 10
    assert claimed.get_json()["summary"]["dailyClaimedCoins"] == 10
    assert duplicate.status_code == 409

    with app.app_context():
        event = UsageEvent.query.filter_by(
            user_id=user_id,
            event_type="mission_claim",
            source="favorite_1",
        ).one()
        assert event.idempotency_key.startswith(f"mission:{user_id}:favorite_1:")
        assert json.loads(event.metadata_json)["daily"] is True


def test_streak_mission_claim_awards_bonus_scan_once(app, client):
    with app.app_context():
        user = create_user()
        user_id = user.id
        add_scan_streak(user.id, 3)
        authenticate(client, user)

    claimed = client.post(
        "/gamification/claim",
        json={"missionId": "streak_3"},
    )
    repeated = client.post(
        "/gamification/claim",
        json={"missionId": "streak_3"},
    )

    assert claimed.status_code == 200
    assert claimed.get_json()["reward"] == {
        "coins": 35,
        "bonusScans": 1,
        "bonusDays": 0,
    }
    assert claimed.get_json()["summary"]["coins"] == 35
    assert repeated.status_code == 400

    with app.app_context():
        user = db.session.get(User, user_id)
        assert user.bonus_scan_credits == 1
        assert UsageEvent.query.filter_by(
            user_id=user_id,
            event_type="bonus_scan_credit",
        ).count() == 1
        assert UsageEvent.query.filter_by(
            user_id=user_id,
            event_type="mission_claim",
            source="streak_3",
        ).count() == 1


def test_incomplete_mission_is_rejected_without_creating_rewards(app, client):
    with app.app_context():
        user = create_user()
        user_id = user.id
        authenticate(client, user)

    response = client.post(
        "/gamification/claim",
        json={"missionId": "favorite_1"},
    )

    assert response.status_code == 400
    assert response.get_json()["summary"]["coins"] == 0

    with app.app_context():
        assert UsageEvent.query.filter_by(
            user_id=user_id,
            event_type="mission_claim",
        ).count() == 0


def test_account_deletion_request_sends_a_confirmable_user_specific_link(
    app, client, monkeypatch
):
    deliveries = []

    with app.app_context():
        user = create_user()
        user_id = user.id
        authenticate(client, user)

    monkeypatch.setattr(
        app_module,
        "send_transactional_email",
        lambda *args, **kwargs: deliveries.append((args, kwargs)) or True,
    )
    response = client.post("/account/delete/request", json={})

    assert response.status_code == 200
    assert response.get_json()["sent"] is True
    assert response.get_json()["email"] == "flows@example.com"
    assert deliveries[0][0][0] == "flows@example.com"
    assert "delete-account?token=" in deliveries[0][0][2]

    token = deliveries[0][0][2].split("delete-account?token=", 1)[1].split()[0]
    with app.app_context():
        assert app_module.verify_account_deletion_token(token).id == user_id


def test_account_deletion_confirmation_removes_all_personal_data(
    app, client, monkeypatch
):
    deleted_files = []

    with app.app_context():
        user = create_user()
        user_id = user.id
        dependent = create_user("dependent@example.com")
        dependent_id = dependent.id
        dependent.referred_by_user_id = user.id
        db.session.add_all([
            Subscription(user_id=user.id, plan="free", status="active"),
            FamilyProfile(user_id=user.id, name="Principal", is_primary=True),
            CartItem(user_id=user.id, product_name="Iaurt", store="Lidl"),
            Favorite(user_id=user.id, product_name="Iaurt", store="Lidl"),
            ScanHistory(user_id=user.id, product_name="Iaurt", store="Lidl"),
            PriceObservation(
                user_id=user.id,
                product_barcode="5941238013309",
                store="Lidl",
                price=4.99,
            ),
            ProductSubmission(
                user_id=user.id,
                product_name="Iaurt nou",
                store="Lidl",
                front_image="/uploads/submissions/front.jpg",
                nutrition_image="/uploads/supabase-submissions/nutrition.jpg",
            ),
            SearchEvent(
                user_id=user.id,
                search_text="iaurt natural",
                source="product_search",
            ),
            UsageEvent(user_id=user.id, event_type="scan", source="barcode"),
            ConsentRecord(
                user_id=user.id,
                consent_type="terms",
                granted=True,
                policy_version="1.0",
            ),
        ])
        db.session.commit()
        token = app_module.create_account_deletion_token(user)
        authenticate(client, user)

    monkeypatch.setattr(
        app_module,
        "delete_submission_file",
        lambda path: deleted_files.append(path),
    )
    response = client.post("/account/delete/confirm", json={"token": token})

    assert response.status_code == 200
    assert app_module.AUTH_COOKIE_NAME in response.headers.get("Set-Cookie", "")
    assert "Expires=Thu, 01 Jan 1970" in response.headers.get("Set-Cookie", "")
    assert client.get("/auth/me").status_code == 401

    with app.app_context():
        assert db.session.get(User, user_id) is None
        dependent = db.session.get(User, dependent_id)
        assert dependent is not None
        assert dependent.referred_by_user_id is None
        for model in (
            CartItem,
            Favorite,
            ScanHistory,
            PriceObservation,
            ProductSubmission,
            SearchEvent,
            Subscription,
            FamilyProfile,
            UsageEvent,
            ConsentRecord,
        ):
            assert model.query.filter_by(user_id=user_id).count() == 0

        assert app_module.verify_account_deletion_token(token) is None

    assert deleted_files == [
        "/uploads/submissions/front.jpg",
        "/uploads/supabase-submissions/nutrition.jpg",
    ]


def test_account_deletion_rejects_invalid_token_and_preserves_on_cancel_failure(
    app, client, monkeypatch
):
    missing = client.post("/account/delete/confirm", json={})
    invalid = client.post("/account/delete/confirm", json={"token": "invalid"})

    with app.app_context():
        user = create_user()
        user_id = user.id
        token = app_module.create_account_deletion_token(user)

    monkeypatch.setattr(
        app_module,
        "cancel_subscription_before_account_deletion",
        lambda _user: (False, "Subscription cancellation failed."),
    )
    blocked = client.post("/account/delete/confirm", json={"token": token})

    assert missing.status_code == 400
    assert invalid.status_code == 400
    assert blocked.status_code == 502
    assert blocked.get_json()["error"] == "Subscription cancellation failed."

    with app.app_context():
        assert db.session.get(User, user_id) is not None


def test_label_search_filters_results_records_query_and_handles_outage(
    app, client, monkeypatch
):
    provider_calls = []

    def fake_search(query):
        provider_calls.append(query)
        return [
            off_yogurt("5941238013309", "Iaurt natural"),
            off_yogurt("5941238013316", "Produs fara legatura"),
        ]

    monkeypatch.setattr(app_module, "fetch_off_text_search_products", fake_search)

    short = client.get("/products/search-label?q=abc")
    found = client.get("/products/search-label?q=iaurt%20natural")

    assert short.status_code == 200
    assert short.get_json() == []
    assert found.status_code == 200
    assert [item["name"] for item in found.get_json()] == ["Iaurt natural"]
    assert found.get_json()[0]["source"] == "openfoodfacts"
    assert provider_calls == ["iaurt natural"]

    with app.app_context():
        event = SearchEvent.query.filter_by(source="label_search").one()
        assert event.search_text == "iaurt natural"
        assert event.result_count == 1

    monkeypatch.setattr(
        app_module,
        "fetch_off_text_search_products",
        lambda _query: (_ for _ in ()).throw(requests.RequestException("offline")),
    )
    outage = client.get("/products/search-label?q=iaurt%20natural")

    assert outage.status_code == 502
    assert outage.get_json()["code"] == "external_catalog_unavailable"
