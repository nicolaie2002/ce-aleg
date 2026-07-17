import io

import requests
from werkzeug.security import generate_password_hash

import app as app_module
from database import db
from models import PriceObservation, Product, ProductSubmission, SearchEvent, UsageEvent, User


def create_user(email="scanner@example.com"):
    user = User(
        name="Scanner User",
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


def create_product(index=0, **overrides):
    values = {
        "name": f"Iaurt natural {index}",
        "store": "Lidl",
        "category": "Lactate",
        "barcode": f"5941238013{309 + index:03d}",
        "score": 8.0 + min(index, 10) / 20,
        "price": 4.5 + index / 10,
        "price_text": f"{4.5 + index / 10:.2f} lei",
        "calories": 60 + index,
        "protein": 5 + index / 10,
        "sugar": 4 + index / 20,
        "fat": 2,
        "ingredients": "lapte, culturi lactice",
        "image": f"https://example.test/yogurt-{index}.jpg",
        "natural": True,
    }
    values.update(overrides)
    product = Product(**values)
    db.session.add(product)
    db.session.commit()
    return product


def open_food_facts_yogurt(name="Iaurt OFF"):
    return {
        "product_name": name,
        "product_name_ro": name,
        "brands": "Brand OFF",
        "categories": "Dairies, Yogurts",
        "categories_tags": ["en:dairies", "en:yogurts"],
        "stores": "Lidl",
        "image_front_url": "https://images.example.test/yogurt.jpg",
        "ingredients_text_ro": "lapte, culturi lactice",
        "nutriments": {
            "energy-kcal_100g": 63,
            "proteins_100g": 5.2,
            "sugars_100g": 3.9,
            "fat_100g": 2.1,
        },
        "nutrition_grades": "a",
    }


def test_products_list_supports_store_filter_and_pagination(app, client):
    with app.app_context():
        first = create_product(0, barcode="5941238013309")
        create_product(1, store="Kaufland", barcode="5941238013316")
        first_id = first.id

    all_products = client.get("/products?limit=1&offset=0")
    lidl_products = client.get("/products?store=Lidl")

    assert all_products.status_code == 200
    assert len(all_products.get_json()) == 1
    assert lidl_products.status_code == 200
    assert [item["id"] for item in lidl_products.get_json()] == [first_id]


def test_local_barcode_lookup_records_usage_and_uses_reported_price(app, client):
    with app.app_context():
        user = create_user()
        product = create_product(
            barcode="5941238013309",
            price=None,
            price_text=None,
        )
        db.session.add(PriceObservation(
            user_id=user.id,
            product_barcode=product.barcode,
            store="Lidl",
            price=4.79,
            currency="RON",
        ))
        db.session.commit()
        authenticate(client, user)

    response = client.get("/barcode/lookup/5941238013309")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["found"] is True
    assert payload["source"] == "local"
    assert payload["product"]["price"] == 4.79
    assert payload["product"]["priceSource"] == "Ce aleg?"
    assert payload["usage"]["monthlyScansUsed"] == 1

    with app.app_context():
        event = UsageEvent.query.filter_by(event_type="scan").one()
        assert event.source == "barcode"


def test_external_barcode_lookup_is_cached_locally(app, client, monkeypatch):
    with app.app_context():
        user = create_user()
        authenticate(client, user)

    monkeypatch.setattr(
        app_module,
        "fetch_off_product_by_barcode",
        lambda _barcode: open_food_facts_yogurt("Iaurt importat"),
    )
    monkeypatch.setattr(app_module, "get_open_prices_summary", lambda _barcode: None)

    response = client.get("/barcode/lookup/5941238013309")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["source"] == "openfoodfacts"
    assert payload["cached"] is True
    assert payload["product"]["name"] == "Iaurt importat"
    assert payload["product"]["category"] != "Altele"

    with app.app_context():
        product = Product.query.filter_by(barcode="5941238013309").one()
        assert product.name == "Iaurt importat"
        assert product.protein == 5.2


def test_external_barcode_lookup_distinguishes_outage_from_missing_product(
    app, client, monkeypatch
):
    with app.app_context():
        user = create_user()
        authenticate(client, user)

    monkeypatch.setattr(app_module, "fetch_off_product_by_barcode", lambda _barcode: None)
    missing = client.get("/barcode/lookup/5941238013309")

    monkeypatch.setattr(
        app_module,
        "fetch_off_product_by_barcode",
        lambda _barcode: (_ for _ in ()).throw(requests.RequestException("offline")),
    )
    outage = client.get("/barcode/lookup/5941238013316")

    assert missing.status_code == 404
    assert missing.get_json()["code"] == "external_product_not_found"
    assert outage.status_code == 503
    assert outage.get_json()["code"] == "openfoodfacts_unavailable"


def test_local_price_report_is_owned_and_readable(app, client):
    with app.app_context():
        owner = create_user()
        other = create_user("other@example.com")
        owner_id = owner.id
        other_id = other.id
        authenticate(client, owner)

    forbidden = client.post("/prices/report", json={
        "user_id": other_id,
        "barcode": "5941238013309",
        "store": "Lidl",
        "price": 5.25,
    })
    invalid = client.post("/prices/report", json={
        "user_id": owner_id,
        "barcode": "5941238013309",
        "store": "Lidl",
        "price": -1,
    })
    saved = client.post("/prices/report", json={
        "user_id": owner_id,
        "barcode": "5941238013309",
        "store": "Lidl",
        "price": 5.25,
    })
    fetched = client.get("/prices/5941238013309")

    assert forbidden.status_code == 403
    assert invalid.status_code == 400
    assert saved.status_code == 201
    assert saved.get_json()["price"]["priceText"] == "5,25 lei"
    assert fetched.status_code == 200
    assert fetched.get_json()["found"] is True


def test_feedback_and_analytics_respect_identity_and_privacy(app, client, monkeypatch):
    alerts = []
    with app.app_context():
        user = create_user()
        user_id = user.id
        authenticate(client, user)

    monkeypatch.setattr(
        app_module,
        "send_admin_alert",
        lambda *args, **kwargs: alerts.append((args, kwargs)) or True,
    )

    analytics = client.post("/analytics/event", json={
        "name": "product_found",
        "metadata": {"barcode": "5941238013309"},
    })
    alternative = client.post("/feedback/alternative", json={
        "product": {"name": "Iaurt prea dulce", "category": "Lactate"},
        "scannedProduct": {"name": "Iaurt natural", "barcode": "5941238013309"},
        "store": "Lidl",
        "reason": "wrong_recommendation",
    })
    product_report = client.post("/feedback/product", json={
        "product": {"name": "Iaurt natural", "barcode": "5941238013309"},
        "store": "Lidl",
        "reason": "wrong_nutrition",
        "details": "Zaharul de pe eticheta este diferit.",
    })

    assert analytics.status_code == 200
    assert alternative.status_code == 200
    assert product_report.status_code == 200
    assert len(alerts) == 2

    with app.app_context():
        user = db.session.get(User, user_id)
        user.analytics_consent = False
        db.session.commit()

    ignored = client.post("/analytics/event", json={"name": "product_found"})
    assert ignored.get_json()["ignored"] is True
    assert ignored.get_json()["reason"] == "privacy_preference"

    with app.app_context():
        event_types = {
            item.event_type for item in UsageEvent.query.filter_by(user_id=user_id).all()
        }
        assert "ui_product_found" in event_types
        assert "alternative_report" in event_types
        assert "product_report" in event_types


def test_catalog_stats_are_public_cached_and_hide_email_like_names(app, client):
    app_module.PUBLIC_CATALOG_STATS_CACHE["data"] = None
    app_module.PUBLIC_CATALOG_STATS_CACHE["expires_at"] = 0

    with app.app_context():
        user = create_user()
        user.name = "private@example.com"
        product = create_product(barcode="5941238013309")
        db.session.add(ProductSubmission(
            user_id=user.id,
            product_name=product.name,
            store=product.store,
            category=product.category,
            barcode=product.barcode,
            status="approved",
        ))
        db.session.add(SearchEvent(
            search_text="produs local lipsa",
            store="Lidl",
            result_count=0,
        ))
        db.session.commit()

    first = client.get("/catalog/romania/stats")
    second = client.get("/catalog/romania/stats")

    assert first.status_code == 200
    payload = first.get_json()
    assert payload["products"] == 1
    assert payload["approvedSubmissions"] == 1
    assert payload["contributors"] == 1
    assert payload["topContributors"][0]["name"].startswith("Contribuitor #")
    assert second.get_json()["generatedAt"] == payload["generatedAt"]


def test_local_alternatives_survive_external_catalog_outage(app, client, monkeypatch):
    alternative_names = [
        "Iaurt natural Napolact",
        "Iaurt grecesc Olympus",
        "Skyr simplu Pilos",
        "Iaurt bio Zuzu",
        "Iaurt simplu Covalact",
        "Iaurt proteic Muller",
        "Iaurt natural Artesana",
        "Iaurt grecesc Laptaria",
        "Skyr natural Milbona",
        "Iaurt simplu Danone",
        "Iaurt bio Andechser",
        "Iaurt natural Nucet",
        "Iaurt proteic YoPro",
    ]
    with app.app_context():
        user = create_user()
        scanned = create_product(
            0,
            name="Iaurt dulce scanat",
            barcode="5941238013309",
            sugar=14,
            score=4.5,
        )
        for index in range(1, 14):
            create_product(
                index,
                name=alternative_names[index - 1],
                barcode=f"5940000000{index:03d}",
                sugar=max(2.0, 8.0 - index / 3),
                protein=5 + index / 2,
                score=6 + index / 5,
            )
        scanned_payload = app_module.product_to_dict(scanned)
        authenticate(client, user)

    monkeypatch.setattr(
        app_module,
        "fetch_off_category_products",
        lambda *_args: (_ for _ in ()).throw(requests.RequestException("offline")),
    )
    monkeypatch.setattr(
        app_module,
        "fetch_off_search_products",
        lambda *_args: (_ for _ in ()).throw(requests.RequestException("offline")),
    )
    monkeypatch.setattr(app_module, "fetch_off_seed_products", lambda *_args: [])
    monkeypatch.setattr(app_module, "attach_open_prices", lambda _products: None)

    response = client.post("/alternatives/open-food-facts", json={
        "product": scanned_payload,
        "criteria": ["low_sugar", "protein"],
        "preferences": {},
    })

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["source"] == "local-fallback"
    assert 2 <= len(payload["products"]) <= 6
    assert all(item["barcode"] != scanned_payload["barcode"] for item in payload["products"])
    assert payload["products"][0]["recommendationScore"] >= payload["products"][-1]["recommendationScore"]


def test_demo_analysis_uses_confirmed_local_product(app, client, monkeypatch):
    with app.app_context():
        user = create_user()
        product = create_product(barcode="5941238013309")
        product_id = product.id
        authenticate(client, user)

    monkeypatch.setattr(app_module, "save_scan_image", lambda *_args: "scan-test.jpg")

    response = client.post(
        "/analyze",
        data={
            "image": (io.BytesIO(b"image-placeholder"), "product.jpg"),
            "demo_product_id": str(product_id),
            "store": "lidl",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.get_json()["id"] == product_id
    assert response.get_json()["name"] == "Iaurt natural 0"
    assert response.get_json()["uploadedFile"] == "scan-test.jpg"
