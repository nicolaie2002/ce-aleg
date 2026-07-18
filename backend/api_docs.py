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


def _response(
    description: str,
    schema: dict[str, Any] | None = None,
    *,
    media_type: str = JSON,
) -> dict[str, Any]:
    response: dict[str, Any] = {"description": description}
    if schema is not None:
        response["content"] = {media_type: {"schema": schema}}
    return response


def _request(
    schema: dict[str, Any],
    *,
    media_type: str = JSON,
    required: bool = True,
) -> dict[str, Any]:
    return {
        "required": required,
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
        "423": "Account data processing is restricted",
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
    alternate_success_statuses: tuple[str, ...] = (),
    request_schema: dict[str, Any] | None = None,
    request_required: bool = True,
    media_type: str = JSON,
    response_media_type: str = JSON,
    security: bool = False,
    security_scheme: str | None = None,
    parameters: list[dict[str, Any]] | None = None,
    error_statuses: tuple[str, ...] = ("400", "500"),
    validation_helper: str | None = None,
) -> dict[str, Any]:
    operation: dict[str, Any] = {
        "operationId": operation_id,
        "summary": summary,
        "tags": [tag],
        "x-contract-source": "explicit",
        "responses": {
            success_status: _response(
                "Successful response",
                success_schema,
                media_type=response_media_type,
            ),
            **_errors(*error_statuses),
        },
    }
    if request_schema is not None:
        operation["requestBody"] = _request(
            request_schema,
            media_type=media_type,
            required=request_required,
        )
    for status_code in alternate_success_statuses:
        operation["responses"][status_code] = _response(
            "Successful response",
            success_schema,
            media_type=response_media_type,
        )
    if security_scheme:
        operation["security"] = [{security_scheme: []}]
    elif security:
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
    nullable_integer = {"type": ["integer", "null"]}

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
        "CurrentUserResponse": {
            "type": "object",
            "required": ["user"],
            "properties": {"user": _ref("User")},
            "additionalProperties": False,
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
        "AiServiceStatus": {
            "type": "object",
            "required": ["enabled", "label"],
            "properties": {
                "enabled": {"type": "boolean"},
                "label": text,
            },
            "additionalProperties": True,
        },
        "AiStatus": {
            "type": "object",
            "additionalProperties": _ref("AiServiceStatus"),
        },
        "TranslationRequest": {
            "type": "object",
            "additionalProperties": False,
            "required": ["text"],
            "properties": {
                "text": {"type": "string", "maxLength": 5000},
                "target": {"type": "string", "enum": ["ro", "en"], "default": "ro"},
            },
        },
        "TranslationResponse": {
            "type": "object",
            "required": ["translatedText"],
            "properties": {
                "translatedText": text,
                "target": {"type": "string", "enum": ["ro", "en"]},
            },
            "additionalProperties": False,
        },
        "DashboardSummary": {
            "type": "object",
            "required": ["counts", "lastScannedProduct", "billing"],
            "properties": {
                "counts": {
                    "type": "object",
                    "required": ["cart", "history", "favorites"],
                    "properties": {
                        "cart": {"type": "integer", "minimum": 0},
                        "history": {"type": "integer", "minimum": 0},
                        "favorites": {"type": "integer", "minimum": 0},
                    },
                    "additionalProperties": False,
                },
                "lastScannedProduct": text,
                "billing": _ref("GenericObject"),
            },
            "additionalProperties": False,
        },
        "FamilyProfile": {
            "type": "object",
            "required": ["id", "name", "color", "avatar", "isPrimary"],
            "properties": {
                "id": {"type": "integer"},
                "name": text,
                "color": text,
                "avatar": text,
                "isPrimary": {"type": "boolean"},
                "createdAt": nullable_text,
            },
            "additionalProperties": False,
        },
        "FamilyProfilesResponse": {
            "type": "object",
            "required": ["plan", "enabled", "maxProfiles", "profiles"],
            "properties": {
                "plan": {"type": "string", "enum": ["free", "pro", "family"]},
                "enabled": {"type": "boolean"},
                "maxProfiles": {"type": "integer", "minimum": 1},
                "profiles": {"type": "array", "items": _ref("FamilyProfile")},
            },
            "additionalProperties": False,
        },
        "FamilyProfileRequest": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "name": {"type": "string", "minLength": 2, "maxLength": 60},
                "color": {"type": "string", "maxLength": 30},
                "avatar": {"type": "string", "maxLength": 20},
            },
        },
        "CreateFamilyProfileRequest": {
            "type": "object",
            "additionalProperties": False,
            "required": ["name"],
            "properties": {
                "name": {"type": "string", "minLength": 2, "maxLength": 60},
                "color": {"type": "string", "maxLength": 30},
                "avatar": {"type": "string", "maxLength": 20},
            },
        },
        "FamilyProfileResponse": {
            "type": "object",
            "required": ["profile"],
            "properties": {"profile": _ref("FamilyProfile")},
            "additionalProperties": False,
        },
        "DeletedResponse": {
            "type": "object",
            "required": ["deleted"],
            "properties": {"deleted": {"const": True}},
            "additionalProperties": False,
        },
        "SavedProductActionRequest": {
            "type": "object",
            "required": ["user_id", "name"],
            "properties": {
                "user_id": {"type": "integer", "minimum": 1},
                "familyProfileId": nullable_integer,
                "name": {"type": "string", "minLength": 1, "maxLength": 250},
                "store": {"type": "string", "maxLength": 100},
                "category": nullable_text,
                "score": nullable_number,
                "price": nullable_number,
                "image": nullable_text,
                "reason": nullable_text,
                "verdict": nullable_text,
                "shortAdvice": nullable_text,
                "quantity": {"type": "integer", "minimum": 1, "maximum": 999},
            },
            "additionalProperties": True,
        },
        "CartItem": {
            "type": "object",
            "required": ["id", "user_id", "name", "store", "quantity", "bought"],
            "properties": {
                "id": {"type": "integer"},
                "user_id": {"type": "integer"},
                "familyProfileId": nullable_integer,
                "name": text,
                "store": text,
                "score": nullable_number,
                "price": nullable_number,
                "image": nullable_text,
                "reason": nullable_text,
                "quantity": {"type": "integer", "minimum": 1},
                "bought": {"type": "boolean"},
                "created_at": text,
            },
            "additionalProperties": False,
        },
        "CartUpdateRequest": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "quantity": {"type": "integer", "minimum": 0, "maximum": 999},
                "bought": {"type": "boolean"},
                "store": {"type": "string", "maxLength": 100},
            },
        },
        "CartMutationResponse": {
            "type": "object",
            "required": ["message", "item"],
            "properties": {"message": text, "item": _ref("CartItem")},
            "additionalProperties": False,
        },
        "CartUpdateResponse": {
            "oneOf": [_ref("CartMutationResponse"), _ref("Message")],
        },
        "FavoriteItem": {
            "type": "object",
            "required": ["id", "user_id", "name", "store"],
            "properties": {
                "id": {"type": "integer"},
                "user_id": {"type": "integer"},
                "name": text,
                "store": text,
                "category": nullable_text,
                "score": nullable_number,
                "price": nullable_number,
                "image": nullable_text,
                "reason": nullable_text,
                "created_at": text,
            },
            "additionalProperties": False,
        },
        "FavoriteMutationResponse": {
            "type": "object",
            "required": ["message", "item"],
            "properties": {"message": text, "item": _ref("FavoriteItem")},
            "additionalProperties": False,
        },
        "HistoryItem": {
            "type": "object",
            "required": ["id", "user_id", "name", "store"],
            "properties": {
                "id": {"type": "integer"},
                "user_id": {"type": "integer"},
                "name": text,
                "store": text,
                "category": nullable_text,
                "score": nullable_number,
                "price": nullable_number,
                "image": nullable_text,
                "verdict": nullable_text,
                "shortAdvice": nullable_text,
                "scanned_at": text,
            },
            "additionalProperties": False,
        },
        "HistoryMutationResponse": {
            "type": "object",
            "required": ["message", "item"],
            "properties": {"message": text, "item": _ref("HistoryItem")},
            "additionalProperties": False,
        },
        "AccountDeletionRequestResponse": {
            "type": "object",
            "required": ["message", "sent", "email", "emailConfigured"],
            "properties": {
                "message": text,
                "sent": {"type": "boolean"},
                "email": {"type": "string", "format": "email"},
                "emailConfigured": {"type": "boolean"},
                "devDeletionLink": {"type": "string", "format": "uri"},
            },
            "additionalProperties": False,
        },
        "ProcessingRestrictionRequest": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "restricted": {"type": "boolean", "default": True},
                "reason": {"type": "string", "maxLength": 500},
            },
        },
        "ProcessingRestrictionResponse": {
            "type": "object",
            "required": ["message", "restricted", "processingRestricted"],
            "properties": {
                "message": text,
                "restricted": {"type": "boolean"},
                "processingRestricted": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
        "AccountConsentRequest": {
            "type": "object",
            "additionalProperties": False,
            "required": ["analytics"],
            "properties": {"analytics": {"type": "boolean"}},
        },
        "AccountConsentResponse": {
            "type": "object",
            "required": ["message", "analyticsConsent", "analyticsConsentAt"],
            "properties": {
                "message": text,
                "analyticsConsent": {"type": "boolean"},
                "analyticsConsentAt": nullable_text,
            },
            "additionalProperties": False,
        },
        "AccountPrivacyResponse": {
            "type": "object",
            "required": ["processingRestricted"],
            "properties": {
                "termsVersion": nullable_text,
                "termsAcceptedAt": nullable_text,
                "ageConfirmedAt": nullable_text,
                "analyticsConsent": {"type": ["boolean", "null"]},
                "analyticsConsentAt": nullable_text,
                "processingRestricted": {"type": "boolean"},
                "processingRestrictedAt": nullable_text,
            },
            "additionalProperties": False,
        },
        "AccountDataSummary": {
            "type": "object",
            "required": ["account", "subscription", "counts", "exportUrl"],
            "properties": {
                "account": _ref("GenericObject"),
                "subscription": {"oneOf": [_ref("GenericObject"), {"type": "null"}]},
                "counts": {
                    "type": "object",
                    "additionalProperties": {"type": "integer", "minimum": 0},
                },
                "exportUrl": {"type": "string", "format": "uri-reference"},
            },
            "additionalProperties": False,
        },
        "AccountDataExport": {
            "type": "object",
            "required": ["exportedAt", "formatVersion", "account"],
            "properties": {
                "exportedAt": text,
                "formatVersion": text,
                "account": _ref("GenericObject"),
                "subscription": {"oneOf": [_ref("GenericObject"), {"type": "null"}]},
                "familyProfiles": {"type": "array", "items": _ref("FamilyProfile")},
                "cart": {"type": "array", "items": _ref("CartItem")},
                "favorites": {"type": "array", "items": _ref("FavoriteItem")},
                "scanHistory": {"type": "array", "items": _ref("HistoryItem")},
                "productSubmissions": {
                    "type": "array",
                    "items": _ref("ProductSubmission"),
                },
            },
            "additionalProperties": True,
        },
        "PrivacyConsentRequest": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "granted"],
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["analytics", "marketing", "functional", "privacy", "terms"],
                },
                "granted": {"type": "boolean"},
                "policyVersion": {"type": "string", "maxLength": 40},
                "source": {"type": "string", "maxLength": 80},
            },
        },
        "PrivacyConsentResponse": {
            "type": "object",
            "required": ["recorded", "consentId"],
            "properties": {
                "recorded": {"const": True},
                "consentId": {"type": "integer"},
            },
            "additionalProperties": False,
        },
        "CookieConsentLogRequest": {
            "type": "object",
            "additionalProperties": False,
            "required": ["categories", "version"],
            "properties": {
                "categories": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["necessary", "analytics", "marketing", "functional"],
                    "properties": {
                        "necessary": {"const": True},
                        "analytics": {"type": "boolean"},
                        "marketing": {"type": "boolean"},
                        "functional": {"type": "boolean"},
                    },
                },
                "version": {
                    "type": "string",
                    "pattern": "^[A-Za-z0-9._-]{1,40}$",
                },
                "timestamp": {"type": "string", "maxLength": 40},
            },
        },
        "CookieConsentLogResponse": {
            "type": "object",
            "required": ["logged", "id"],
            "properties": {
                "logged": {"const": True},
                "id": {"type": "integer"},
            },
            "additionalProperties": False,
        },
        "AiExtractionForm": {
            "type": "object",
            "properties": {
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
                "product_hint": {"type": "string", "maxLength": 250},
            },
            "anyOf": [
                {"required": ["front_image"]},
                {"required": ["nutrition_image"]},
                {"required": ["product_hint"]},
            ],
        },
        "AiExtractionData": {
            "type": "object",
            "required": ["productName", "category", "confidence", "source", "notes"],
            "properties": {
                "productName": text,
                "brand": text,
                "category": text,
                "quantityValue": text,
                "quantityUnit": text,
                "calories": text,
                "protein": text,
                "sugar": text,
                "fat": text,
                "ingredients": text,
                "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
                "source": text,
                "notes": {"type": "array", "items": text},
            },
            "additionalProperties": False,
        },
        "AiExtractionResponse": {
            "type": "object",
            "required": ["message", "data"],
            "properties": {
                "message": text,
                "data": _ref("AiExtractionData"),
            },
            "additionalProperties": False,
        },
        "VisionFrameForm": {
            "type": "object",
            "required": ["frame"],
            "properties": {
                "frame": {
                    "type": "string",
                    "format": "binary",
                    "contentMediaType": "image/jpeg",
                }
            },
            "additionalProperties": False,
        },
        "VisionCandidate": {
            "type": "object",
            "properties": {
                "name": nullable_text,
                "brand": nullable_text,
                "variant": nullable_text,
                "barcode": nullable_text,
                "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
                "needs_barcode": {"type": "boolean"},
                "message": text,
                "local_match_score": {"type": "number", "minimum": 0},
            },
            "additionalProperties": False,
        },
        "VisionFrameResponse": {
            "type": "object",
            "required": ["identified"],
            "properties": {
                "identified": {"type": "boolean"},
                "chargeable": {"type": "boolean"},
                "source": {"type": "string", "enum": ["local", "vision"]},
                "message": text,
                "product": {"oneOf": [_ref("Product"), {"type": "null"}]},
                "candidate": _ref("VisionCandidate"),
            },
            "additionalProperties": False,
        },
        "SubmissionReviewResponse": {
            "type": "object",
            "required": ["message", "status", "confidence", "problems", "warnings", "item"],
            "properties": {
                "message": text,
                "status": text,
                "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
                "problems": {"type": "array", "items": text},
                "warnings": {"type": "array", "items": text},
                "item": _ref("ProductSubmission"),
            },
            "additionalProperties": False,
        },
        "SubmissionApprovalResponse": {
            "type": "object",
            "required": ["message", "reward", "product", "submission"],
            "properties": {
                "message": text,
                "reward": {
                    "type": "object",
                    "required": ["bonusScans", "coins", "claimed"],
                    "properties": {
                        "bonusScans": {"type": "integer", "minimum": 0},
                        "coins": {"type": "integer", "minimum": 0},
                        "claimed": {"type": "boolean"},
                    },
                    "additionalProperties": False,
                },
                "product": _ref("Product"),
                "submission": _ref("ProductSubmission"),
            },
            "additionalProperties": False,
        },
        "HomeResponse": {
            "type": "object",
            "required": ["message", "database"],
            "properties": {"message": text, "database": text},
            "additionalProperties": False,
        },
        "ReadinessResponse": {
            "type": "object",
            "required": [
                "ready",
                "environment",
                "database",
                "cookieSecure",
                "devTunnelOriginsAllowed",
                "paymentProvider",
                "emailProvider",
                "emailConfigured",
                "freeMode",
                "cloudVisionRequired",
                "blockers",
                "warnings",
            ],
            "properties": {
                "ready": {"type": "boolean"},
                "environment": text,
                "database": {"type": "string", "enum": ["postgres", "sqlite"]},
                "cookieSecure": {"type": "boolean"},
                "devTunnelOriginsAllowed": {"type": "boolean"},
                "paymentProvider": text,
                "emailProvider": text,
                "emailConfigured": {"type": "boolean"},
                "freeMode": {"const": True},
                "cloudVisionRequired": {"const": False},
                "blockers": {"type": "array", "items": text},
                "warnings": {"type": "array", "items": text},
            },
            "additionalProperties": False,
        },
        "RetentionResponse": {
            "type": "object",
            "required": [
                "applied",
                "activityCutoff",
                "analyticsCutoff",
                "searchCutoff",
                "unverifiedAccountCutoff",
                "rejectedSubmissionCutoff",
                "consentCutoff",
                "usageEvents",
                "searchEvents",
                "webhookEvents",
                "consentLogs",
                "unverifiedAccounts",
                "rejectedSubmissions",
                "scanFiles",
            ],
            "properties": {
                "applied": {"type": "boolean"},
                "activityCutoff": text,
                "analyticsCutoff": text,
                "searchCutoff": text,
                "unverifiedAccountCutoff": text,
                "rejectedSubmissionCutoff": text,
                "consentCutoff": text,
                "usageEvents": {"type": "integer", "minimum": 0},
                "searchEvents": {"type": "integer", "minimum": 0},
                "webhookEvents": {"type": "integer", "minimum": 0},
                "consentLogs": {"type": "integer", "minimum": 0},
                "unverifiedAccounts": {"type": "integer", "minimum": 0},
                "rejectedSubmissions": {"type": "integer", "minimum": 0},
                "scanFiles": {"type": "integer", "minimum": 0},
            },
            "additionalProperties": False,
        },
        "RetentionRequest": {
            "type": "object",
            "properties": {"apply": {"type": "boolean", "default": False}},
            "additionalProperties": False,
        },
        "CronMaintenanceRequest": {
            "type": "object",
            "properties": {
                "runId": {
                    "type": "string",
                    "pattern": "^[A-Za-z0-9._:-]{1,100}$",
                },
                "recategorizeLimit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                },
                "digestLimit": {"type": "integer", "minimum": 1, "maximum": 250},
                "sendDigest": {"type": "boolean", "default": True},
                "recategorize": {"type": "boolean", "default": True},
                "retention": {"type": "boolean", "default": True},
                "catalogQuality": {"type": "boolean", "default": True},
            },
            "additionalProperties": False,
        },
        "CronMaintenanceResponse": {
            "type": "object",
            "required": [
                "ok",
                "generatedAt",
                "recategorize",
                "missionDigest",
                "retention",
                "catalogQuality",
                "warnings",
                "durationsMs",
                "status",
                "runId",
                "lock",
                "completedAt",
                "durationMs",
            ],
            "properties": {
                "ok": {"const": True},
                "generatedAt": text,
                "recategorize": {
                    "oneOf": [_ref("RecategorizationBatch"), {"type": "null"}]
                },
                "missionDigest": {
                    "oneOf": [_ref("MissionDigestBatch"), {"type": "null"}]
                },
                "retention": {"oneOf": [_ref("RetentionResponse"), {"type": "null"}]},
                "catalogQuality": {
                    "oneOf": [_ref("AdminCatalogQuality"), {"type": "null"}]
                },
                "warnings": {"type": "array", "items": text},
                "durationsMs": {
                    "type": "object",
                    "additionalProperties": {"type": "number", "minimum": 0},
                },
                "status": {"type": "string", "enum": ["success", "degraded"]},
                "runId": text,
                "lock": {"type": "string", "enum": ["redis", "local"]},
                "completedAt": text,
                "durationMs": {"type": "number", "minimum": 0},
            },
            "additionalProperties": False,
        },
        "StripeWebhookResponse": {
            "type": "object",
            "required": ["received"],
            "properties": {
                "received": {"const": True},
                "duplicate": {"type": "boolean"},
                "processing": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
        "CatalogSeedResponse": {
            "type": "object",
            "required": ["message", "inserted"],
            "properties": {
                "message": text,
                "inserted": {"type": "integer", "minimum": 0},
            },
            "additionalProperties": False,
        },
        "DuplicateProductRecord": {
            "type": "object",
            "required": ["removed_id", "removed_name"],
            "properties": {
                "removed_id": {"type": "integer"},
                "removed_name": text,
                "barcode": nullable_text,
                "kept_id": {"type": "integer"},
                "kept_name": text,
            },
            "additionalProperties": False,
        },
        "CatalogCleanupResponse": {
            "type": "object",
            "required": [
                "message",
                "applied",
                "removed_count",
                "duplicates",
                "demo_products",
            ],
            "properties": {
                "message": text,
                "applied": {"type": "boolean"},
                "removed_count": {"type": "integer", "minimum": 0},
                "duplicates": {
                    "type": "array",
                    "items": _ref("DuplicateProductRecord"),
                },
                "demo_products": {
                    "type": "array",
                    "items": _ref("DuplicateProductRecord"),
                },
            },
            "additionalProperties": False,
        },
        "OpenApiDocument": {
            "type": "object",
            "required": ["openapi", "info", "paths", "components"],
            "properties": {
                "openapi": text,
                "info": _ref("GenericObject"),
                "paths": _ref("GenericObject"),
                "components": _ref("GenericObject"),
            },
            "additionalProperties": True,
        },
        "AdminOverview": {
            "type": "object",
            "required": [
                "users",
                "products",
                "uncategorizedProducts",
                "pendingSubmissions",
                "searches",
                "missingProducts",
                "priceObservations",
                "proUsers",
            ],
            "properties": {
                key: {"type": "integer", "minimum": 0}
                for key in (
                    "users",
                    "products",
                    "uncategorizedProducts",
                    "pendingSubmissions",
                    "searches",
                    "missingProducts",
                    "priceObservations",
                    "proUsers",
                )
            },
            "additionalProperties": False,
        },
        "AdminUser": {
            "type": "object",
            "required": [
                "id",
                "name",
                "email",
                "is_admin",
                "email_verified",
                "plan",
                "subscription_status",
                "created_at",
            ],
            "properties": {
                "id": {"type": "integer"},
                "name": text,
                "email": {"type": "string", "format": "email"},
                "is_admin": {"type": "boolean"},
                "email_verified": {"type": "boolean"},
                "plan": {"type": "string", "enum": ["free", "pro", "family"]},
                "subscription_status": text,
                "created_at": text,
            },
            "additionalProperties": False,
        },
        "AdminUserList": {"type": "array", "items": _ref("AdminUser")},
        "AdminSearchMiss": {
            "type": "object",
            "required": ["query", "store", "source", "count", "lastSeen"],
            "properties": {
                "query": nullable_text,
                "store": text,
                "source": text,
                "count": {"type": "integer", "minimum": 0},
                "lastSeen": nullable_text,
            },
            "additionalProperties": False,
        },
        "AdminSearchMissList": {
            "type": "array",
            "items": _ref("AdminSearchMiss"),
        },
        "AdminUsageEvent": {
            "type": "object",
            "required": [
                "id",
                "type",
                "source",
                "userId",
                "userEmail",
                "createdAt",
                "metadata",
            ],
            "properties": {
                "id": {"type": "integer"},
                "type": text,
                "source": nullable_text,
                "userId": nullable_integer,
                "userEmail": text,
                "createdAt": nullable_text,
                "metadata": _ref("GenericObject"),
            },
            "additionalProperties": False,
        },
        "EmailDiagnostics": {
            "type": "object",
            "required": [
                "provider",
                "configured",
                "from",
                "fromName",
                "replyTo",
                "providerKeyOrHostConfigured",
                "httpMaxAttempts",
                "issues",
                "lastProviderError",
            ],
            "properties": {
                "provider": text,
                "configured": {"type": "boolean"},
                "from": text,
                "fromName": text,
                "replyTo": text,
                "providerKeyOrHostConfigured": {"type": "boolean"},
                "httpMaxAttempts": {"type": "integer", "minimum": 1},
                "issues": {"type": "array", "items": text},
                "lastProviderError": text,
            },
            "additionalProperties": False,
        },
        "AdminEmailTestRequest": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "format": "email", "maxLength": 254}
            },
            "additionalProperties": False,
        },
        "AdminEmailTestResponse": {
            "type": "object",
            "required": ["sent", "from", "to", "diagnostics"],
            "properties": {
                "sent": {"type": "boolean"},
                "message": text,
                "error": text,
                "provider": text,
                "from": text,
                "to": {"type": "string", "format": "email"},
                "diagnostics": _ref("EmailDiagnostics"),
            },
            "additionalProperties": False,
        },
        "AdminVerificationUser": {
            "type": "object",
            "required": ["id", "name", "email", "emailVerified"],
            "properties": {
                "id": {"type": "integer"},
                "name": text,
                "email": {"type": "string", "format": "email"},
                "emailVerified": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
        "AdminVerificationResponse": {
            "type": "object",
            "required": ["sent", "message", "provider", "user"],
            "properties": {
                "sent": {"const": True},
                "message": text,
                "provider": text,
                "user": _ref("AdminVerificationUser"),
            },
            "additionalProperties": False,
        },
        "AdminMonitoringResponse": {
            "type": "object",
            "required": [
                "windowDays",
                "generatedAt",
                "backend",
                "cache",
                "scanIssues",
                "payments",
                "email",
                "catalog",
            ],
            "properties": {
                "windowDays": {"type": "integer", "minimum": 1, "maximum": 90},
                "generatedAt": text,
                "backend": _ref("GenericObject"),
                "cache": _ref("GenericObject"),
                "scanIssues": _ref("GenericObject"),
                "payments": _ref("GenericObject"),
                "email": _ref("GenericObject"),
                "catalog": _ref("AdminCatalogQuality"),
            },
            "additionalProperties": False,
        },
        "AdminProductUpdateRequest": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "minLength": 2, "maxLength": 150},
                "store": {"type": "string", "maxLength": 100},
                "category": {"type": "string", "maxLength": 100},
                "barcode": {"type": "string", "pattern": "^\\d{8,14}$"},
                "image": {"type": "string", "maxLength": 255},
                "priceText": {"type": "string", "maxLength": 100},
                "tag": {"type": "string", "maxLength": 100},
                "reason": {"type": "string", "maxLength": 5000},
                "ingredients": {"type": "string", "maxLength": 5000},
                "price": {"type": ["number", "string", "null"]},
                "calories": {"type": ["number", "string", "null"]},
                "protein": {"type": ["number", "string", "null"]},
                "sugar": {"type": ["number", "string", "null"]},
                "fat": {"type": ["number", "string", "null"]},
                "score": {"type": ["number", "string", "null"]},
                "vegan": {"type": "boolean"},
                "lactoseFree": {"type": "boolean"},
                "natural": {"type": "boolean"},
                "recalculate": {"type": "boolean", "default": False},
                "notifyUsers": {"type": "boolean", "default": False},
            },
            "additionalProperties": False,
        },
        "AdminProductUpdateResponse": {
            "type": "object",
            "required": ["message", "notifications", "product"],
            "properties": {
                "message": text,
                "notifications": {
                    "type": "object",
                    "required": ["requested", "sent", "emailConfigured", "error"],
                    "properties": {
                        "requested": {"type": "boolean"},
                        "sent": {"type": "integer", "minimum": 0},
                        "emailConfigured": {"type": "boolean"},
                        "error": nullable_text,
                    },
                    "additionalProperties": False,
                },
                "product": _ref("Product"),
            },
            "additionalProperties": False,
        },
        "AdminCatalogQuality": {
            "type": "object",
            "required": [
                "products",
                "healthScore",
                "uncategorizedProducts",
                "missingBarcode",
                "missingImage",
                "missingNutrition",
                "missingIngredients",
                "invalidScores",
                "invalidNutrition",
                "duplicateBarcodes",
                "duplicateProducts",
                "withBarcode",
                "withImage",
                "withNutrition",
                "barcodeCoverage",
                "imageCoverage",
                "nutritionCoverage",
                "categoryCoverage",
                "uncategorizedRate",
                "duplicateExamples",
                "categories",
                "issueExamples",
            ],
            "properties": {
                "products": {"type": "integer", "minimum": 0},
                "healthScore": {"type": "number", "minimum": 0, "maximum": 100},
                "uncategorizedProducts": {"type": "integer", "minimum": 0},
                "missingBarcode": {"type": "integer", "minimum": 0},
                "missingImage": {"type": "integer", "minimum": 0},
                "missingNutrition": {"type": "integer", "minimum": 0},
                "missingIngredients": {"type": "integer", "minimum": 0},
                "invalidScores": {"type": "integer", "minimum": 0},
                "invalidNutrition": {"type": "integer", "minimum": 0},
                "duplicateBarcodes": {"type": "integer", "minimum": 0},
                "duplicateProducts": {"type": "integer", "minimum": 0},
                "withBarcode": {"type": "integer", "minimum": 0},
                "withImage": {"type": "integer", "minimum": 0},
                "withNutrition": {"type": "integer", "minimum": 0},
                "barcodeCoverage": {"type": "number", "minimum": 0, "maximum": 100},
                "imageCoverage": {"type": "number", "minimum": 0, "maximum": 100},
                "nutritionCoverage": {"type": "number", "minimum": 0, "maximum": 100},
                "categoryCoverage": {"type": "number", "minimum": 0, "maximum": 100},
                "uncategorizedRate": {"type": "number", "minimum": 0, "maximum": 100},
                "duplicateExamples": {"type": "array", "items": _ref("GenericObject")},
                "categories": {"type": "array", "items": _ref("GenericObject")},
                "issueExamples": {"type": "array", "items": _ref("GenericObject")},
                "generatedAt": text,
                "pendingSubmissions": {"type": "integer", "minimum": 0},
                "priceObservations": {"type": "integer", "minimum": 0},
                "searches": {"type": "integer", "minimum": 0},
            },
            "additionalProperties": False,
        },
        "AdminRecategorizeRequest": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                "includeAll": {"type": "boolean"},
                "minId": {"type": "integer", "minimum": 1},
                "category": {"type": "string", "maxLength": 100},
                "apply": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
        "RecategorizationBatch": {
            "type": "object",
            "required": [
                "scanned",
                "changed",
                "applied",
                "minId",
                "lastScannedId",
                "nextMinId",
                "hasMore",
                "category",
                "changes",
            ],
            "properties": {
                "scanned": {"type": "integer", "minimum": 0},
                "changed": {"type": "integer", "minimum": 0},
                "applied": {"type": "boolean"},
                "minId": nullable_integer,
                "lastScannedId": nullable_integer,
                "nextMinId": nullable_integer,
                "hasMore": {"type": "boolean"},
                "category": nullable_text,
                "changes": {"type": "array", "items": _ref("GenericObject")},
            },
            "additionalProperties": False,
        },
        "AdminRecategorizeResponse": {
            "type": "object",
            "required": [
                "scanned",
                "changed",
                "applied",
                "minId",
                "lastScannedId",
                "nextMinId",
                "hasMore",
                "category",
                "changes",
                "message",
                "catalog",
            ],
            "properties": {
                "scanned": {"type": "integer", "minimum": 0},
                "changed": {"type": "integer", "minimum": 0},
                "applied": {"type": "boolean"},
                "minId": nullable_integer,
                "lastScannedId": nullable_integer,
                "nextMinId": nullable_integer,
                "hasMore": {"type": "boolean"},
                "category": nullable_text,
                "changes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["id", "name", "barcode", "oldCategory", "newCategory"],
                        "properties": {
                            "id": {"type": "integer"},
                            "name": text,
                            "barcode": nullable_text,
                            "oldCategory": text,
                            "newCategory": text,
                        },
                        "additionalProperties": False,
                    },
                },
                "message": text,
                "catalog": _ref("AdminCatalogQuality"),
            },
            "additionalProperties": False,
        },
        "AdminMissionDigestRequest": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 500},
                "apply": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
        "MissionDigestBatch": {
            "type": "object",
            "required": [
                "scanned",
                "eligible",
                "sent",
                "failed",
                "skippedRecent",
                "skippedUnverified",
                "applied",
                "recipients",
            ],
            "properties": {
                "scanned": {"type": "integer", "minimum": 0},
                "eligible": {"type": "integer", "minimum": 0},
                "sent": {"type": "integer", "minimum": 0},
                "failed": {"type": "integer", "minimum": 0},
                "skippedRecent": {"type": "integer", "minimum": 0},
                "skippedUnverified": {"type": "integer", "minimum": 0},
                "applied": {"type": "boolean"},
                "recipients": {"type": "array", "items": _ref("GenericObject")},
                "emailConfigured": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
        "AdminMissionDigestResponse": {
            "type": "object",
            "required": [
                "scanned",
                "eligible",
                "sent",
                "failed",
                "skippedRecent",
                "skippedUnverified",
                "applied",
                "recipients",
                "emailConfigured",
                "cooldownDays",
                "message",
            ],
            "properties": {
                "scanned": {"type": "integer", "minimum": 0},
                "eligible": {"type": "integer", "minimum": 0},
                "sent": {"type": "integer", "minimum": 0},
                "failed": {"type": "integer", "minimum": 0},
                "skippedRecent": {"type": "integer", "minimum": 0},
                "skippedUnverified": {"type": "integer", "minimum": 0},
                "applied": {"type": "boolean"},
                "recipients": {"type": "array", "items": _ref("GenericObject")},
                "emailConfigured": {"type": "boolean"},
                "cooldownDays": {"type": "integer", "minimum": 1},
                "message": text,
            },
            "additionalProperties": False,
        },
        "AdminAlternativeResolveRequest": {
            "type": "object",
            "properties": {"category": {"type": "string", "maxLength": 100}},
            "additionalProperties": False,
        },
        "AdminAlternativeResolveResponse": {
            "type": "object",
            "required": ["message", "fixed", "product", "event"],
            "properties": {
                "message": text,
                "fixed": {"type": "boolean"},
                "product": _ref("Product"),
                "event": _ref("AdminUsageEvent"),
            },
            "additionalProperties": False,
        },
        "AdminPlanUpdateRequest": {
            "type": "object",
            "required": ["plan"],
            "properties": {
                "plan": {"type": "string", "enum": ["free", "pro", "family"]},
                "status": {
                    "type": "string",
                    "enum": ["active", "inactive", "canceled"],
                    "default": "active",
                },
                "provider": {"type": "string", "maxLength": 80},
            },
            "additionalProperties": False,
        },
        "AdminPlanUpdateResponse": {
            "type": "object",
            "required": ["message", "user", "usage"],
            "properties": {
                "message": text,
                "user": _ref("User"),
                "usage": _ref("GenericObject"),
            },
            "additionalProperties": False,
        },
        "GenericObject": {"type": "object", "additionalProperties": True},
    }


def _paths() -> dict[str, Any]:
    product_list = _ref("ProductList")
    generic = _ref("GenericObject")
    message = _ref("Message")

    return {
        "/": {
            "get": _operation(
                "getApiHome",
                "Get API service and database mode",
                "System",
                _ref("HomeResponse"),
                error_statuses=("500",),
            ),
        },
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
        "/readiness": {
            "get": _operation(
                "getPublicationReadiness",
                "Inspect production configuration readiness",
                "Admin",
                _ref("ReadinessResponse"),
                security=True,
                error_statuses=("401", "403", "500"),
            ),
        },
        "/init-db": {
            "get": _operation(
                "initializeDevelopmentDatabase",
                "Initialize a non-production development database",
                "Admin",
                message,
                security=True,
                error_statuses=("401", "403", "409", "500"),
            ),
        },
        "/openapi.json": {
            "get": _operation(
                "getOpenApiDocument",
                "Get the runtime OpenAPI document",
                "System",
                _ref("OpenApiDocument"),
                error_statuses=("500",),
            ),
        },
        "/api/openapi.json": {
            "get": _operation(
                "getNamespacedOpenApiDocument",
                "Get the runtime OpenAPI document through its API alias",
                "System",
                _ref("OpenApiDocument"),
                error_statuses=("500",),
            ),
        },
        "/docs": {
            "get": _operation(
                "getApiDocumentation",
                "Open interactive API documentation",
                "System",
                {"type": "string"},
                response_media_type="text/html",
                error_statuses=("500",),
            ),
        },
        "/api/docs": {
            "get": _operation(
                "getNamespacedApiDocumentation",
                "Open interactive API documentation through its API alias",
                "System",
                {"type": "string"},
                response_media_type="text/html",
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
                _ref("CurrentUserResponse"),
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
        "/account/delete/request": {
            "post": _operation(
                "requestAccountDeletion",
                "Email a signed account deletion confirmation link",
                "Privacy",
                _ref("AccountDeletionRequestResponse"),
                security=True,
                error_statuses=("401", "429", "500", "502"),
            ),
        },
        "/account/delete/confirm": {
            "post": _operation(
                "confirmAccountDeletion",
                "Permanently delete an account using a signed token",
                "Privacy",
                message,
                request_schema=_ref("TokenRequest"),
                error_statuses=("400", "429", "500", "502"),
            ),
        },
        "/account/restriction": {
            "post": _operation(
                "updateProcessingRestriction",
                "Restrict or resume optional account data processing",
                "Privacy",
                _ref("ProcessingRestrictionResponse"),
                request_schema=_ref("ProcessingRestrictionRequest"),
                security=True,
                error_statuses=("400", "401", "423", "429", "500"),
            ),
        },
        "/account/consent": {
            "post": _operation(
                "updateAccountConsent",
                "Update the authenticated user's analytics consent",
                "Privacy",
                _ref("AccountConsentResponse"),
                request_schema=_ref("AccountConsentRequest"),
                security=True,
                error_statuses=("400", "401", "429", "500"),
            ),
        },
        "/account/privacy": {
            "get": _operation(
                "getAccountPrivacy",
                "Get account privacy and consent state",
                "Privacy",
                _ref("AccountPrivacyResponse"),
                security=True,
                error_statuses=("401", "500"),
            ),
        },
        "/account/data": {
            "get": _operation(
                "getAccountDataSummary",
                "Get an account data summary before export",
                "Privacy",
                _ref("AccountDataSummary"),
                security=True,
                error_statuses=("401", "500"),
            ),
        },
        "/account/data-export": {
            "get": _operation(
                "exportAccountData",
                "Download the authenticated user's complete JSON data export",
                "Privacy",
                _ref("AccountDataExport"),
                security=True,
                error_statuses=("401", "500"),
            ),
        },
        "/account/export": {
            "get": _operation(
                "exportAccountDataLegacyAlias",
                "Legacy alias for the complete JSON account export",
                "Privacy",
                _ref("AccountDataExport"),
                security=True,
                error_statuses=("401", "500"),
            ),
        },
        "/privacy/consent": {
            "post": _operation(
                "recordPrivacyConsent",
                "Record a versioned account privacy decision",
                "Privacy",
                _ref("PrivacyConsentResponse"),
                success_status="201",
                request_schema=_ref("PrivacyConsentRequest"),
                security=True,
                error_statuses=("400", "401", "429", "500"),
            ),
        },
        "/consent/log": {
            "post": _operation(
                "logCookieConsent",
                "Record an anonymous or authenticated cookie consent decision",
                "Privacy",
                _ref("CookieConsentLogResponse"),
                success_status="201",
                request_schema=_ref("CookieConsentLogRequest"),
                error_statuses=("400", "413", "429", "500"),
                validation_helper="validate_consent_log_payload",
            ),
        },
        "/translate": {
            "post": _operation(
                "translateText",
                "Translate a short catalog text",
                "Localization",
                _ref("TranslationResponse"),
                request_schema=_ref("TranslationRequest"),
                security=True,
                error_statuses=("400", "401", "429", "500", "502"),
            ),
        },
        "/ai/status": {
            "get": _operation(
                "getAiStatus",
                "Get availability of optional scanning services",
                "Scanning",
                _ref("AiStatus"),
                error_statuses=("429", "500"),
            ),
        },
        "/ai/extract-product-info": {
            "post": _operation(
                "extractProductInfo",
                "Extract product and nutrition fields from contribution photos",
                "Scanning",
                _ref("AiExtractionResponse"),
                request_schema=_ref("AiExtractionForm"),
                media_type=MULTIPART,
                security=True,
                error_statuses=("400", "401", "413", "429", "500"),
            ),
        },
        "/ai/identify-product-frame": {
            "post": _operation(
                "identifyProductFrame",
                "Identify a product from one live camera frame",
                "Scanning",
                _ref("VisionFrameResponse"),
                request_schema=_ref("VisionFrameForm"),
                media_type=MULTIPART,
                security=True,
                error_statuses=("400", "401", "402", "413", "429", "500", "502", "503"),
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
        "/billing/stripe/webhook": {
            "post": _operation(
                "processStripeWebhook",
                "Verify and process one Stripe webhook event",
                "Billing",
                _ref("StripeWebhookResponse"),
                alternate_success_statuses=("202",),
                request_schema=_ref("GenericObject"),
                security_scheme="stripeSignature",
                error_statuses=("400", "500", "503"),
            ),
        },
        "/dashboard/summary": {
            "get": _operation(
                "getDashboardSummary",
                "Get the current user's compact dashboard summary",
                "Dashboard",
                _ref("DashboardSummary"),
                security=True,
                parameters=[
                    _query_parameter(
                        "profile_id",
                        {"type": "integer", "minimum": 1},
                        "Optional active Family profile",
                    )
                ],
                error_statuses=("400", "401", "500"),
            ),
        },
        "/family/profiles": {
            "get": _operation(
                "getFamilyProfiles",
                "List Family profiles for the current account",
                "Family",
                _ref("FamilyProfilesResponse"),
                security=True,
                error_statuses=("401", "500"),
            ),
            "post": _operation(
                "createFamilyProfile",
                "Create a Family profile",
                "Family",
                _ref("FamilyProfileResponse"),
                success_status="201",
                request_schema=_ref("CreateFamilyProfileRequest"),
                security=True,
                error_statuses=("400", "401", "402", "429", "500"),
            ),
        },
        "/family/profiles/{profile_id}": {
            "patch": _operation(
                "updateFamilyProfile",
                "Update a Family profile",
                "Family",
                _ref("FamilyProfileResponse"),
                request_schema=_ref("FamilyProfileRequest"),
                security=True,
                parameters=[
                    _path_parameter(
                        "profile_id", {"type": "integer", "minimum": 1}, "Profile identifier"
                    )
                ],
                error_statuses=("400", "401", "402", "404", "429", "500"),
            ),
            "delete": _operation(
                "deleteFamilyProfile",
                "Delete a non-primary Family profile and its cart",
                "Family",
                _ref("DeletedResponse"),
                security=True,
                parameters=[
                    _path_parameter(
                        "profile_id", {"type": "integer", "minimum": 1}, "Profile identifier"
                    )
                ],
                error_statuses=("400", "401", "402", "404", "429", "500"),
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
        "/cart/{user_id}": {
            "get": _operation(
                "getCart",
                "List cart items for the current account and Family profile",
                "Cart",
                {"type": "array", "items": _ref("CartItem")},
                security=True,
                parameters=[
                    _path_parameter(
                        "user_id", {"type": "integer", "minimum": 1}, "User identifier"
                    ),
                    _query_parameter(
                        "profile_id",
                        {"type": "integer", "minimum": 1},
                        "Optional active Family profile",
                    ),
                ],
                error_statuses=("401", "403", "404", "500"),
            ),
        },
        "/cart/add": {
            "post": _operation(
                "addCartItem",
                "Add a product to the current profile cart",
                "Cart",
                _ref("CartMutationResponse"),
                alternate_success_statuses=("201",),
                request_schema=_ref("SavedProductActionRequest"),
                security=True,
                error_statuses=("400", "401", "403", "404", "423", "429", "500"),
            ),
        },
        "/cart/item/{item_id}": {
            "patch": _operation(
                "updateCartItem",
                "Update quantity, store or bought state for a cart item",
                "Cart",
                _ref("CartUpdateResponse"),
                request_schema=_ref("CartUpdateRequest"),
                security=True,
                parameters=[
                    _path_parameter(
                        "item_id", {"type": "integer", "minimum": 1}, "Cart item identifier"
                    )
                ],
                error_statuses=("400", "401", "403", "404", "423", "500"),
            ),
            "delete": _operation(
                "deleteCartItem",
                "Delete one cart item",
                "Cart",
                message,
                security=True,
                parameters=[
                    _path_parameter(
                        "item_id", {"type": "integer", "minimum": 1}, "Cart item identifier"
                    )
                ],
                error_statuses=("401", "403", "404", "423", "500"),
            ),
        },
        "/cart/clear/{user_id}": {
            "delete": _operation(
                "clearCart",
                "Delete all cart items for the active profile",
                "Cart",
                message,
                security=True,
                parameters=[
                    _path_parameter(
                        "user_id", {"type": "integer", "minimum": 1}, "User identifier"
                    ),
                    _query_parameter(
                        "profile_id",
                        {"type": "integer", "minimum": 1},
                        "Optional active Family profile",
                    ),
                ],
                error_statuses=("401", "403", "404", "423", "500"),
            ),
        },
        "/favorites/{user_id}": {
            "get": _operation(
                "getFavorites",
                "List favorite products for the current account",
                "Favorites",
                {"type": "array", "items": _ref("FavoriteItem")},
                security=True,
                parameters=[
                    _path_parameter(
                        "user_id", {"type": "integer", "minimum": 1}, "User identifier"
                    )
                ],
                error_statuses=("401", "403", "404", "500"),
            ),
        },
        "/favorites/add": {
            "post": _operation(
                "addFavorite",
                "Save a product as favorite",
                "Favorites",
                _ref("FavoriteMutationResponse"),
                alternate_success_statuses=("201",),
                request_schema=_ref("SavedProductActionRequest"),
                security=True,
                error_statuses=("400", "401", "403", "404", "423", "500"),
            ),
        },
        "/favorites/item/{favorite_id}": {
            "delete": _operation(
                "deleteFavorite",
                "Delete one favorite product",
                "Favorites",
                message,
                security=True,
                parameters=[
                    _path_parameter(
                        "favorite_id", {"type": "integer", "minimum": 1}, "Favorite identifier"
                    )
                ],
                error_statuses=("401", "403", "404", "423", "500"),
            ),
        },
        "/favorites/clear/{user_id}": {
            "delete": _operation(
                "clearFavorites",
                "Delete all favorite products for the current account",
                "Favorites",
                message,
                security=True,
                parameters=[
                    _path_parameter(
                        "user_id", {"type": "integer", "minimum": 1}, "User identifier"
                    )
                ],
                error_statuses=("401", "403", "404", "423", "500"),
            ),
        },
        "/history/{user_id}": {
            "get": _operation(
                "getScanHistory",
                "List scan history for the current account",
                "History",
                {"type": "array", "items": _ref("HistoryItem")},
                security=True,
                parameters=[
                    _path_parameter(
                        "user_id", {"type": "integer", "minimum": 1}, "User identifier"
                    )
                ],
                error_statuses=("401", "403", "404", "500"),
            ),
        },
        "/history/add": {
            "post": _operation(
                "addScanHistory",
                "Save a completed product scan",
                "History",
                _ref("HistoryMutationResponse"),
                success_status="201",
                request_schema=_ref("SavedProductActionRequest"),
                security=True,
                error_statuses=("400", "401", "403", "404", "423", "500"),
            ),
        },
        "/history/item/{history_id}": {
            "delete": _operation(
                "deleteScanHistoryItem",
                "Delete one scan history item",
                "History",
                message,
                security=True,
                parameters=[
                    _path_parameter(
                        "history_id", {"type": "integer", "minimum": 1}, "History item identifier"
                    )
                ],
                error_statuses=("401", "403", "404", "423", "500"),
            ),
        },
        "/history/clear/{user_id}": {
            "delete": _operation(
                "clearScanHistory",
                "Delete all scan history for the current account",
                "History",
                message,
                security=True,
                parameters=[
                    _path_parameter(
                        "user_id", {"type": "integer", "minimum": 1}, "User identifier"
                    )
                ],
                error_statuses=("401", "403", "404", "423", "500"),
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
        "/products/seed": {
            "get": _operation(
                "seedDemoProducts",
                "Insert missing demonstration catalog products",
                "Admin",
                _ref("CatalogSeedResponse"),
                security=True,
                error_statuses=("401", "403", "500"),
            ),
        },
        "/products/cleanup-duplicates": {
            "get": _operation(
                "previewDuplicateProductCleanup",
                "Preview duplicate and demonstration product cleanup",
                "Admin",
                _ref("CatalogCleanupResponse"),
                security=True,
                error_statuses=("401", "403", "500"),
            ),
            "post": _operation(
                "applyDuplicateProductCleanup",
                "Apply duplicate and demonstration product cleanup",
                "Admin",
                _ref("CatalogCleanupResponse"),
                security=True,
                parameters=[
                    _query_parameter(
                        "apply", {"type": "boolean", "default": False}, "Delete matches"
                    )
                ],
                error_statuses=("401", "403", "500"),
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
        "/uploads/submissions/{filename}": {
            "get": _operation(
                "getSubmissionImage",
                "Read an authorized local submission image",
                "Submissions",
                {"type": "string", "format": "binary"},
                response_media_type="application/octet-stream",
                security=True,
                parameters=[
                    _path_parameter("filename", {"type": "string"}, "Stored image path")
                ],
                error_statuses=("401", "403", "404", "500"),
            ),
        },
        "/uploads/scans/{filename}": {
            "get": _operation(
                "getScanImage",
                "Read an authorized temporary scan image",
                "Scanning",
                {"type": "string", "format": "binary"},
                response_media_type="application/octet-stream",
                security=True,
                parameters=[
                    _path_parameter("filename", {"type": "string"}, "Stored image path")
                ],
                error_statuses=("401", "403", "404", "500"),
            ),
        },
        "/uploads/supabase-submissions/{object_path}": {
            "get": _operation(
                "getSupabaseSubmissionImage",
                "Read an authorized private Supabase submission image",
                "Submissions",
                {"type": "string", "format": "binary"},
                response_media_type="application/octet-stream",
                security=True,
                parameters=[
                    _path_parameter(
                        "object_path", {"type": "string"}, "Private storage object path"
                    )
                ],
                error_statuses=("401", "403", "404", "500", "502", "503"),
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
        "/submissions/item/{submission_id}": {
            "delete": _operation(
                "deleteProductSubmission",
                "Delete one owned or administrator-visible product submission",
                "Submissions",
                message,
                security=True,
                parameters=[
                    _path_parameter(
                        "submission_id",
                        {"type": "integer", "minimum": 1},
                        "Submission identifier",
                    )
                ],
                error_statuses=("401", "403", "404", "423", "500"),
            ),
        },
        "/submissions/ai-review/{submission_id}": {
            "post": _operation(
                "reviewProductSubmission",
                "Run the deterministic submission review as administrator",
                "Submissions",
                _ref("SubmissionReviewResponse"),
                security=True,
                parameters=[
                    _path_parameter(
                        "submission_id",
                        {"type": "integer", "minimum": 1},
                        "Submission identifier",
                    )
                ],
                error_statuses=("401", "403", "404", "500"),
            ),
        },
        "/submissions/approve/{submission_id}": {
            "post": _operation(
                "approveProductSubmission",
                "Publish an approved submission and synchronize its reward",
                "Submissions",
                _ref("SubmissionApprovalResponse"),
                security=True,
                parameters=[
                    _path_parameter(
                        "submission_id",
                        {"type": "integer", "minimum": 1},
                        "Submission identifier",
                    )
                ],
                error_statuses=("400", "401", "403", "404", "500", "502"),
            ),
        },
        "/users": {
            "get": _operation(
                "getAdminUsers",
                "List users with plan and verification state",
                "Admin",
                _ref("AdminUserList"),
                security=True,
                error_statuses=("401", "403", "500"),
            ),
        },
        "/admin/overview": {
            "get": _operation(
                "getAdminOverview",
                "Get the compact administration overview",
                "Admin",
                _ref("AdminOverview"),
                security=True,
                error_statuses=("401", "403", "500"),
            ),
        },
        "/admin/monitoring": {
            "get": _operation(
                "getAdminMonitoring",
                "Get launch monitoring, catalog, payment and email diagnostics",
                "Admin",
                _ref("AdminMonitoringResponse"),
                security=True,
                parameters=[
                    _query_parameter(
                        "days",
                        {"type": "integer", "minimum": 1, "maximum": 90, "default": 7},
                        "Monitoring window in days",
                    ),
                    _query_parameter(
                        "limit",
                        {"type": "integer", "minimum": 5, "maximum": 50, "default": 16},
                        "Maximum recent rows per section",
                    ),
                ],
                error_statuses=("401", "403", "500"),
            ),
        },
        "/admin/submissions": {
            "get": _operation(
                "getAdminSubmissions",
                "List all community product submissions",
                "Admin",
                {"type": "array", "items": _ref("ProductSubmission")},
                security=True,
                error_statuses=("401", "403", "500"),
            ),
        },
        "/admin/search-misses": {
            "get": _operation(
                "getAdminSearchMisses",
                "Aggregate catalog searches with no result",
                "Admin",
                _ref("AdminSearchMissList"),
                security=True,
                parameters=[
                    _query_parameter(
                        "days",
                        {"type": "integer", "minimum": 1, "maximum": 365, "default": 30},
                        "Aggregation window in days",
                    ),
                    _query_parameter(
                        "limit",
                        {"type": "integer", "minimum": 1, "maximum": 200, "default": 50},
                        "Maximum aggregated rows",
                    ),
                ],
                error_statuses=("401", "403", "500"),
            ),
        },
        "/admin/products/search": {
            "get": _operation(
                "searchAdminProducts",
                "Search catalog products for administration",
                "Admin",
                product_list,
                security=True,
                parameters=[
                    _query_parameter(
                        "q",
                        {"type": "string"},
                        "Name, category, store or barcode query",
                    ),
                    _query_parameter(
                        "limit",
                        {"type": "integer", "minimum": 1, "maximum": 50, "default": 20},
                        "Maximum products",
                    ),
                ],
                error_statuses=("401", "403", "500"),
            ),
        },
        "/admin/products/{product_id}": {
            "patch": _operation(
                "updateAdminProduct",
                "Edit and optionally recalculate a catalog product",
                "Admin",
                _ref("AdminProductUpdateResponse"),
                request_schema=_ref("AdminProductUpdateRequest"),
                request_required=False,
                security=True,
                parameters=[
                    _path_parameter(
                        "product_id",
                        {"type": "integer", "minimum": 1},
                        "Product identifier",
                    )
                ],
                error_statuses=("400", "401", "403", "404", "500"),
            ),
            "delete": _operation(
                "deleteAdminProduct",
                "Delete a catalog product",
                "Admin",
                message,
                security=True,
                parameters=[
                    _path_parameter(
                        "product_id",
                        {"type": "integer", "minimum": 1},
                        "Product identifier",
                    )
                ],
                error_statuses=("401", "403", "404", "500"),
            ),
        },
        "/admin/catalog/quality": {
            "get": _operation(
                "getAdminCatalogQuality",
                "Get catalog completeness and integrity metrics",
                "Admin",
                _ref("AdminCatalogQuality"),
                security=True,
                error_statuses=("401", "403", "500"),
            ),
        },
        "/admin/catalog/recategorize": {
            "get": _operation(
                "previewAdminCatalogRecategorization",
                "Preview one catalog recategorization batch",
                "Admin",
                _ref("AdminRecategorizeResponse"),
                security=True,
                parameters=[
                    _query_parameter(
                        "limit",
                        {"type": "integer", "minimum": 1, "maximum": 1000, "default": 300},
                        "Maximum products to scan",
                    ),
                    _query_parameter(
                        "include_all", {"type": "boolean"}, "Include categorized products"
                    ),
                    _query_parameter(
                        "min_id",
                        {"type": "integer", "minimum": 1},
                        "First product identifier in the batch",
                    ),
                    _query_parameter(
                        "category", {"type": "string", "maxLength": 100}, "Category filter"
                    ),
                ],
                error_statuses=("401", "403", "500"),
            ),
            "post": _operation(
                "applyAdminCatalogRecategorization",
                "Apply one catalog recategorization batch",
                "Admin",
                _ref("AdminRecategorizeResponse"),
                request_schema=_ref("AdminRecategorizeRequest"),
                request_required=False,
                security=True,
                parameters=[
                    _query_parameter(
                        "apply", {"type": "boolean", "default": False}, "Persist changes"
                    )
                ],
                error_statuses=("401", "403", "500"),
            ),
        },
        "/admin/missions/digest": {
            "get": _operation(
                "previewAdminMissionDigest",
                "Preview recipients with missions near completion",
                "Admin",
                _ref("AdminMissionDigestResponse"),
                security=True,
                parameters=[
                    _query_parameter(
                        "limit",
                        {"type": "integer", "minimum": 1, "maximum": 500, "default": 100},
                        "Maximum users to inspect",
                    )
                ],
                error_statuses=("401", "403", "500"),
            ),
            "post": _operation(
                "sendAdminMissionDigest",
                "Send mission digest emails to eligible users",
                "Admin",
                _ref("AdminMissionDigestResponse"),
                request_schema=_ref("AdminMissionDigestRequest"),
                request_required=False,
                security=True,
                parameters=[
                    _query_parameter(
                        "apply", {"type": "boolean", "default": False}, "Send emails"
                    )
                ],
                error_statuses=("400", "401", "403", "500", "502", "503"),
            ),
        },
        "/admin/retention": {
            "get": _operation(
                "previewAdminRetention",
                "Preview records and files eligible for retention cleanup",
                "Admin",
                _ref("RetentionResponse"),
                security=True,
                error_statuses=("401", "403", "500"),
            ),
            "post": _operation(
                "applyAdminRetention",
                "Apply the configured data retention policy",
                "Admin",
                _ref("RetentionResponse"),
                request_schema=_ref("RetentionRequest"),
                request_required=False,
                security=True,
                error_statuses=("401", "403", "500"),
            ),
        },
        "/internal/cron/maintenance": {
            "post": _operation(
                "runProductionMaintenance",
                "Run the idempotent production maintenance batch",
                "System",
                _ref("CronMaintenanceResponse"),
                request_schema=_ref("CronMaintenanceRequest"),
                request_required=False,
                security_scheme="cronBearer",
                error_statuses=("400", "401", "409", "500"),
            ),
        },
        "/admin/email-test": {
            "post": _operation(
                "sendAdminEmailTest",
                "Send one transactional email configuration test",
                "Admin",
                _ref("AdminEmailTestResponse"),
                request_schema=_ref("AdminEmailTestRequest"),
                request_required=False,
                security=True,
                error_statuses=("400", "401", "403", "500", "502"),
            ),
        },
        "/admin/users/resend-verification": {
            "post": _operation(
                "resendAdminUserVerification",
                "Resend account verification to one user",
                "Admin",
                _ref("AdminVerificationResponse"),
                request_schema=_ref("EmailRequest"),
                security=True,
                error_statuses=("400", "401", "403", "404", "409", "500", "502", "503"),
            ),
        },
        "/admin/users/{user_id}/plan": {
            "patch": _operation(
                "updateAdminUserPlan",
                "Update a user's plan and subscription state",
                "Admin",
                _ref("AdminPlanUpdateResponse"),
                request_schema=_ref("AdminPlanUpdateRequest"),
                security=True,
                parameters=[
                    _path_parameter(
                        "user_id", {"type": "integer", "minimum": 1}, "User identifier"
                    )
                ],
                error_statuses=("400", "401", "403", "404", "500"),
            ),
        },
        "/admin/alternative-reports/{event_id}/resolve": {
            "post": _operation(
                "resolveAdminAlternativeReport",
                "Resolve an unsuitable alternative report",
                "Admin",
                _ref("AdminAlternativeResolveResponse"),
                request_schema=_ref("AdminAlternativeResolveRequest"),
                request_required=False,
                security=True,
                parameters=[
                    _path_parameter(
                        "event_id", {"type": "integer", "minimum": 1}, "Report event identifier"
                    )
                ],
                error_statuses=("400", "401", "403", "404", "500"),
            ),
        },
        "/admin/export/search-misses.csv": {
            "get": _operation(
                "exportAdminSearchMisses",
                "Download search misses as CSV",
                "Admin",
                {"type": "string"},
                response_media_type="text/csv",
                security=True,
                parameters=[
                    _query_parameter(
                        "days",
                        {"type": "integer", "minimum": 1, "maximum": 180, "default": 30},
                        "Export window in days",
                    )
                ],
                error_statuses=("401", "403", "500"),
            ),
        },
        "/admin/export/alternative-reports.csv": {
            "get": _operation(
                "exportAdminAlternativeReports",
                "Download alternative reports as CSV",
                "Admin",
                {"type": "string"},
                response_media_type="text/csv",
                security=True,
                parameters=[
                    _query_parameter(
                        "days",
                        {"type": "integer", "minimum": 1, "maximum": 180, "default": 30},
                        "Export window in days",
                    )
                ],
                error_statuses=("401", "403", "500"),
            ),
        },
        "/admin/export/payment-events.csv": {
            "get": _operation(
                "exportAdminPaymentEvents",
                "Download payment events as CSV",
                "Admin",
                {"type": "string"},
                response_media_type="text/csv",
                security=True,
                parameters=[
                    _query_parameter(
                        "days",
                        {"type": "integer", "minimum": 1, "maximum": 180, "default": 30},
                        "Export window in days",
                    )
                ],
                error_statuses=("401", "403", "500"),
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
            {"name": "Privacy"},
            {"name": "Localization"},
            {"name": "Analytics"},
            {"name": "Support"},
            {"name": "Feedback"},
            {"name": "Billing"},
            {"name": "Dashboard"},
            {"name": "Family"},
            {"name": "Gamification"},
            {"name": "Cart"},
            {"name": "Favorites"},
            {"name": "History"},
            {"name": "Catalog"},
            {"name": "Scanning"},
            {"name": "Submissions"},
            {"name": "Prices"},
            {"name": "Admin"},
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
                "stripeSignature": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "Stripe-Signature",
                    "description": "Stripe webhook signature verified against the raw body.",
                },
                "cronBearer": {
                    "type": "http",
                    "scheme": "bearer",
                    "description": "Internal maintenance bearer secret.",
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
