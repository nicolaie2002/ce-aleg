import os
from datetime import timedelta

from werkzeug.security import generate_password_hash


if os.environ.get("APP_ENV", "").lower() not in {"test", "testing"}:
    raise RuntimeError("The E2E seed is restricted to APP_ENV=test.")

if os.environ.get("E2E_TEST_MODE", "false").lower() != "true":
    raise RuntimeError("Set E2E_TEST_MODE=true before running the E2E seed.")

from app import app  # noqa: E402
from database import db  # noqa: E402
from models import Product, Subscription, User  # noqa: E402
from time_utils import utcnow  # noqa: E402


PASSWORD = "E2e-password-123"


def create_user(name, email, invite_code, *, admin=False, plan="free"):
    now = utcnow()
    user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(PASSWORD),
        is_admin=admin,
        email_verified=True,
        email_verified_at=now,
        invite_code=invite_code,
        terms_version="e2e",
        terms_accepted_at=now,
        age_confirmed_at=now,
    )
    db.session.add(user)
    db.session.flush()
    db.session.add(Subscription(
        user_id=user.id,
        plan=plan,
        status="active",
        provider="e2e" if plan != "free" else None,
        current_period_start=now,
        current_period_end=now + timedelta(days=30) if plan != "free" else None,
    ))
    return user


def seed_database():
    with app.app_context():
        db.drop_all()
        db.create_all()
        create_user(
            "Admin E2E",
            "admin.e2e@cealeg.test",
            "CE-ADMIN1",
            admin=True,
        )
        create_user(
            "Pro E2E",
            "pro.e2e@cealeg.test",
            "CE-PRO001",
            plan="pro",
        )
        db.session.add_all([
            Product(
                name="Iaurt natural E2E",
                store="Lidl",
                category="Lactate",
                barcode="5449000000996",
                score=8.7,
                image="/products/iaurt-natural.png",
                price=5.49,
                calories=62,
                protein=5.2,
                sugar=3.8,
                fat=2.1,
                ingredients="lapte, culturi lactice",
                reason="Ingrediente scurte și aport bun de proteine.",
            ),
            Product(
                name="Skyr simplu E2E",
                store="Kaufland",
                category="Lactate",
                barcode="5940000000001",
                score=9.1,
                image="/products/skyr.png",
                price=6.25,
                calories=64,
                protein=10.5,
                sugar=3.4,
                fat=0.3,
                ingredients="lapte degresat, culturi lactice",
                reason="Mai multe proteine și puțin zahăr.",
            ),
        ])
        db.session.commit()


if __name__ == "__main__":
    seed_database()
