import json
import re

import pytest

from api_docs import build_openapi_spec, render_swagger_ui
from validation import (
    validate_alternative_feedback_payload,
    validate_analytics_payload,
    validate_barcode_import_payload,
    validate_cecoin_checkout_payload,
    validate_checkout_sync_payload,
    validate_login_payload,
    validate_payload,
    validate_product_feedback_payload,
    validate_product_submission_payload,
    validate_register_payload,
    validate_subscription_checkout_payload,
    validate_support_payload,
)


def error_codes(result):
    return {issue.code for issue in result.errors}


def test_register_payload_normalizes_aliases_and_user_input():
    result = validate_register_payload(
        {
            "name": "  Ana Popescu  ",
            "email": "  ANA@EXAMPLE.COM ",
            "password": "a-long-enough-password",
            "ageConfirmed": True,
            "acceptedTerms": "true",
            "invite_code": " cea-12 ab ",
        },
        password_min_length=12,
    )

    assert result.ok
    assert result.data == {
        "name": "Ana Popescu",
        "email": "ana@example.com",
        "password": "a-long-enough-password",
        "ageConfirmed": True,
        "acceptedTerms": True,
        "inviteCode": "CEA12AB",
    }


def test_register_payload_returns_machine_readable_errors():
    result = validate_register_payload(
        {
            "name": "",
            "email": "not-an-email",
            "password": "short",
            "ageConfirmed": False,
            "acceptedTerms": False,
        }
    )

    assert not result.ok
    assert {
        "required",
        "invalid_email",
        "password_too_short",
        "age_confirmation_required",
        "terms_required",
    } <= error_codes(result)
    payload = result.error_payload()
    assert payload["code"] == "validation_error"
    assert payload["error"] == payload["errors"][0]["message"]
    assert all(
        set(error) == {"field", "code", "message"} for error in payload["errors"]
    )


def test_non_object_payload_is_rejected_without_throwing():
    result = validate_login_payload(["unexpected"])

    assert not result.ok
    assert result.errors[0].field == "$"
    assert result.errors[0].code == "invalid_type"


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({}, {"plan": "pro", "billingInterval": "monthly"}),
        (
            {"plan": "family", "interval": "annual"},
            {"plan": "family", "billingInterval": "yearly"},
        ),
        (
            {"plan": "pro", "billingInterval": "an"},
            {"plan": "pro", "billingInterval": "yearly"},
        ),
    ],
)
def test_subscription_checkout_matches_existing_defaults_and_aliases(payload, expected):
    result = validate_subscription_checkout_payload(payload)

    assert result.ok
    assert result.data == expected


def test_checkout_validators_reject_unknown_pack_and_invalid_session():
    pack_result = validate_cecoin_checkout_payload({"packId": "platinum"})
    sync_result = validate_checkout_sync_payload({"sessionId": "pi_123"})

    assert "invalid_choice" in error_codes(pack_result)
    assert "invalid_stripe_session" in error_codes(sync_result)


def test_analytics_keeps_allow_list_semantics_and_bounds_metadata():
    result = validate_analytics_payload(
        {
            "name": " Product Found ",
            "metadata": {"x" * 80: "y" * 300, "empty": None, "count": 2},
        }
    )

    assert result.ok
    assert result.data["name"] == "product_found"
    assert result.data["ignored"] is False
    assert "empty" not in result.data["metadata"]
    assert len(next(iter(result.data["metadata"]))) == 50
    assert len(next(iter(result.data["metadata"].values()))) == 250
    assert result.data["metadata"]["count"] == "2"


def test_unknown_analytics_event_is_ignored_not_rejected():
    result = validate_analytics_payload({"name": "private_event"})

    assert result.ok
    assert result.data["ignored"] is True


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "bad", "message": "A valid support message"},
        {"email": "user@example.com", "message": "short"},
        {"email": "user@example.com", "message": "x" * 4001},
    ],
)
def test_support_payload_enforces_existing_limits(payload):
    assert not validate_support_payload(payload).ok


