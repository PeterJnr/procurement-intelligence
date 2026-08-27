import unittest
from decimal import Decimal
from types import SimpleNamespace

from app.services.feedback_measurement import measure_analysis_feedback


def record(
    score: int,
    match_correct: bool,
    helpful: bool,
    corrected_price: str | None = None,
    median_price: str | None = "800000",
    currency: str = "NGN",
):
    feedback = SimpleNamespace(
        accuracy_score=score,
        product_match_correct=match_correct,
        evidence_helpful=helpful,
        corrected_fair_price=(
            Decimal(corrected_price) if corrected_price is not None else None
        ),
    )
    analysis = SimpleNamespace(
        analysis_snapshot={
            "request": {"currency": currency},
            "evidence": {"median_unit_price": median_price},
        }
    )
    return feedback, analysis


class FeedbackMeasurementTests(unittest.TestCase):
    def test_no_feedback_returns_empty_measurement(self) -> None:
        result = measure_analysis_feedback([])

        self.assertEqual(result.measurement_status, "insufficient_feedback")
        self.assertEqual(result.feedback_count, 0)
        self.assertIsNone(result.average_accuracy_score)

    def test_feedback_rates_and_price_corrections_are_calculated(self) -> None:
        records = [
            record(4, True, True, "840000"),
            record(2, False, True, "760000"),
        ]

        result = measure_analysis_feedback(records)

        self.assertEqual(result.average_accuracy_score, Decimal("3.00"))
        self.assertEqual(result.product_match_correct_rate, Decimal("50.00"))
        self.assertEqual(result.evidence_helpful_rate, Decimal("100.00"))
        self.assertEqual(result.corrected_fair_price_count, 2)
        self.assertEqual(
            result.price_corrections[0].average_price_difference,
            Decimal("0.00"),
        )
        self.assertEqual(
            result.price_corrections[0].average_percentage_difference,
            Decimal("0.00"),
        )

    def test_ten_records_are_required_for_sufficient_feedback(self) -> None:
        records = [record(5, True, True) for _ in range(10)]

        result = measure_analysis_feedback(records)

        self.assertEqual(result.measurement_status, "sufficient_feedback")

    def test_price_corrections_are_kept_separate_by_currency(self) -> None:
        records = [
            record(4, True, True, "900000", currency="NGN"),
            record(4, True, True, "1100", median_price="1000", currency="USD"),
        ]

        result = measure_analysis_feedback(records)

        self.assertEqual(
            [metric.currency for metric in result.price_corrections],
            ["NGN", "USD"],
        )


if __name__ == "__main__":
    unittest.main()
