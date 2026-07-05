import argparse
import csv
import hashlib
import sys

from app import (
    app,
    calculate_product_score,
    db,
    generate_product_reason,
    generate_product_tag,
    normalize_search_text,
    validate_barcode,
)
from models import Product


COLUMN_ALIASES = {
    "barcode": ["barcode", "code", "ean", "gtin", "cod", "cod_bare", "cod bare"],
    "name": ["name", "product_name", "produs", "nume", "denumire", "title"],
    "brand": ["brand", "marca"],
    "store": ["store", "retailer", "magazin"],
    "category": ["category", "categorie", "departament", "subcategory", "subcategorie"],
    "image": ["image", "image_url", "poza", "imagine", "url_imagine"],
    "price": ["price", "pret", "preț", "price_ron", "pret_ron"],
    "calories": ["calories", "kcal", "energy-kcal_100g", "calorii"],
    "protein": ["protein", "proteins", "proteins_100g", "proteine"],
    "sugar": ["sugar", "sugars", "sugars_100g", "zahar", "zahăr"],
    "fat": ["fat", "fat_100g", "grasimi", "grăsimi"],
    "ingredients": ["ingredients", "ingrediente", "ingredients_text"],
}


def clip(value, max_length):
    if value is None:
        return None

    value = str(value).strip()
    return value[:max_length] if value else None


def parse_float(value):
    if value in (None, ""):
        return None

    try:
        return float(str(value).strip().replace(",", ".").replace(" lei", ""))
    except ValueError:
        return None


def normalize_headers(headers):
    return {normalize_search_text(header): header for header in headers or []}


def read_value(row, normalized_headers, field):
    for alias in COLUMN_ALIASES[field]:
        original_header = normalized_headers.get(normalize_search_text(alias))

        if not original_header:
            continue

        value = row.get(original_header)

        if value not in (None, ""):
            return str(value).strip()

    return ""


def detect_delimiter(sample):
    if sample.count(";") > sample.count(",") and sample.count(";") >= sample.count("\t"):
        return ";"

    if sample.count("\t") > sample.count(","):
        return "\t"

    return ","


def identity_key(barcode, name, store, category, ingredients):
    if barcode:
        return f"barcode:{barcode}"

    text = normalize_search_text(" ".join([name, store, category, ingredients[:180]]))

    if not text:
        return ""

    return "name:" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:18]


def existing_keys():
    keys = set()

    for product in Product.query.with_entities(
        Product.barcode,
        Product.name,
        Product.store,
        Product.category,
        Product.ingredients,
    ).all():
        keys.add(
            identity_key(
                str(product.barcode or "").strip(),
                product.name or "",
                product.store or "",
                product.category or "",
                product.ingredients or "",
            )
        )

    return {key for key in keys if key}


def import_feed(source, fallback_store, dry_run, batch_size):
    saved = skipped = duplicates = failed = pending = 0

    with app.app_context():
        seen_keys = existing_keys()

        with open(source, "r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            sample = handle.read(4096)
            handle.seek(0)
            reader = csv.DictReader(handle, delimiter=detect_delimiter(sample))
            normalized_headers = normalize_headers(reader.fieldnames)

            for index, row in enumerate(reader, start=2):
                try:
                    raw_barcode = read_value(row, normalized_headers, "barcode")
                    barcode = raw_barcode if raw_barcode and not validate_barcode(raw_barcode) else ""
                    name = read_value(row, normalized_headers, "name")
                    store = read_value(row, normalized_headers, "store") or fallback_store
                    category = read_value(row, normalized_headers, "category") or "Altele"
                    ingredients = read_value(row, normalized_headers, "ingredients")

                    if not name:
                        skipped += 1
                        continue

                    key = identity_key(barcode, name, store, category, ingredients)

                    if not key or key in seen_keys:
                        duplicates += 1
                        continue

                    calories = parse_float(read_value(row, normalized_headers, "calories"))
                    protein = parse_float(read_value(row, normalized_headers, "protein"))
                    sugar = parse_float(read_value(row, normalized_headers, "sugar"))
                    fat = parse_float(read_value(row, normalized_headers, "fat"))
                    price = parse_float(read_value(row, normalized_headers, "price"))
                    score = calculate_product_score(category, calories, protein, sugar, fat, ingredients)
                    tag = generate_product_tag(category, calories, protein, sugar, fat, ingredients)
                    reason = generate_product_reason(category, calories, protein, sugar, fat, ingredients)

                    if not barcode:
                        barcode = "feed-" + key.split(":", 1)[1]

                    if not dry_run:
                        db.session.add(Product(
                            name=clip(name, 150),
                            store=clip(store, 100) or "Catalog partener",
                            category=clip(category, 100) or "Altele",
                            barcode=clip(barcode, 80),
                            score=score if score is not None else 5.0,
                            tag=clip(tag, 100),
                            image=clip(read_value(row, normalized_headers, "image"), 255),
                            price=price,
                            price_text=f"{price:.2f} lei".replace(".", ",") if price is not None else "preț necunoscut",
                            calories=calories,
                            protein=protein,
                            sugar=sugar,
                            fat=fat,
                            vegan=False,
                            lactose_free=False,
                            natural=False,
                            reason=reason,
                            ingredients=ingredients,
                        ))
                        pending += 1

                        if pending >= batch_size:
                            db.session.commit()
                            pending = 0

                    seen_keys.add(key)
                    saved += 1
                except Exception as error:
                    db.session.rollback()
                    pending = 0
                    failed += 1
                    print(f"line {index}: failed ({error})", flush=True)

        if not dry_run and pending:
            db.session.commit()

    print(
        f"Done. saved={saved}, duplicates={duplicates}, skipped={skipped}, failed={failed}.",
        flush=True,
    )


def main():
    csv.field_size_limit(min(sys.maxsize, 2_147_483_647))

    parser = argparse.ArgumentParser(
        description="Importa un CSV de la retailer/partener in catalogul Ce aleg?."
    )
    parser.add_argument("--source", required=True, help="Fisier CSV local.")
    parser.add_argument("--store", default="Catalog partener")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    import_feed(
        source=args.source,
        fallback_store=args.store,
        dry_run=args.dry_run,
        batch_size=max(1, min(args.batch_size, 500)),
    )


if __name__ == "__main__":
    main()