def test_feedback_validators_preserve_existing_fallbacks():
    product_result = validate_product_feedback_payload(
        {
            "product": {"barcode": "5941238013309", "store": "Lidl"},
            "reason": "not-a-real-reason",
            "details": "  Datele de pe etichetă diferă.  ",
        }
    )
    alternative_result = validate_alternative_feedback_payload(
        {"product": {"name": "  Skyr simplu  "}, "reason": ""}
    )

    assert product_result.ok
    assert product_result.data["reason"] == "other"
    assert product_result.data["store"] == "Lidl"
    assert alternative_result.ok
    assert alternative_result.data["product"]["name"] == "Skyr simplu"
    assert alternative_result.data["reason"] == "wrong_recommendation"


@pytest.mark.parametrize("barcode", ["5941238013308", "1234abcd", "123456789012345"])
def test_barcode_import_rejects_bad_checksum_or_shape(barcode):
    result = validate_barcode_import_payload({"barcode": barcode})

    assert not result.ok
    assert error_codes(result) & {"invalid_barcode", "invalid_checksum"}


def test_product_submission_normalizes_finite_nutrition_values():
    result = validate_product_submission_payload(
        {
            "user_id": "42",
            "product_name": "  Iaurt natural  ",
            "store": " Lidl ",
            "barcode": "5941238013309",
            "calories": "62.5",
            "protein": "4",
            "sugar": "3.8",
            "fat": "3.2",
        }
    )

    assert result.ok
    assert result.data["user_id"] == 42
    assert result.data["product_name"] == "Iaurt natural"
    assert result.data["calories"] == 62.5


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity", [], {}])
def test_product_submission_rejects_non_finite_or_non_numeric_values(value):
    result = validate_product_submission_payload(
        {
            "user_id": "42",
            "product_name": "Iaurt natural",
            "store": "Lidl",
            "calories": value,
        }
    )

    assert not result.ok
    assert "invalid_number" in error_codes(result)


def test_named_validator_dispatches_and_rejects_unknown_names():
    assert validate_payload("cecoin_checkout", {"packId": "gold"}).ok
    with pytest.raises(ValueError, match="Unknown payload validator"):
        validate_payload("missing", {})


@pytest.fixture()
def openapi_document():
    return build_openapi_spec(
        server_url="https://api.cealeg.shop/",
        version="abc1234",
        contact_email="contact@cealeg.shop",
        auth_cookie_name="cealeg_session",
    )


def test_openapi_document_has_production_metadata(openapi_document):
    assert openapi_document["openapi"] == "3.1.0"
    assert openapi_document["jsonSchemaDialect"].endswith("2020-12/schema")
    assert openapi_document["servers"] == [{"url": "https://api.cealeg.shop"}]
    assert openapi_document["info"]["version"] == "abc1234"
    assert openapi_document["info"]["contact"]["email"] == "contact@cealeg.shop"
    assert (
        openapi_document["components"]["securitySchemes"]["sessionCookie"]["name"]
        == "cealeg_session"
    )
    assert (
        openapi_document["components"]["schemas"]["RegisterRequest"]["properties"][
            "password"
        ]["minLength"]
        == 12
    )
    assert (
        openapi_document["components"]["schemas"]["ResetPasswordRequest"]["properties"][
            "password"
        ]["minLength"]
        == 12
    )


def test_openapi_covers_each_primary_payload_family(openapi_document):
    paths = openapi_document["paths"]
    expected = {
        "/register",
        "/login",
        "/billing/checkout",
        "/gamification/coin-checkout",
        "/analytics/event",
        "/support/contact",
        "/feedback/alternative",
        "/feedback/product",
        "/products/search",
        "/barcode/import",
        "/analyze",
        "/submissions/add",
    }

    assert expected <= set(paths)
    assert paths["/submissions/add"]["post"]["requestBody"]["content"][
        "multipart/form-data"
    ]
    assert paths["/billing/checkout"]["post"]["security"] == [{"sessionCookie": []}]
    assert (
        paths["/support/contact"]["post"]["x-validation-helper"]
        == "validate_support_payload"
    )


