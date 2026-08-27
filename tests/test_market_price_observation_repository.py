import unittest
import uuid
from datetime import date, datetime, timezone
from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from app.models.market_price_observation_schema import MarketPriceObservationCreate
from app.models.market_price_observation_schema import MarketPriceObservationFilters
from app.repositories.market_price_observation import (
    find_observations_by_ids,
    find_comparable_observations,
    save_market_price_observation,
)


VALID_OBSERVATION = {
    "product_name": "dell latitude 5440",
    "manufacturer": "dell",
    "product_line": "latitude",
    "model_number": "5440",
    "cpu": "intel core i5",
    "ram_gb": 16,
    "storage_capacity_gb": 512,
    "storage_type": "ssd",
    "condition": "new",
    "supplier_name": "Example Supplier",
    "location_city": "Lagos",
    "location_country": "Nigeria",
    "quantity": 50,
    "unit_price": "850000.00",
    "currency": "NGN",
    "source_name": "Supplier quotation",
    "source_url": None,
    "source_external_id": "test-listing-1",
    "observation_date": date(2026, 8, 24),
    "source_reliability": "0.80",
    "last_seen_at": datetime(2026, 8, 25, tzinfo=timezone.utc),
}


class MarketPriceObservationRepositoryTests(unittest.TestCase):
    def test_validated_observation_is_added_and_committed(self) -> None:
        session = MagicMock(spec=Session)
        session.scalar.return_value = None
        data = MarketPriceObservationCreate.model_validate(VALID_OBSERVATION)

        saved = save_market_price_observation(session, data)

        self.assertEqual(saved.model_number, "5440")
        self.assertEqual(saved.currency, "NGN")
        session.add.assert_called_once_with(saved)
        session.commit.assert_called_once_with()
        session.refresh.assert_called_once_with(saved)

    def test_same_source_listing_and_date_updates_existing_record(self) -> None:
        session = MagicMock(spec=Session)
        existing = MagicMock()
        session.scalar.return_value = existing
        data = MarketPriceObservationCreate.model_validate(VALID_OBSERVATION)

        saved = save_market_price_observation(session, data)

        self.assertIs(saved, existing)
        self.assertEqual(existing.unit_price, data.unit_price)
        session.add.assert_not_called()
        session.commit.assert_called_once_with()

    def test_comparable_observation_filters_are_applied(self) -> None:
        session = MagicMock(spec=Session)
        session.scalars.return_value.all.return_value = []
        filters = MarketPriceObservationFilters(
            product_name="Dell Latitude 5440",
            condition="new",
            ram_gb=16,
            currency="NGN",
            limit=10,
        )

        observations = find_comparable_observations(session, filters)

        self.assertEqual(observations, [])
        session.scalars.assert_called_once()
        statement = session.scalars.call_args.args[0]
        compiled = str(statement.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("lower(market_price_observations.product_name)", compiled)
        self.assertIn("market_price_observations.ram_gb = 16", compiled)
        self.assertIn("market_price_observations.currency = 'NGN'", compiled)
        self.assertIn("LIMIT 10", compiled)

    def test_identity_filters_replace_brittle_product_name_equality(self) -> None:
        session = MagicMock(spec=Session)
        session.scalars.return_value.all.return_value = []
        filters = MarketPriceObservationFilters(
            product_name="Dell 5440 Latitude Laptop",
            manufacturer="dell",
            product_line="latitude",
            model_number="5440",
            condition="new",
        )

        find_comparable_observations(session, filters)

        statement = session.scalars.call_args.args[0]
        compiled = str(statement.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("lower(market_price_observations.manufacturer)", compiled)
        self.assertIn("lower(market_price_observations.model_number)", compiled)
        self.assertIn("lower(market_price_observations.product_line)", compiled)
        self.assertNotIn("lower(market_price_observations.product_name)", compiled)

    def test_vector_matches_are_returned_in_similarity_rank_order(self) -> None:
        session = MagicMock(spec=Session)
        first_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        second_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
        first = MagicMock(id=first_id)
        second = MagicMock(id=second_id)
        session.scalars.return_value.all.return_value = [second, first]

        result = find_observations_by_ids(session, [first_id, second_id])

        self.assertEqual(result, [first, second])


if __name__ == "__main__":
    unittest.main()
