import argparse
import time

import requests

from database import db
from app import (
    app,
    build_product_from_open_food_facts,
    fetch_off_products,
    save_product_to_local_database,
    validate_barcode,
)
from models import Product


CATEGORY_GROUPS = {
    "drinks": [
        "en:beverages",
        "en:non-alcoholic-beverages",
        "en:energy-drinks",
        "en:iced-coffees",
        "en:ready-to-drink-coffees",
        "en:coffees",
        "en:teas",
        "en:iced-teas",
        "en:soft-drinks",
        "en:colas",
        "en:sodas",
        "en:carbonated-drinks",
        "en:waters",
        "en:mineral-waters",
        "en:flavored-waters",
        "en:fruit-juices",
        "en:nectars",
        "en:syrups",
        "en:sports-drinks",
        "en:tonic-waters",
    ],
    "dairy": [
        "en:dairies",
        "en:yogurts",
        "en:fruit-yogurts",
        "en:greek-yogurts",
        "en:skyrs",
        "en:drinking-yogurts",
        "en:kefirs",
        "en:fermented-milk-products",
        "en:dairy-desserts",
        "en:dessert-creams",
        "en:chilled-desserts",
        "en:milks",
        "en:cheeses",
        "en:fresh-cheeses",
        "en:hard-cheeses",
        "en:processed-cheeses",
        "en:butters",
        "en:creams",
        "en:sour-creams",
        "en:plant-based-milks",
    ],
    "sweets": [
        "en:ice-creams",
        "en:frozen-desserts",
        "en:chocolates",
        "en:chocolate-bars",
        "en:filled-chocolates",
        "en:biscuits",
        "en:cookies",
        "en:wafers",
        "en:croissants",
        "en:sweet-snacks",
        "en:candies",
        "en:cakes",
        "en:desserts",
        "en:puddings",
    ],
    "snacks_and_breakfast": [
        "en:salty-snacks",
        "en:chips-and-fries",
        "en:crackers",
        "en:popcorn",
        "en:breakfast-cereals",
        "en:mueslis",
        "en:granolas",
        "en:oatmeals",
        "en:protein-bars",
        "en:cereal-bars",
        "en:nut-bars",
        "en:breakfasts",
        "en:cocoa-and-chocolate-powders",
    ],
    "bakery": [
        "en:breads",
        "en:bread-products",
        "en:pastries",
        "en:bakery-products",
        "en:crispbreads",
        "en:toasts",
        "en:tortillas",
    ],
    "ready_and_frozen": [
        "en:pizzas",
        "en:frozen-foods",
        "en:frozen-ready-made-meals",
        "en:frozen-pizzas",
        "en:frozen-vegetables",
        "en:frozen-fruits",
        "en:ready-meals",
        "en:instant-noodles",
        "en:noodles",
        "en:ramens",
        "en:soups",
        "en:sandwiches",
        "en:salads",
    ],
    "cooking_and_pantry": [
        "en:sauces",
        "en:mustards",
        "en:ketchups",
        "en:mayonnaises",
        "en:condiments",
        "en:spices",
        "en:cooking-oils",
        "en:vinegars",
        "en:pastas",
        "en:rice",
        "en:legumes",
        "en:canned-foods",
        "en:canned-vegetables",
        "en:canned-legumes",
        "en:canned-fish",
        "en:pickles",
        "en:olives",
        "en:flours",
        "en:sugars",
        "en:baking-aids",
    ],
    "protein": [
        "en:meat-products",
        "en:meats",
        "en:pork",
        "en:chicken",
        "en:turkey",
        "en:cold-cuts",
        "en:hams",
        "en:salami",
        "en:bacon",
        "en:sausages",
        "en:fish",
        "en:seafood",
        "en:eggs",
    ],
    "spreads_and_nuts": [
        "en:jams",
        "en:spreads",
        "en:hazelnut-spreads",
        "en:peanut-butters",
        "en:honey",
        "en:nuts",
        "en:seeds",
        "en:dried-fruits",
    ],
    "fruit_and_veg": [
        "en:vegetables",
        "en:fruits",
        "en:fruits-and-vegetables",
        "en:prepared-vegetables",
        "en:vegetable-mixes",
    ],
    "special_diets": [
        "en:baby-foods",
        "en:baby-milks",
        "en:lactose-free-foods",
        "en:gluten-free-foods",
        "en:organic-foods",
        "en:vegan-products",
        "en:vegetarian-products",
        "en:sports-nutrition",
        "en:protein-powders",
        "en:meal-replacements",
    ],
}

CORE_CATEGORIES = [
    category
    for group_name in [
        "drinks",
        "dairy",
        "sweets",
        "snacks_and_breakfast",
        "bakery",
        "ready_and_frozen",
        "cooking_and_pantry",
        "protein",
        "spreads_and_nuts",
        "fruit_and_veg",
        "special_diets",
    ]
    for category in CATEGORY_GROUPS[group_name]
]

