import json

import pytest
import requests
from werkzeug.security import generate_password_hash

import app as app_module
from database import db
from models import Product, UsageEvent, User


class FakeResponse:
    def __init__(self, payload, *, error=None):
        self.payload = payload
        self.error = error

    def raise_for_status(self):
        if self.error:
            raise self.error

    def json(self):
        return self.payload


@pytest.fixture(autouse=True)
def isolate_catalog_integrations(monkeypatch):
    app_module.OPEN_PRICES_CACHE.clear()
    app_module.OPEN_FOOD_FACTS_ALTERNATIVES_CACHE.clear()
    monkeypatch.setattr(app_module, "distributed_cache_get", lambda *_args: None)
    monkeypatch.setattr(app_module, "distributed_cache_set", lambda *_args: True)
    monkeypatch.setattr(app_module, "rate_limit", lambda *_args: True)

    def reject_unmocked_network(*_args, **_kwargs):
        raise AssertionError("Catalog tests must not access the network")

    monkeypatch.setattr(app_module.requests, "get", reject_unmocked_network)
    yield
    app_module.OPEN_PRICES_CACHE.clear()
    app_module.OPEN_FOOD_FACTS_ALTERNATIVES_CACHE.clear()


def create_user(email, *, admin=False):
    user = User(
        name="Catalog Admin" if admin else "Catalog Reporter",
        email=email,
        password_hash=generate_password_hash("A-secure-password-123!"),
        email_verified=True,
        is_admin=admin,
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


def create_product(**overrides):
    values = {
        "name": "Produs de catalog",
        "store": "Lidl",
        "category": "Altele",
        "barcode": "5941000000001",
        "score": 5.0,
        "calories": 80,
        "protein": 4,
        "sugar": 5,
        "fat": 2,
        "ingredients": "ingrediente simple",
    }
    values.update(overrides)
    product = Product(**values)
    db.session.add(product)
    db.session.commit()
    return product


def create_alternative_report(user, alternative_product):
    event = UsageEvent(
        user_id=user.id,
        event_type="alternative_report",
        source="scanner",
        metadata_json=json.dumps(
            {"reason": "categorie greșită", "alternativeProduct": alternative_product},
            ensure_ascii=False,
        ),
    )
    db.session.add(event)
    db.session.commit()
    return event


def test_recategorize_dry_run_reports_pagination_without_persisting(app, monkeypatch):
    with app.app_context():
        first = create_product(name="Iaurt simplu", barcode="5941000000001")
        second = create_product(name="Suc de mere", barcode="5941000000002")
        first_id = first.id
        second_id = second.id

        monkeypatch.setattr(
            app_module,
            "infer_catalog_category",
            lambda product: (
                "Iaurturi simple" if "Iaurt" in product["name"] else "Suc de mere"
            ),
        )

        result = app_module.recategorize_catalog_products(
            limit=1,
            apply_changes=False,
        )

        assert result == {
            "scanned": 1,
            "changed": 1,
            "applied": False,
            "minId": None,
            "lastScannedId": first_id,
            "nextMinId": first_id + 1,
            "hasMore": True,
            "category": None,
            "changes": [
                {
                    "id": first_id,
                    "name": "Iaurt simplu",
                    "barcode": "5941000000001",
                    "oldCategory": "Altele",
                    "newCategory": "Iaurturi simple",
                }
            ],
        }
        assert db.session.get(Product, first_id).category == "Altele"
        assert db.session.get(Product, second_id).category == "Altele"


def test_recategorize_apply_updates_category_and_derived_fields(app, monkeypatch):
    with app.app_context():
        target = create_product(name="Skyr proteic", barcode="5941000000003")
        ignored = create_product(
            name="Ciocolată neagră",
            barcode="5941000000004",
            category="Ciocolată",
        )
        target_id = target.id
        ignored_id = ignored.id

        monkeypatch.setattr(
            app_module,
            "infer_catalog_category",
            lambda _product: "Iaurturi proteice",
        )
        monkeypatch.setattr(app_module, "calculate_product_score", lambda *_args: 9.4)
        monkeypatch.setattr(app_module, "generate_product_tag", lambda *_args: "Proteic")
        monkeypatch.setattr(
            app_module,
            "generate_product_reason",
            lambda *_args: "Conținut bun de proteine.",
        )

        result = app_module.recategorize_catalog_products(
            limit=50,
            apply_changes=True,
            category="Altele",
        )

        db.session.expire_all()
        updated = db.session.get(Product, target_id)
        untouched = db.session.get(Product, ignored_id)
        assert result["scanned"] == 1
        assert result["changed"] == 1
        assert result["applied"] is True
        assert result["category"] == "Altele"
        assert result["hasMore"] is False
        assert updated.category == "Iaurturi proteice"
        assert updated.score == 9.4
        assert updated.tag == "Proteic"
        assert updated.reason == "Conținut bun de proteine."
        assert untouched.category == "Ciocolată"


def test_resolve_admin_alternative_report_manual_persists_review_and_audit(
    app, client
):
    with app.app_context():
        admin = create_user("admin-catalog@example.com", admin=True)
        reporter = create_user("reporter@example.com")
        product = create_product(
            name="Telemea de vacă",
            barcode="5941000000005",
        )
        product_id = product.id
        event = create_alternative_report(
            reporter,
            {
                "id": product.id,
                "name": product.name,
                "barcode": product.barcode,
                "category": "Altele",
                "store": product.store,
            },
        )
        event_id = event.id
        admin_id = admin.id
        authenticate(client, admin)

    response = client.post(
        f"/admin/alternative-reports/{event_id}/resolve",
        json={"category": "Telemea și feta"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["fixed"] is True
    assert payload["product"]["id"] == product_id
    assert payload["product"]["category"] == "Telemea și feta"
    assert payload["event"]["metadata"]["adminReview"]["method"] == "manual"
    assert payload["event"]["metadata"]["adminReview"]["reviewedBy"] == (
        "admin-catalog@example.com"
    )

    with app.app_context():
        assert db.session.get(Product, product_id).category == "Telemea și feta"
        stored_metadata = json.loads(db.session.get(UsageEvent, event_id).metadata_json)
        assert stored_metadata["alternativeProduct"]["category"] == "Telemea și feta"
        audit = UsageEvent.query.filter_by(
            user_id=admin_id,
            event_type="alternative_report_resolved",
        ).one()
        assert json.loads(audit.metadata_json)["reportId"] == event_id


def test_resolve_admin_alternative_report_auto_uses_catalog_inference(app, client):
    with app.app_context():
        admin = create_user("admin-auto@example.com", admin=True)
        reporter = create_user("reporter-auto@example.com")
        product = create_product(
            name="Iaurt grecesc simplu",
            barcode="5941000000006",
        )
        product_id = product.id
        event = create_alternative_report(
            reporter,
            {
                "id": product.id,
                "name": product.name,
                "barcode": product.barcode,
                "category": "Altele",
                "ingredients": "lapte, culturi lactice",
            },
        )
        event_id = event.id
        authenticate(client, admin)

    response = client.post(f"/admin/alternative-reports/{event_id}/resolve", json={})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["fixed"] is True
    assert payload["product"]["category"] == "Iaurturi grecești"
    assert payload["event"]["metadata"]["adminReview"]["method"] == "auto"

    with app.app_context():
        assert db.session.get(Product, product_id).category == "Iaurturi grecești"


def test_resolve_admin_alternative_report_validates_report(app, client):
    with app.app_context():
        admin = create_user("admin-errors@example.com", admin=True)
        reporter = create_user("reporter-errors@example.com")
        malformed = UsageEvent(
            user_id=reporter.id,
            event_type="alternative_report",
            metadata_json=json.dumps({"alternativeProduct": {"barcode": "123"}}),
        )
        db.session.add(malformed)
        db.session.commit()
        malformed_id = malformed.id
        authenticate(client, admin)

    missing = client.post("/admin/alternative-reports/999999/resolve", json={})
    invalid = client.post(
        f"/admin/alternative-reports/{malformed_id}/resolve",
        json={},
    )

    assert missing.status_code == 404
    assert missing.get_json()["error"] == "Raportarea nu exista."
    assert invalid.status_code == 400
    assert invalid.get_json()["error"] == "Raportarea nu contine alternativa valida."


def test_open_prices_prefers_romanian_result_and_reuses_cache(monkeypatch):
    calls = []
    response = FakeResponse({
        "items": [
            {
                "price": 3.0,
                "currency": "EUR",
                "date": "2026-07-16",
                "location": {"osm_name": "Foreign Store", "osm_address_country_code": "DE"},
            },
            {
                "price": 12.49,
                "currency": "RON",
                "date": "2026-06-01",
                "location": {"osm_brand": "Lidl", "osm_address_country_code": "RO"},
            },
            {"price": None, "currency": "RON"},
        ]
    })

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return response

    monkeypatch.setattr(app_module, "OPEN_PRICES_ENABLED", True)
    monkeypatch.setattr(app_module.requests, "get", fake_get)

    first = app_module.get_open_prices_summary("5941000000010")
    second = app_module.get_open_prices_summary("5941000000010")

    assert first == second
    assert first["price"] == 12.49
    assert first["priceText"] == "12,49 lei"
    assert first["priceStore"] == "Lidl"
    assert first["priceCountry"] == "RO"
    assert first["priceCurrency"] == "RON"
    assert first["priceIsLocal"] is True
    assert first["priceIsConverted"] is False
    assert len(calls) == 1
    assert calls[0][0] == "https://prices.openfoodfacts.org/api/v1/prices"
    assert calls[0][1]["params"] == {
        "product_code": "5941000000010",
        "size": 12,
        "order_by": "-date",
    }


def test_open_prices_converts_supported_currency_and_preserves_unknown_currency(
    monkeypatch,
):
    payloads = iter([
        {
            "items": [{
                "price": "2.50",
                "currency": "EUR",
                "date": "2026-07-15",
                "location": {"osm_name": "Euro Store", "osm_address_country_code": "DE"},
            }]
        },
        {
            "items": [{
                "price": 7,
                "currency": "XYZ",
                "date": "2026-07-14",
                "location": {"osm_name": "Unknown Store", "osm_address_country_code": "ZZ"},
            }]
        },
    ])
    monkeypatch.setattr(app_module, "OPEN_PRICES_ENABLED", True)
    monkeypatch.setattr(
        app_module.requests,
        "get",
        lambda *_args, **_kwargs: FakeResponse(next(payloads)),
    )

    converted = app_module.get_open_prices_summary("5941000000011")
    unknown = app_module.get_open_prices_summary("5941000000012")

    assert converted["price"] == 12.5
    assert converted["priceText"] == "aprox. 12,50 lei"
    assert converted["priceCurrency"] == "RON"
    assert converted["priceOriginal"] == 2.5
    assert converted["priceOriginalCurrency"] == "EUR"
    assert converted["priceIsLocal"] is False
    assert converted["priceIsConverted"] is True
    assert unknown["price"] is None
    assert unknown["priceText"] == "Verifică prețul în magazin"
    assert unknown["priceCurrency"] == "XYZ"
    assert unknown["priceOriginal"] == 7.0
    assert unknown["priceIsConverted"] is False


def test_open_prices_error_is_cached_as_empty_result(monkeypatch):
    calls = []

    def fail_get(*_args, **_kwargs):
        calls.append(True)
        raise requests.RequestException("Open Prices unavailable")

    monkeypatch.setattr(app_module, "OPEN_PRICES_ENABLED", True)
    monkeypatch.setattr(app_module.requests, "get", fail_get)

    assert app_module.get_open_prices_summary("5941000000013") is None
    assert app_module.get_open_prices_summary("5941000000013") is None
    assert len(calls) == 1


def test_fetch_off_text_search_deduplicates_and_caches_mocked_responses(monkeypatch):
    calls = []
    payloads = iter([
        {
            "products": [
                {"code": "111", "product_name": "Primul"},
                {"_id": "222", "product_name": "Al doilea"},
                {"product_name": "Fără cod"},
            ]
        },
        {
            "products": [
                {"code": "111", "product_name": "Duplicat"},
                {"code": "333", "product_name": "Al treilea"},
            ]
        },
    ])

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse(next(payloads))

    monkeypatch.setattr(app_module, "EXTERNAL_CATALOG_ENABLED", True)
    monkeypatch.setattr(app_module, "get_off_text_search_terms", lambda _query: "iaurt")
    monkeypatch.setattr(app_module, "detect_query_brand", lambda _query: "brand")
    monkeypatch.setattr(app_module.requests, "get", fake_get)

    first = app_module.fetch_off_text_search_products("Iaurt Brand")
    second = app_module.fetch_off_text_search_products("Iaurt Brand")

    assert [item.get("code") or item.get("_id") for item in first] == [
        "111",
        "222",
        "333",
    ]
    assert second == first
    assert len(calls) == 2
    assert {call[1]["params"]["search_terms"] for call in calls} == {"iaurt", "iaurt brand"}
    assert all(call[1]["params"]["page_size"] == 20 for call in calls)


def test_fetch_off_text_search_raises_when_all_mocked_requests_fail(monkeypatch):
    calls = []

    def fail_get(*_args, **_kwargs):
        calls.append(True)
        raise requests.RequestException("OFF unavailable")

    monkeypatch.setattr(app_module, "EXTERNAL_CATALOG_ENABLED", True)
    monkeypatch.setattr(app_module, "get_off_text_search_terms", lambda _query: "produs")
    monkeypatch.setattr(app_module, "detect_query_brand", lambda _query: "brand")
    monkeypatch.setattr(app_module.requests, "get", fail_get)

    with pytest.raises(requests.RequestException, match="OFF unavailable"):
        app_module.fetch_off_text_search_products("Produs necunoscut")

    assert len(calls) == 2


def test_build_product_from_open_food_facts_maps_localized_product_without_network():
    product = app_module.build_product_from_open_food_facts(
        "5941000000014",
        {
            "product_name": "Fallback name",
            "product_name_ro": "Monster Energy original",
            "brands": "Monster",
            "quantity": "500 ml",
            "categories": "Energy drinks",
            "categories_tags": ["en:energy-drinks"],
            "ingredients_text_ro": "apă, zahăr, taurină, cafeină",
            "ingredients_analysis_tags": ["en:vegan"],
            "labels_tags": ["en:lactose-free"],
            "additives_n": 0,
            "nutrition_grades": "d",
            "image_front_url": "https://images.example.test/monster.jpg",
            "nutriments": {
                "energy-kcal_100g": 45,
                "proteins_100g": 0,
                "sugars_100g": 11,
                "fat_100g": 0,
            },
        },
        translate_ingredients=False,
    )

    assert product["barcode"] == "5941000000014"
    assert product["name"] == "Monster Energy original"
    assert product["brand"] == "Monster"
    assert product["store"] == "Open Food Facts"
    assert product["category"] == "Băuturi energizante"
    assert product["quantity"] == "500 ml"
    assert product["calories"] == 45
    assert product["protein"] == 0
    assert product["sugar"] == 11
    assert product["fat"] == 0
    assert product["vegan"] is True
    assert product["lactoseFree"] is True
    assert product["natural"] is True
    assert product["nutriScore"] == "d"
    assert product["score"] is not None
    assert product["image"] == "https://images.example.test/monster.jpg"
    assert product["ingredients"] == "apă, zahăr, taurină, cafeină"
