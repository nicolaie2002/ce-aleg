"""OpenAPI 3.1 contract and Swagger UI renderer for the Ce aleg API."""

from __future__ import annotations

import html
import json
from typing import Any


JSON = "application/json"
MULTIPART = "multipart/form-data"
COOKIE_SECURITY = [{"sessionCookie": []}]


def _ref(name: str) -> dict[str, str]:
    return {"$ref": f"#/components/schemas/{name}"}


def _json_content(schema: dict[str, Any]) -> dict[str, Any]:
    return {"content": {JSON: {"schema": schema}}}


def _response(description: str, schema: dict[str, Any] | None = None) -> dict[str, Any]:
    response: dict[str, Any] = {"description": description}
    if schema is not None:
        response.update(_json_content(schema))
    return response


def _request(schema: dict[str, Any], *, media_type: str = JSON) -> dict[str, Any]:
    return {
        "required": True,
        "content": {media_type: {"schema": schema}},
    }


def _errors(*status_codes: str) -> dict[str, Any]:
    descriptions = {
        "400": "Invalid request payload",
        "401": "Authentication required",
        "402": "Payment or paid plan required",
        "403": "Operation forbidden",
        "404": "Resource not found",
        "409": "Resource state conflict",
        "413": "Request payload too large",
        "429": "Rate limit exceeded",
        "500": "Unexpected server error",
        "502": "Upstream provider failed",
        "503": "Service is not configured or temporarily unavailable",
    }
    return {code: _response(descriptions[code], _ref("Error")) for code in status_codes}


def _operation(
    operation_id: str,
    summary: str,
    tag: str,
    success_schema: dict[str, Any],
    *,
    success_status: str = "200",
    request_schema: dict[str, Any] | None = None,
    media_type: str = JSON,
    security: bool = False,
    parameters: list[dict[str, Any]] | None = None,
    error_statuses: tuple[str, ...] = ("400", "500"),
    validation_helper: str | None = None,
) -> dict[str, Any]:
    operation: dict[str, Any] = {
        "operationId": operation_id,
        "summary": summary,
        "tags": [tag],
        "responses": {
            success_status: _response("Successful response", success_schema),
            **_errors(*error_statuses),
        },
    }
    if request_schema is not None:
        operation["requestBody"] = _request(request_schema, media_type=media_type)
    if security:
        operation["security"] = COOKIE_SECURITY
    if parameters:
        operation["parameters"] = parameters
    if validation_helper:
        operation["x-validation-helper"] = validation_helper
    return operation


def _query_parameter(
    name: str,
    schema: dict[str, Any],
    description: str,
    *,
    required: bool = False,
) -> dict[str, Any]:
    return {
        "name": name,
        "in": "query",
        "required": required,
        "description": description,
        "schema": schema,
    }


def _path_parameter(
    name: str, schema: dict[str, Any], description: str
) -> dict[str, Any]:
    return {
        "name": name,
        "in": "path",
        "required": True,
        "description": description,
        "schema": schema,
    }


