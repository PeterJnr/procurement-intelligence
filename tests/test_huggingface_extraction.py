import json
import os
import unittest
from unittest.mock import patch

import httpx

from app.models.natural_language_procurement import ExtractedProcurementFields
from app.services.huggingface_extraction import (
    DEFAULT_MODEL,
    HuggingFaceExtractionError,
    HuggingFaceNotConfiguredError,
    HuggingFaceTimeoutError,
    _get_timeout_seconds,
    extract_procurement_request,
)


class _Message:
    def __init__(self, content: str) -> None:
        self.content = content


class _Choice:
    def __init__(self, content: str) -> None:
        self.message = _Message(content)


class _Response:
    def __init__(self, payload: dict) -> None:
        self.choices = [_Choice(json.dumps(payload))]


class _FakeClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.call = None

    def chat_completion(self, **kwargs):
        self.call = kwargs
        return _Response(self.payload)


class _TimeoutClient:
    def chat_completion(self, **kwargs):
        raise httpx.ReadTimeout("provider timed out")


class HuggingFaceExtractionTests(unittest.TestCase):
    def test_default_timeout_is_bounded(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(_get_timeout_seconds(), 20.0)

    def test_timeout_can_be_configured(self) -> None:
        with patch.dict(os.environ, {"HF_INFERENCE_TIMEOUT_SECONDS": "12"}):
            self.assertEqual(_get_timeout_seconds(), 12.0)

    def test_provider_timeout_has_specific_error(self) -> None:
        with patch.dict(os.environ, {"HF_TOKEN": "test-token"}):
            with self.assertRaises(HuggingFaceTimeoutError):
                extract_procurement_request(
                    "I need 50 new Dell Latitude 5440 laptops at 850000 naira each.",
                    client_factory=lambda token: _TimeoutClient(),
                )

    def test_ai_schema_forbids_unexpected_fields(self) -> None:
        schema = ExtractedProcurementFields.model_json_schema()

        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["required"]), set(schema["properties"]))

    def test_complete_text_becomes_validated_request(self) -> None:
        payload = {
            "product": "Dell Latitude 5440",
            "cpu": "Intel Core i5",
            "ram": "16GB",
            "storage": "512GB SSD",
            "condition": "new",
            "quantity": 50,
            "quoted_price": "850000",
            "currency": "NGN",
        }
        client = _FakeClient(payload)

        with patch.dict(os.environ, {"HF_TOKEN": "test-token"}):
            result = extract_procurement_request(
                "I need 50 new Dell Latitude 5440 laptops for 850,000 naira each",
                client_factory=lambda token: client,
            )

        self.assertTrue(result.ready_for_analysis)
        self.assertEqual(result.procurement_request.quantity, 50)
        self.assertEqual(result.procurement_request.quoted_price, 850000)
        self.assertEqual(result.procurement_request.specifications.ram, "16GB")
        self.assertEqual(client.call["temperature"], 0)
        self.assertEqual(client.call["max_tokens"], 800)
        self.assertEqual(client.call["model"], DEFAULT_MODEL)
        system_prompt = client.call["messages"][0]["content"]
        self.assertIn("brand, product family, and model number", system_prompt)
        self.assertIn("never replace a specific identity", system_prompt)

    def test_invalid_extracted_price_is_rejected(self) -> None:
        payload = {
            "product": "Dell Latitude 5440",
            "cpu": None,
            "ram": None,
            "storage": None,
            "condition": "new",
            "quantity": 2,
            "quoted_price": "eight hundred thousand",
            "currency": "NGN",
        }

        with patch.dict(os.environ, {"HF_TOKEN": "test-token"}):
            with self.assertRaises(HuggingFaceExtractionError):
                extract_procurement_request(
                    "I need two new Dell laptops at eight hundred thousand naira each.",
                    client_factory=lambda token: _FakeClient(payload),
                )

    def test_missing_facts_are_reported_without_invention(self) -> None:
        payload = {
            "product": "Dell Latitude",
            "cpu": None,
            "ram": None,
            "storage": None,
            "condition": None,
            "quantity": None,
            "quoted_price": None,
            "currency": None,
        }

        with patch.dict(os.environ, {"HF_TOKEN": "test-token"}):
            result = extract_procurement_request(
                "I may need some Dell Latitude laptops but have no other details yet.",
                client_factory=lambda token: _FakeClient(payload),
            )

        self.assertFalse(result.ready_for_analysis)
        self.assertIsNone(result.procurement_request)
        self.assertEqual(
            result.missing_fields,
            ["condition", "quantity", "quoted_price"],
        )

    def test_missing_token_has_clear_error(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(HuggingFaceNotConfiguredError):
                extract_procurement_request("I need a Dell business laptop for work")


if __name__ == "__main__":
    unittest.main()
