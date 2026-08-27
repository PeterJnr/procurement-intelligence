import unittest
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError

from app.main import (
    create_procurement_request,
    extract_natural_language_procurement_request,
    health_check,
)
from app.models.natural_language_procurement import NaturalLanguageProcurementInput
from app.models.procurement_request import ProcurementRequest
from app.services.huggingface_extraction import HuggingFaceTimeoutError
from app.services.laptop_normalization import normalize_laptop_request


VALID_REQUEST = {
    "product": "Dell Latitude 5440",
    "specifications": {
        "cpu": "Intel Core i5",
        "ram": "16GB",
        "storage": "512GB SSD",
    },
    "condition": "new",
    "quantity": 50,
    "quoted_price": 850000,
}


class ApiTests(unittest.TestCase):
    def test_hugging_face_timeout_returns_gateway_timeout(self) -> None:
        text_request = NaturalLanguageProcurementInput(
            text="I need 50 new Dell Latitude laptops at 850000 naira each."
        )

        with patch(
            "app.main.extract_procurement_request",
            side_effect=HuggingFaceTimeoutError("provider timed out"),
        ):
            with self.assertRaises(HTTPException) as context:
                extract_natural_language_procurement_request(text_request)

        self.assertEqual(context.exception.status_code, 504)

    def test_health_check(self) -> None:
        self.assertEqual(health_check(), {"status": "ok"})

    def test_valid_procurement_request(self) -> None:
        request = ProcurementRequest.model_validate(VALID_REQUEST)

        response = create_procurement_request(request)

        self.assertEqual(response.request.product, "Dell Latitude 5440")
        self.assertEqual(response.request.quantity, 50)
        self.assertEqual(response.request.quoted_price, 850000)
        self.assertEqual(response.normalized_product.ram_gb, 16)
        self.assertEqual(response.normalized_product.storage_capacity_gb, 512)
        self.assertEqual(response.normalized_product.analysis_readiness, "ready")
        self.assertEqual(response.normalized_product.missing_fields, [])

    def test_request_with_missing_specifications_is_accepted(self) -> None:
        limited_request = {
            "product": "Dell Latitude 5440",
            "condition": "new",
            "quantity": 50,
            "quoted_price": 850000,
        }

        response = create_procurement_request(
            ProcurementRequest.model_validate(limited_request)
        )

        normalized = response.normalized_product
        self.assertIsNone(normalized.cpu)
        self.assertIsNone(normalized.ram_gb)
        self.assertIsNone(normalized.storage_capacity_gb)
        self.assertIsNone(normalized.storage_type)
        self.assertEqual(normalized.missing_fields, ["cpu", "ram", "storage"])
        self.assertEqual(normalized.analysis_readiness, "needs_more_information")
        self.assertIn("more product information is needed", response.message)

    def test_partially_known_specifications_are_preserved(self) -> None:
        partial_request = {
            **VALID_REQUEST,
            "specifications": {"ram": "16GB"},
        }

        normalized = normalize_laptop_request(
            ProcurementRequest.model_validate(partial_request)
        )

        self.assertEqual(normalized.ram_gb, 16)
        self.assertEqual(normalized.missing_fields, ["cpu", "storage"])
        self.assertEqual(normalized.analysis_readiness, "needs_more_information")

    def test_laptop_information_is_normalized_deterministically(self) -> None:
        varied_request = {
            **VALID_REQUEST,
            "product": "  DELL   Latitude 5440 ",
            "specifications": {
                "cpu": " INTEL   Core i5 ",
                "ram": "16 GB",
                "storage": "0.5 TB SSD",
            },
        }

        normalized = normalize_laptop_request(
            ProcurementRequest.model_validate(varied_request)
        )

        self.assertEqual(normalized.product_name, "dell latitude 5440")
        self.assertEqual(normalized.manufacturer, "dell")
        self.assertEqual(normalized.product_line, "latitude")
        self.assertEqual(normalized.model_number, "5440")
        self.assertEqual(normalized.cpu, "intel core i5")
        self.assertEqual(normalized.ram_gb, 16)
        self.assertEqual(normalized.storage_capacity_gb, 512)
        self.assertEqual(normalized.storage_type, "ssd")
        self.assertEqual(
            normalized.matching_key,
            "dell latitude 5440|intel core i5|ram:16gb|storage:512gb:ssd|new",
        )

    def test_quantity_must_be_positive(self) -> None:
        invalid_request = {**VALID_REQUEST, "quantity": 0}

        with self.assertRaises(ValidationError):
            ProcurementRequest.model_validate(invalid_request)

    def test_condition_must_be_supported(self) -> None:
        invalid_request = {**VALID_REQUEST, "condition": "damaged"}

        with self.assertRaises(ValidationError):
            ProcurementRequest.model_validate(invalid_request)


if __name__ == "__main__":
    unittest.main()
