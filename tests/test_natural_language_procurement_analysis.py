import os
import unittest
import uuid
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session

from app.main import create_natural_language_procurement_analysis
from app.models.natural_language_procurement import (
    ExtractedProcurementFields,
    NaturalLanguageProcurementInput,
    NaturalLanguageProcurementResponse,
)
from app.models.procurement_request import ProcurementRequest
from app.services.procurement_analysis import analyze_procurement_request as analyze_service


COMPLETE_REQUEST = ProcurementRequest.model_validate(
    {
        "product": "Dell Latitude 5440",
        "specifications": {
            "cpu": "Intel Core i5",
            "ram": "16GB",
            "storage": "512GB SSD",
        },
        "condition": "new",
        "quantity": 50,
        "quoted_price": "850000",
        "currency": "NGN",
    }
)


def extraction(request: ProcurementRequest | None):
    fields = ExtractedProcurementFields(
        product="Dell Latitude 5440",
        cpu="Intel Core i5" if request else None,
        ram="16GB" if request else None,
        storage="512GB SSD" if request else None,
        condition="new" if request else None,
        quantity=50 if request else None,
        quoted_price="850000" if request else None,
        currency="NGN" if request else None,
    )
    return NaturalLanguageProcurementResponse(
        extracted_fields=fields,
        procurement_request=request,
        missing_fields=[] if request else ["condition", "quantity", "quoted_price"],
        ready_for_analysis=request is not None,
    )


class NaturalLanguageProcurementAnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.external_ai = patch.dict(
            os.environ,
            {
                "ENABLE_SEMANTIC_RETRIEVAL": "false",
                "ENABLE_LANGCHAIN_EXPLANATION": "false",
            },
        )
        self.external_ai.start()
        self.addCleanup(self.external_ai.stop)
        self.input = NaturalLanguageProcurementInput(
            text="I need 50 new Dell Latitude 5440 laptops at 850000 naira each."
        )
        self.session = MagicMock(spec=Session)

    @patch("app.main.save_procurement_analysis_run")
    @patch("app.main.analyze_procurement_request")
    @patch("app.main.extract_procurement_request")
    def test_complete_extraction_is_analyzed(self, extract, analyze, save) -> None:
        extracted = extraction(COMPLETE_REQUEST)
        extract.return_value = extracted
        with patch(
            "app.services.procurement_analysis.find_comparable_observations",
            return_value=[],
        ):
            expected_analysis = analyze_service(self.session, COMPLETE_REQUEST)
        analyze.return_value = expected_analysis
        analysis_id = uuid.uuid4()
        save.return_value.id = analysis_id

        result = create_natural_language_procurement_analysis(
            self.input,
            "user_test",
            self.session,
        )

        analyze.assert_called_once_with(self.session, COMPLETE_REQUEST)
        save.assert_called_once_with(
            self.session,
            expected_analysis,
            owner_id="user_test",
        )
        self.assertIs(result.extraction, extracted)
        self.assertEqual(result.analysis.analysis_id, analysis_id)
        self.assertEqual(result.analysis.request, expected_analysis.request)

    @patch("app.main.save_procurement_analysis_run")
    @patch("app.main.analyze_procurement_request")
    @patch("app.main.extract_procurement_request")
    def test_incomplete_extraction_does_not_run_analysis(
        self, extract, analyze, save
    ) -> None:
        extract.return_value = extraction(None)

        result = create_natural_language_procurement_analysis(
            self.input,
            "user_test",
            self.session,
        )

        analyze.assert_not_called()
        save.assert_not_called()
        self.assertFalse(result.extraction.ready_for_analysis)
        self.assertIsNone(result.analysis)
        self.assertEqual(
            result.extraction.missing_fields,
            ["condition", "quantity", "quoted_price"],
        )


if __name__ == "__main__":
    unittest.main()
