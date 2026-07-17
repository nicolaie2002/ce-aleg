import io
import json

import pytest
from PIL import Image
from werkzeug.security import generate_password_hash

import app as app_module
from database import db
from models import Product, ProductSubmission, Subscription, User


@pytest.fixture(autouse=True)
def reset_local_rate_limits():
    app_module.RATE_LIMIT_BUCKETS.clear()
    yield
    app_module.RATE_LIMIT_BUCKETS.clear()


def create_user(*, plan="free"):
    user = User(
        name="Vision Tester",
        email=f"{plan}@example.com",
        password_hash=generate_password_hash("A-secure-password-123!"),
        email_verified=True,
    )
    db.session.add(user)
    db.session.flush()
    db.session.add(Subscription(user_id=user.id, plan=plan, status="active"))
    db.session.commit()
    return user


def authenticate(client, user):
    token = app_module.get_auth_serializer().dumps({
        "user_id": user.id,
        "auth_version": int(user.auth_version or 0),
    })
    client.set_cookie(app_module.AUTH_COOKIE_NAME, token)


def jpeg_frame():
    buffer = io.BytesIO()
    Image.new("RGB", (16, 16), (255, 255, 255)).save(buffer, "JPEG")
    return buffer.getvalue()


def submission(**overrides):
    values = {
        "user_id": 1,
        "product_name": "Iaurt natural",
        "store": "Lidl",
        "category": "Lactate",
        "quantity": "150 g",
        "front_image": "/uploads/submissions/front.jpg",
        "nutrition_image": "/uploads/submissions/nutrition.jpg",
        "calories": 62,
        "protein": 4,
        "sugar": 3.8,
        "fat": 3.2,
        "ingredients": "lapte, culturi lactice",
    }
    values.update(overrides)
    return ProductSubmission(**values)


def test_submission_review_classifies_complete_partial_and_invalid_products():
    approved = app_module.review_product_submission_with_ai(submission())
    partial = app_module.review_product_submission_with_ai(submission(
        category="",
        quantity="",
        front_image=None,
    ))
    rejected = app_module.review_product_submission_with_ai(submission(
        product_name="x",
        store="",
        category="Bauturi energizante",
        quantity="",
        front_image=None,
        nutrition_image=None,
        calories=-10,
        protein=-1,
        sugar=-2,
        fat=-3,
        ingredients="",
    ))

    assert approved["status"] == "ai_approved"
    assert approved["confidence"] == 100
    assert partial["status"] == "needs_review"
    assert partial["warnings"]
    assert rejected["status"] == "rejected"
    assert rejected["confidence"] == 0
    assert len(rejected["problems"]) >= 5
    assert any("cafeina" in warning.lower() for warning in rejected["warnings"])


