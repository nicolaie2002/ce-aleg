"""Provider-neutral product identification from a retail product image.

The module has no Flask or database dependency. Providers return one validated
domain object, so route code never has to trust provider-specific JSON.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import base64
from dataclasses import dataclass
import json
import os
import re
from typing import Any, Mapping

import requests


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
DEFAULT_TIMEOUT_SECONDS = 20.0
MIN_TIMEOUT_SECONDS = 3.0
MAX_TIMEOUT_SECONDS = 60.0
MAX_IMAGE_BYTES = 4 * 1024 * 1024
MAX_PROMPT_LENGTH = 5_000
MAX_RESPONSE_TEXT_LENGTH = 8_192
SUPPORTED_IMAGE_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
BARCODE_PATTERN = re.compile(r"^\d{8}$|^\d{12,14}$")
MODEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")

DEFAULT_IDENTIFICATION_PROMPT = (
    "Identify the main retail product visible in the image. Do not guess text "
    "that is not legible. Use null for unknown product details and set "
    "identified to false when the product cannot be identified reliably."
)

_RESULT_FIELDS = frozenset(
    {
        "identified",
        "product_name",
        "brand",
        "variant",
        "barcode",
        "confidence",
        "needs_barcode",
        "message",
    }
)

_PRODUCT_IDENTIFICATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "identified": {"type": "boolean"},
        "product_name": {"type": ["string", "null"], "maxLength": 150},
        "brand": {"type": ["string", "null"], "maxLength": 100},
        "variant": {"type": ["string", "null"], "maxLength": 100},
        "barcode": {
            "type": ["string", "null"],
            "pattern": r"^(\d{8}|\d{12,14})$",
        },
        "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
        "needs_barcode": {"type": "boolean"},
        "message": {"type": ["string", "null"], "maxLength": 240},
    },
    "required": sorted(_RESULT_FIELDS),
}


class ProductIdentificationError(RuntimeError):
    """Base error safe for route-level handling."""


class ProductIdentificationNotConfigured(ProductIdentificationError):
    """The selected provider cannot run with the available configuration."""


class ProductIdentificationInputError(ProductIdentificationError):
    """The caller supplied an invalid image, MIME type, or prompt."""


class ProductIdentificationTimeout(ProductIdentificationError):
    """The provider did not answer within the configured deadline."""


class ProductIdentificationRequestError(ProductIdentificationError):
    """The provider rejected the request or was unavailable."""


class ProductIdentificationResponseError(ProductIdentificationError):
    """The provider returned malformed or unsafe output."""


# Compatibility names let app.py migrate by changing only its import module.
VisionProviderError = ProductIdentificationError
VisionProviderNotConfigured = ProductIdentificationNotConfigured


@dataclass(frozen=True, slots=True)
class ProductIdentification:
    identified: bool
    product_name: str | None
    brand: str | None
    variant: str | None
    barcode: str | None
    confidence: int
    needs_barcode: bool
    message: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "identified": self.identified,
            "product_name": self.product_name,
            "brand": self.brand,
            "variant": self.variant,
            "barcode": self.barcode,
            "confidence": self.confidence,
            "needs_barcode": self.needs_barcode,
            "message": self.message,
        }


class ProductIdentificationProvider(ABC):
    """Interface implemented by every image identification provider."""

    @property
    @abstractmethod
    def configured(self) -> bool:
        """Return whether the provider can currently serve requests."""

    @abstractmethod
    def identify(
        self,
        image_bytes: bytes,
        mime_type: str,
        prompt: str | None = None,
    ) -> ProductIdentification:
        """Identify a product and return provider-neutral validated data."""

    def analyze(self, image_bytes: bytes, mime_type: str, prompt: str) -> str:
        """Compatibility adapter for the existing identify_product_frame route."""

        return json.dumps(
            self.identify(image_bytes, mime_type, prompt).to_dict(),
            ensure_ascii=False,
            separators=(",", ":"),
        )


class DisabledProductIdentificationProvider(ProductIdentificationProvider):
    @property
    def configured(self) -> bool:
        return False

    def identify(
        self,
        image_bytes: bytes,
        mime_type: str,
        prompt: str | None = None,
    ) -> ProductIdentification:
        del image_bytes, mime_type, prompt
        raise ProductIdentificationNotConfigured(
            "Product image identification is disabled."
        )


class LocalFallbackProductIdentificationProvider(ProductIdentificationProvider):
    """Safe no-network fallback that asks the scanner to use the barcode."""

    @property
    def configured(self) -> bool:
        return True

    def identify(
        self,
        image_bytes: bytes,
        mime_type: str,
        prompt: str | None = None,
    ) -> ProductIdentification:
        _validate_input(image_bytes, mime_type, prompt)
        return ProductIdentification(
            identified=False,
            product_name=None,
            brand=None,
            variant=None,
            barcode=None,
            confidence=0,
            needs_barcode=True,
            message="Arată codul de bare pentru identificarea sigură a produsului.",
        )


class OpenAIResponsesProductIdentificationProvider(ProductIdentificationProvider):
    """OpenAI Responses API provider with strict Structured Outputs."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float | str | None = None,
        http_client: Any = None,
    ) -> None:
        self._api_key = (
            os.environ.get("OPENAI_API_KEY", "") if api_key is None else api_key
        ).strip()
        configured_model = (
            os.environ.get("OPENAI_VISION_MODEL", DEFAULT_OPENAI_MODEL)
            if model is None
            else model
        ).strip()
        self._model = _validate_model(configured_model)
        configured_timeout = (
            os.environ.get("OPENAI_VISION_TIMEOUT", str(DEFAULT_TIMEOUT_SECONDS))
            if timeout_seconds is None
            else timeout_seconds
        )
        self._timeout_seconds = _normalize_timeout(configured_timeout)
        self._http_client = http_client or requests

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    def identify(
        self,
        image_bytes: bytes,
        mime_type: str,
        prompt: str | None = None,
    ) -> ProductIdentification:
        if not self.configured:
            raise ProductIdentificationNotConfigured(
                "OPENAI_API_KEY is not configured."
            )

        normalized_mime, normalized_prompt = _validate_input(
            image_bytes, mime_type, prompt
        )
        image_base64 = base64.b64encode(image_bytes).decode("ascii")
        request_payload = {
            "model": self._model,
            "store": False,
            "max_output_tokens": 350,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": normalized_prompt},
                        {
                            "type": "input_image",
                            "image_url": (
                                f"data:{normalized_mime};base64,{image_base64}"
                            ),
                            "detail": "low",
                        },
                    ],
                }
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "product_identification",
                    "strict": True,
                    "schema": _PRODUCT_IDENTIFICATION_SCHEMA,
                }
            },
        }

        try:
            response = self._http_client.post(
                OPENAI_RESPONSES_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=request_payload,
                timeout=(3.5, self._timeout_seconds),
            )
        except requests.Timeout:
            raise ProductIdentificationTimeout(
                "Product identification provider timed out."
            ) from None
        except requests.RequestException:
            raise ProductIdentificationRequestError(
                "Product identification provider is unavailable."
            ) from None

        if not 200 <= int(getattr(response, "status_code", 0)) < 300:
            raise ProductIdentificationRequestError(
                "Product identification provider rejected the request."
            )

        try:
            response_payload = response.json()
        except (TypeError, ValueError):
            raise ProductIdentificationResponseError(
                "Product identification provider returned invalid JSON."
            ) from None

        output_text = _extract_response_text(response_payload)
        return parse_product_identification(output_text)