def _schemas(password_min_length: int) -> dict[str, Any]:
    text = {"type": "string"}
    nullable_text = {"type": ["string", "null"]}
    nullable_number = {"type": ["number", "null"]}

    return {
        "ValidationIssue": {
            "type": "object",
            "additionalProperties": False,
            "required": ["field", "code", "message"],
            "properties": {
                "field": text,
                "code": text,
                "message": text,
            },
        },
        "Error": {
            "type": "object",
            "required": ["error"],
            "properties": {
                "error": text,
                "code": text,
                "errors": {"type": "array", "items": _ref("ValidationIssue")},
                "limit": {"type": "integer"},
                "required": {"type": "array", "items": text},
            },
            "additionalProperties": True,
        },
        "Message": {
            "type": "object",
            "required": ["message"],
            "properties": {"message": text},
            "additionalProperties": True,
        },
        "Health": {
            "type": "object",
            "required": ["ok", "service"],
            "properties": {
                "ok": {"const": True},
                "service": {"const": "ce-aleg-api"},
            },
            "additionalProperties": False,
        },
        "Version": {
            "type": "object",
            "required": ["ok"],
            "properties": {
                "ok": {"type": "boolean"},
                "version": text,
                "commit": text,
                "shortCommit": text,
            },
            "additionalProperties": True,
        },
        "User": {
            "type": "object",
            "required": ["id", "name", "email"],
            "properties": {
                "id": {"type": "integer"},
                "name": text,
                "email": {"type": "string", "format": "email"},
                "isAdmin": {"type": "boolean"},
                "emailVerified": {"type": "boolean"},
                "inviteCode": nullable_text,
            },
            "additionalProperties": True,
        },
        "AuthResponse": {
            "type": "object",
            "required": ["message", "user"],
            "properties": {
                "message": text,
                "user": _ref("User"),
                "emailStatus": {"type": "object", "additionalProperties": True},
            },
            "additionalProperties": False,
        },
        "RegisterRequest": {
            "type": "object",
            "additionalProperties": False,
            "required": ["name", "email", "password", "ageConfirmed", "acceptedTerms"],
            "properties": {
                "name": {"type": "string", "minLength": 1, "maxLength": 120},
                "email": {"type": "string", "format": "email", "maxLength": 254},
                "password": {
                    "type": "string",
                    "minLength": password_min_length,
                    "maxLength": 1024,
                },
                "ageConfirmed": {"type": "boolean", "const": True},
                "acceptedTerms": {"type": "boolean", "const": True},
                "inviteCode": {"type": "string", "maxLength": 24},
                "invite_code": {"type": "string", "maxLength": 24},
            },
        },
        "LoginRequest": {
            "type": "object",
            "additionalProperties": False,
            "required": ["email", "password"],
            "properties": {
                "email": {"type": "string", "format": "email", "maxLength": 254},
                "password": {"type": "string", "minLength": 1, "maxLength": 1024},
            },
        },
        "EmailRequest": {
            "type": "object",
            "additionalProperties": False,
            "required": ["email"],
            "properties": {
                "email": {"type": "string", "format": "email", "maxLength": 254},
            },
        },
        "TokenRequest": {
            "type": "object",
            "additionalProperties": False,
            "required": ["token"],
            "properties": {
                "token": {"type": "string", "minLength": 1, "maxLength": 4096}
            },
        },
        "ResetPasswordRequest": {
            "type": "object",
            "additionalProperties": False,
            "required": ["token", "password"],
            "properties": {
                "token": {"type": "string", "minLength": 1, "maxLength": 4096},
                "password": {
                    "type": "string",
                    "minLength": password_min_length,
                    "maxLength": 1024,
                },
            },
        },
        "PasswordStrengthRequest": {
            "type": "object",
            "additionalProperties": False,
            "properties": {"password": {"type": "string", "maxLength": 1024}},
        },
        "PasswordStrength": {
            "type": "object",
            "required": ["label", "score", "isValid", "suggestions"],
            "properties": {
                "label": {"type": "string", "enum": ["slaba", "medie", "puternica"]},
                "score": {"type": "integer", "minimum": 0, "maximum": 5},
                "isValid": {"type": "boolean"},
                "suggestions": {"type": "array", "items": text},
            },
            "additionalProperties": False,
        },
        "Product": {
            "type": "object",
            "required": ["name"],
            "properties": {
                "id": {"type": ["integer", "string", "null"]},
                "name": text,
                "brand": nullable_text,
                "store": nullable_text,
                "category": nullable_text,
                "barcode": nullable_text,
                "score": nullable_number,
                "tag": nullable_text,
                "image": nullable_text,
                "price": nullable_number,
                "priceText": nullable_text,
                "calories": nullable_number,
                "protein": nullable_number,
                "sugar": nullable_number,
                "fat": nullable_number,
                "ingredients": nullable_text,
                "source": nullable_text,
            },
            "additionalProperties": True,
        },
        "ProductList": {"type": "array", "items": _ref("Product")},
        "ProductFeedbackRequest": {
            "type": "object",
            "additionalProperties": False,
            "required": ["product"],
            "properties": {
                "product": _ref("Product"),
                "store": {"type": "string", "maxLength": 100},
                "reason": {
                    "type": "string",
                    "enum": [
                        "wrong_product",
                        "wrong_price",
                        "wrong_nutrition",
                        "wrong_score",
                        "wrong_image",
                        "missing_data",
                        "other",
                    ],
                },
                "details": {"type": "string", "maxLength": 1000},
                "source": {"type": "string", "maxLength": 80},
            },
        },
        "AlternativeFeedbackRequest": {
            "type": "object",
            "additionalProperties": False,
            "required": ["product"],
            "properties": {
                "product": _ref("Product"),
                "scannedProduct": _ref("Product"),
                "store": {"type": "string", "maxLength": 100},
                "request": {"type": "string", "maxLength": 250},
                "reason": {"type": "string", "maxLength": 80},
            },
        },
        "AlternativesRequest": {
            "type": "object",
            "additionalProperties": False,
            "required": ["product"],
            "properties": {
                "product": _ref("Product"),
                "preferences": {"type": "object", "additionalProperties": True},
                "criteria": {"type": "array", "items": text, "maxItems": 20},
                "request": {"type": "string", "maxLength": 500},
            },
        },
        "AlternativesResponse": {
            "type": "object",
            "required": ["source", "products", "message"],
            "properties": {
                "source": text,
                "category": nullable_text,
                "products": _ref("ProductList"),
                "message": text,
            },
            "additionalProperties": False,
        },
        "AnalyticsEventRequest": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "name": {"type": "string", "maxLength": 80},
                "metadata": {
                    "type": "object",
                    "additionalProperties": {
                        "type": ["string", "number", "boolean", "null"]
                    },
                    "maxProperties": 50,
                },
            },
        },
        "AnalyticsEventResponse": {
            "type": "object",
            "required": ["ok"],
            "properties": {
                "ok": {"const": True},
                "ignored": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
        "SupportRequest": {
            "type": "object",
            "additionalProperties": False,
            "required": ["email", "message"],
            "properties": {
                "email": {"type": "string", "format": "email", "maxLength": 254},
                "topic": {"type": "string", "maxLength": 120, "default": "Suport"},
                "message": {"type": "string", "minLength": 10, "maxLength": 4000},
            },
        },
        "SubscriptionCheckoutRequest": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "plan": {"type": "string", "enum": ["pro", "family"], "default": "pro"},
                "billingInterval": {"type": "string", "enum": ["monthly", "yearly"]},
                "interval": {"type": "string", "enum": ["monthly", "yearly"]},
            },
        },
        "CheckoutResponse": {
            "type": "object",
            "required": ["mode", "plan", "billingInterval"],
            "properties": {
                "mode": {"type": "string", "enum": ["stripe", "manual"]},
                "plan": {"type": "string", "enum": ["pro", "family"]},
                "billingInterval": {"type": "string", "enum": ["monthly", "yearly"]},
                "checkoutUrl": {"type": "string", "format": "uri"},
                "sessionId": text,
                "message": text,
                "nextStep": text,
            },
            "additionalProperties": False,
        },
        "CoinCheckoutRequest": {
            "type": "object",
            "additionalProperties": False,
            "required": ["packId"],
            "properties": {
                "packId": {"type": "string", "enum": ["bronze", "gold", "diamond"]}
            },
        },
        "CoinCheckoutResponse": {
            "type": "object",
            "required": ["mode", "pack", "checkoutUrl", "sessionId"],
            "properties": {
                "mode": {"const": "stripe"},
                "pack": {"type": "string", "enum": ["bronze", "gold", "diamond"]},
                "checkoutUrl": {"type": "string", "format": "uri"},
                "sessionId": text,
            },
            "additionalProperties": False,
        },
        "CheckoutSyncRequest": {
            "type": "object",
            "additionalProperties": False,
            "required": ["sessionId"],
            "properties": {
                "sessionId": {"type": "string", "pattern": "^cs_", "maxLength": 255}
            },
        },
        "MissionActionRequest": {
            "type": "object",
            "additionalProperties": False,
            "required": ["missionId"],
            "properties": {
                "missionId": {"type": "string", "minLength": 1, "maxLength": 120}
            },
        },
        "RewardActionRequest": {
            "type": "object",
            "additionalProperties": False,
            "required": ["itemId"],
            "properties": {
                "itemId": {"type": "string", "minLength": 1, "maxLength": 120}
            },
        },
        "BarcodeRequest": {
            "type": "object",
            "additionalProperties": False,
            "required": ["barcode"],
            "properties": {"barcode": {"type": "string", "pattern": "^\\d{8,14}$"}},
        },
        "BarcodeLookupResponse": {
            "type": "object",
            "required": ["found"],
            "properties": {
                "found": {"type": "boolean"},
                "source": text,
                "matchedBarcode": text,
                "product": _ref("Product"),
                "usage": {"type": "object", "additionalProperties": True},
                "message": text,
            },
            "additionalProperties": True,
        },
        "ProductSubmission": {
            "type": "object",
            "required": ["id", "user_id", "product_name", "store", "status"],
            "properties": {
                "id": {"type": "integer"},
                "user_id": {"type": "integer"},
                "product_name": text,
                "brand": nullable_text,
                "store": text,
                "category": nullable_text,
                "quantity": nullable_text,
                "barcode": nullable_text,
                "price": nullable_text,
                "calories": nullable_number,
                "protein": nullable_number,
                "sugar": nullable_number,
                "fat": nullable_number,
                "ingredients": nullable_text,
                "status": text,
            },
            "additionalProperties": True,
        },
        "ProductSubmissionForm": {
            "type": "object",
            "required": ["user_id", "product_name", "store"],
            "properties": {
                "user_id": {"type": "integer", "minimum": 1},
                "product_name": {"type": "string", "minLength": 2, "maxLength": 150},
                "store": {"type": "string", "minLength": 2, "maxLength": 100},
                "category": {"type": "string", "maxLength": 100},
                "quantity": {"type": "string", "maxLength": 100},
                "barcode": {"type": "string", "pattern": "^\\d{8,14}$"},
                "brand": {"type": "string", "maxLength": 100},
                "price": {"type": "string", "maxLength": 100},
                "calories": {"type": "number", "minimum": 0, "maximum": 1000},
                "protein": {"type": "number", "minimum": 0, "maximum": 100},
                "sugar": {"type": "number", "minimum": 0, "maximum": 100},
                "fat": {"type": "number", "minimum": 0, "maximum": 100},
                "ingredients": {"type": "string", "maxLength": 5000},
                "front_image": {
                    "type": "string",
                    "format": "binary",
                    "contentMediaType": "image/jpeg",
                },
                "nutrition_image": {
                    "type": "string",
                    "format": "binary",
                    "contentMediaType": "image/jpeg",
                },
            },
        },
        "AnalysisForm": {
            "type": "object",
            "required": ["image"],
            "properties": {
                "image": {
                    "type": "string",
                    "format": "binary",
                    "contentMediaType": "image/jpeg",
                },
                "store": {"type": "string", "maxLength": 100, "default": "any"},
                "product_query": {"type": "string", "maxLength": 250},
                "label_text": {"type": "string", "maxLength": 2000},
                "selected_barcode": {"type": "string", "pattern": "^\\d{8,14}$"},
                "demo_product_id": {"type": "integer"},
            },
        },
        "AnalysisResponse": {
            "allOf": [_ref("Product")],
            "type": "object",
            "properties": {
                "verdict": text,
                "shortAdvice": text,
                "uploadedFile": text,
                "searchedText": text,
                "limitedData": {"type": "boolean"},
            },
            "additionalProperties": True,
        },
        "PriceReportRequest": {
            "type": "object",
            "additionalProperties": False,
            "required": ["barcode", "store", "user_id", "price"],
            "properties": {
                "barcode": {"type": "string", "pattern": "^\\d{8,14}$"},
                "store": {"type": "string", "minLength": 1, "maxLength": 100},
                "user_id": {"type": "integer", "minimum": 1},
                "price": {"type": "number", "exclusiveMinimum": 0, "maximum": 100000},
            },
        },
        "GenericObject": {"type": "object", "additionalProperties": True},
    }


