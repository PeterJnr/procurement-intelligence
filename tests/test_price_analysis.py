import unittest
from decimal import Decimal

from app.models.market_price_observation import MarketPriceObservation
from app.services.price_analysis import summarize_price_evidence


def observation(
    price: str,
    reliability: str,
    currency: str = "NGN",
) -> MarketPriceObservation:
    return MarketPriceObservation(
        unit_price=Decimal(price),
        source_reliability=Decimal(reliability),
        currency=currency,
    )


class PriceAnalysisTests(unittest.TestCase):
    def test_no_observations_returns_no_data(self) -> None:
        summary = summarize_price_evidence([])

        self.assertEqual(summary.evidence_status, "no_data")
        self.assertEqual(summary.observation_count, 0)
        self.assertIsNone(summary.median_unit_price)

    def test_fewer_than_three_observations_are_limited(self) -> None:
        summary = summarize_price_evidence(
            [observation("800000", "0.70"), observation("900000", "0.90")]
        )

        self.assertEqual(summary.evidence_status, "limited")
        self.assertEqual(summary.median_unit_price, Decimal("850000.00"))
        self.assertEqual(summary.lowest_unit_price, Decimal("800000.00"))
        self.assertEqual(summary.highest_unit_price, Decimal("900000.00"))
        self.assertEqual(summary.average_source_reliability, Decimal("0.80"))

    def test_three_observations_are_sufficient_for_initial_summary(self) -> None:
        summary = summarize_price_evidence(
            [
                observation("800000", "0.70"),
                observation("850000", "0.80"),
                observation("900000", "0.90"),
            ]
        )

        self.assertEqual(summary.evidence_status, "sufficient")
        self.assertEqual(summary.median_unit_price, Decimal("850000.00"))

    def test_mixed_currencies_are_rejected(self) -> None:
        observations = [
            observation("850000", "0.80", "NGN"),
            observation("550", "0.80", "USD"),
        ]

        with self.assertRaisesRegex(ValueError, "same currency"):
            summarize_price_evidence(observations)


if __name__ == "__main__":
    unittest.main()
