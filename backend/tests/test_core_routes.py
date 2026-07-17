import pytest
from werkzeug.security import generate_password_hash

import app as app_module
from database import db
from models import CartItem, FamilyProfile, Favorite, ScanHistory, Subscription, UsageEvent, User


def create_user(email="user@example.com", name="Test User", plan=None):
    user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash("A-secure-password-123"),
        email_verified=True,
    )
    db.session.add(user)
    db.session.flush()

    if plan:
        db.session.add(
            Subscription(
                user_id=user.id,
                plan=plan,
                status="active",
            )
        )

    db.session.commit()
    return user


def auth_cookie_for(user):
    return app_module.get_auth_serializer().dumps({
        "user_id": user.id,
        "auth_version": int(user.auth_version or 0),
    })


def authenticate(client, user):
    client.set_cookie(app_module.AUTH_COOKIE_NAME, auth_cookie_for(user))


@pytest.mark.parametrize(
    ("method", "path", "json"),
    [
        ("get", "/dashboard/summary", None),
        ("get", "/family/profiles", None),
        ("post", "/family/profiles", {"name": "Copil"}),
        ("get", "/cart/1", None),
        ("post", "/cart/add", {"user_id": 1, "name": "Iaurt"}),
        ("get", "/favorites/1", None),
        ("post", "/favorites/add", {"user_id": 1, "name": "Iaurt"}),
        ("get", "/history/1", None),
        ("post", "/history/add", {"user_id": 1, "name": "Iaurt"}),
    ],
)
def test_core_routes_require_authentication(app, client, method, path, json):
    response = getattr(client, method)(path, json=json)

    assert response.status_code == 401
    assert response.get_json()["code"] == "auth_required"


def test_authenticated_cart_lifecycle_and_usage_tracking(app, client):
    with app.app_context():
        user = create_user()
        user_id = user.id
        authenticate(client, user)

    created = client.post(
        "/cart/add",
        json={
            "user_id": user_id,
            "name": "Iaurt grecesc",
            "store": "Lidl",
            "score": 8.7,
            "price": "7.99 lei",
            "quantity": 2,
        },
    )

    assert created.status_code == 201
    item_id = created.get_json()["item"]["id"]
    assert created.get_json()["item"] == {
        **created.get_json()["item"],
        "name": "Iaurt grecesc",
        "store": "Lidl",
        "quantity": 2,
        "bought": False,
    }

    duplicate = client.post(
        "/cart/add",
        json={"user_id": user_id, "name": "Iaurt grecesc", "store": "Lidl"},
    )
    assert duplicate.status_code == 200
    assert duplicate.get_json()["item"]["id"] == item_id
    assert duplicate.get_json()["item"]["quantity"] == 3

    updated = client.patch(
        f"/cart/item/{item_id}",
        json={"quantity": 5, "bought": True, "store": "Kaufland"},
    )
    assert updated.status_code == 200
    assert updated.get_json()["item"]["quantity"] == 5
    assert updated.get_json()["item"]["bought"] is True
    assert updated.get_json()["item"]["store"] == "Kaufland"

    listed = client.get(f"/cart/{user_id}")
    assert listed.status_code == 200
    assert [(item["id"], item["quantity"]) for item in listed.get_json()] == [(item_id, 5)]

    with app.app_context():
        events = UsageEvent.query.filter_by(user_id=user_id, event_type="cart_add").all()
        assert len(events) == 2

    cleared = client.delete(f"/cart/clear/{user_id}")
    assert cleared.status_code == 200
    assert client.get(f"/cart/{user_id}").get_json() == []


def test_authenticated_favorites_lifecycle_is_idempotent(app, client):
    with app.app_context():
        user = create_user()
        user_id = user.id
        authenticate(client, user)

    payload = {
        "user_id": user_id,
        "name": "Skyr simplu",
        "store": "Kaufland",
        "category": "Lactate",
        "score": 9.1,
    }
    created = client.post("/favorites/add", json=payload)
    duplicate = client.post("/favorites/add", json=payload)

    assert created.status_code == 201
    assert duplicate.status_code == 200
    assert duplicate.get_json()["item"]["id"] == created.get_json()["item"]["id"]

    listed = client.get(f"/favorites/{user_id}")
    assert listed.status_code == 200
    assert len(listed.get_json()) == 1
    assert listed.get_json()[0]["name"] == "Skyr simplu"

    deleted = client.delete(f"/favorites/item/{created.get_json()['item']['id']}")
    assert deleted.status_code == 200
    assert client.get(f"/favorites/{user_id}").get_json() == []

    assert client.post(
        "/favorites/add",
        json={"user_id": user_id, "name": "Mere", "store": "Lidl"},
    ).status_code == 201
    assert client.post(
        "/favorites/add",
        json={"user_id": user_id, "name": "Pere", "store": "Lidl"},
    ).status_code == 201
    assert client.delete(f"/favorites/clear/{user_id}").status_code == 200
    assert client.get(f"/favorites/{user_id}").get_json() == []