def _paths() -> dict[str, Any]:
    product_list = _ref("ProductList")
    generic = _ref("GenericObject")
    message = _ref("Message")

    return {
        "/health": {
            "get": _operation(
                "health",
                "Check API liveness",
                "System",
                _ref("Health"),
                error_statuses=("500",),
            ),
        },
        "/version": {
            "get": _operation(
                "getVersion",
                "Get deployed application version",
                "System",
                _ref("Version"),
                error_statuses=("500",),
            ),
        },
        "/register": {
            "post": _operation(
                "register",
                "Create a user account",
                "Authentication",
                _ref("AuthResponse"),
                success_status="201",
                request_schema=_ref("RegisterRequest"),
                error_statuses=("400", "409", "429", "500"),
                validation_helper="validate_register_payload",
            ),
        },
        "/login": {
            "post": _operation(
                "login",
                "Create an authenticated browser session",
                "Authentication",
                _ref("AuthResponse"),
                request_schema=_ref("LoginRequest"),
                error_statuses=("400", "401", "403", "429", "500"),
                validation_helper="validate_login_payload",
            ),
        },
        "/auth/verify-email": {
            "post": _operation(
                "verifyEmail",
                "Verify an email address",
                "Authentication",
                _ref("AuthResponse"),
                request_schema=_ref("TokenRequest"),
                error_statuses=("400", "429", "500"),
                validation_helper="validate_token_payload",
            ),
        },
        "/auth/resend-verification": {
            "post": _operation(
                "resendEmailVerification",
                "Request another email verification link",
                "Authentication",
                message,
                request_schema=_ref("EmailRequest"),
                error_statuses=("400", "429", "500"),
                validation_helper="validate_email_payload",
            ),
        },
        "/auth/password-strength": {
            "post": _operation(
                "getPasswordStrength",
                "Evaluate password strength",
                "Authentication",
                _ref("PasswordStrength"),
                request_schema=_ref("PasswordStrengthRequest"),
                error_statuses=("400", "429", "500"),
            ),
        },
        "/forgot-password": {
            "post": _operation(
                "forgotPassword",
                "Request a password reset link",
                "Authentication",
                message,
                request_schema=_ref("EmailRequest"),
                error_statuses=("400", "429", "500"),
                validation_helper="validate_email_payload",
            ),
        },
        "/reset-password": {
            "post": _operation(
                "resetPassword",
                "Reset a password and start a new session",
                "Authentication",
                _ref("AuthResponse"),
                request_schema=_ref("ResetPasswordRequest"),
                error_statuses=("400", "429", "500"),
                validation_helper="validate_reset_password_payload",
            ),
        },
        "/auth/me": {
            "get": _operation(
                "getAuthenticatedUser",
                "Get the current authenticated user",
                "Authentication",
                _ref("User"),
                security=True,
                error_statuses=("401", "500"),
            ),
        },
        "/logout": {
            "post": _operation(
                "logout",
                "End the current browser session",
                "Authentication",
                message,
                security=True,
                error_statuses=("401", "500"),
            ),
        },
        "/analytics/event": {
            "post": _operation(
                "trackAnalyticsEvent",
                "Record an allow-listed product analytics event",
                "Analytics",
                _ref("AnalyticsEventResponse"),
                request_schema=_ref("AnalyticsEventRequest"),
                error_statuses=("400", "413", "429", "500"),
                validation_helper="validate_analytics_payload",
            ),
        },
        "/support/contact": {
            "post": _operation(
                "contactSupport",
                "Send a support request",
                "Support",
                message,
                request_schema=_ref("SupportRequest"),
                error_statuses=("400", "413", "429", "502", "503"),
                validation_helper="validate_support_payload",
            ),
        },
        "/feedback/alternative": {
            "post": _operation(
                "reportAlternativeIssue",
                "Report an unsuitable product alternative",
                "Feedback",
                message,
                request_schema=_ref("AlternativeFeedbackRequest"),
                security=True,
                error_statuses=("400", "401", "413", "429", "500"),
                validation_helper="validate_alternative_feedback_payload",
            ),
        },
        "/feedback/product": {
            "post": _operation(
                "reportProductIssue",
                "Report incorrect product data",
                "Feedback",
                message,
                request_schema=_ref("ProductFeedbackRequest"),
                security=True,
                error_statuses=("400", "401", "413", "429", "500"),
                validation_helper="validate_product_feedback_payload",
            ),
        },
        "/billing/status": {
            "get": _operation(
                "getBillingStatus",
                "Get current plan and usage",
                "Billing",
                generic,
                security=True,
                parameters=[
                    _query_parameter(
                        "sync",
                        {"type": "string", "enum": ["stripe"]},
                        "Optionally synchronize Stripe state",
                    ),
                ],
                error_statuses=("401", "502", "503"),
            ),
        },
        "/billing/checkout": {
            "post": _operation(
                "startCheckout",
                "Start Pro or Family checkout",
                "Billing",
                _ref("CheckoutResponse"),
                request_schema=_ref("SubscriptionCheckoutRequest"),
                security=True,
                error_statuses=("400", "401", "409", "429", "502", "503"),
                validation_helper="validate_subscription_checkout_payload",
            ),
        },
        "/billing/portal": {
            "post": _operation(
                "startBillingPortal",
                "Open the Stripe customer portal",
                "Billing",
                generic,
                security=True,
                error_statuses=("401", "404", "409", "429", "502", "503"),
            ),
        },
        "/gamification/coin-packs": {
            "get": _operation(
                "getCeCoinPacks",
                "List purchasable CeCoin packs",
                "Gamification",
                generic,
                error_statuses=("500",),
            ),
        },
        "/gamification/summary": {
            "get": _operation(
                "getGamificationSummary",
                "Get missions, rewards and CeCoin balance",
                "Gamification",
                generic,
                security=True,
                parameters=[
                    _query_parameter(
                        "leaderboard",
                        {"type": "string", "enum": ["0", "1"]},
                        "Include leaderboard data",
                    )
                ],
                error_statuses=("401", "500"),
            ),
        },
        "/gamification/leaderboard": {
            "get": _operation(
                "getGamificationLeaderboard",
                "Get the CeCoin leaderboard",
                "Gamification",
                generic,
                security=True,
                parameters=[
                    _query_parameter(
                        "period",
                        {"type": "string", "enum": ["weekly", "all_time"]},
                        "Leaderboard period",
                    )
                ],
                error_statuses=("401", "500"),
            ),
        },
        "/gamification/claim": {
            "post": _operation(
                "claimGamificationMission",
                "Claim a completed mission reward",
                "Gamification",
                generic,
                request_schema=_ref("MissionActionRequest"),
                security=True,
                error_statuses=("400", "401", "404", "409", "429", "500"),
            ),
        },
        "/gamification/redeem": {
            "post": _operation(
                "redeemCeCoinReward",
                "Redeem CeCoins for an in-app reward",
                "Gamification",
                generic,
                request_schema=_ref("RewardActionRequest"),
                security=True,
                error_statuses=("400", "401", "402", "404", "429", "500"),
            ),
        },
        "/gamification/coin-checkout": {
            "post": _operation(
                "startCeCoinCheckout",
                "Start Stripe checkout for a CeCoin pack",
                "Gamification",
                _ref("CoinCheckoutResponse"),
                request_schema=_ref("CoinCheckoutRequest"),
                security=True,
                error_statuses=("400", "401", "429", "502", "503"),
                validation_helper="validate_cecoin_checkout_payload",
            ),
        },
        "/gamification/coin-checkout/sync": {
            "post": _operation(
                "syncCeCoinCheckoutSession",
                "Synchronize a completed CeCoin checkout",
                "Gamification",
                generic,
                request_schema=_ref("CheckoutSyncRequest"),
                security=True,
                error_statuses=("400", "401", "403", "409", "429", "500", "502", "503"),
                validation_helper="validate_checkout_sync_payload",
            ),
        },
        "/catalog/romania/stats": {
            "get": _operation(
                "getRomaniaCatalogStats",
                "Get public Romania catalog statistics",
                "Catalog",
                generic,
                error_statuses=("500",),
            ),
        },
        "/products": {
            "get": _operation(
                "getProducts",
                "List catalog products",
                "Catalog",
                product_list,
                parameters=[
                    _query_parameter(
                        "store", {"type": "string", "maxLength": 100}, "Filter by store"
                    ),
                    _query_parameter(
                        "limit",
                        {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 500,
                            "default": 200,
                        },
                        "Maximum number of rows",
                    ),
                    _query_parameter(
                        "offset",
                        {"type": "integer", "minimum": 0, "default": 0},
                        "Pagination offset",
                    ),
                ],
                error_statuses=("400", "429", "500"),
            ),
        },
        "/products/search": {
            "get": _operation(
                "searchProducts",
                "Search verified external catalog products",
                "Catalog",
                product_list,
                parameters=[
                    _query_parameter(
                        "q",
                        {"type": "string", "minLength": 1, "maxLength": 250},
                        "Product search text",
                        required=True,
                    ),
                    _query_parameter(
                        "store",
                        {"type": "string", "maxLength": 100},
                        "Optional store identifier",
                    ),
                ],
                error_statuses=("400", "429", "502", "503"),
                validation_helper="validate_product_search_query",
            ),
        },
        "/products/search-label": {
            "get": _operation(
                "searchProductsByLabel",
                "Search products from recognized label text",
                "Catalog",
                product_list,
                parameters=[
                    _query_parameter(
                        "q",
                        {"type": "string", "minLength": 5, "maxLength": 2000},
                        "Recognized label text",
                        required=True,
                    )
                ],
                error_statuses=("400", "429", "502", "503"),
            ),
        },
        "/alternatives/open-food-facts": {
            "post": _operation(
                "getOpenFoodFactsAlternatives",
                "Find compatible product alternatives",
                "Catalog",
                _ref("AlternativesResponse"),
                request_schema=_ref("AlternativesRequest"),
                security=True,
                error_statuses=("400", "401", "429", "502", "503"),
                validation_helper="validate_alternatives_payload",
            ),
        },
        "/barcode/import": {
            "post": _operation(
                "importBarcodeProduct",
                "Import a barcode from the verified external catalog",
                "Catalog",
                generic,
                success_status="201",
                request_schema=_ref("BarcodeRequest"),
                security=True,
                error_statuses=("400", "401", "404", "409", "429", "502", "503"),
                validation_helper="validate_barcode_import_payload",
            ),
        },
        "/barcode/lookup/{barcode}": {
            "get": _operation(
                "lookupBarcode",
                "Look up and analyze a barcode",
                "Catalog",
                _ref("BarcodeLookupResponse"),
                security=True,
                parameters=[
                    _path_parameter(
                        "barcode",
                        {"type": "string", "pattern": "^\\d{8,14}$"},
                        "EAN, UPC or GTIN barcode",
                    )
                ],
                error_statuses=("400", "401", "402", "404", "429", "502", "503"),
            ),
        },
        "/analyze": {
            "post": _operation(
                "analyzeProduct",
                "Analyze a product image",
                "Scanning",
                _ref("AnalysisResponse"),
                request_schema=_ref("AnalysisForm"),
                media_type=MULTIPART,
                security=True,
                error_statuses=("400", "401", "402", "404", "413", "429", "502", "503"),
                validation_helper="validate_analysis_form",
            ),
        },
        "/submissions/{user_id}": {
            "get": _operation(
                "getUserSubmissions",
                "List product submissions for the current user",
                "Submissions",
                {"type": "array", "items": _ref("ProductSubmission")},
                security=True,
                parameters=[
                    _path_parameter(
                        "user_id", {"type": "integer", "minimum": 1}, "User identifier"
                    )
                ],
                error_statuses=("401", "403", "404", "500"),
            ),
        },
        "/submissions/add": {
            "post": _operation(
                "addProductSubmission",
                "Submit a missing product for verification",
                "Submissions",
                generic,
                success_status="201",
                request_schema=_ref("ProductSubmissionForm"),
                media_type=MULTIPART,
                security=True,
                error_statuses=("400", "401", "404", "409", "413", "429", "500"),
                validation_helper="validate_product_submission_payload",
            ),
        },
        "/prices/report": {
            "post": _operation(
                "reportLocalPrice",
                "Report a local product price",
                "Prices",
                generic,
                success_status="201",
                request_schema=_ref("PriceReportRequest"),
                security=True,
                error_statuses=("400", "401", "409", "429", "500"),
            ),
        },
        "/prices/{barcode}": {
            "get": _operation(
                "getLatestLocalPrice",
                "Get the latest local price summary",
                "Prices",
                generic,
                parameters=[
                    _path_parameter(
                        "barcode",
                        {"type": "string", "pattern": "^\\d{8,14}$"},
                        "EAN, UPC or GTIN barcode",
                    )
                ],
                error_statuses=("400", "429", "500", "502"),
            ),
        },
    }


