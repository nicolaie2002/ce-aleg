from pathlib import Path
import os
import sqlite3

from app import app, db
from models import (
    CartItem,
    Favorite,
    PriceObservation,
    Product,
    ProductSubmission,
    ScanHistory,
    SearchEvent,
    Subscription,
    UsageEvent,
    User,
)


SQLITE_PATH = Path(__file__).parent / "instance" / "cealeg.db"

MODELS = [
    (User, "users"),
    (Product, "products"),
    (ProductSubmission, "product_submissions"),
    (ScanHistory, "scan_history"),
    (Favorite, "favorites"),
    (CartItem, "cart_items"),
    (PriceObservation, "price_observations"),
    (SearchEvent, "search_events"),
    (Subscription, "subscriptions"),
    (UsageEvent, "usage_events"),
]


def get_rows(connection, table_name):
    tables = {
        row["name"]
        for row in connection.execute(
            "select name from sqlite_master where type = 'table'"
        ).fetchall()
    }

    if table_name not in tables:
        return []

    return connection.execute(f"select * from {table_name}").fetchall()


def migrate_table(connection, model, table_name):
    inserted = 0
    skipped = 0
    model_columns = {
        column.name: column.key
        for column in model.__table__.columns
    }

    for row in get_rows(connection, table_name):
        row_data = {
            model_columns[key]: row[key]
            for key in row.keys()
            if key in model_columns
        }
        row_id = row_data.get("id")

        if row_id is not None and db.session.get(model, row_id):
            skipped += 1
            continue

        db.session.add(model(**row_data))
        inserted += 1

    db.session.commit()
    return inserted, skipped


def main():
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL lipsește. Migrarea trebuie rulată spre Supabase.")

    if not SQLITE_PATH.exists():
        raise SystemExit(f"Baza SQLite nu există: {SQLITE_PATH}")

    connection = sqlite3.connect(SQLITE_PATH)
    connection.row_factory = sqlite3.Row

    with app.app_context():
        db.create_all()

        for model, table_name in MODELS:
            inserted, skipped = migrate_table(connection, model, table_name)
            print(f"{table_name}: inserted={inserted}, skipped={skipped}")

    connection.close()


if __name__ == "__main__":
    main()
