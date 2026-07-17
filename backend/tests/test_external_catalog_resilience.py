import requests

import pytest

import app as app_module


class FakeResponse:
    def __init__(self, payload=None, *, status_code=200, error=None):
        self._payload = payload or {}
        self.status_code = status_code
        self._error = error

    def raise_for_status(self):
        if self._error:
            raise self._error
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def isolate_off_caches(monkeypatch):
    app_module.OPEN_FOOD_FACTS_ALTERNATIVES_CACHE.clear()
    app_module.OPEN_FOOD_FACTS_PRODUCT_CACHE.clear()
    monkeypatch.setattr(app_module, "EXTERNAL_CATALOG_ENABLED", True)
    monkeypatch.setattr(app_module, "distributed_cache_get", lambda *_args: None)
    monkeypatch.setattr(app_module, "distributed_cache_set", lambda *_args: True)

    def reject_network(*_args, **_kwargs):
        raise AssertionError("External catalog test attempted an unmocked request")

    monkeypatch.setattr(app_module.requests, "get", reject_network)
    yield
    app_module.OPEN_FOOD_FACTS_ALTERNATIVES_CACHE.clear()
    app_module.OPEN_FOOD_FACTS_PRODUCT_CACHE.clear()


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("", ""),
        ("Gelatelli inghetata alune ciocolata", "gelatelli hazelnut chocolate ice cream"),
        ("Samyang Buldak", "samyang buldak ramen instant noodles"),
        ("ramen Nongshim", "ramen instant noodles"),
        ("Zuzu iaurt cu capsuni", "zuzu iaurt fructe"),
        ("iaurt cu afine", "fruit yogurt"),
        ("Red Bull zero", "red bull zero sugar"),
        ("Red Bull clasic", "red bull"),
        ("Monster 0", "monster zero sugar"),
        ("Hell cafea fara zahar", "hell cafea fara zahar zero sugar energy drink"),
        ("Lidl produs unt 200g pret 12 lei", "unt 200g"),
    ],
)
def test_text_search_terms_are_stable_for_romanian_queries(query, expected):
    assert app_module.get_off_text_search_terms(query) == expected


@pytest.mark.parametrize(
    ("product", "expected"),
    [
        ({"name": "Danette budinca", "brand": "", "category": ""}, "dairy dessert pudding"),
        ({"name": "Samyang Buldak", "brand": "", "category": ""}, "samyang buldak ramen instant noodles"),
        ({"name": "Zuzu iaurt fructe", "brand": "", "category": ""}, "zuzu iaurt fructe"),
        ({"name": "Gelatelli inghetata", "brand": "", "category": ""}, "gelatelli ice cream"),
        ({"name": "Red Bull", "brand": "", "category": ""}, "zero sugar energy drink"),
        ({"name": "Cafea latte", "brand": "", "category": ""}, "zero sugar energy drink iced coffee"),
        ({"name": "Produs", "brand": "", "category": "Altele"}, ""),
    ],
)
def test_alternative_search_terms_prioritize_product_families(product, expected):
    assert app_module.get_off_search_terms(product) == expected


def test_fetch_off_products_supports_kill_switch_distributed_and_local_cache(monkeypatch):
    monkeypatch.setattr(app_module, "EXTERNAL_CATALOG_ENABLED", False)
    assert app_module.fetch_off_products({}, "disabled") == []

    monkeypatch.setattr(app_module, "EXTERNAL_CATALOG_ENABLED", True)
    monkeypatch.setattr(
        app_module,
        "distributed_cache_get",
        lambda namespace, key: [{"code": "distributed"}]
        if (namespace, key) == ("off-search", "distributed")
        else None,
    )
    assert app_module.fetch_off_products({}, "distributed") == [
        {"code": "distributed"}
    ]

    app_module.OPEN_FOOD_FACTS_ALTERNATIVES_CACHE["local"] = {
        "created_at": app_module.time.time(),
        "products": [{"code": "local"}],
    }
    assert app_module.fetch_off_products({}, "local") == [{"code": "local"}]


