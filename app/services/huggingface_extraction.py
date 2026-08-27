import json
import os
from collections.abc import Callable
from typing import Any

import httpx
from pydantic import ValidationError

from app.models.natural_language_procurement import (
    ExtractedProcurementFields,
    NaturalLanguageProcurementResponse,
)
from app.models.procurement_request import ProcurementRequest, ProductSpecifications


DEFAULT_MODEL = "openai/gpt-oss-20b:groq"
DEFAULT_TIMEOUT_SECONDS = 20.0
REQUIRED_FIELDS = ("product", "condition", "quantity", "quoted_price")


class HuggingFaceNotConfiguredError(RuntimeError):
    pass


class HuggingFaceExtractionError(RuntimeError):
    pass


class HuggingFaceTimeoutError(RuntimeError):
    pass


def _get_timeout_seconds() -> float:
    raw_value = os.getenv("HF_INFERENCE_TIMEOUT_SECONDS")
    if raw_value is None:
        return DEFAULT_TIMEOUT_SECONDS
    try:
        timeout = float(raw_value)
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS
    return timeout if timeout > 0 else DEFAULT_TIMEOUT_SECONDS


def _create_client(token: str) -> Any:
    from huggingface_hub import InferenceClient

    return InferenceClient(
        provider="auto",
        api_key=token,
        timeout=_get_timeout_seconds(),
    )


def extract_procurement_request(
    text: str,
    *,
    client_factory: Callable[[str], Any] = _create_client,
) -> NaturalLanguageProcurementResponse:
    """Extract user-stated facts; absent information must remain null."""
    token = os.getenv("HF_TOKEN")
    if not token:
        raise HuggingFaceNotConfiguredError(
            "Natural-language extraction is not configured; add HF_TOKEN to .env"
        )

    client = client_factory(token)
    try:
        response = client.chat_completion(
            model=os.getenv("HF_EXTRACTION_MODEL", DEFAULT_MODEL),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract a business-laptop procurement request. Use only facts "
                        "explicitly stated by the user. Never guess missing values. "
                        "For product, copy the complete product identity stated by the "
                        "user, including brand, product family, and model number; never "
                        "replace a specific identity with a generic word like laptop. "
                        "Return null for every absent field. Currency must be a three-letter "
                        "uppercase ISO code; interpret naira as NGN. quoted_price must "
                        "be a plain numeric string without currency symbols or commas, "
                        "and is the unit price, not quantity multiplied by price."
                    ),
                },
                {"role": "user", "content": text},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "procurement_request_extraction",
                    "schema": ExtractedProcurementFields.model_json_schema(),
                    "strict": True,
                },
            },
            temperature=0,
            max_tokens=800,
        )
        content = response.choices[0].message.content
        fields = ExtractedProcurementFields.model_validate(json.loads(content))
    except httpx.TimeoutException as error:
        raise HuggingFaceTimeoutError(
            "Hugging Face did not respond within the configured time limit"
        ) from error
    except Exception as error:
        raise HuggingFaceExtractionError(
            "Hugging Face could not extract a valid procurement request"
        ) from error

    missing_fields = [name for name in REQUIRED_FIELDS if getattr(fields, name) is None]
    if missing_fields:
        return NaturalLanguageProcurementResponse(
            extracted_fields=fields,
            procurement_request=None,
            missing_fields=missing_fields,
            ready_for_analysis=False,
        )

    try:
        request = ProcurementRequest(
            product=fields.product,
            specifications=ProductSpecifications(
                cpu=fields.cpu,
                ram=fields.ram,
                storage=fields.storage,
            ),
            condition=fields.condition,
            quantity=fields.quantity,
            quoted_price=fields.quoted_price,
            currency=(fields.currency or "NGN").upper(),
        )
    except ValidationError as error:
        raise HuggingFaceExtractionError(
            "Hugging Face extracted values that failed procurement validation"
        ) from error
    return NaturalLanguageProcurementResponse(
        extracted_fields=fields,
        procurement_request=request,
        missing_fields=[],
        ready_for_analysis=True,
    )
