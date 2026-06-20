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


SEED_QUERIES = [
    ("energy-drinks", {"categories_tags": "en:energy-drinks"}),
    ("iced-coffees", {"categories_tags": "en:iced-coffees"}),
    ("soft-drinks", {"categories_tags": "en:soft-drinks"}),
    ("dairy-desserts", {"categories_tags": "en:dairy-desserts"}),
    ("yogurts", {"categories_tags": "en:yogurts"}),
    ("chocolates", {"categories_tags": "en:chocolates"}),
    ("biscuits", {"categories_tags": "en:biscuits"}),
    ("breakfast-cereals", {"categories_tags": "en:breakfast-cereals"}),
    ("mustards", {"categories_tags": "en:mustards"}),
    ("sauces", {"categories_tags": "en:sauces"}),
]


def import_off_product(raw_product):
    barcode = str(
        raw_product.get("code") or raw_product.get("_id") or ""
    ).strip()

    if validate_barcode(barcode, required=True):
        return "skipped"

    product_data = build_product_from_open_food_facts(
        barcode,
        raw_product,
        translate_ingredients=False,
    )
    save_product_to_local_database(product_data)
    return "saved"


def prewarm(limit_per_category):
    totals = {"saved": 0, "skipped": 0, "failed": 0}

    with app.app_context():
        for label, params in SEED_QUERIES:
            products = None
            last_error = None
            query_variants = [
                {**params, "page_size": limit_per_category, "sort_by": "unique_scans_n"},
                {**params, "page_size": limit_per_category},
            ]

            for attempt_index, query_params in enumerate(query_variants):
                try:
                    products = fetch_off_products(
                        query_params,
                        f"prewarm:{label}:{limit_per_category}:{attempt_index}",
                    )
                    break
                except requests.RequestException as error:
                    last_error = error
                    time.sleep(0.4)

            if products is None:
                print(f"{label}: failed to fetch ({last_error})")
                totals["failed"] += 1
                continue

            saved = 0
            skipped = 0

            for raw_product in products[:limit_per_category]:
                try:
                    result = import_off_product(raw_product)
                except Exception as error:
                    print(f"{label}: failed product ({error})")
                    totals["failed"] += 1
                    continue

                totals[result] += 1

                if result == "saved":
                    saved += 1
                else:
                    skipped += 1

            print(f"{label}: saved {saved}, skipped {skipped}")

    print(
        "Done. "
        f"Saved {totals['saved']}, skipped {totals['skipped']}, "
        f"failed {totals['failed']}."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Prewarm the cloud catalog from Open Food Facts."
    )
    parser.add_argument(
        "--limit-per-category",
        type=int,
        default=40,
        help="Maximum products to import from each seed category.",
    )
    args = parser.parse_args()
    prewarm(max(1, min(args.limit_per_category, 100)))


if __name__ == "__main__":
    main()
