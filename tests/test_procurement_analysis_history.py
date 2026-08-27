import unittest
import os
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session

from app.models.procurement_analysis_run_schema import ProcurementAnalysisRunFilters
from app.models.procurement_request import ProcurementRequest
from app.repositories.procurement_analysis_run import (
    list_procurement_analysis_runs,
    save_procurement_analysis_run,
)
from app.services.procurement_analysis import analyze_procurement_request


class ProcurementAnalysisHistoryTests(unittest.TestCase):
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
        self.session = MagicMock(spec=Session)
        self.request = ProcurementRequest.model_validate(
            {
                "product": "Dell Latitude 5440",
                "condition": "new",
                "quantity": 50,
                "quoted_price": "850000",
                "currency": "NGN",
            }
        )

    def _analysis(self):
        with patch(
            "app.services.procurement_analysis.find_comparable_observations",
            return_value=[],
        ):
            return analyze_procurement_request(self.session, self.request)

    def test_completed_analysis_is_snapshotted(self) -> None:
        analysis = self._analysis()

        saved = save_procurement_analysis_run(self.session, analysis)

        self.session.add.assert_called_once_with(saved)
        self.session.commit.assert_called_once_with()
        self.assertEqual(saved.product_name, "dell latitude 5440")
        self.assertEqual(saved.assessment, "undetermined")
        self.assertEqual(saved.evidence_count, 0)
        self.assertEqual(saved.request_snapshot["quantity"], 50)
        self.assertNotIn("analysis_id", saved.analysis_snapshot)

    def test_history_filters_are_applied(self) -> None:
        self.session.scalars.return_value.all.return_value = []
        filters = ProcurementAnalysisRunFilters(
            product_name="Dell Latitude 5440",
            assessment="undetermined",
            limit=5,
        )

        result = list_procurement_analysis_runs(self.session, filters)

        self.assertEqual(result, [])
        statement = self.session.scalars.call_args.args[0]
        compiled = str(statement.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("lower(procurement_analysis_runs.product_name)", compiled)
        self.assertIn("procurement_analysis_runs.assessment = 'undetermined'", compiled)
        self.assertIn("LIMIT 5", compiled)


if __name__ == "__main__":
    unittest.main()
