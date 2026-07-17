import requests

import app as app_module
from database import db
from models import Product


def add_local_product():
    product = Product(
        name="Iaurt natural local",
        store="Lidl",
        category="Lactate",
        barcode="5940000000100",
        score=8.8,
        calories=62,
        protein=5.2,
        sugar=3.8,
        fat=2.1,
        ingredients="lapte, culturi lactice",
    )
    db.session.add(product)
    db.session.commit()
    return product


def test_local_search_survives_external_catalog_outage(app, client, monkeypatch):
    with app.app_context():
        add_local_product()

    app_module.PRODUCT_SEARCH_RESULT_CACHE.clear()
    monkeypatch.setattr(app_module, "EXTERNAL_CATALOG_ENABLED", True)
    monkeypatch.setattr(
        app_module,
        "fetch_off_text_search_products",
        lambda _query: (_ for _ in ()).throw(requests.RequestException("offline")),
    )

    response = client.get("/products/search?q=Iaurt%20local&store=any")

    assert response.status_code == 200
    assert response.headers["X-Product-Source"] == "local-fallback"
    assert response.headers["X-External-Catalog"] == "unavailable"
    assert response.get_json()[0]["name"] == "Iaurt natural local"


def test_search_reports_external_outage_when_no_local_match(app, client, monkeypatch):
    app_module.PRODUCT_SEARCH_RESULT_CACHE.clear()
    monkeypatch.setattr(app_module, "EXTERNAL_CATALOG_ENABLED", True)
    monkeypatch.setattr(
        app_module,
        "fetch_off_text_search_products",
        lambda _query: (_ for _ in ()).throw(requests.RequestException("offline")),
    )

    response = client.get("/products/search?q=produs%20inexistent&store=any")

    assert response.status_code == 502
    assert response.get_json()["code"] == "external_catalog_unavailable"


def test_exact_local_search_skips_external_catalog(app, client, monkeypatch):
    with app.app_context():
        add_local_product()

    app_module.PRODUCT_SEARCH_RESULT_CACHE.clear()
    monkeypatch.setattr(app_module, "EXTERNAL_CATALOG_ENABLED", True)
    monkeypatch.setattr(
        app_module,
        "fetch_off_text_search_products",
        lambda _query: (_ for _ in ()).throw(AssertionError("external lookup should be skipped")),
    )

    response = client.get("/products/search?q=Iaurt%20natural%20local&store=any")

    assert response.status_code == 200
    assert response.headers["X-Product-Source"] == "local_catalog"
    assert response.get_json()[0]["name"] == "Iaurt natural local"


def test_external_catalog_can_be_disabled_without_network(app, client, monkeypatch):
    monkeypatch.setattr(app_module, "EXTERNAL_CATALOG_ENABLED", False)
    monkeypatch.setattr(
        app_module.requests,
        "get",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("network disabled")),
    )

    response = client.get("/products/search?q=produs%20inexistent&store=any")

    assert response.status_code == 200
    assert response.headers["X-External-Catalog"] == "disabled"
    assert response.get_json() == []


def test_open_prices_can_be_disabled_without_network(monkeypatch):
    monkeypatch.setattr(app_module, "OPEN_PRICES_ENABLED", False)
    monkeypatch.setattr(
        app_module.requests,
        "get",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("network disabled")),
    )

    assert app_module.get_open_prices_summary("5940000000100") is None
