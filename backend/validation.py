"""Reusable request validation for Ce aleg API payloads.

The functions in this module deliberately have no Flask or database dependency.
Routes can therefore validate and normalize input before touching application
state, while tests and API documentation can share the same field contracts.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Any, Callable, Iterable, Mapping


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
BARCODE_PATTERN = re.compile(r"^\d{8,14}$")
DEFAULT_ANALYTICS_EVENTS = frozenset(
    {
        "landing_cta",
        "scan_started",
        "barcode_lookup",
        "product_found",
        "product_missing",
        "add_to_cart",
        "add_to_favorites",
        "alternative_report",
        "checkout_started",
        "pricing_checkout",
        "cecoins_checkout",
        "subscription_started",
        "support_message",
        "product_report",
        "register_started",
        "login_success",
    }
)
PRODUCT_REPORT_REASONS = frozenset(
    {
        "wrong_product",
        "wrong_price",
        "wrong_nutrition",
        "wrong_score",
        "wrong_image",
        "missing_data",
        "other",
    }
)
SUBSCRIPTION_PLANS = frozenset({"pro", "family"})
CECOIN_PACKS = frozenset({"bronze", "gold", "diamond"})


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """A stable, machine-readable validation problem."""

    field: str
    code: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {
            "field": self.field,
            "code": self.code,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Normalized data plus zero or more validation issues."""

    data: dict[str, Any]
    errors: tuple[ValidationIssue, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.errors

    def error_payload(self) -> dict[str, Any]:
        """Return the common API error shape used by Flask routes."""

        if self.ok:
            return {}

        return {
            "error": self.errors[0].message,
            "code": "validation_error",
            "errors": [issue.as_dict() for issue in self.errors],
        }


def _issue(field: str, code: str, message: str) -> ValidationIssue:
    return ValidationIssue(field=field, code=code, message=message)


def _payload(value: Any) -> tuple[Mapping[str, Any], list[ValidationIssue]]:
    if isinstance(value, Mapping):
        return value, []

    return {}, [
        _issue("$", "invalid_type", "Corpul cererii trebuie să fie un obiect JSON."),
    ]


def _text(value: Any, *, lower: bool = False, upper: bool = False) -> str:
    normalized = str(value or "").strip()
    if lower:
        return normalized.lower()
    if upper:
        return normalized.upper()
    return normalized


def _boolean(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in {0, 1}:
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "da"}
    return False


def _finite_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _required_text(
    data: Mapping[str, Any],
    field: str,
    errors: list[ValidationIssue],
    *,
    aliases: Iterable[str] = (),
    label: str | None = None,
    minimum: int = 1,
    maximum: int | None = None,
    lower: bool = False,
) -> str:
    value = data.get(field)
    if value is None:
        for alias in aliases:
            if data.get(alias) is not None:
                value = data.get(alias)
                break
    normalized = _text(value, lower=lower)
    display = label or field

    if not normalized:
        errors.append(_issue(field, "required", f"{display} este obligatoriu."))
    elif len(normalized) < minimum:
        errors.append(
            _issue(
                field,
                "too_short",
                f"{display} trebuie să conțină cel puțin {minimum} caractere.",
            )
        )
    elif maximum is not None and len(normalized) > maximum:
        errors.append(
            _issue(
                field,
                "too_long",
                f"{display} poate conține maximum {maximum} caractere.",
            )
        )
    return normalized


def _optional_text(
    data: Mapping[str, Any],
    field: str,
    errors: list[ValidationIssue],
    *,
    aliases: Iterable[str] = (),
    label: str | None = None,
    maximum: int | None = None,
    lower: bool = False,
) -> str:
    value = data.get(field)
    if value is None:
        for alias in aliases:
            if data.get(alias) is not None:
                value = data.get(alias)
                break
    normalized = _text(value, lower=lower)
    if maximum is not None and len(normalized) > maximum:
        errors.append(
            _issue(
                field,
                "too_long",
                f"{label or field} poate conține maximum {maximum} caractere.",
            )
        )
    return normalized


def _normalize_invite_code(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]", "", _text(value, upper=True))[:24]


def _normalize_event_name(value: Any) -> str:
    return _text(value, lower=True).replace(" ", "_")


def _has_valid_gs1_checksum(barcode: str) -> bool:
    digits = [int(digit) for digit in barcode]
    check_digit = digits.pop()
    weighted_sum = sum(
        digit * (3 if position % 2 == 0 else 1)
        for position, digit in enumerate(reversed(digits))
    )
    return (10 - weighted_sum % 10) % 10 == check_digit


def validate_barcode_value(
    value: Any,
    *,
    required: bool = False,
    field: str = "barcode",
) -> tuple[str, tuple[ValidationIssue, ...]]:
    barcode = _text(value)
    errors: list[ValidationIssue] = []

    if not barcode:
        if required:
            errors.append(_issue(field, "required", "Codul de bare lipsește."))
        return barcode, tuple(errors)

    if not BARCODE_PATTERN.fullmatch(barcode):
        errors.append(
            _issue(
                field,
                "invalid_barcode",
                "Codul de bare trebuie să conțină între 8 și 14 cifre.",
            )
        )
    elif len(barcode) in {8, 12, 13, 14} and not _has_valid_gs1_checksum(barcode):
        errors.append(
            _issue(
                field,
                "invalid_checksum",
                "Codul de bare pare citit greșit. Verifică cifrele sau scanează din nou.",
            )
        )
    return barcode, tuple(errors)


def validate_register_payload(
    value: Any,
    *,
    password_min_length: int = 12,
) -> ValidationResult:
    data, errors = _payload(value)
    name = _required_text(data, "name", errors, label="Numele", maximum=120)
    email = _required_text(data, "email", errors, label="Emailul", maximum=254, lower=True)
    password = str(data.get("password") or "")
    age_confirmed = _boolean(data.get("ageConfirmed"))
    accepted_terms = _boolean(data.get("acceptedTerms"))
    invite_code = _normalize_invite_code(data.get("inviteCode") or data.get("invite_code"))

    if email and not EMAIL_PATTERN.fullmatch(email):
        errors.append(_issue("email", "invalid_email", "Introdu o adresă de email validă."))
    if not password:
        errors.append(_issue("password", "required", "Parola este obligatorie."))
    elif len(password) < password_min_length:
        errors.append(
            _issue(
                "password",
                "password_too_short",
                f"Parola trebuie să aibă minimum {password_min_length} caractere.",
            )
        )
    if not age_confirmed:
        errors.append(
            _issue(
                "ageConfirmed",
                "age_confirmation_required",
                "Confirmă vârsta minimă sau acordul părintelui/tutorelui.",
            )
        )
    if not accepted_terms:
        errors.append(
            _issue(
                "acceptedTerms",
                "terms_required",
                "Trebuie să accepți Termenii și Politica de confidențialitate.",
            )
        )

    return ValidationResult(
        {
            "name": name,
            "email": email,
            "password": password,
            "ageConfirmed": age_confirmed,
            "acceptedTerms": accepted_terms,
            "inviteCode": invite_code,
        },
        tuple(errors),
    )


def validate_login_payload(value: Any) -> ValidationResult:
    data, errors = _payload(value)
    email = _required_text(data, "email", errors, label="Emailul", maximum=254, lower=True)
    password = str(data.get("password") or "")
    if not password:
        errors.append(_issue("password", "required", "Parola este obligatorie."))
    return ValidationResult({"email": email, "password": password}, tuple(errors))


def validate_email_payload(value: Any) -> ValidationResult:
    """Validate forgot-password and resend-verification payloads."""

    data, errors = _payload(value)
    email = _required_text(data, "email", errors, label="Emailul", maximum=254, lower=True)
    if email and not EMAIL_PATTERN.fullmatch(email):
        errors.append(_issue("email", "invalid_email", "Introdu o adresă de email validă."))
    return ValidationResult({"email": email}, tuple(errors))


def validate_token_payload(value: Any) -> ValidationResult:
    data, errors = _payload(value)
    token = _required_text(data, "token", errors, label="Tokenul", maximum=4096)
    return ValidationResult({"token": token}, tuple(errors))


def validate_reset_password_payload(
    value: Any,
    *,
    password_min_length: int = 12,
) -> ValidationResult:
    data, errors = _payload(value)
    token = _required_text(data, "token", errors, label="Tokenul", maximum=4096)
    password = str(data.get("password") or "")
    if not password:
        errors.append(_issue("password", "required", "Parola nouă este obligatorie."))
    elif len(password) < password_min_length:
        errors.append(
            _issue(
                "password",
                "password_too_short",
                f"Parola trebuie să aibă minimum {password_min_length} caractere.",
            )
        )
    return ValidationResult({"token": token, "password": password}, tuple(errors))


def validate_subscription_checkout_payload(value: Any) -> ValidationResult:
    data, errors = _payload(value)
    plan = _text(data.get("plan") or "pro", lower=True)
    raw_interval = _text(data.get("billingInterval") or data.get("interval") or "monthly", lower=True)
    billing_interval = "yearly" if raw_interval in {"yearly", "annual", "year", "an"} else "monthly"
    if plan not in SUBSCRIPTION_PLANS:
        errors.append(_issue("plan", "invalid_choice", "Plan invalid."))
    return ValidationResult(
        {"plan": plan, "billingInterval": billing_interval},
        tuple(errors),
    )


def validate_cecoin_checkout_payload(value: Any) -> ValidationResult:
    data, errors = _payload(value)
    pack_id = _text(data.get("packId"), lower=True)
    if not pack_id:
        errors.append(_issue("packId", "required", "Pachetul CeCoins este obligatoriu."))
    elif pack_id not in CECOIN_PACKS:
        errors.append(_issue("packId", "invalid_choice", "Pachet CeCoins invalid."))
    return ValidationResult({"packId": pack_id}, tuple(errors))


def validate_checkout_sync_payload(value: Any) -> ValidationResult:
    data, errors = _payload(value)
    session_id = _required_text(data, "sessionId", errors, label="Sesiunea Stripe", maximum=255)
    if session_id and not session_id.startswith("cs_"):
        errors.append(
            _issue("sessionId", "invalid_stripe_session", "Sesiunea Stripe este invalidă.")
        )
    return ValidationResult({"sessionId": session_id}, tuple(errors))


def validate_analytics_payload(
    value: Any,
    *,
    allowed_events: Iterable[str] = DEFAULT_ANALYTICS_EVENTS,
) -> ValidationResult:
    data, errors = _payload(value)
    name = _normalize_event_name(data.get("name"))
    allowed = frozenset(str(event) for event in allowed_events)
    raw_metadata = data.get("metadata")
    metadata = raw_metadata if isinstance(raw_metadata, Mapping) else {}
    safe_metadata = {
        str(key)[:50]: str(item)[:250]
        for key, item in metadata.items()
        if item is not None
    }
    return ValidationResult(
        {
            "name": name,
            "metadata": safe_metadata,
            "ignored": name not in allowed,
        },
        tuple(errors),
    )


def validate_support_payload(value: Any) -> ValidationResult:
    data, errors = _payload(value)
    email = _required_text(data, "email", errors, label="Emailul", maximum=254, lower=True)
    topic = _optional_text(data, "topic", errors, label="Subiectul", maximum=120) or "Suport"
    message = _required_text(
        data,
        "message",
        errors,
        label="Mesajul",
        minimum=10,
        maximum=4000,
    )
    if email and not EMAIL_PATTERN.fullmatch(email):
        errors.append(_issue("email", "invalid_email", "Introdu o adresă de email validă."))
    return ValidationResult(
        {"email": email, "topic": topic, "message": message},
        tuple(errors),
    )


def _normalized_product(value: Any) -> dict[str, Any]:
    product = value if isinstance(value, Mapping) else {}
    return {
        "id": product.get("id"),
        "name": _text(product.get("name"))[:160],
        "barcode": _text(product.get("barcode"))[:80],
        "brand": _text(product.get("brand"))[:120],
        "store": _text(product.get("store"))[:100],
        "category": _text(product.get("category"))[:120],
        "score": product.get("score"),
        "price": product.get("price"),
        "image": _text(product.get("image"))[:255],
        "source": _text(product.get("source"))[:80],
    }


def validate_alternative_feedback_payload(value: Any) -> ValidationResult:
    data, errors = _payload(value)
    product = _normalized_product(data.get("product"))
    scanned_product = _normalized_product(data.get("scannedProduct"))
    store = _optional_text(data, "store", errors, label="Magazinul", maximum=100)
    request_text = _optional_text(data, "request", errors, label="Cerința", maximum=250)
    reason = _optional_text(data, "reason", errors, label="Motivul", maximum=80) or "wrong_recommendation"
    if not product["name"]:
        errors.append(
            _issue(
                "product.name",
                "required",
                "Alternativa raportată nu este validă.",
            )
        )
    return ValidationResult(
        {
            "product": product,
            "scannedProduct": scanned_product,
            "store": store,
            "request": request_text,
            "reason": reason,
        },
        tuple(errors),
    )


def validate_product_feedback_payload(value: Any) -> ValidationResult:
    data, errors = _payload(value)
    product = _normalized_product(data.get("product"))
    store = _optional_text(data, "store", errors, label="Magazinul", maximum=100) or product["store"]
    reason = _text(data.get("reason") or "other", lower=True)
    details = _optional_text(data, "details", errors, label="Detaliile", maximum=1000)
    source = _optional_text(data, "source", errors, label="Sursa", maximum=80) or "result"
    if reason not in PRODUCT_REPORT_REASONS:
        reason = "other"
    if not product["name"] and not product["barcode"]:
        errors.append(
            _issue("product", "required", "Produsul raportat nu este valid.")
        )
    return ValidationResult(
        {
            "product": product,
            "store": store,
            "reason": reason,
            "details": details,
            "source": source,
        },
        tuple(errors),
    )


def validate_product_search_query(value: Any) -> ValidationResult:
    data, errors = _payload(value)
    query = _required_text(data, "q", errors, label="Parametrul q", maximum=250)
    store = _optional_text(data, "store", errors, label="Magazinul", maximum=100)
    return ValidationResult({"q": query, "store": store}, tuple(errors))


def validate_barcode_import_payload(value: Any) -> ValidationResult:
    data, errors = _payload(value)
    barcode, barcode_errors = validate_barcode_value(data.get("barcode"), required=True)
    errors.extend(barcode_errors)
    return ValidationResult({"barcode": barcode}, tuple(errors))


def validate_alternatives_payload(value: Any) -> ValidationResult:
    data, errors = _payload(value)
    product = _normalized_product(data.get("product"))
    raw_preferences = data.get("preferences")
    preferences = dict(raw_preferences) if isinstance(raw_preferences, Mapping) else {}
    raw_criteria = data.get("criteria")
    criteria: list[str] = []
    if isinstance(raw_criteria, list):
        for item in raw_criteria:
            criterion = _text(item)
            if criterion and criterion not in criteria:
                criteria.append(criterion[:80])
    request_text = _optional_text(data, "request", errors, label="Cerința", maximum=500)
    if not product["name"] and not product["barcode"]:
        errors.append(_issue("product", "required", "Produsul scanat este obligatoriu."))
    return ValidationResult(
        {
            "product": product,
            "preferences": preferences,
            "criteria": criteria,
            "request": request_text,
        },
        tuple(errors),
    )


def validate_analysis_form(value: Any) -> ValidationResult:
    """Normalize non-file fields accepted by the multipart /analyze route."""

    data, errors = _payload(value)
    store = _optional_text(data, "store", errors, label="Magazinul", maximum=100) or "any"
    product_query = _optional_text(data, "product_query", errors, label="Produsul", maximum=250)
    label_text = _optional_text(data, "label_text", errors, label="Textul etichetei", maximum=2000)
    selected_barcode, barcode_errors = validate_barcode_value(data.get("selected_barcode"))
    errors.extend(barcode_errors)
    demo_product_id = _text(data.get("demo_product_id"))
    if demo_product_id and not demo_product_id.isdigit():
        errors.append(
            _issue("demo_product_id", "invalid_integer", "Produsul demo este invalid.")
        )
    return ValidationResult(
        {
            "store": store,
            "product_query": product_query or label_text,
            "label_text": label_text,
            "selected_barcode": selected_barcode,
            "demo_product_id": int(demo_product_id) if demo_product_id.isdigit() else None,
        },
        tuple(errors),
    )


def validate_product_submission_payload(value: Any) -> ValidationResult:
    """Validate text/form fields for multipart product submissions.

    Uploaded images remain the route's responsibility because this module does
    not depend on Flask's ``FileStorage`` type.
    """

    data, errors = _payload(value)
    raw_user_id = data.get("user_id")
    try:
        user_id = int(raw_user_id)
        if user_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        user_id = None
        errors.append(
            _issue("user_id", "invalid_integer", "user_id trebuie să fie un număr valid.")
        )

    product_name = _required_text(
        data,
        "product_name",
        errors,
        label="Numele produsului",
        minimum=2,
        maximum=150,
    )
    store = _required_text(
        data,
        "store",
        errors,
        label="Magazinul",
        minimum=2,
        maximum=100,
    )
    category = _optional_text(data, "category", errors, label="Categoria", maximum=100)
    quantity = _optional_text(data, "quantity", errors, label="Cantitatea", maximum=100)
    brand = _optional_text(data, "brand", errors, label="Brandul", maximum=100)
    price = _optional_text(data, "price", errors, label="Prețul", maximum=100)
    ingredients = _optional_text(
        data,
        "ingredients",
        errors,
        label="Ingredientele",
        maximum=5000,
    )
    barcode, barcode_errors = validate_barcode_value(data.get("barcode"))
    errors.extend(barcode_errors)

    nutrition: dict[str, float | None] = {}
    nutrition_limits = {
        "calories": ("Caloriile", 1000.0),
        "protein": ("Proteina", 100.0),
        "sugar": ("Zahărul", 100.0),
        "fat": ("Grăsimile", 100.0),
    }
    for field, (label, maximum) in nutrition_limits.items():
        raw_value = data.get(field)
        parsed = _finite_float(raw_value)
        nutrition[field] = parsed
        if raw_value not in {None, ""} and parsed is None:
            errors.append(
                _issue(field, "invalid_number", f"{label} trebuie să fie un număr valid.")
            )
        elif parsed is not None and not 0 <= parsed <= maximum:
            errors.append(
                _issue(
                    field,
                    "out_of_range",
                    f"{label} trebuie să fie între 0 și {maximum:g} per 100 g/ml.",
                )
            )

    normalized = {
        "user_id": user_id,
        "product_name": product_name,
        "store": store,
        "category": category,
        "quantity": quantity,
        "barcode": barcode,
        "brand": brand,
        "price": price,
        "ingredients": ingredients,
        **nutrition,
    }
    return ValidationResult(normalized, tuple(errors))


VALIDATORS: dict[str, Callable[..., ValidationResult]] = {
    "register": validate_register_payload,
    "login": validate_login_payload,
    "email": validate_email_payload,
    "token": validate_token_payload,
    "reset_password": validate_reset_password_payload,
    "subscription_checkout": validate_subscription_checkout_payload,
    "cecoin_checkout": validate_cecoin_checkout_payload,
    "checkout_sync": validate_checkout_sync_payload,
    "analytics": validate_analytics_payload,
    "support": validate_support_payload,
    "alternative_feedback": validate_alternative_feedback_payload,
    "product_feedback": validate_product_feedback_payload,
    "product_search": validate_product_search_query,
    "barcode_import": validate_barcode_import_payload,
    "alternatives": validate_alternatives_payload,
    "analysis": validate_analysis_form,
    "product_submission": validate_product_submission_payload,
}


def validate_payload(kind: str, value: Any, **options: Any) -> ValidationResult:
    """Dispatch to a named validator for route-level integration."""

    try:
        validator = VALIDATORS[kind]
    except KeyError as error:
        raise ValueError(f"Unknown payload validator: {kind}") from error
    return validator(value, **options)

