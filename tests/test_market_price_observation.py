import unittest

from app.models.market_price_observation import MarketPriceObservation


class MarketPriceObservationModelTests(unittest.TestCase):
    def test_analysis_fields_are_present(self) -> None:
        columns = MarketPriceObservation.__table__.columns

        expected_columns = {
            "product_name",
            "manufacturer",
            "product_line",
            "model_number",
            "cpu",
            "ram_gb",
            "storage_capacity_gb",
            "storage_type",
            "condition",
            "supplier_name",
            "location_city",
            "location_country",
            "quantity",
            "unit_price",
            "currency",
            "source_name",
            "source_url",
            "source_external_id",
            "observation_date",
            "source_reliability",
            "last_seen_at",
        }

        self.assertTrue(expected_columns.issubset(columns.keys()))

    def test_comparable_lookup_index_exists(self) -> None:
        index_names = {index.name for index in MarketPriceObservation.__table__.indexes}

        self.assertIn("ix_market_observation_comparable_lookup", index_names)


if __name__ == "__main__":
    unittest.main()
