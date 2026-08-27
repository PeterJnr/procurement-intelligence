import unittest
import uuid
from decimal import Decimal
from unittest.mock import MagicMock

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models.analysis_feedback import AnalysisFeedback
from app.models.analysis_feedback_schema import AnalysisFeedbackUpsert
from app.models.procurement_analysis_run import ProcurementAnalysisRun
from app.repositories.analysis_feedback import (
    AnalysisFeedbackNotFoundError,
    AnalysisRunNotFoundError,
    get_analysis_feedback,
    upsert_analysis_feedback,
)


class AnalysisFeedbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session = MagicMock(spec=Session)
        self.analysis_id = uuid.uuid4()
        self.data = AnalysisFeedbackUpsert(
            accuracy_score=4,
            product_match_correct=True,
            evidence_helpful=True,
            corrected_fair_price="825000",
            notes="The product match was correct.",
        )

    def test_accuracy_score_must_be_between_one_and_five(self) -> None:
        with self.assertRaises(ValidationError):
            AnalysisFeedbackUpsert(
                accuracy_score=6,
                product_match_correct=True,
                evidence_helpful=True,
            )

    def test_feedback_is_created_for_existing_analysis(self) -> None:
        self.session.get.return_value = MagicMock(spec=ProcurementAnalysisRun)
        self.session.scalar.return_value = None

        result = upsert_analysis_feedback(
            self.session, self.analysis_id, self.data
        )

        self.session.add.assert_called_once_with(result)
        self.session.commit.assert_called_once_with()
        self.assertEqual(result.analysis_id, self.analysis_id)
        self.assertEqual(result.corrected_fair_price, Decimal("825000"))

    def test_existing_feedback_is_updated(self) -> None:
        existing = AnalysisFeedback(
            analysis_id=self.analysis_id,
            accuracy_score=2,
            product_match_correct=False,
            evidence_helpful=False,
        )
        self.session.get.return_value = MagicMock(spec=ProcurementAnalysisRun)
        self.session.scalar.return_value = existing

        result = upsert_analysis_feedback(
            self.session, self.analysis_id, self.data
        )

        self.session.add.assert_not_called()
        self.assertEqual(result.accuracy_score, 4)
        self.assertTrue(result.product_match_correct)

    def test_unknown_analysis_is_rejected(self) -> None:
        self.session.get.return_value = None

        with self.assertRaises(AnalysisRunNotFoundError):
            upsert_analysis_feedback(self.session, self.analysis_id, self.data)

    def test_missing_feedback_is_reported(self) -> None:
        self.session.scalar.return_value = None

        with self.assertRaises(AnalysisFeedbackNotFoundError):
            get_analysis_feedback(self.session, self.analysis_id)

    def test_database_constraints_are_present(self) -> None:
        names = {
            constraint.name for constraint in AnalysisFeedback.__table__.constraints
        }

        self.assertIn("ck_analysis_feedback_accuracy_range", names)
        self.assertIn("ck_analysis_feedback_corrected_price_positive", names)
        self.assertIn("uq_analysis_feedback_analysis", names)


if __name__ == "__main__":
    unittest.main()
