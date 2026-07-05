import argparse
import contextlib
import csv
import gzip
import hashlib
import io
import json
import os
import sys
import time
from urllib.parse import urlparse

import requests
from sqlalchemy import or_

from app import (
    app,
    build_product_from_open_food_facts,
    db,
    normalize_search_text,
    validate_barcode,
)
from models import Product


DEFAULT_OFF_CSV_URL = "https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz"

ROMANIA_TOKENS = {
    "ro",
    "rou",
    "romania",
    "românia",
    "roumanie",
    "rumania",
    "en romania",
    "ro romania",
}

ROMANIAN_RETAILER_HINTS = {
    "lidl romania",
    "kaufland romania",
    "carrefour romania",
    "mega image",
    "penny romania",
    "penny market romania",
    "profi romania",
    "auchan romania",
    "selgros romania",
    "metro romania",
    "la cocos",
    "annabella",
}

ROMANIAN_TEXT_HINTS = {
    "ingrediente",
    "zahar",
    "zahăr",
    "grasimi",
    "grăsimi",
    "sare",
    "proteine",
    "valoare energetica",
    "valoare energetică",
    "fabricat in romania",
    "fabricat în românia",
    "produs in romania",
    "produs în românia",
}

CSV_FIELD_ALIASES = {
    "code": ["code", "_id", "barcode"],
    "product_name": ["product_name", "product_name_ro", "product_name_en", "name"],
    "product_name_ro": ["product_name_ro"],
    "product_name_en": ["product_name_en", "product_name"],
    "generic_name": ["generic_name", "generic_name_ro", "generic_name_en"],
    "brands": ["brands", "brand"],
    "quantity": ["quantity", "serving_quantity"],
    "categories": ["categories", "categories_ro", "categories_en"],
    "categories_tags": ["categories_tags"],
    "labels_tags": ["labels_tags"],
    "ingredients_analysis_tags": ["ingredients_analysis_tags"],
    "ingredients_text": ["ingredients_text", "ingredients_text_ro", "ingredients_text_en"],
    "ingredients_text_ro": ["ingredients_text_ro"],
    "ingredients_text_en": ["ingredients_text_en", "ingredients_text"],
    "image_front_url": ["image_front_url", "image_url"],
    "image_url": ["image_url", "image_front_url"],
    "nutrition_grades": ["nutrition_grades", "nutrition_grade_fr"],
    "additives_n": ["additives_n"],
    "countries": ["countries", "countries_ro", "countries_en"],
    "countries_tags": ["countries_tags"],
    "stores": ["stores", "stores_tags"],
    "purchase_places": ["purchase_places"],
}

NUTRIMENT_ALIASES = {
    "energy-kcal": ["energy-kcal_100g", "energy-kcal", "energy-kcal_value"],
    "proteins": ["proteins_100g", "proteins", "proteins_value"],
    "sugars": ["sugars_100g", "sugars", "sugars_value"],
    "fat": ["fat_100g", "fat", "fat_value"],
}


def clip(value, max_length):
    if value is None:
        return None

    value = str(value).strip()
    return value[:max_length] if value else None


def first_value(row, aliases, default=""):
    for key in aliases:
        value = row.get(key)

        if value not in (None, ""):
            if isinstance(value, (list, dict)):
                return value

            return str(value).strip()

    return default


def parse_float(value):
    if value in (None, ""):
        return None

    try:
        return float(str(value).strip().replace(",", "."))
    except ValueError:
        return None


def parse_int(value):
    if value in (None, ""):
        return None

    try:
        return int(float(str(value).strip().replace(",", ".")))
    except ValueError:
        return None