def create_product_identification_provider(
    provider_name: str | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    http_client: Any = None,
) -> ProductIdentificationProvider:
    """Build the configured provider without importing application state."""

    environment = os.environ if environ is None else environ
    selected = (
        environment.get("VISION_PROVIDER", "openai")
        if provider_name is None
        else provider_name
    ).strip().lower()

    if selected == "openai":
        return OpenAIResponsesProductIdentificationProvider(
            api_key=environment.get("OPENAI_API_KEY", ""),
            model=environment.get("OPENAI_VISION_MODEL", DEFAULT_OPENAI_MODEL),
            timeout_seconds=environment.get(
                "OPENAI_VISION_TIMEOUT", str(DEFAULT_TIMEOUT_SECONDS)
            ),
            http_client=http_client,
        )
    if selected in {"local", "fallback", "local_fallback"}:
        return LocalFallbackProductIdentificationProvider()
    if selected in {"", "disabled", "none", "off"}:
        return DisabledProductIdentificationProvider()

    raise ProductIdentificationNotConfigured(
        "The selected product identification provider is not supported."
    )


def get_product_identification_provider() -> ProductIdentificationProvider:
    return create_product_identification_provider()


def get_vision_provider() -> ProductIdentificationProvider:
    """Compatibility factory for the current app.py integration."""

    return get_product_identification_provider()


