import copy

import pytest

import app as app_module
from database import db
from models import Product


def recommendation_product(name, **overrides):
    product = {
        "name": name,
        "brand": "Marcă test",
        "category": "Lactate",
        "score": 7.0,
        "calories": 100,
        "protein": 5,
        "sugar": 10,
        "fat": 3,
        "ingredients": "lapte, culturi lactice",
        "image": "https://example.test/product.jpg",
    }
    product.update(overrides)
    return product


@pytest.mark.parametrize(
    ("label", "expected_type"),
    [
        ("Iaurt cu căpșuni", "fruit_yogurt"),
        ("Iaurt natural", "yogurt"),
        ("Apă minerală", "water"),
        ("Suc de mere", "juice"),
        ("Coca-Cola original", "soft_drink"),
        ("Cafea latte rece", "coffee_drink"),
        ("Înghețată de vanilie", "ice_cream"),
        ("Buldak ramen picant", "instant_noodles"),
        ("Cașcaval afumat", "cheese"),
        ("Monster energy drink", "energy_drink"),
        ("Pufuleți din porumb", "chips"),
        ("Pâine toast", "bread"),
        ("Somon afumat", "fish"),
        ("Detergent pentru vase", None),
    ],
)
def test_detect_product_type_recognizes_product_intent(label, expected_type):
    assert app_module.detect_product_type(label) == expected_type


@pytest.mark.parametrize(
    ("product_data", "expected_family"),
    [
        ({"name": "Apă plată de izvor"}, "still_water"),
        ({"name": "Apă minerală carbogazoasă"}, "sparkling_water"),
        (
            {"name": "Red Bull Zero Sugar băutură energizantă"},
            "zero_energy_drink",
        ),
        ({"name": "Iaurt grecesc 2%"}, "greek_yogurt"),
        ({"name": "Skyr proteic cu vanilie"}, "protein_yogurt"),
        ({"name": "Ciocolată neagră 85%"}, "dark_chocolate"),
        ({"name": "Salam de Sibiu"}, "salami"),
        ({"name": "Ton conservă"}, "tuna_canned"),
        ({"name": "Ulei de măsline extravirgin"}, "olive_oil"),
        ({"name": "Oțet balsamic de Modena"}, "vinegar"),
        ({"name": "Buldak ramen picant"}, "ramen_noodles"),
        ({"name": "Ceai verde la plic"}, "tea_bags"),
        ({"name": "Bere fără alcool 0.0"}, "alcohol_free_beer"),
        ({"name": "Lapte fără lactoză 1.5%"}, "lactose_free_milk"),
        ({"name": "Pâine integrală feliată"}, "wholegrain_bread"),
        ({"name": "Zacuscă de vinete"}, "vegetable_spread"),
        ({"name": "Orez basmati"}, "basmati_rice"),
        ({"name": "Făină albă de grâu"}, "wheat_flour"),
    ],
)
def test_recommendation_family_preserves_specific_product_semantics(
    product_data,
    expected_family,
):
    assert (
        app_module._compute_product_recommendation_family(product_data)
        == expected_family
    )


@pytest.mark.parametrize(
    ("product_data", "expected_category"),
    [
        ({"name": "Bere fără alcool 0.0"}, "Bere fără alcool"),
        ({"name": "Vin roșu Merlot"}, "Băuturi alcoolice"),
        ({"name": "Castraveți murați în oțet"}, "Castraveți murați"),
        ({"name": "Salam de Sibiu"}, "Salam"),
        ({"name": "Iaurt grecesc natural"}, "Iaurturi grecești"),
        ({"name": "Oțet balsamic"}, "Oțet"),
        ({"name": "Pâine integrală feliată"}, "Pâine"),
        (
            {
                "name": "Produs alimentar",
                "ingredients": "semoule de blé dur, apă",
            },
            "Paste",
        ),
        ({"name": "Produs complet necunoscut"}, None),
        ({}, None),
    ],
)
def test_catalog_category_inference_uses_label_and_ingredient_evidence(
    product_data,
    expected_category,
):
    assert (
        app_module.infer_catalog_category_from_label(product_data)
        == expected_category
    )