def split_tags(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    text = str(value or "").strip()

    if not text:
        return []

    return [
        item.strip()
        for chunk in text.split(";")
        for item in chunk.split(",")
        if item.strip()
    ]


def detect_format(source, forced_format):
    if forced_format != "auto":
        return forced_format

    lowered = str(source).lower()

    if ".jsonl" in lowered or lowered.endswith(".json") or lowered.endswith(".json.gz"):
        return "jsonl"

    return "csv"


@contextlib.contextmanager
def open_text_source(source):
    response = None
    text_file = None
    binary_file = None

    try:
        parsed = urlparse(source)

        if parsed.scheme in {"http", "https"}:
            response = requests.get(
                source,
                stream=True,
                headers={
                    "User-Agent": "CeAlegCatalogImporter/1.0 (contact: contact@cealeg.shop)",
                    "Accept": "*/*",
                },
                timeout=(15, 90),
            )
            response.raise_for_status()
            binary_file = response.raw
        else:
            binary_file = open(source, "rb")

        if str(source).lower().endswith(".gz"):
            binary_file = gzip.GzipFile(fileobj=binary_file)

        text_file = io.TextIOWrapper(binary_file, encoding="utf-8", errors="replace")
        yield text_file
    finally:
        if text_file is not None:
            text_file.detach()

        if response is not None:
            response.close()
        elif binary_file is not None and hasattr(binary_file, "close"):
            binary_file.close()


def iter_csv_rows(text_file, delimiter="auto"):
    first_line = text_file.readline()

    if not first_line:
        return

    if delimiter == "auto":
        selected_delimiter = "\t" if first_line.count("\t") >= first_line.count(",") else ","
    elif delimiter == "tab":
        selected_delimiter = "\t"
    else:
        selected_delimiter = delimiter

    fieldnames = next(csv.reader([first_line], delimiter=selected_delimiter))
    reader = csv.DictReader(text_file, fieldnames=fieldnames, delimiter=selected_delimiter)

    for row in reader:
        yield row


def iter_jsonl_rows(text_file):
    for raw_line in text_file:
        line = raw_line.strip()

        if not line:
            continue

        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def row_to_off_product(row):
    if "product" in row and isinstance(row["product"], dict):
        row = row["product"]

    product = {}

    for target_key, aliases in CSV_FIELD_ALIASES.items():
        value = first_value(row, aliases)

        if target_key.endswith("_tags"):
            product[target_key] = split_tags(value)
        else:
            product[target_key] = value

    product["code"] = first_value(row, CSV_FIELD_ALIASES["code"])
    product["_id"] = product["code"]

    nutriments = {}

    raw_nutriments = row.get("nutriments")

    if isinstance(raw_nutriments, dict):
        nutriments.update(raw_nutriments)

    for target_key, aliases in NUTRIMENT_ALIASES.items():
        value = None

        for alias in aliases:
            value = parse_float(row.get(alias))

            if value is not None:
                break

        if value is not None:
            nutriments[target_key] = value

    product["nutriments"] = nutriments

    additives_n = parse_int(first_value(row, CSV_FIELD_ALIASES["additives_n"]))

    if additives_n is not None:
        product["additives_n"] = additives_n

    return product


def has_romanian_signal(row, loose=True):
    relevant_fields = [
        "countries",
        "countries_tags",
        "stores",
        "stores_tags",
        "purchase_places",
        "origins",
        "manufacturing_places",
    ]
    haystack = normalize_search_text(
        " ".join(str(row.get(field) or "") for field in relevant_fields)
    )

    if any(normalize_search_text(token) in haystack for token in ROMANIA_TOKENS):
        return True

    if not loose:
        return False

    product_text = normalize_search_text(
        " ".join(
            str(row.get(field) or "")
            for field in [
                "product_name",
                "product_name_ro",
                "ingredients_text",
                "ingredients_text_ro",
                "categories",
            ]
        )
    )

    has_store_hint = any(hint in haystack for hint in ROMANIAN_RETAILER_HINTS)
    has_text_hint = any(normalize_search_text(hint) in product_text for hint in ROMANIAN_TEXT_HINTS)

    return has_store_hint and has_text_hint


def stable_identity_key(product_data):
    barcode = str(product_data.get("barcode") or "").strip()

    if barcode and not barcode.startswith("off-name-"):
        return f"barcode:{barcode}"

    name = normalize_search_text(product_data.get("name"))
    category = normalize_search_text(product_data.get("category"))
    ingredients = normalize_search_text(product_data.get("ingredients"))[:220]
    image = normalize_search_text(product_data.get("image"))
    source_value = " ".join([name, category, ingredients, image]).strip()

    if not source_value:
        return ""

    digest = hashlib.sha1(source_value.encode("utf-8")).hexdigest()[:18]
    return f"name:{digest}"


def existing_identity_sets():
    barcodes = set()
    name_keys = set()

    products = Product.query.with_entities(
        Product.barcode,
        Product.name,
        Product.category,
        Product.ingredients,
        Product.image,
    ).all()

    for barcode, name, category, ingredients, image in products:
        if barcode and not str(barcode).startswith("off-name-"):
            barcodes.add(str(barcode).strip())

        key_source = normalize_search_text(
            " ".join([
                str(name or ""),
                str(category or ""),
                str(ingredients or "")[:220],
                str(image or ""),
            ])
        )

        if key_source:
            digest = hashlib.sha1(key_source.encode("utf-8")).hexdigest()[:18]
            name_keys.add(f"name:{digest}")

    return barcodes, name_keys


def is_low_value_product(product_data):
    name = normalize_search_text(product_data.get("name"))

    if not name or name.startswith("produs "):
        return True

    if len(name) < 3:
        return True

    if name in {"unknown", "inconnu", "sans nom", "no name"}:
        return True

    return False


def build_model_product(product_data):
    return Product(
        name=clip(product_data.get("name"), 150) or "Produs",
        store=clip(product_data.get("store") or "Open Food Facts", 100) or "Open Food Facts",
        category=clip(product_data.get("category") or "Altele", 100) or "Altele",
        barcode=clip(product_data.get("barcode"), 80),
        score=product_data.get("score") if product_data.get("score") is not None else 5.0,
        tag=clip(product_data.get("tag"), 100),
        image=clip(product_data.get("image"), 255),
        price=product_data.get("price"),
        price_text=clip(product_data.get("priceText") or "preț necunoscut", 100),
        calories=product_data.get("calories"),
        protein=product_data.get("protein"),
        sugar=product_data.get("sugar"),
        fat=product_data.get("fat"),
        vegan=bool(product_data.get("vegan")),
        lactose_free=bool(product_data.get("lactoseFree")),
        natural=bool(product_data.get("natural")),
        reason=product_data.get("reason"),
        ingredients=product_data.get("ingredients"),
    )


def import_export(
    source,
    source_format,
    delimiter,
    country,
    loose_romania,
    limit,
    max_scan,
    batch_size,
    allow_no_barcode,
    dry_run,
    progress_every,
    skip_rows,
):
    scanned = imported = skipped = duplicates = failed = 0
    pending = 0
    started_at = time.time()

    country_filter_enabled = normalize_search_text(country) not in {"", "all", "world"}

    with app.app_context():
        existing_barcodes, existing_name_keys = existing_identity_sets()

        with open_text_source(source) as text_file:
            if source_format == "jsonl":
                rows = iter_jsonl_rows(text_file)
            else:
                rows = iter_csv_rows(text_file, delimiter=delimiter)

            for row in rows:
                scanned += 1

                if scanned <= skip_rows:
                    continue

                if max_scan and scanned > skip_rows + max_scan:
                    break

                try:
                    if country_filter_enabled and not has_romanian_signal(row, loose=loose_romania):
                        skipped += 1
                        continue

                    raw_product = row_to_off_product(row)
                    raw_barcode = str(raw_product.get("code") or raw_product.get("_id") or "").strip()
                    barcode_error = validate_barcode(raw_barcode, required=True) if raw_barcode else "missing"

                    if barcode_error and not allow_no_barcode:
                        skipped += 1
                        continue

                    if raw_barcode and not barcode_error:
                        product_barcode = raw_barcode
                    else:
                        product_barcode = ""

                    product_data = build_product_from_open_food_facts(
                        product_barcode,
                        raw_product,
                        translate_ingredients=False,
                    )
                    product_data["store"] = "Open Food Facts"

                    if is_low_value_product(product_data):
                        skipped += 1
                        continue

                    identity_key = stable_identity_key(product_data)

                    if product_barcode and product_barcode in existing_barcodes:
                        duplicates += 1
                        continue

                    if not product_barcode and identity_key in existing_name_keys:
                        duplicates += 1
                        continue

                    if not product_barcode:
                        digest = identity_key.split(":", 1)[1] if ":" in identity_key else hashlib.sha1(
                            json.dumps(raw_product, sort_keys=True, default=str).encode("utf-8")
                        ).hexdigest()[:18]
                        product_data["barcode"] = f"off-name-{digest}"

                    if dry_run:
                        imported += 1
                    else:
                        db.session.add(build_model_product(product_data))
                        pending += 1
                        imported += 1

                        if product_barcode:
                            existing_barcodes.add(product_barcode)
                        elif identity_key:
                            existing_name_keys.add(identity_key)

                        if pending >= batch_size:
                            db.session.commit()
                            pending = 0

                    if limit and imported >= limit:
                        break
                except Exception as error:
                    db.session.rollback()
                    pending = 0
                    failed += 1
                    print(f"row {scanned}: failed ({error})", flush=True)

                if scanned % progress_every == 0:
                    elapsed = max(1, int(time.time() - started_at))
                    print(
                        f"scanned={scanned} imported={imported} "
                        f"duplicates={duplicates} skipped={skipped} failed={failed} "
                        f"elapsed={elapsed}s",
                        flush=True,
                    )

        if not dry_run and pending:
            db.session.commit()

    print(
        "Done. "
        f"scanned={scanned}, imported={imported}, duplicates={duplicates}, "
        f"skipped={skipped}, failed={failed}.",
        flush=True,
    )


def main():
    csv.field_size_limit(min(sys.maxsize, 2_147_483_647))

    parser = argparse.ArgumentParser(
        description="Importa produse din exportul Open Food Facts, cu filtru pentru Romania."
    )
    parser.add_argument("--source", default=DEFAULT_OFF_CSV_URL)
    parser.add_argument("--format", choices=["auto", "csv", "jsonl"], default="auto")
    parser.add_argument("--delimiter", default="auto", help="auto, tab, comma sau un caracter.")
    parser.add_argument("--country", default="romania")
    parser.add_argument("--loose-romania", action="store_true", default=True)
    parser.add_argument("--strict-romania", action="store_false", dest="loose_romania")
    parser.add_argument("--limit", type=int, default=3000)
    parser.add_argument("--max-scan", type=int, default=500000)
    parser.add_argument("--skip-rows", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--allow-no-barcode", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--progress-every", type=int, default=5000)
    args = parser.parse_args()

    source_format = detect_format(args.source, args.format)

    import_export(
        source=args.source,
        source_format=source_format,
        delimiter=args.delimiter,
        country=args.country,
        loose_romania=args.loose_romania,
        limit=max(1, args.limit),
        max_scan=max(0, args.max_scan),
        batch_size=max(1, min(args.batch_size, 500)),
        allow_no_barcode=args.allow_no_barcode,
        dry_run=args.dry_run,
        progress_every=max(100, args.progress_every),
        skip_rows=max(0, args.skip_rows),
    )


if __name__ == "__main__":
    main()
