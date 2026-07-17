from sqlalchemy import case, func, or_


def _percent(value, total):
    return round((int(value or 0) / int(total)) * 100, 1) if total else 0.0


def build_catalog_quality_report(session, product_model, uncategorized_terms=None, example_limit=20):
    terms = [str(term).strip().lower() for term in (uncategorized_terms or []) if str(term).strip()]
    category_missing = or_(
        product_model.category.is_(None),
        func.trim(product_model.category) == "",
        func.lower(func.trim(product_model.category)).in_(terms),
    )
    barcode_missing = or_(
        product_model.barcode.is_(None),
        func.trim(product_model.barcode) == "",
    )
    image_missing = or_(
        product_model.image.is_(None),
        func.trim(product_model.image) == "",
    )
    nutrition_missing = (
        product_model.calories.is_(None)
        & product_model.protein.is_(None)
        & product_model.sugar.is_(None)
        & product_model.fat.is_(None)
    )
    ingredients_missing = or_(
        product_model.ingredients.is_(None),
        func.trim(product_model.ingredients) == "",
    )
    invalid_score = or_(product_model.score < 0, product_model.score > 10)
    invalid_nutrition = or_(
        product_model.calories < 0,
        product_model.calories > 1500,
        product_model.protein < 0,
        product_model.protein > 100,
        product_model.sugar < 0,
        product_model.sugar > 100,
        product_model.fat < 0,
        product_model.fat > 100,
    )

    totals = session.query(
        func.count(product_model.id).label("total"),
        func.sum(case((barcode_missing, 1), else_=0)).label("missing_barcode"),
        func.sum(case((image_missing, 1), else_=0)).label("missing_image"),
        func.sum(case((nutrition_missing, 1), else_=0)).label("missing_nutrition"),
        func.sum(case((ingredients_missing, 1), else_=0)).label("missing_ingredients"),
        func.sum(case((category_missing, 1), else_=0)).label("uncategorized"),
        func.sum(case((invalid_score, 1), else_=0)).label("invalid_score"),
        func.sum(case((invalid_nutrition, 1), else_=0)).label("invalid_nutrition"),
    ).one()
    total = int(totals.total or 0)

    duplicate_barcode_counts = (
        session.query(
            product_model.barcode.label("barcode"),
            func.count(product_model.id).label("product_count"),
        )
        .filter(~barcode_missing)
        .group_by(product_model.barcode)
        .having(func.count(product_model.id) > 1)
        .subquery()
    )
    duplicate_totals = session.query(
        func.count(duplicate_barcode_counts.c.barcode).label("barcode_count"),
        func.sum(duplicate_barcode_counts.c.product_count - 1).label("product_count"),
    ).one()
    duplicate_groups = (
        session.query(
            duplicate_barcode_counts.c.barcode,
            duplicate_barcode_counts.c.product_count.label("count"),
        )
        .order_by(
            duplicate_barcode_counts.c.product_count.desc(),
            duplicate_barcode_counts.c.barcode.asc(),
        )
        .limit(max(1, int(example_limit)))
        .all()
    )
    category_rows = (
        session.query(
            product_model.category.label("category"),
            func.count(product_model.id).label("count"),
        )
        .filter(~category_missing)
        .group_by(product_model.category)
        .order_by(func.count(product_model.id).desc(), product_model.category.asc())
        .limit(20)
        .all()
    )
    issue_filter = or_(
        category_missing,
        barcode_missing,
        image_missing,
        nutrition_missing,
        invalid_score,
        invalid_nutrition,
    )
    issue_examples = (
        session.query(product_model)
        .filter(issue_filter)
        .order_by(product_model.id.asc())
        .limit(max(1, int(example_limit)))
        .all()
    )

    missing_barcode = int(totals.missing_barcode or 0)
    missing_image = int(totals.missing_image or 0)
    missing_nutrition = int(totals.missing_nutrition or 0)
    uncategorized = int(totals.uncategorized or 0)
    invalid_values = int(totals.invalid_score or 0) + int(totals.invalid_nutrition or 0)
    barcode_coverage = 100 - _percent(missing_barcode, total) if total else 0.0
    image_coverage = 100 - _percent(missing_image, total) if total else 0.0
    nutrition_coverage = 100 - _percent(missing_nutrition, total) if total else 0.0
    category_coverage = 100 - _percent(uncategorized, total) if total else 0.0
    valid_value_rate = max(0.0, 100 - _percent(invalid_values, total)) if total else 0.0
    health_score = round(
        barcode_coverage * 0.20
        + image_coverage * 0.15
        + nutrition_coverage * 0.25
        + category_coverage * 0.20
        + valid_value_rate * 0.20,
        1,
    )

    return {
        "products": total,
        "healthScore": health_score,
        "uncategorizedProducts": uncategorized,
        "missingBarcode": missing_barcode,
        "missingImage": missing_image,
        "missingNutrition": missing_nutrition,
        "missingIngredients": int(totals.missing_ingredients or 0),
        "invalidScores": int(totals.invalid_score or 0),
        "invalidNutrition": int(totals.invalid_nutrition or 0),
        "duplicateBarcodes": int(duplicate_totals.barcode_count or 0),
        "duplicateProducts": int(duplicate_totals.product_count or 0),
        "withBarcode": total - missing_barcode,
        "withImage": total - missing_image,
        "withNutrition": total - missing_nutrition,
        "barcodeCoverage": barcode_coverage,
        "imageCoverage": image_coverage,
        "nutritionCoverage": nutrition_coverage,
        "categoryCoverage": category_coverage,
        "uncategorizedRate": _percent(uncategorized, total),
        "duplicateExamples": [
            {"barcode": row.barcode, "count": int(row.count)} for row in duplicate_groups
        ],
        "categories": [
            {"category": row.category, "count": int(row.count)} for row in category_rows
        ],
        "issueExamples": [
            {
                "id": product.id,
                "name": product.name,
                "barcode": product.barcode,
                "category": product.category,
            }
            for product in issue_examples
        ],
    }