@pytest.mark.parametrize(
    ("hint", "expected_name", "expected_category", "expected_confidence"),
    [
        ("Monster Ultra", "Monster Energy Ultra White", "B\u0103uturi energizante", 82),
        ("Skyr simplu", "Skyr natural", "Lactate", 78),
        ("Iaurt natural", "Iaurt natural", "Lactate", 70),
        ("Produs misterios", "Produs misterios", "Altele", 35),
    ],
)
def test_local_demo_extraction_covers_known_and_unknown_hints(
    app, client, hint, expected_name, expected_category, expected_confidence
):
    with app.app_context():
        user = create_user()
        authenticate(client, user)

    response = client.post(
        "/ai/extract-product-info",
        data={"product_hint": hint},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["productName"] == expected_name
    assert data["category"] == expected_category
    assert data["confidence"] == expected_confidence
    assert data["source"] == "AI demo local"


def test_local_demo_extraction_requires_an_input(app, client):
    with app.app_context():
        user = create_user()
        authenticate(client, user)

    response = client.post(
        "/ai/extract-product-info",
        data={},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400


def test_live_vision_is_not_available_to_free_plan(app, client):
    with app.app_context():
        user = create_user(plan="free")
        authenticate(client, user)

    response = client.post(
        "/ai/identify-product-frame",
        data={"frame": (io.BytesIO(jpeg_frame()), "frame.jpg")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 402
    assert response.get_json()["code"] == "paid_plan_required"


def test_live_vision_reports_missing_free_configuration(app, client, monkeypatch):
    with app.app_context():
        user = create_user(plan="pro")
        authenticate(client, user)

    monkeypatch.setenv("ENABLE_OPENAI_VISION", "false")
    response = client.post(
        "/ai/identify-product-frame",
        data={"frame": (io.BytesIO(jpeg_frame()), "frame.jpg")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 503
    assert response.get_json()["code"] == "vision_not_configured"


class FakeVisionProvider:
    configured = True

    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error

    def analyze(self, _image_bytes, mime_type, prompt):
        assert mime_type == "image/jpeg"
        assert "exclusiv JSON" in prompt
        if self.error:
            raise self.error
        return self.response


def configure_fake_vision(monkeypatch, response=None, error=None):
    monkeypatch.setenv("ENABLE_OPENAI_VISION", "true")
    monkeypatch.setattr(
        app_module,
        "get_vision_provider",
        lambda: FakeVisionProvider(response=response, error=error),
    )


def test_live_vision_validates_frame_before_provider_call(app, client, monkeypatch):
    with app.app_context():
        user = create_user(plan="pro")
        authenticate(client, user)

    configure_fake_vision(monkeypatch, response="{}")
    missing = client.post(
        "/ai/identify-product-frame",
        data={},
        content_type="multipart/form-data",
    )
    invalid = client.post(
        "/ai/identify-product-frame",
        data={"frame": (io.BytesIO(b"not-an-image"), "frame.jpg")},
        content_type="multipart/form-data",
    )
    too_large = client.post(
        "/ai/identify-product-frame",
        data={"frame": (io.BytesIO(b"x" * (2 * 1024 * 1024 + 1)), "frame.jpg")},
        content_type="multipart/form-data",
    )

    assert missing.status_code == 400
    assert invalid.status_code == 400
    assert too_large.status_code == 400


def test_live_vision_handles_invalid_and_unavailable_provider_responses(
    app, client, monkeypatch
):
    with app.app_context():
        user = create_user(plan="pro")
        authenticate(client, user)

    configure_fake_vision(monkeypatch, response="not-json")
    invalid_json = client.post(
        "/ai/identify-product-frame",
        data={"frame": (io.BytesIO(jpeg_frame()), "frame.jpg")},
        content_type="multipart/form-data",
    )
    configure_fake_vision(
        monkeypatch,
        error=app_module.VisionProviderError("provider unavailable"),
    )
    unavailable = client.post(
        "/ai/identify-product-frame",
        data={"frame": (io.BytesIO(jpeg_frame()), "frame.jpg")},
        content_type="multipart/form-data",
    )

    assert invalid_json.status_code == 502
    assert unavailable.status_code == 503
    assert unavailable.get_json()["code"] == "vision_unavailable"


def test_live_vision_returns_non_chargeable_candidate_when_not_confirmed(
    app, client, monkeypatch
):
    with app.app_context():
        user = create_user(plan="pro")
        authenticate(client, user)

    configure_fake_vision(monkeypatch, response=json.dumps({
        "identified": True,
        "product_name": "Produs care nu exista",
        "brand": "Brand necunoscut",
        "variant": "Test",
        "barcode": None,
        "confidence": "75",
        "needs_barcode": True,
        "message": "Confirma codul de bare.",
    }))

    response = client.post(
        "/ai/identify-product-frame",
        data={"frame": (io.BytesIO(jpeg_frame()), "frame.jpg")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.get_json()["identified"] is False
    assert response.get_json()["chargeable"] is False
    assert response.get_json()["candidate"]["needs_barcode"] is True


def test_live_vision_confirms_known_local_barcode_and_consumes_usage(
    app, client, monkeypatch
):
    with app.app_context():
        user = create_user(plan="pro")
        product = Product(
            name="Skyr natural",
            store="Lidl",
            category="Lactate",
            barcode="5941238013309",
            score=8.8,
        )
        db.session.add(product)
        db.session.commit()
        product_id = product.id
        authenticate(client, user)

    configure_fake_vision(monkeypatch, response=json.dumps({
        "identified": True,
        "product_name": "Skyr natural",
        "brand": "Pilos",
        "variant": "Simplu",
        "barcode": "5941238013309",
        "confidence": 96,
        "needs_barcode": False,
        "message": "Produs confirmat.",
    }))

    response = client.post(
        "/ai/identify-product-frame",
        data={"frame": (io.BytesIO(jpeg_frame()), "frame.jpg")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.get_json()["identified"] is True
    assert response.get_json()["source"] == "local"
    assert response.get_json()["product"]["id"] == product_id
