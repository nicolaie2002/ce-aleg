import argparse
import time

import requests

from app import (
    app,
    build_product_from_open_food_facts,
    fetch_off_products,
    save_product_to_local_database,
    validate_barcode,
)
from models import Product


CORE_CATEGORIES = [
    "en:energy-drinks",
    "en:iced-coffees",
    "en:coffees",
    "en:soft-drinks",
    "en:waters",
    "en:fruit-juices",
    "en:yogurts",
    "en:dairy-desserts",
    "en:milks",
    "en:cheeses",
    "en:ice-creams",
    "en:chocolates",
    "en:biscuits",
    "en:sweet-snacks",
    "en:salty-snacks",
    "en:breakfast-cereals",
    "en:breads",
    "en:pastries",
    "en:pizzas",
    "en:frozen-foods",
    "en:ready-meals",
    "en:soups",
    "en:sauces",
    "en:mustards",
    "en:ketchups",
    "en:mayonnaises",
    "en:pastas",
    "en:rice",
    "en:meat-products",
    "en:sausages",
    "en:fish",
    "en:canned-foods",
    "en:jams",
    "en:spreads",
    "en:nuts",
    "en:protein-bars",
]

LARGE_EXTRA_CATEGORIES = [
    "en:plant-based-foods-and-beverages",
    "en:plant-based-milks",
    "en:vegan-products",
    "en:gluten-free-foods",
    "en:baby-foods",
    "en:breakfasts",
    "en:desserts",
    "en:cakes",
    "en:candies",
    "en:instant-noodles",
    "en:chips-and-fries",
    "en:crackers",
    "en:olives",
    "en:pickles",
    "en:vegetables",
    "en:fruits",
    "en:legumes",
    "en:cooking-oils",
    "en:vinegars",
    "en:spices",
    "en:tea",
    "en:cocoa-and-chocolate-powders",
]

PRESETS = {
    "starter": CORE_CATEGORIES[:10],
    "launch": CORE_CATEGORIES,
    "large": CORE_CATEGORIES + LARGE_EXTRA_CATEGORIES,
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
