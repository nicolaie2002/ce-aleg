from database import db
from models import Product

from catalog_quality import build_catalog_quality_report


def add_product(**overrides):
    values = {
        "name": "Produs test",
        "store": "Magazin",
        "category": "Lactate",
        "barcode": "5940000000001",
        "score": 8.0,
        "image": "https://example.test/product.jpg",
        "calories": 120,
        "protein": 5,
        "sugar": 4,
        "fat": 3,
        "ingredients": "lapte",
    }
    values.update(overrides)
    product = Product(**values)
    db.session.add(product)
    db.session.commit()
    return product


def test_catalog_quality_reports_coverage_duplicates_and_invalid_values(app):
    with app.app_context():
        add_product()
        add_product(name="Duplicat", barcode="5940000000001", category="Altele", image=None)
        add_product(
            name="Date imposibile",
            barcode=None,
            calories=1800,
            sugar=140,
            score=12,
            ingredients=None,
        )

        report = build_catalog_quality_report(
            db.session,
            Product,
            uncategorized_terms=["altele", "other"],
        )

        assert report["products"] == 3
        assert report["duplicateBarcodes"] == 1
        assert report["duplicateProducts"] == 1
        assert report["uncategorizedProducts"] == 1
        assert report["missingBarcode"] == 1
        assert report["missingImage"] == 1
        assert report["invalidScores"] == 1
        assert report["invalidNutrition"] == 1
        assert 0 < report["healthScore"] < 100
        assert report["duplicateExamples"] == [
            {"barcode": "5940000000001", "count": 2}
        ]


def test_catalog_quality_empty_catalog_is_stable(app):
    with app.app_context():
        report = build_catalog_quality_report(db.session, Product, ["altele"])

        assert report["products"] == 0
        assert report["healthScore"] == 0.0
        assert report["categories"] == []
        assert report["issueExamples"] == []


def test_catalog_quality_duplicate_totals_are_not_limited_to_examples(app):
    with app.app_context():
        for index in range(3):
            barcode = f"5940000000{index:03d}"
            add_product(name=f"Original {index}", barcode=barcode)
            add_product(name=f"Duplicat {index}", barcode=barcode)

        report = build_catalog_quality_report(
            db.session,
            Product,
            uncategorized_terms=["altele"],
            example_limit=1,
        )

        assert report["duplicateBarcodes"] == 3
        assert report["duplicateProducts"] == 3
        assert len(report["duplicateExamples"]) == 1
