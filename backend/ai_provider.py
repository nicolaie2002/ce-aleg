import base64
import os

import requests


class VisionProviderError(RuntimeError):
    pass


class VisionProviderNotConfigured(VisionProviderError):
    pass


def extract_response_text(payload):
    direct_text = payload.get("output_text")
    if direct_text:
        return str(direct_text)

    for output_item in payload.get("output") or []:
        for content_item in output_item.get("content") or []:
            text = content_item.get("text") or content_item.get("output_text")
            if text:
                return str(text)

    raise VisionProviderError("Vision provider returned no text output.")


class OpenAIVisionProvider:
    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        self.model = os.environ.get("OPENAI_VISION_MODEL", "gpt-4.1-mini").strip()
        self.timeout = max(5, min(int(os.environ.get("OPENAI_VISION_TIMEOUT", "20")), 60))

    @property
    def configured(self):
        return bool(self.api_key)

    def analyze(self, image_bytes, mime_type, prompt):
        if not self.configured:
            raise VisionProviderNotConfigured("OPENAI_API_KEY is missing.")

        image_base64 = base64.b64encode(image_bytes).decode("ascii")

        try:
            response = requests.post(
                "https://api.openai.com/v1/responses",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": [{
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            {
                                "type": "input_image",
                                "image_url": f"data:{mime_type};base64,{image_base64}",
                                "detail": "low",
                            },
                        ],
                    }],
                },
                timeout=(3.5, self.timeout),
            )
            response.raise_for_status()
            return extract_response_text(response.json())
        except (requests.RequestException, ValueError) as error:
            raise VisionProviderError(str(error)) from error


def get_vision_provider():
    provider_name = os.environ.get("VISION_PROVIDER", "openai").strip().lower()

    if provider_name == "openai":
        return OpenAIVisionProvider()

    raise VisionProviderNotConfigured(f"Unknown VISION_PROVIDER: {provider_name}")