def test_authenticated_history_lifecycle_preserves_scan_details(app, client):
    with app.app_context():
        user = create_user()
        user_id = user.id
        authenticate(client, user)

    first = client.post(
        "/history/add",
        json={
            "user_id": user_id,
            "name": "Baton proteic",
            "store": "Mega Image",
            "category": "Snacks",
            "score": 6.4,
            "verdict": "Mult zahar pentru o gustare zilnica.",
            "shortAdvice": "Compara zaharul per 100 g.",
        },
    )
    second = client.post(
        "/history/add",
        json={"user_id": user_id, "name": "Iaurt natural", "store": "Lidl"},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.get_json()["item"]["verdict"] == "Mult zahar pentru o gustare zilnica."
    assert first.get_json()["item"]["shortAdvice"] == "Compara zaharul per 100 g."

    listed = client.get(f"/history/{user_id}")
    assert listed.status_code == 200
    assert [item["name"] for item in listed.get_json()] == ["Iaurt natural", "Baton proteic"]

    deleted = client.delete(f"/history/item/{first.get_json()['item']['id']}")
    assert deleted.status_code == 200
    assert [item["name"] for item in client.get(f"/history/{user_id}").get_json()] == [
        "Iaurt natural"
    ]

    assert client.delete(f"/history/clear/{user_id}").status_code == 200
    assert client.get(f"/history/{user_id}").get_json() == []


def test_dashboard_summary_counts_only_authenticated_users_data(app, client):
    with app.app_context():
        owner = create_user("owner@example.com")
        other = create_user("other@example.com")
        owner_id = owner.id
        other_id = other.id
        authenticate(client, owner)

        db.session.add_all([
            CartItem(user_id=other_id, product_name="Other cart", store="Other", quantity=20),
            Favorite(user_id=other_id, product_name="Other favorite", store="Other"),
            ScanHistory(user_id=other_id, product_name="Other history", store="Other"),
        ])
        db.session.commit()

    assert client.post(
        "/cart/add",
        json={"user_id": owner_id, "name": "Ovaz", "store": "Lidl", "quantity": 3},
    ).status_code == 201
    assert client.post(
        "/favorites/add",
        json={"user_id": owner_id, "name": "Lapte", "store": "Lidl"},
    ).status_code == 201
    assert client.post(
        "/history/add",
        json={"user_id": owner_id, "name": "Produs vechi", "store": "Lidl"},
    ).status_code == 201
    assert client.post(
        "/history/add",
        json={"user_id": owner_id, "name": "Produs recent", "store": "Kaufland"},
    ).status_code == 201

    response = client.get("/dashboard/summary")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["counts"] == {"cart": 3, "favorites": 1, "history": 2}
    assert payload["lastScannedProduct"] == "Produs recent"
    assert payload["billing"]["user"]["id"] == owner_id
    assert payload["billing"]["subscription"]["plan"] == "free"
    assert payload["billing"]["subscription"]["status"] == "active"


def test_family_profile_crud_requires_family_plan_and_cleans_profile_cart(app, client):
    with app.app_context():
        free_user = create_user("free@example.com")
        authenticate(client, free_user)

    blocked = client.post("/family/profiles", json={"name": "Copil"})
    assert blocked.status_code == 402
    assert blocked.get_json()["code"] == "family_plan_required"

    with app.app_context():
        family_user = create_user("family@example.com", name="Familia Pop", plan="family")
        family_user_id = family_user.id
        authenticate(client, family_user)

    initial = client.get("/family/profiles")
    assert initial.status_code == 200
    assert initial.get_json()["enabled"] is True
    assert initial.get_json()["plan"] == "family"
    assert len(initial.get_json()["profiles"]) == 1
    primary = initial.get_json()["profiles"][0]
    assert primary["name"] == "Familia Pop"
    assert primary["isPrimary"] is True

    created = client.post(
        "/family/profiles",
        json={"name": "  Ana   Maria  ", "color": "Rose", "avatar": "STAR"},
    )
    assert created.status_code == 201
    child = created.get_json()["profile"]
    assert child["name"] == "Ana Maria"
    assert child["color"] == "rose"
    assert child["avatar"] == "star"
    assert child["isPrimary"] is False

    updated = client.patch(
        f"/family/profiles/{child['id']}",
        json={"name": "Ana", "color": "Mint", "avatar": "HEART"},
    )
    assert updated.status_code == 200
    assert updated.get_json()["profile"]["name"] == "Ana"
    assert updated.get_json()["profile"]["color"] == "mint"
    assert updated.get_json()["profile"]["avatar"] == "heart"

    cart = client.post(
        "/cart/add",
        json={
            "user_id": family_user_id,
            "family_profile_id": child["id"],
            "name": "Cereale",
            "store": "Lidl",
        },
    )
    assert cart.status_code == 201
    assert cart.get_json()["item"]["familyProfileId"] == child["id"]

    cannot_delete_primary = client.delete(f"/family/profiles/{primary['id']}")
    assert cannot_delete_primary.status_code == 400

    deleted = client.delete(f"/family/profiles/{child['id']}")
    assert deleted.status_code == 200
    assert deleted.get_json() == {"deleted": True}

    with app.app_context():
        assert db.session.get(FamilyProfile, child["id"]) is None
        assert CartItem.query.filter_by(
            user_id=family_user_id,
            family_profile_id=child["id"],
        ).count() == 0


def test_cross_account_collection_and_item_access_is_rejected(app, client):
    with app.app_context():
        attacker = create_user("attacker@example.com")
        owner = create_user("owner@example.com")
        owner_id = owner.id
        authenticate(client, attacker)

        cart = CartItem(user_id=owner_id, product_name="Owner cart", store="Lidl", quantity=2)
        favorite = Favorite(user_id=owner_id, product_name="Owner favorite", store="Lidl")
        history = ScanHistory(user_id=owner_id, product_name="Owner history", store="Lidl")
        db.session.add_all([cart, favorite, history])
        db.session.commit()
        cart_id = cart.id
        favorite_id = favorite.id
        history_id = history.id

    for path in [f"/cart/{owner_id}", f"/favorites/{owner_id}", f"/history/{owner_id}"]:
        response = client.get(path)
        assert response.status_code == 403
        assert response.get_json()["code"] == "wrong_account"

    for path in [
        f"/cart/clear/{owner_id}",
        f"/favorites/clear/{owner_id}",
        f"/history/clear/{owner_id}",
    ]:
        response = client.delete(path)
        assert response.status_code == 403
        assert response.get_json()["code"] == "wrong_account"

    for path in ["/cart/add", "/favorites/add", "/history/add"]:
        response = client.post(path, json={"user_id": owner_id, "name": "Injected"})
        assert response.status_code == 403

    assert client.patch(f"/cart/item/{cart_id}", json={"quantity": 99}).status_code == 403
    assert client.delete(f"/cart/item/{cart_id}").status_code == 403
    assert client.delete(f"/favorites/item/{favorite_id}").status_code == 403
    assert client.delete(f"/history/item/{history_id}").status_code == 403

    with app.app_context():
        assert db.session.get(CartItem, cart_id).quantity == 2
        assert db.session.get(Favorite, favorite_id) is not None
        assert db.session.get(ScanHistory, history_id) is not None
        assert CartItem.query.filter_by(user_id=owner_id).count() == 1
        assert Favorite.query.filter_by(user_id=owner_id).count() == 1
        assert ScanHistory.query.filter_by(user_id=owner_id).count() == 1


def test_family_profile_ownership_isolated_between_family_accounts(app, client):
    with app.app_context():
        attacker = create_user("attacker@example.com", plan="family")
        owner = create_user("owner@example.com", plan="family")
        authenticate(client, attacker)
        owner_profile = FamilyProfile(
            user_id=owner.id,
            name="Owner child",
            color="blue",
            avatar="user",
            is_primary=False,
        )
        db.session.add(owner_profile)
        db.session.commit()
        owner_profile_id = owner_profile.id

    update = client.patch(
        f"/family/profiles/{owner_profile_id}",
        json={"name": "Taken over"},
    )
    delete = client.delete(f"/family/profiles/{owner_profile_id}")

    assert update.status_code == 404
    assert delete.status_code == 404

    with app.app_context():
        profile = db.session.get(FamilyProfile, owner_profile_id)
        assert profile is not None
        assert profile.name == "Owner child"