def parse_product_identification(value: str | Mapping[str, Any]) -> ProductIdentification:
    """Strictly validate untrusted provider output."""

    if isinstance(value, str):
        if not value or len(value) > MAX_RESPONSE_TEXT_LENGTH:
            raise ProductIdentificationResponseError(
                "Product identification response has an invalid length."
            )
        try:
            raw = json.loads(
                value,
                object_pairs_hook=_unique_object,
                parse_constant=_reject_json_constant,
            )
        except (TypeError, ValueError, json.JSONDecodeError):
            raise ProductIdentificationResponseError(
                "Product identification response is not valid JSON."
            ) from None
    elif isinstance(value, Mapping):
        raw = dict(value)
    else:
        raise ProductIdentificationResponseError(
            "Product identification response must be a JSON object."
        )

    if not isinstance(raw, dict):
        raise ProductIdentificationResponseError(
            "Product identification response must be a JSON object."
        )

    fields = set(raw)
    if fields != _RESULT_FIELDS:
        raise ProductIdentificationResponseError(
            "Product identification response has unexpected or missing fields."
        )

    identified = _strict_boolean(raw["identified"], "identified")
    product_name = _optional_string(raw["product_name"], "product_name", 150)
    brand = _optional_string(raw["brand"], "brand", 100)
    variant = _optional_string(raw["variant"], "variant", 100)
    barcode = _validate_barcode(raw["barcode"])
    confidence = _validate_confidence(raw["confidence"])
    needs_barcode = _strict_boolean(raw["needs_barcode"], "needs_barcode")
    message = _optional_string(raw["message"], "message", 240)

    if identified and not product_name and not barcode:
        raise ProductIdentificationResponseError(
            "An identified product requires a product name or valid barcode."
        )

    return ProductIdentification(
        identified=identified,
        product_name=product_name,
        brand=brand,
        variant=variant,
        barcode=barcode,
        confidence=confidence,
        needs_barcode=needs_barcode,
        message=message,
    )


def _validate_input(
    image_bytes: bytes,
    mime_type: str,
    prompt: str | None,
) -> tuple[str, str]:
    if not isinstance(image_bytes, bytes) or not image_bytes:
        raise ProductIdentificationInputError("Image bytes are required.")
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise ProductIdentificationInputError("Image exceeds the provider limit.")

    normalized_mime = str(mime_type or "").strip().lower()
    if normalized_mime not in SUPPORTED_IMAGE_TYPES:
        raise ProductIdentificationInputError("Unsupported image MIME type.")

    normalized_prompt = (
        DEFAULT_IDENTIFICATION_PROMPT if prompt is None else str(prompt).strip()
    )
    if not normalized_prompt or len(normalized_prompt) > MAX_PROMPT_LENGTH:
        raise ProductIdentificationInputError("Prompt has an invalid length.")

    return normalized_mime, normalized_prompt