@pytest.mark.parametrize(
    ("product_data", "expected_off_category"),
    [
        ({"category": "Apă plată"}, "en:spring-waters"),
        (
            {"category": "Apă minerală carbogazoasă"},
            "en:sparkling-waters",
        ),
        ({"category": "Iaurturi grecești"}, "en:greek-yogurts"),
        ({"category": "Conserve de ton"}, "en:canned-tunas"),
        ({"category": "Oțet"}, "en:vinegars"),
        ({"category": "Uleiuri"}, "en:oils"),
        ({"name": "Salam de Sibiu"}, "en:processed-meats"),
        (
            {"name": "Red Bull băutură energizantă"},
            "en:energy-drinks",
        ),
        ({"name": "Iaurt cu căpșuni"}, "en:fruit-yogurts"),
        ({"name": "Telemea de vacă"}, "en:cheeses"),
        ({"name": "Potato chips"}, "en:chips-and-fries"),
        ({"name": "Biscuiți digestivi"}, "en:biscuits-and-cakes"),
        ({"name": "Ciocolată neagră"}, "en:chocolates"),
        ({"name": "Granola cu nuci"}, "en:mueslis"),
        ({"name": "Bere lager"}, "en:beers"),
        ({"name": "Vin roșu Merlot"}, "en:alcoholic-beverages"),
        ({"name": "Buldak ramen"}, "en:instant-noodles"),
        ({"name": "Cafea boabe arabica"}, "en:coffees"),
        ({"name": "Cafea latte"}, "en:iced-coffees"),
        ({"name": "Budincă de vanilie"}, "en:dairy-desserts"),
        ({"name": "Piure pentru bebeluși"}, "en:baby-foods"),
        ({"name": "Înghețată de vanilie"}, "en:ice-creams"),
        ({"name": "Apă aromată cu lămâie"}, "en:flavoured-waters"),
        ({"name": "Apă plată de izvor"}, "en:waters"),
        ({"name": "Cola zero"}, "en:soft-drinks"),
        ({"name": "Suc de mere"}, "en:fruit-juices"),
        ({"name": "Sos ketchup"}, "en:condiments"),
        ({"name": "Paste penne"}, "en:pastas"),
        ({"name": "Orez basmati"}, "en:rices"),
        ({"name": "Năut fiert"}, "en:legumes"),
        ({"name": "Pufuleți sărați"}, "en:salty-snacks"),
        ({"name": "Whey protein"}, "en:sports-nutrition"),
        ({"name": "Cereale pentru mic dejun"}, "en:breakfast-cereals"),
        ({"name": "Pizza Margherita"}, "en:pizzas"),
        ({"name": "Legume congelate"}, "en:frozen-foods"),
        ({"name": "Sandwich gata preparat"}, "en:ready-meals"),
        (
            {"name": "Burger plant based vegan"},
            "en:plant-based-foods-and-beverages",
        ),
        ({"name": "Produs complet necunoscut"}, None),
    ],
)
def test_off_category_targets_the_matching_catalog_branch(
    product_data,
    expected_off_category,
):
    assert app_module.get_off_alternative_category(product_data) == expected_off_category


