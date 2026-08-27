import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.services.semantic_calibration import calibrate_semantic_threshold


def record(score: float, correct: bool):
    feedback = SimpleNamespace(product_match_correct=correct)
    analysis = SimpleNamespace(
        analysis_snapshot={
            "match_level": "semantic",
            "evidence_observations": [
                {
                    "retrieval_method": "semantic",
                    "semantic_similarity_score": score,
                }
            ],
        }
    )
    return feedback, analysis


class SemanticCalibrationTests(unittest.TestCase):
    def test_ten_semantic_reviews_are_required(self) -> None:
        result = calibrate_semantic_threshold(
            [record(0.80, True), record(0.68, False)]
        )

        self.assertEqual(result.calibration_status, "insufficient_feedback")
        self.assertIsNone(result.recommended_threshold)

    def test_both_correct_and_incorrect_labels_are_required(self) -> None:
        result = calibrate_semantic_threshold([record(0.80, True) for _ in range(10)])

        self.assertEqual(
            result.calibration_status,
            "insufficient_label_diversity",
        )

    def test_separable_feedback_recommends_reviewed_threshold(self) -> None:
        records = [record(score, True) for score in (0.82, 0.84, 0.86, 0.88, 0.90)]
        records += [record(score, False) for score in (0.67, 0.70, 0.73, 0.76, 0.79)]

        with patch.dict(os.environ, {"PINECONE_MIN_SIMILARITY": "0.65"}):
            result = calibrate_semantic_threshold(records)

        self.assertEqual(result.calibration_status, "recommendation_ready")
        self.assertEqual(result.recommended_action, "review_threshold_change")
        self.assertEqual(result.recommended_threshold, 0.791)
        self.assertEqual(result.estimated_balanced_accuracy, 1.0)

    def test_non_semantic_feedback_is_ignored(self) -> None:
        feedback, analysis = record(0.80, True)
        analysis.analysis_snapshot["match_level"] = "exact"

        result = calibrate_semantic_threshold([(feedback, analysis)])

        self.assertEqual(result.semantic_feedback_count, 0)


if __name__ == "__main__":
    unittest.main()
