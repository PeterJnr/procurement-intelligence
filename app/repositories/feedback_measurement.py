from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis_feedback import AnalysisFeedback
from app.models.procurement_analysis_run import ProcurementAnalysisRun


def list_feedback_with_analyses(
    session: Session,
) -> list[tuple[AnalysisFeedback, ProcurementAnalysisRun]]:
    statement = (
        select(AnalysisFeedback, ProcurementAnalysisRun)
        .join(
            ProcurementAnalysisRun,
            ProcurementAnalysisRun.id == AnalysisFeedback.analysis_id,
        )
        .order_by(AnalysisFeedback.created_at.asc())
    )
    return list(session.execute(statement).tuples().all())