LARGE_EXTRA_CATEGORIES = [
    "en:plant-based-foods-and-beverages",
    "en:vegan-products",
    "en:vegetarian-products",
    "en:gluten-free-foods",
    "en:lactose-free-foods",
    "en:organic-foods",
    "en:baby-foods",
    "en:baby-milks",
    "en:sports-nutrition",
    "en:protein-powders",
    "en:meal-replacements",
    "en:breakfasts",
    "en:cocoa-and-chocolate-powders",
    "en:breakfast-drinks",
    "en:carbonated-drinks",
    "en:flavored-waters",
    "en:non-sugared-beverages",
    "en:sugar-free-beverages",
    "en:fermented-milk-products",
    "en:dessert-creams",
    "en:chilled-desserts",
    "en:frozen-desserts",
    "en:filled-chocolates",
    "en:chocolate-candies",
    "en:protein-snacks",
    "en:cereal-bars",
    "en:nut-bars",
    "en:prepared-meats",
    "en:canned-fish",
    "en:canned-vegetables",
    "en:canned-legumes",
    "en:tomato-sauces",
    "en:hot-sauces",
    "en:barbecue-sauces",
    "en:salad-dressings",
    "en:frozen-pizzas",
    "en:frozen-ready-made-meals",
    "en:frozen-vegetables",
    "en:frozen-fruits",
    "en:frozen-seafood",
    "en:plant-based-meals",
    "en:plant-based-dairy-alternatives",
    "en:plant-based-meat-alternatives",
    "en:plant-based-desserts",
]

RETAIL_EXPANSION_CATEGORIES = [
    "en:aldi-products",
    "en:carrefour-products",
    "en:lidl-products",
    "en:private-label-products",
    "en:discount-products",
    "en:romanian-products",
    "en:european-products",
    "en:beverages",
    "en:dairies",
    "en:snacks",
    "en:groceries",
    "en:meals",
    "en:fresh-foods",
    "en:frozen-groceries",
    "en:shelf-stable-foods",
    "en:non-alcoholic-beverages",
]

ROMANIA_FOCUS_CATEGORIES = [
    "en:romanian-products",
    "en:lidl-products",
    "en:carrefour-products",
    "en:private-label-products",
    "en:dairies",
    "en:yogurts",
    "en:fruit-yogurts",
    "en:drinking-yogurts",
    "en:kefirs",
    "en:sour-creams",
    "en:cheeses",
    "en:fresh-cheeses",
    "en:processed-cheeses",
    "en:milk",
    "en:dessert-creams",
    "en:dairy-desserts",
    "en:meat-products",
    "en:cold-cuts",
    "en:hams",
    "en:salami",
    "en:sausages",
    "en:prepared-meats",
    "en:fish",
    "en:canned-fish",
    "en:beers",
    "en:non-alcoholic-beers",
    "en:lagers",
    "en:radlers",
    "en:waters",
    "en:mineral-waters",
    "en:soft-drinks",
    "en:colas",
    "en:energy-drinks",
    "en:iced-coffees",
    "en:fruit-juices",
    "en:nectars",
    "en:chocolates",
    "en:chocolate-bars",
    "en:biscuits",
    "en:wafers",
    "en:croissants",
    "en:sweet-snacks",
    "en:salty-snacks",
    "en:chips-and-fries",
    "en:breakfast-cereals",
    "en:sauces",
    "en:ketchups",
    "en:mustards",
    "en:mayonnaises",
    "en:condiments",
    "en:cooking-oils",
    "en:pastas",
    "en:rice",
    "en:flours",
    "en:canned-foods",
    "en:canned-vegetables",
    "en:canned-legumes",
    "en:pickles",
    "en:jams",
    "en:spreads",
    "en:instant-noodles",
    "en:ready-meals",
    "en:frozen-foods",
    "en:frozen-pizzas",
    "en:frozen-vegetables",
]

PRESETS = {
    "starter": CORE_CATEGORIES[:10],
    "launch": CORE_CATEGORIES,
    "large": CORE_CATEGORIES + LARGE_EXTRA_CATEGORIES,
    "romania_focus": ROMANIA_FOCUS_CATEGORIES,
    "retail": CORE_CATEGORIES + LARGE_EXTRA_CATEGORIES + RETAIL_EXPANSION_CATEGORIES,
    "massive": (
        CORE_CATEGORIES
        + LARGE_EXTRA_CATEGORIES
        + RETAIL_EXPANSION_CATEGORIES
        + [
            "en:food",
            "en:plant-based-foods",
            "en:breakfast-foods",
            "en:refrigerated-foods",
            "en:confectioneries",
            "en:appetizers",
            "en:seafood-products",
            "en:milk-substitutes",
            "en:cheese-substitutes",
            "en:dessert-mixes",
            "en:sweetened-beverages",
            "en:unsweetened-beverages",
            "en:instant-drinks",
            "en:powdered-drinks",
            "en:fruit-preparations",
            "en:savory-spreads",
            "en:sweet-spreads",
        ]
    ),
}