@pytest.mark.parametrize(
    ("scanned_name", "candidate_name", "expected"),
    [
        ("Apă plată", "Apă minerală carbogazoasă", True),
        ("Apă plată", "Cola zero", False),
        ("Buldak ramen", "Samyang ramen", True),
        ("Buldak ramen", "Iaurt natural", False),
        ("Salam de Sibiu", "Șuncă de Praga", True),
        ("Salam de Sibiu", "Iaurt natural", False),
        ("Iaurt grecesc", "Skyr proteic", True),
        ("Iaurt grecesc", "Ciocolată neagră", False),
        ("Bere lager", "Bere fără alcool 0.0", True),
        ("Bere lager", "Vin roșu Merlot", False),
        ("Red Bull energizant", "Cafea latte", True),
        ("Red Bull energizant", "Apă plată", False),
        ("Potato chips", "Tortilla chips", True),
        ("Ulei de măsline", "Ulei de floarea-soarelui", True),
        ("Sare de mare", "Piper negru", False),
        ("Pâine integrală", "Pâine toast", True),
        ("Lapte fără lactoză", "Lapte UHT", True),
    ],
)
def test_compatibility_accepts_close_substitutes_and_blocks_category_drift(
    scanned_name,
    candidate_name,
    expected,
):
    scanned = {"name": scanned_name}
    candidate = {"name": candidate_name}

    assert app_module.is_compatible_alternative(scanned, candidate) is expected


def scoring_scenarios():
    return [
        pytest.param(
            ["low_sugar"],
            recommendation_product("Iaurt cu căpșuni", sugar=14),
            recommendation_product("Iaurt cu afine", sugar=3),
            recommendation_product("Iaurt cu piersici", sugar=20),
            "mai puțin zahăr",
            id="lower-sugar-wins",
        ),
        pytest.param(
            ["protein"],
            recommendation_product("Skyr proteic", protein=6),
            recommendation_product("Skyr proteic vanilie", protein=12),
            recommendation_product("Skyr proteic căpșuni", protein=3),
            "mai multă proteină",
            id="higher-protein-wins",
        ),
        pytest.param(
            ["different_flavor"],
            recommendation_product("Iaurt cu căpșuni"),
            recommendation_product("Iaurt cu afine"),
            recommendation_product("Iaurt cu căpșuni natural"),
            "altă aromă",
            id="different-flavor-wins",
        ),
        pytest.param(
            ["caffeine"],
            recommendation_product(
                "Red Bull energizant",
                category="Băuturi energizante",
                calories=45,
                protein=0,
                sugar=11,
                fat=0,
            ),
            recommendation_product(
                "Monster Ultra Zero energizant",
                category="Băuturi energizante",
                calories=3,
                protein=0,
                sugar=0,
                fat=0,
                ingredients="apă, cafeină, taurină",
            ),
            recommendation_product(
                "Apă plată",
                category="Apă",
                calories=0,
                protein=0,
                sugar=0,
                fat=0,
                ingredients="apă",
            ),
            "băutură energizantă",
            id="caffeinated-family-wins",
        ),
        pytest.param(
            ["natural"],
            recommendation_product("Iaurt natural"),
            recommendation_product(
                "Iaurt simplu curat",
                ingredients="lapte, culturi lactice",
            ),
            recommendation_product(
                "Iaurt cu aditivi",
                ingredients="lapte, zahăr, colorant, conservant, aspartam",
            ),
            "ingrediente mai curate",
            id="clean-ingredients-win",
        ),
        pytest.param(
            ["cheap"],
            recommendation_product("Iaurt natural"),
            recommendation_product(
                "Iaurt ieftin",
                price=3,
                priceIsLocal=True,
            ),
            recommendation_product(
                "Iaurt scump",
                price=12,
                priceIsLocal=True,
            ),
            "preț observat mai bun",
            id="lower-local-price-wins",
        ),
        pytest.param(
            ["low_calorie"],
            recommendation_product("Iaurt cu fructe", calories=160),
            recommendation_product("Iaurt light cu afine", calories=55),
            recommendation_product("Iaurt cremos cu căpșuni", calories=240),
            "mai puține calorii",
            id="lower-calories-win",
        ),
        pytest.param(
            ["value"],
            recommendation_product("Iaurt natural"),
            recommendation_product("Iaurt cu scor bun", score=9),
            recommendation_product("Iaurt cu scor slab", score=3),
            "scor nutrițional mai bun",
            id="higher-nutrition-score-wins",
        ),
        pytest.param(
            ["vegan"],
            recommendation_product(
                "Burger vegetal",
                category="Alternative vegetale",
                calories=200,
                protein=10,
                sugar=2,
                fat=8,
            ),
            recommendation_product(
                "Burger vegetal vegan",
                category="Alternative vegetale",
                vegan=True,
                ingredients="soia, apă, sare",
            ),
            recommendation_product(
                "Burger de vită",
                category="Carne",
                ingredients="carne de vită, sare",
            ),
            "potrivit pentru post",
            id="vegan-candidate-wins",
        ),
        pytest.param(
            ["lactose_free"],
            recommendation_product("Lapte UHT", category="Lapte"),
            recommendation_product(
                "Lapte fără lactoză",
                category="Lapte",
                lactoseFree=True,
            ),
            recommendation_product("Lapte integral", category="Lapte"),
            "fără lactoză",
            id="lactose-free-candidate-wins",
        ),
        pytest.param(
            [],
            recommendation_product(
                "Buldak ramen",
                category="Ramen instant",
                calories=400,
                protein=8,
                sugar=5,
                fat=10,
            ),
            recommendation_product(
                "Samyang ramen",
                category="Ramen instant",
                calories=380,
                protein=9,
                sugar=4,
                fat=9,
                ingredients="făină, condimente",
            ),
            recommendation_product("Iaurt natural"),
            "aceeași categorie de produs",
            id="same-family-wins",
        ),
    ]