def test_openapi_core_frontend_flows_have_explicit_typed_contracts(openapi_document):
    paths = openapi_document["paths"]
    expected_operations = {
        ("/auth/me", "get"),
        ("/account/delete/request", "post"),
        ("/account/delete/confirm", "post"),
        ("/account/restriction", "post"),
        ("/ai/status", "get"),
        ("/translate", "post"),
        ("/dashboard/summary", "get"),
        ("/family/profiles", "get"),
        ("/family/profiles", "post"),
        ("/family/profiles/{profile_id}", "patch"),
        ("/family/profiles/{profile_id}", "delete"),
        ("/cart/{user_id}", "get"),
        ("/cart/add", "post"),
        ("/cart/item/{item_id}", "patch"),
        ("/cart/item/{item_id}", "delete"),
        ("/cart/clear/{user_id}", "delete"),
        ("/favorites/{user_id}", "get"),
        ("/favorites/add", "post"),
        ("/favorites/item/{favorite_id}", "delete"),
        ("/favorites/clear/{user_id}", "delete"),
        ("/history/{user_id}", "get"),
        ("/history/add", "post"),
        ("/history/item/{history_id}", "delete"),
        ("/history/clear/{user_id}", "delete"),
    }

    for path, method in expected_operations:
        operation = paths[path][method]
        assert operation["x-contract-source"] == "explicit", (path, method)
        success_responses = [
            response
            for status, response in operation["responses"].items()
            if status.startswith("2")
        ]
        assert success_responses, (path, method)
        assert all(response.get("content") for response in success_responses), (
            path,
            method,
        )

        if method in {"post", "put", "patch"} and path != "/account/delete/request":
            assert operation.get("requestBody", {}).get("content"), (path, method)

    assert paths["/auth/me"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/CurrentUserResponse"}


def test_openapi_operation_ids_are_unique_and_path_parameters_declared(
    openapi_document,
):
    operation_ids = []
    for path, path_item in openapi_document["paths"].items():
        for method, operation in path_item.items():
            operation_ids.append(operation["operationId"])
            declared = {
                parameter["name"]
                for parameter in operation.get("parameters", [])
                if parameter["in"] == "path"
            }
            assert set(re.findall(r"{([^}]+)}", path)) == declared

    assert len(operation_ids) == len(set(operation_ids))


def test_openapi_has_no_dangling_local_schema_references(openapi_document):
    schemas = openapi_document["components"]["schemas"]
    serialized = json.dumps(openapi_document, ensure_ascii=False, allow_nan=False)
    references = set(re.findall(r"#/components/schemas/([A-Za-z0-9_]+)", serialized))

    assert references <= set(schemas)
    assert json.loads(serialized)["paths"]["/health"]["get"]["operationId"] == "health"


def test_openapi_error_schema_matches_validation_result(openapi_document):
    error_schema = openapi_document["components"]["schemas"]["Error"]
    issue_schema = openapi_document["components"]["schemas"]["ValidationIssue"]
    payload = validate_support_payload(
        {"email": "bad", "message": "short"}
    ).error_payload()

    assert set(error_schema["required"]) <= set(payload)
    assert set(issue_schema["required"]) == set(payload["errors"][0])


def test_swagger_ui_escapes_title_and_serializes_spec_url():
    document = render_swagger_ui(
        '/api/openapi.json?value="quoted"',
        title="<Ce aleg?>",
    )

    assert "&lt;Ce aleg?&gt;" in document
    assert 'url:"/api/openapi.json?value=\\"quoted\\""' in document
    assert "SwaggerUIBundle" in document


@pytest.mark.parametrize(
    ("path", "payload", "expected_field"),
    [
        (
            "/register",
            {
                "name": "",
                "email": "invalid",
                "password": "short",
                "ageConfirmed": False,
                "acceptedTerms": False,
            },
            "name",
        ),
        (
            "/support/contact",
            {"email": "invalid", "message": "short"},
            "message",
        ),
    ],
)
def test_public_routes_return_the_common_structured_validation_error(
    client, path, payload, expected_field
):
    response = client.post(path, json=payload)

    assert response.status_code == 400
    body = response.get_json()
    assert body["code"] == "validation_error"
    assert isinstance(body["errors"], list)
    assert expected_field in {issue["field"] for issue in body["errors"]}
    assert all({"field", "code", "message"} <= set(issue) for issue in body["errors"])


def test_query_validation_and_authentication_order_are_consistent(client):
    missing_query = client.get("/products/search")
    signed_out_checkout = client.post("/billing/checkout", json={"plan": "invalid"})

    assert missing_query.status_code == 400
    assert missing_query.get_json()["code"] == "validation_error"
    assert signed_out_checkout.status_code == 401
    assert signed_out_checkout.get_json()["code"] == "auth_required"