def normalize_category(category):
    category = str(category or "").strip()

    if not category:
        return ""

    return category if category.startswith("en:") else f"en:{category}"


def build_query(category, page, page_size, country):
    params = {
        "categories_tags": category,
        "page": page,
        "page_size": page_size,
    }

    country_tag = normalize_country(country)

    if country_tag:
        params["countries_tags"] = country_tag

    return params


def normalize_country(country):
    normalized = str(country or "").strip().lower()
    aliases = {
        "": "",
        "all": "",
        "world": "",
        "ro": "romania",
        "rou": "romania",
        "romania": "romania",
        "românia": "romania",
        "uk": "united-kingdom",
        "gb": "united-kingdom",
        "us": "united-states",
        "usa": "united-states",
    }
    normalized = aliases.get(normalized, normalized)
    return f"en:{normalized}" if normalized else ""


def fetch_category_page(category, page, page_size, country):
    query_variants = [
        {**build_query(category, page, page_size, country), "sort_by": "unique_scans_n"},
        build_query(category, page, page_size, country),
    ]
    last_error = None

    for attempt_index, params in enumerate(query_variants):
        try:
            return fetch_off_products(
                params,
                (
                    "prewarm:"
                    f"{category}:{country or 'world'}:{page}:{page_size}:{attempt_index}"
                ),
            )
        except requests.RequestException as error:
            last_error = error
            time.sleep(0.5)

    raise last_error


def import_off_product(raw_product, dry_run=False):
    barcode = str(raw_product.get("code") or raw_product.get("_id") or "").strip()

    if validate_barcode(barcode, required=True):
        return "skipped"

    if Product.query.filter_by(barcode=barcode).first():
        return "existing"

    if dry_run:
        return "dry_run"

    product_data = build_product_from_open_food_facts(
        barcode,
        raw_product,
        translate_ingredients=False,
    )
    save_product_to_local_database(product_data)
    return "saved"


def prewarm(categories, limit_per_category, page_size, country, delay, dry_run):
    totals = {"saved": 0, "existing": 0, "skipped": 0, "dry_run": 0, "failed": 0}
    page_size = max(1, min(page_size, 100))
    max_pages = max(1, (limit_per_category + page_size - 1) // page_size)

    with app.app_context():
        for category in categories:
            saved = existing = skipped = dry_run_count = failed = imported = 0

            for page in range(1, max_pages + 1):
                if imported >= limit_per_category:
                    break

                try:
                    products = fetch_category_page(category, page, page_size, country)
                except requests.RequestException as error:
                    print(f"{category} page {page}: fetch failed ({error})")
                    totals["failed"] += 1
                    failed += 1
                    continue

                if not products:
                    break

                for raw_product in products:
                    if imported >= limit_per_category:
                        break

                    try:
                        result = import_off_product(raw_product, dry_run=dry_run)
                    except Exception as error:
                        db.session.rollback()
                        print(f"{category}: product failed ({error})")
                        totals["failed"] += 1
                        failed += 1
                        continue

                    totals[result] += 1
                    imported += 1

                    if result == "saved":
                        saved += 1
                    elif result == "existing":
                        existing += 1
                    elif result == "dry_run":
                        dry_run_count += 1
                    else:
                        skipped += 1

                time.sleep(delay)

            print(
                f"{category}: saved {saved}, existing {existing}, "
                f"skipped {skipped}, dry-run {dry_run_count}, failed {failed}"
            )

    print(
        "Done. "
        f"Saved {totals['saved']}, existing {totals['existing']}, "
        f"skipped {totals['skipped']}, dry-run {totals['dry_run']}, "
        f"failed {totals['failed']}."
    )


def parse_categories(raw_categories):
    if not raw_categories:
        return []

    return [
        normalize_category(category)
        for category in raw_categories.split(",")
        if normalize_category(category)
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Prewarm the cloud catalog from Open Food Facts."
    )
    parser.add_argument(
        "--preset",
        choices=sorted(PRESETS),
        default="launch",
        help="Category preset to import.",
    )
    parser.add_argument(
        "--categories",
        default="",
        help="Comma-separated Open Food Facts categories, e.g. en:yogurts,en:waters.",
    )
    parser.add_argument(
        "--country",
        default="world",
        help="Country filter. Use 'world' for global results.",
    )
    parser.add_argument(
        "--limit-per-category",
        type=int,
        default=80,
        help="Maximum products to import from each category.",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=40,
        help="Products requested per Open Food Facts page.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.35,
        help="Delay in seconds between Open Food Facts pages.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be imported without writing to the database.",
    )
    args = parser.parse_args()

    custom_categories = parse_categories(args.categories)
    categories = custom_categories or PRESETS[args.preset]
    categories = list(dict.fromkeys(categories))
    limit_per_category = max(1, min(args.limit_per_category, 500))

    prewarm(
        categories=categories,
        limit_per_category=limit_per_category,
        page_size=args.page_size,
        country=args.country,
        delay=max(0.1, args.delay),
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