@pytest.mark.parametrize(
    ("criteria", "scanned", "preferred", "weaker", "reason_fragment"),
    scoring_scenarios(),
)
def test_alternative_scoring_ranks_the_behaviorally_better_candidate_higher(
    criteria,
    scanned,
    preferred,
    weaker,
    reason_fragment,
):
    preferred = copy.deepcopy(preferred)
    weaker = copy.deepcopy(weaker)
    candidates = [preferred, weaker]

    preferred_score = app_module.score_off_alternative(
        candidates,
        preferred,
        criteria,
        scanned_product=scanned,
    )
    weaker_score = app_module.score_off_alternative(
        candidates,
        weaker,
        criteria,
        scanned_product=scanned,
    )

    assert preferred_score > weaker_score
    assert preferred["recommendationScore"] == round(preferred_score, 2)
    assert reason_fragment in preferred["recommendationReason"]


def add_catalog_product(name, barcode, score, category="Mezeluri"):
    product = Product(
        name=name,
        store="Magazin test",
        category=category,
        barcode=barcode,
        score=score,
        calories=200,
        protein=15,
        sugar=1,
        fat=12,
        ingredients="carne, sare, condimente",
    )
    db.session.add(product)
    return product


def test_local_alternative_selection_excludes_same_and_unrelated_products(app):
    scanned = {
        "name": "Salam de Sibiu",
        "category": "Altele",
        "barcode": "5940000000001",
    }

    with app.app_context():
        add_catalog_product("Salam de Sibiu", "5940000000001", 10)
        add_catalog_product("Salam uscat premium", "5940000000002", 9)
        add_catalog_product("Salam picant", "5940000000003", 7)
        add_catalog_product(
            "Iaurt natural",
            "5940000000004",
            9.5,
            category="Lactate",
        )
        db.session.commit()

        alternatives = app_module.get_local_catalog_alternatives(scanned, [])

    assert [item["name"] for item in alternatives] == [
        "Salam uscat premium",
        "Salam picant",
    ]
    assert all(item["barcode"] != scanned["barcode"] for item in alternatives)
    assert all(
        app_module.is_compatible_alternative(scanned, item)
        for item in alternatives
    )


def test_local_alternative_selection_does_not_guess_for_general_products(app):
    with app.app_context():
        add_catalog_product("Salam uscat", "5940000000010", 9)
        db.session.commit()

        alternatives = app_module.get_local_catalog_alternatives(
            {"name": "Produs complet necunoscut", "category": "Altele"},
            [],
        )

    assert alternatives == []
