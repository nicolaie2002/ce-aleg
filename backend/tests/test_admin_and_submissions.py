from werkzeug.security import generate_password_hash

import app as app_module
from database import db
from models import Product, SearchEvent, Subscription, UsageEvent, User


def create_user(email="user@example.com", *, admin=False, verified=True):
    user = User(
        name="Admin" if admin else "Contributor",
        email=email,
        password_hash=generate_password_hash("A-secure-password-123!"),
        email_verified=verified,
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


def authenticate(client, user):
    client.set_cookie(app_module.AUTH_COOKIE_NAME, auth_cookie_for(user))


def create_product(**overrides):
    values = {
        "name": "Iaurt natural",
        "store": "Lidl",
        "category": "Lactate",
        "barcode": "5941238013309",
        "score": 8.2,
        "price": 4.99,
        "price_text": "4,99 lei",
        "calories": 62,
        "protein": 4.5,
        "sugar": 4.1,
        "fat": 2.0,
        "ingredients": "lapte, culturi lactice",
    }
    values.update(overrides)
    product = Product(**values)
    db.session.add(product)
    db.session.commit()
    return product


def test_admin_overview_search_misses_and_catalog_search(app, client):
    with app.app_context():
        admin = create_user("admin@example.com", admin=True)
        member = create_user()
        product = create_product()
        db.session.add_all([
            SearchEvent(search_text="produs lipsa", store="Lidl", result_count=0),
            SearchEvent(search_text="produs lipsa", store="Lidl", result_count=0),
            Subscription(user_id=member.id, plan="pro", status="active"),
        ])
        db.session.commit()
        product_id = product.id
        authenticate(client, admin)

    overview = client.get("/admin/overview")
    misses = client.get("/admin/search-misses?days=30&limit=10")
    search = client.get("/admin/products/search?q=5941238013309")

    assert overview.status_code == 200
    assert overview.get_json()["users"] == 2
    assert overview.get_json()["products"] == 1
    assert overview.get_json()["missingProducts"] == 2
    assert overview.get_json()["proUsers"] == 1
    assert misses.status_code == 200
    assert misses.get_json()[0]["query"] == "produs lipsa"
    assert misses.get_json()[0]["count"] == 2
    assert search.status_code == 200
    assert search.get_json()[0]["id"] == product_id


def test_admin_product_update_validates_values_and_persists_changes(app, client):
    with app.app_context():
        admin = create_user("admin@example.com", admin=True)
        product = create_product()
        product_id = product.id
        authenticate(client, admin)

    invalid = client.patch(
        f"/admin/products/{product_id}",
        json={"score": 11, "sugar": "not-a-number"},
    )
    updated = client.patch(
        f"/admin/products/{product_id}",
        json={
            "name": "Iaurt grecesc 2%",
            "store": "Kaufland",
            "category": "Lactate si branzeturi",
            "score": 9.1,
            "sugar": 3.2,
            "protein": 8.5,
            "natural": True,
            "notifyUsers": False,
        },
    )

    assert invalid.status_code == 400
    assert updated.status_code == 200
    payload = updated.get_json()
    assert payload["product"]["name"] == "Iaurt grecesc 2%"
    assert payload["product"]["store"] == "Kaufland"
    assert payload["product"]["score"] == 9.1
    assert payload["product"]["protein"] == 8.5
    assert payload["product"]["natural"] is True

    with app.app_context():
        event = UsageEvent.query.filter_by(event_type="admin_product_updated").one()
        assert event.user_id == admin.id


def test_admin_can_delete_product_and_update_member_plan(app, client):
    with app.app_context():
        admin = create_user("admin@example.com", admin=True)
        member = create_user()
        product = create_product()
        member_id = member.id
        product_id = product.id
        authenticate(client, admin)

    plan = client.patch(
        f"/admin/users/{member_id}/plan",
        json={"plan": "family", "status": "active"},
    )
    deleted = client.delete(f"/admin/products/{product_id}")

    assert plan.status_code == 200
    assert plan.get_json()["user"]["plan"] == "family"
    assert deleted.status_code == 200

    with app.app_context():
        assert db.session.get(Product, product_id) is None
        subscription = Subscription.query.filter_by(user_id=member_id).one()
        assert subscription.plan == "family"
        assert subscription.provider == "manual_admin"


def test_admin_resends_verification_email_and_records_audit_event(
    app, client, monkeypatch
):
    sent_to = []
    with app.app_context():
        admin = create_user("admin@example.com", admin=True)
        target = create_user("pending@example.com", verified=False)
        target_id = target.id
        authenticate(client, admin)

    monkeypatch.setattr(app_module, "is_email_configured", lambda: True)
    monkeypatch.setattr(
        app_module,
        "send_email_verification_email",
        lambda user: (sent_to.append(user.email) or True, "https://example.test/verify"),
    )

    response = client.post(
        "/admin/users/resend-verification",
        json={"email": "PENDING@EXAMPLE.COM"},
    )

    assert response.status_code == 200
    assert response.get_json()["sent"] is True
    assert sent_to == ["pending@example.com"]

    with app.app_context():
        event = UsageEvent.query.filter_by(event_type="admin_verification_email").one()
        assert event.user_id == admin.id
        assert str(target_id) in event.metadata_json


def test_admin_verification_resend_handles_known_non_delivery_cases(
    app, client, monkeypatch
):
    with app.app_context():
        admin = create_user("admin@example.com", admin=True)
        create_user("verified@example.com", verified=True)
        create_user("pending@example.com", verified=False)
        authenticate(client, admin)

    already_verified = client.post(
        "/admin/users/resend-verification",
        json={"email": "verified@example.com"},
    )
    monkeypatch.setattr(app_module, "is_email_configured", lambda: False)
    not_configured = client.post(
        "/admin/users/resend-verification",
        json={"email": "pending@example.com"},
    )

    assert already_verified.status_code == 409
    assert already_verified.get_json()["code"] == "email_already_verified"
    assert not_configured.status_code == 503
    assert not_configured.get_json()["code"] == "email_not_configured"


def test_submission_can_be_reviewed_and_published_by_admin(app, client, monkeypatch):
    with app.app_context():
        contributor = create_user("contributor@example.com")
        contributor_id = contributor.id
        admin = create_user("admin@example.com", admin=True)
        contributor_cookie = auth_cookie_for(contributor)
        admin_cookie = auth_cookie_for(admin)

    saved_paths = iter([
        "/uploads/submissions/front.jpg",
        "/uploads/submissions/nutrition.jpg",
    ])
    monkeypatch.setattr(app_module, "save_uploaded_file", lambda *_args: next(saved_paths))
    monkeypatch.setattr(app_module, "publish_submission_image", lambda _path: "/products/published.jpg")
    monkeypatch.setattr(app_module, "send_product_submission_approved_email", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        app_module,
        "review_product_submission_with_ai",
        lambda _submission: {
            "status": "ai_approved",
            "message": "Approved",
            "confidence": 98,
            "problems": [],
            "warnings": [],
        },
    )

    client.set_cookie(app_module.AUTH_COOKIE_NAME, contributor_cookie)
    created = client.post(
        "/submissions/add",
        data={
            "user_id": str(contributor_id),
            "product_name": "Skyr simplu",
            "brand": "Brand Test",
            "store": "Lidl",
            "category": "Lactate",
            "barcode": "5941238013316",
            "calories": "64",
            "protein": "10",
            "sugar": "4",
            "fat": "0.2",
            "ingredients": "lapte degresat, culturi lactice",
        },
        content_type="multipart/form-data",
    )

    assert created.status_code == 201
    submission_id = created.get_json()["item"]["id"]
    assert client.get(f"/submissions/{contributor_id}").status_code == 200

    client.set_cookie(app_module.AUTH_COOKIE_NAME, admin_cookie)
    review = client.post(f"/submissions/ai-review/{submission_id}", json={})
    published = client.post(f"/submissions/approve/{submission_id}", json={})

    assert review.status_code == 200
    assert review.get_json()["status"] == "ai_approved"
    assert published.status_code == 200
    assert published.get_json()["product"]["name"] == "Skyr simplu"
    assert published.get_json()["submission"]["status"] == "approved"
    assert published.get_json()["reward"]["bonusScans"] >= 1

    with app.app_context():
        product = Product.query.filter_by(barcode="5941238013316").one()
        contributor = db.session.get(User, contributor_id)
        assert product.image == "/products/published.jpg"
        assert contributor.bonus_scan_credits >= 1


def test_submission_rejects_existing_catalog_barcode(app, client, monkeypatch):
    with app.app_context():
        contributor = create_user()
        contributor_id = contributor.id
        create_product()
        authenticate(client, contributor)

    monkeypatch.setattr(app_module, "save_uploaded_file", lambda *_args: None)
    response = client.post(
        "/submissions/add",
        data={
            "user_id": str(contributor_id),
            "product_name": "Duplicate",
            "store": "Lidl",
            "barcode": "5941238013309",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 409
    assert response.get_json()["code"] == "product_already_exists"


def test_internal_maintenance_cron_rejects_missing_or_wrong_secret(app, client, monkeypatch):
    monkeypatch.setattr(app_module, "CRON_SECRET", "test-cron-secret")

    missing = client.post("/internal/cron/maintenance", json={})
    wrong = client.post(
        "/internal/cron/maintenance",
        json={},
        headers={"Authorization": "Bearer wrong"},
    )

    assert missing.status_code == 401
    assert wrong.status_code == 401


def test_internal_maintenance_cron_runs_all_free_jobs_with_valid_secret(
    app, client, monkeypatch
):
    monkeypatch.setattr(app_module, "CRON_SECRET", "test-cron-secret")
    monkeypatch.setattr(app_module, "is_email_configured", lambda: False)
    monkeypatch.setattr(
        app_module,
        "recategorize_catalog_products",
        lambda **kwargs: {"changed": 2, "scanned": kwargs["limit"], "applied": True},
    )
    monkeypatch.setattr(
        app_module,
        "build_mission_digest_batch",
        lambda **kwargs: {"eligible": 3, "sent": 0, "applied": kwargs["apply_changes"]},
    )
    monkeypatch.setattr(
        app_module,
        "run_retention_cleanup",
        lambda **kwargs: {"applied": kwargs["apply_changes"], "searchEvents": 1},
    )
    monkeypatch.setattr(
        app_module,
        "get_catalog_quality_snapshot",
        lambda: {"healthScore": 92.5, "products": 100},
    )

    response = client.post(
        "/internal/cron/maintenance",
        json={
            "recategorizeLimit": 25,
            "digestLimit": 10,
            "sendDigest": True,
            "recategorize": True,
            "retention": True,
            "catalogQuality": True,
        },
        headers={"Authorization": "Bearer test-cron-secret"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["recategorize"]["scanned"] == 25
    assert payload["missionDigest"]["emailConfigured"] is False
    assert payload["missionDigest"]["applied"] is False
    assert payload["retention"]["applied"] is True
    assert payload["catalogQuality"]["healthScore"] == 92.5
    assert payload["status"] == "degraded"
    assert payload["runId"].startswith("manual-")
    assert payload["lock"] == "local"
    assert payload["durationMs"] >= 0
    assert set(payload["durationsMs"]) == {
        "recategorize",
        "missionDigest",
        "retention",
        "catalogQuality",
    }
    assert payload["warnings"]


def test_internal_maintenance_cron_validates_run_id_and_rejects_overlap(
    app, client, monkeypatch
):
    monkeypatch.setattr(app_module, "CRON_SECRET", "test-cron-secret")
    headers = {"Authorization": "Bearer test-cron-secret"}

    invalid = client.post(
        "/internal/cron/maintenance",
        json={"runId": "invalid run id"},
        headers=headers,
    )

    assert invalid.status_code == 400

    monkeypatch.setattr(
        app_module,
        "acquire_maintenance_lock",
        lambda _run_id: ("redis", False),
    )
    overlapping = client.post(
        "/internal/cron/maintenance",
        json={"runId": "github-123-1"},
        headers=headers,
    )

    assert overlapping.status_code == 409
    assert overlapping.headers["Retry-After"] == "30"
    assert overlapping.get_json()["status"] == "already_running"


def test_maintenance_redis_lock_is_released_only_with_its_owner_token(monkeypatch):
    class FakeRedis:
        def __init__(self):
            self.set_call = None
            self.eval_call = None

        def set(self, *args, **kwargs):
            self.set_call = (args, kwargs)
            return True

        def eval(self, *args):
            self.eval_call = args
            return 1

    redis = FakeRedis()
    monkeypatch.setattr(app_module, "get_redis_client", lambda: redis)

    lock_type, acquired = app_module.acquire_maintenance_lock("github-42-1")
    app_module.release_maintenance_lock(lock_type, "github-42-1")

    assert lock_type == "redis"
    assert acquired is True
    assert redis.set_call[0] == (
        app_module.MAINTENANCE_LOCK_KEY,
        "github-42-1",
    )
    assert redis.set_call[1]["nx"] is True
    assert redis.eval_call[-2:] == (
        app_module.MAINTENANCE_LOCK_KEY,
        "github-42-1",
    )


def test_internal_maintenance_releases_local_lock_after_failure(
    app, client, monkeypatch
):
    monkeypatch.setattr(app_module, "CRON_SECRET", "test-cron-secret")
    monkeypatch.setattr(app_module, "get_redis_client", lambda: None)
    monkeypatch.setattr(
        app_module,
        "execute_cron_maintenance",
        lambda _data: (_ for _ in ()).throw(RuntimeError("maintenance failed")),
    )

    response = client.post(
        "/internal/cron/maintenance",
        json={"runId": "failure-test"},
        headers={"Authorization": "Bearer test-cron-secret"},
    )

    assert response.status_code == 500
    assert response.get_json()["status"] == "failed"
    assert app_module.MAINTENANCE_LOCAL_LOCK.locked() is False


def test_admin_readiness_monitoring_and_email_diagnostics_are_available(
    app, client, monkeypatch
):
    with app.app_context():
        admin = create_user("admin@example.com", admin=True)
        member = create_user()
        db.session.add_all([
            SearchEvent(
                search_text="missing barcode",
                store="Lidl",
                result_count=0,
                source="barcode_not_found",
            ),
            UsageEvent(
                user_id=member.id,
                event_type="payment_error",
                source="subscription_checkout",
                metadata_json='{"error":"provider unavailable"}',
            ),
            UsageEvent(
                user_id=member.id,
                event_type="cecoin_purchase",
                source="stripe",
                metadata_json='{"coins":500}',
            ),
        ])
        db.session.commit()
        authenticate(client, admin)

    monkeypatch.setattr(app_module, "get_redis_client", lambda: None)
    readiness = client.get("/readiness")
    monitoring = client.get("/admin/monitoring?days=7&limit=10")
    email_test = client.post("/admin/email-test", json={"to": "admin@example.com"})

    assert readiness.status_code == 200
    assert readiness.get_json()["freeMode"] is True
    assert "blockers" in readiness.get_json()
    assert monitoring.status_code == 200
    payload = monitoring.get_json()
    assert payload["scanIssues"]["barcodeNotFound"] == 1
    assert payload["payments"]["checkoutErrors"] == 1
    assert payload["payments"]["cecoinsSold"] == 500
    assert payload["cache"]["connected"] is False
    assert email_test.status_code == 400
    assert email_test.get_json()["sent"] is False


def test_admin_csv_export_neutralizes_formula_cells(app, client):
    with app.app_context():
        admin = create_user("admin@example.com", admin=True)
        db.session.add(SearchEvent(
            search_text='=HYPERLINK("https://example.test")',
            store="Lidl",
            result_count=0,
            source="search",
        ))
        db.session.commit()
        authenticate(client, admin)

    response = client.get("/admin/export/search-misses.csv")

    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert "'=HYPERLINK" in response.get_data(as_text=True)


def test_ai_status_uses_free_local_mode_and_cache(app, client, monkeypatch):
    app_module.AI_STATUS_CACHE["data"] = None
    app_module.AI_STATUS_CACHE["created_at"] = 0
    monkeypatch.delenv("LIBRETRANSLATE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ENABLE_OPENAI_VISION", "false")

    first = client.get("/ai/status")
    second = client.get("/ai/status")

    assert first.status_code == 200
    payload = first.get_json()
    assert payload["localOcr"]["enabled"] is True
    assert payload["cloudVision"]["enabled"] is False
    assert payload["cloudVision"]["required"] is False
    assert payload["freeMode"]["enabled"] is True
    assert second.get_json() == payload
