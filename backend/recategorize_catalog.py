import argparse
import json

from app import app, recategorize_catalog_products


def build_parser():
    parser = argparse.ArgumentParser(
        description="Preview or apply Ce aleg? catalog recategorization."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Maximum products to inspect in this batch. Capped at 1000.",
    )
    parser.add_argument(
        "--include-all",
        action="store_true",
        help="Inspect all products, not only uncategorized/Other products.",
    )
    parser.add_argument(
        "--min-id",
        type=int,
        default=None,
        help="Start inspecting products from this catalog ID.",
    )
    parser.add_argument(
        "--category",
        default=None,
        help="Inspect only products whose current category matches this value.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist category, score, tag and reason updates.",
    )
    return parser


def main():
    args = build_parser().parse_args()

    with app.app_context():
        result = recategorize_catalog_products(
            limit=args.limit,
            apply_changes=args.apply,
            include_all=args.include_all,
            min_id=args.min_id,
            category=args.category,
        )

    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not args.apply and result["changed"]:
        print("\nDry run only. Re-run with --apply to persist these changes.")


if __name__ == "__main__":
    main()
