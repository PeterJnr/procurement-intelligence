import os
import unittest
from unittest.mock import MagicMock, patch

from app.models.procurement_request import ProcurementRequest
from app.services.analysis_explanation import generate_analysis_explanation
from app.services.procurement_analysis import analyze_procurement_request


REQUEST = ProcurementRequest.model_validate(
    {
        "product": "Dell Latitude 5440",
        "condition": "new",
        "quantity": 1,
        "quoted_price": "850000",
        "currency": "NGN",
    }
)


def analysis():
    with (
        patch(
            "app.services.procurement_analysis.find_comparable_observations",
            return_value=[],
        ),
        patch(
            "app.services.procurement_analysis.find_semantic_observations",
            return_value=([], {}),
        ),
        patch(
            "app.services.procurement_analysis.generate_analysis_explanation"
        ) as explain,
    ):
        explain.return_value.text = "initial"
        explain.return_value.status = "disabled"
        return analyze_procurement_request(MagicMock(), REQUEST)


class AnalysisExplanationTests(unittest.TestCase):
    def test_disabled_ai_returns_deterministic_explanation(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            result = generate_analysis_explanation(analysis())

        self.assertEqual(result.status, "disabled")
        self.assertIn("No qualifying market observations", result.text)

    def test_langchain_result_is_marked_generated(self) -> None:
        chain = MagicMock()
        chain.invoke.return_value = "  Evidence is limited.  Verify more sources. "
        with patch.dict(os.environ, {"ENABLE_LANGCHAIN_EXPLANATION": "true"}):
            result = generate_analysis_explanation(
                analysis(),
                chain_factory=lambda: chain,
            )

        self.assertEqual(result.status, "generated")
        self.assertEqual(result.text, "Evidence is limited. Verify more sources.")
        chain.invoke.assert_called_once()

    def test_model_failure_returns_safe_fallback(self) -> None:
        chain = MagicMock()
        chain.invoke.side_effect = RuntimeError("provider unavailable")
        with (
            patch.dict(os.environ, {"ENABLE_LANGCHAIN_EXPLANATION": "true"}),
            self.assertLogs("app.services.analysis_explanation", level="ERROR"),
        ):
            result = generate_analysis_explanation(
                analysis(),
                chain_factory=lambda: chain,
            )

        self.assertEqual(result.status, "fallback")
        self.assertIn("No qualifying market observations", result.text)


if __name__ == "__main__":
    unittest.main()