def test_fetch_off_products_requests_and_caches_provider_response(monkeypatch):
    cache_writes = []
    calls = []
    monkeypatch.setattr(
        app_module,
        "distributed_cache_set",
        lambda *args: cache_writes.append(args) or True,
    )
    monkeypatch.setattr(
        app_module.requests,
        "get",
        lambda url, **kwargs: calls.append((url, kwargs))
        or FakeResponse({"products": [{"code": "5940000000001"}]}),
    )

    result = app_module.fetch_off_products(
        {"categories_tags": "en:yogurts"},
        "category:en:yogurts",
    )

    assert result == [{"code": "5940000000001"}]
    assert calls[0][0].endswith("/api/v2/search")
    assert calls[0][1]["params"]["page_size"] == 40
    assert calls[0][1]["params"]["categories_tags"] == "en:yogurts"
    assert cache_writes[0][0:2] == ("off-search", "category:en:yogurts")
    assert app_module.fetch_off_category_products("en:yogurts") == result


def test_fetch_barcode_uses_kill_switch_and_distributed_cache(monkeypatch):
    monkeypatch.setattr(app_module, "EXTERNAL_CATALOG_ENABLED", False)
    assert app_module.fetch_off_product_by_barcode("5940000000001") is None

    monkeypatch.setattr(app_module, "EXTERNAL_CATALOG_ENABLED", True)
    assert app_module.fetch_off_product_by_barcode("") is None

    cached = {"code": "5940000000001", "product_name": "Cached"}
    monkeypatch.setattr(
        app_module,
        "distributed_cache_get",
        lambda _namespace, key: {"found": True, "product": cached}
        if key.endswith("001")
        else {"found": False, "product": None},
    )
    assert app_module.fetch_off_product_by_barcode("5940000000001") == cached
    assert app_module.fetch_off_product_by_barcode("5940000000002") is None


def test_fetch_barcode_caches_404_invalid_and_valid_payloads(monkeypatch):
    responses = iter(
        [
            FakeResponse(status_code=404),
            FakeResponse({"status": 0}),
            FakeResponse(
                {
                    "status": 1,
                    "code": "5940000000005",
                    "product": {"product_name": "Provider product"},
                }
            ),
        ]
    )
    writes = []
    monkeypatch.setattr(app_module.requests, "get", lambda *_a, **_kw: next(responses))
    monkeypatch.setattr(
        app_module,
        "distributed_cache_set",
        lambda *args: writes.append(args) or True,
    )

    assert app_module.fetch_off_product_by_barcode("5940000000003") is None
    assert app_module.fetch_off_product_by_barcode("5940000000004") is None
    product = app_module.fetch_off_product_by_barcode("5940000000005")

    assert product["code"] == "5940000000005"
    assert product["product_name"] == "Provider product"
    assert writes[0][2]["found"] is False
    assert writes[-1][2]["found"] is True


def test_fetch_off_search_products_builds_category_query(monkeypatch):
    calls = []
    monkeypatch.setattr(
        app_module,
        "fetch_off_products",
        lambda params, key: calls.append((params, key)) or [{"code": "one"}],
    )

    assert app_module.fetch_off_search_products(
        {"name": "Iaurt cu fructe", "brand": "", "category": "Lactate"},
        "en:yogurts",
    ) == [{"code": "one"}]
    assert calls == [
        (
            {"search_terms": "fruit yogurt", "categories_tags": "en:yogurts"},
            "search:en:yogurts:fruit yogurt",
        )
    ]
    assert app_module.fetch_off_search_products(
        {"name": "Produs", "brand": "", "category": "Altele"}
    ) == []


def test_seed_fallback_deduplicates_and_survives_provider_errors(monkeypatch):
    monkeypatch.setitem(
        app_module.OFF_FALLBACK_BARCODES_BY_CATEGORY,
        "test:category",
        ["scan", "good", "broken", "good"],
    )
    monkeypatch.setitem(
        app_module.OFF_FALLBACK_BARCODES_BY_CATEGORY,
        "en:iced-coffees",
        ["coffee"],
    )
    monkeypatch.setitem(
        app_module.OFF_FALLBACK_BARCODES_BY_CATEGORY,
        "en:energy-drinks",
        ["energy"],
    )
    calls = []

    def fake_fetch(barcode):
        calls.append(barcode)
        if barcode == "broken":
            raise requests.ConnectionError("provider offline")
        return None if barcode == "energy" else {"code": barcode}

    monkeypatch.setattr(app_module, "fetch_off_product_by_barcode", fake_fetch)

    products = app_module.fetch_off_seed_products(
        {
            "barcode": "scan",
            "name": "Hell ice coffee",
            "brand": "Hell",
            "category": "Bauturi cu cafea",
            "ingredients": "cafeina",
        },
        "test:category",
    )

    assert calls == ["good", "broken", "coffee", "energy"]
    assert products == [{"code": "good"}, {"code": "coffee"}]