def build_openapi_spec(
    *,
    server_url: str,
    version: str,
    contact_email: str = "",
    auth_cookie_name: str = "cealeg_session",
    password_min_length: int = 12,
) -> dict[str, Any]:
    """Build the explicit OpenAPI contract used by production and tests."""

    normalized_server = str(server_url or "/").strip().rstrip("/") or "/"
    normalized_version = str(version or "unknown").strip() or "unknown"
    normalized_password_min_length = max(10, int(password_min_length))
    contact = {"email": contact_email.strip()} if contact_email.strip() else {}

    return {
        "openapi": "3.1.0",
        "jsonSchemaDialect": "https://json-schema.org/draft/2020-12/schema",
        "info": {
            "title": "Ce aleg? API",
            "version": normalized_version,
            "description": (
                "Production API contract for authentication, catalog scanning, "
                "community submissions, gamification and billing."
            ),
            **({"contact": contact} if contact else {}),
        },
        "servers": [{"url": normalized_server}],
        "tags": [
            {"name": "System"},
            {"name": "Authentication"},
            {"name": "Analytics"},
            {"name": "Support"},
            {"name": "Feedback"},
            {"name": "Billing"},
            {"name": "Gamification"},
            {"name": "Catalog"},
            {"name": "Scanning"},
            {"name": "Submissions"},
            {"name": "Prices"},
        ],
        "paths": _paths(),
        "components": {
            "securitySchemes": {
                "sessionCookie": {
                    "type": "apiKey",
                    "in": "cookie",
                    "name": auth_cookie_name,
                    "description": "Signed, HttpOnly Ce aleg browser session cookie.",
                },
            },
            "schemas": _schemas(normalized_password_min_length),
        },
    }


def render_swagger_ui(spec_url: str, *, title: str = "Ce aleg? API") -> str:
    """Render a small Swagger UI shell for a same-origin OpenAPI document."""

    safe_title = html.escape(str(title), quote=True)
    serialized_url = (
        json.dumps(str(spec_url or "/api/openapi.json"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{safe_title}</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>SwaggerUIBundle({{url:{serialized_url},dom_id:'#swagger-ui',deepLinking:true}});</script>
</body>
</html>"""