def _validate_model(value: str) -> str:
    if not MODEL_PATTERN.fullmatch(value):
        raise ProductIdentificationNotConfigured(
            "OPENAI_VISION_MODEL has an invalid value."
        )
    return value


def _normalize_timeout(value: float | str) -> float:
    try:
        timeout = float(value)
    except (TypeError, ValueError):
        timeout = DEFAULT_TIMEOUT_SECONDS
    if timeout != timeout or timeout in {float("inf"), float("-inf")}:
        timeout = DEFAULT_TIMEOUT_SECONDS
    return max(MIN_TIMEOUT_SECONDS, min(timeout, MAX_TIMEOUT_SECONDS))


def _extract_response_text(payload: Any) -> str:
    if not isinstance(payload, Mapping):
        raise ProductIdentificationResponseError(
            "Product identification provider returned an invalid envelope."
        )

    status = payload.get("status")
    if status and status != "completed":
        raise ProductIdentificationResponseError(
            "Product identification provider did not complete the response."
        )

    direct_text = payload.get("output_text")
    if isinstance(direct_text, str) and direct_text:
        return direct_text

    output = payload.get("output")
    if not isinstance(output, list):
        raise ProductIdentificationResponseError(
            "Product identification provider returned no text output."
        )

    for output_item in output:
        if not isinstance(output_item, Mapping):
            continue
        content = output_item.get("content")
        if not isinstance(content, list):
            continue
        for content_item in content:
            if not isinstance(content_item, Mapping):
                continue
            text = content_item.get("text") or content_item.get("output_text")
            if isinstance(text, str) and text:
                return text

    raise ProductIdentificationResponseError(
        "Product identification provider returned no text output."
    )


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key.")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"Invalid JSON constant: {value}")


def _strict_boolean(value: Any, field: str) -> bool:
    if type(value) is not bool:
        raise ProductIdentificationResponseError(f"{field} must be a boolean.")
    return value


def _optional_string(value: Any, field: str, maximum: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ProductIdentificationResponseError(f"{field} must be text or null.")
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > maximum or any(ord(character) < 32 for character in normalized):
        raise ProductIdentificationResponseError(f"{field} contains invalid text.")
    return normalized


def _validate_barcode(value: Any) -> str | None:
    barcode = _optional_string(value, "barcode", 14)
    if barcode is None:
        return None
    if not BARCODE_PATTERN.fullmatch(barcode) or not _has_valid_gtin_checksum(barcode):
        raise ProductIdentificationResponseError("barcode must be a valid GTIN.")
    return barcode


def _has_valid_gtin_checksum(barcode: str) -> bool:
    digits = [int(character) for character in barcode]
    check_digit = digits.pop()
    weighted_sum = sum(
        digit * (3 if position % 2 == 0 else 1)
        for position, digit in enumerate(reversed(digits))
    )
    return (10 - weighted_sum % 10) % 10 == check_digit


def _validate_confidence(value: Any) -> int:
    if type(value) is not int or not 0 <= value <= 100:
        raise ProductIdentificationResponseError(
            "confidence must be an integer between 0 and 100."
        )
    return value


__all__ = [
    "DisabledProductIdentificationProvider",
    "LocalFallbackProductIdentificationProvider",
    "OpenAIResponsesProductIdentificationProvider",
    "ProductIdentification",
    "ProductIdentificationError",
    "ProductIdentificationInputError",
    "ProductIdentificationNotConfigured",
    "ProductIdentificationProvider",
    "ProductIdentificationRequestError",
    "ProductIdentificationResponseError",
    "ProductIdentificationTimeout",
    "VisionProviderError",
    "VisionProviderNotConfigured",
    "create_product_identification_provider",
    "get_product_identification_provider",
    "get_vision_provider",
    "parse_product_identification",
]
