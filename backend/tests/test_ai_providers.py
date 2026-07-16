import json

import pytest
import requests

from ai_providers import (
    DisabledProductIdentificationProvider,
    LocalFallbackProductIdentificationProvider,
    OpenAIResponsesProductIdentificationProvider,
    ProductIdentificationInputError,
    ProductIdentificationNotConfigured,
    ProductIdentificationRequestError,
    ProductIdentificationResponseError,
    ProductIdentificationTimeout,
    create_product_identification_provider,
    parse_product_identification,
)


VALID_RESULT = {
    "identified": True,
    "product_name": "Iaurt natural",
    "brand": "Exemplu",
    "variant": None,
    "barcode": "4006381333931",
    "confidence": 91,
    "needs_barcode": False,
    "message": "Produs identificat.",
}


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload


class FakeHttpClient:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error:
            raise self.error
        return self.response


def test_openai_provider_uses_responses_structured_output_and_timeout():
    response_payload = {
        "status": "completed",
        "output": [
            {
                "content": [
                    {"type": "output_text", "text": json.dumps(VALID_RESULT)}
                ]
            }
        ],
    }
    client = FakeHttpClient(FakeResponse(response_payload))
    provider = OpenAIResponsesProductIdentificationProvider(
        api_key="secret-test-key",
        model="gpt-4.1-mini",
        timeout_seconds=12,
        http_client=client,
    )

    result = provider.identify(b"jpeg-data", "image/jpeg", "Identify the product.")

    assert result.to_dict() == VALID_RESULT
    assert len(client.calls) == 1
    url, request = client.calls[0]
    assert url == "https://api.openai.com/v1/responses"
    assert request["timeout"] == (3.5, 12.0)
    assert request["json"]["store"] is False
    assert request["json"]["text"]["format"]["type"] == "json_schema"
    assert request["json"]["text"]["format"]["strict"] is True
    image_url = request["json"]["input"][0]["content"][1]["image_url"]
    assert image_url.startswith("data:image/jpeg;base64,")


def test_compatibility_analyze_returns_validated_json():
    client = FakeHttpClient(
        FakeResponse({"status": "completed", "output_text": json.dumps(VALID_RESULT)})
    )
    provider = OpenAIResponsesProductIdentificationProvider(
        api_key="secret-test-key", http_client=client
    )

    output = provider.analyze(b"image", "image/jpeg", "Identify.")

    assert json.loads(output) == VALID_RESULT


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("product_name", "x" * 151),
        ("barcode", "12345678"),
        ("barcode", "400638133393"),
        ("confidence", -1),
        ("confidence", 101),
        ("confidence", 90.5),
        ("identified", 1),
    ],
)
def test_response_validation_rejects_invalid_fields(field, value):
    payload = {**VALID_RESULT, field: value}

    with pytest.raises(ProductIdentificationResponseError):
        parse_product_identification(payload)


def test_response_validation_rejects_missing_extra_duplicate_and_non_finite_data():
    missing = {key: value for key, value in VALID_RESULT.items() if key != "brand"}
    extra = {**VALID_RESULT, "raw_provider_data": "not allowed"}
    duplicate = (
        '{"identified":true,"identified":false,"product_name":"Test",'
        '"brand":null,"variant":null,"barcode":"4006381333931",'
        '"confidence":90,"needs_barcode":false,"message":null}'
    )
    non_finite = json.dumps({**VALID_RESULT, "confidence": float("nan")})

    for payload in (missing, extra, duplicate, non_finite):
        with pytest.raises(ProductIdentificationResponseError):
            parse_product_identification(payload)


def test_identified_result_requires_name_or_barcode():
    payload = {**VALID_RESULT, "product_name": None, "barcode": None}

    with pytest.raises(ProductIdentificationResponseError):
        parse_product_identification(payload)


def test_local_fallback_is_deterministic_and_never_uses_network():
    provider = create_product_identification_provider("local")

    assert isinstance(provider, LocalFallbackProductIdentificationProvider)
    result = provider.identify(b"image", "image/jpeg")
    assert result.identified is False
    assert result.confidence == 0
    assert result.needs_barcode is True


def test_disabled_and_unknown_provider_fail_closed():
    disabled = create_product_identification_provider("disabled")

    assert isinstance(disabled, DisabledProductIdentificationProvider)
    assert disabled.configured is False
    with pytest.raises(ProductIdentificationNotConfigured):
        disabled.identify(b"image", "image/jpeg")
    with pytest.raises(ProductIdentificationNotConfigured):
        create_product_identification_provider("unexpected-provider")


def test_factory_uses_existing_openai_environment_names():
    provider = create_product_identification_provider(
        environ={
            "VISION_PROVIDER": "openai",
            "OPENAI_API_KEY": "configured-test-key",
            "OPENAI_VISION_MODEL": "gpt-4.1-mini",
            "OPENAI_VISION_TIMEOUT": "9",
        },
        http_client=FakeHttpClient(),
    )

    assert isinstance(provider, OpenAIResponsesProductIdentificationProvider)
    assert provider.configured is True


def test_timeout_and_request_errors_are_typed_without_sensitive_data():
    image = b"sensitive-image-bytes"
    api_key = "sensitive-api-key"

    timeout_provider = OpenAIResponsesProductIdentificationProvider(
        api_key=api_key,
        http_client=FakeHttpClient(error=requests.Timeout("upstream timeout")),
    )
    with pytest.raises(ProductIdentificationTimeout) as timeout_error:
        timeout_provider.identify(image, "image/jpeg")

    request_provider = OpenAIResponsesProductIdentificationProvider(
        api_key=api_key,
        http_client=FakeHttpClient(
            error=requests.RequestException(
                f"request failed with {api_key} and {image.decode()}"
            )
        ),
    )
    with pytest.raises(ProductIdentificationRequestError) as request_error:
        request_provider.identify(image, "image/jpeg")

    combined_errors = f"{timeout_error.value} {request_error.value}"
    assert api_key not in combined_errors
    assert image.decode() not in combined_errors


@pytest.mark.parametrize(
    ("image", "mime_type", "prompt"),
    [
        (b"", "image/jpeg", None),
        (b"image", "text/html", None),
        (b"image", "image/jpeg", ""),
        (b"image", "image/jpeg", "x" * 5_001),
    ],
)
def test_provider_rejects_invalid_input_before_network(image, mime_type, prompt):
    client = FakeHttpClient()
    provider = OpenAIResponsesProductIdentificationProvider(
        api_key="configured-test-key", http_client=client
    )

    with pytest.raises(ProductIdentificationInputError):
        provider.identify(image, mime_type, prompt)

    assert client.calls == []


def test_provider_rejects_http_and_incomplete_responses():
    rejected = OpenAIResponsesProductIdentificationProvider(
        api_key="configured-test-key",
        http_client=FakeHttpClient(FakeResponse({}, status_code=429)),
    )
    incomplete = OpenAIResponsesProductIdentificationProvider(
        api_key="configured-test-key",
        http_client=FakeHttpClient(
            FakeResponse({"status": "incomplete", "output_text": "{}"})
        ),
    )

    with pytest.raises(ProductIdentificationRequestError):
        rejected.identify(b"image", "image/jpeg")
    with pytest.raises(ProductIdentificationResponseError):
        incomplete.identify(b"image", "image/jpeg")
