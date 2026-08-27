import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis_feedback import AnalysisFeedback
from app.models.analysis_feedback_schema import AnalysisFeedbackUpsert
from app.models.procurement_analysis_run import ProcurementAnalysisRun


class AnalysisRunNotFoundError(LookupError):
    pass


class AnalysisFeedbackNotFoundError(LookupError):
    pass


def upsert_analysis_feedback(
    session: Session,
    analysis_id: uuid.UUID,
    data: AnalysisFeedbackUpsert,
) -> AnalysisFeedback:
    if session.get(ProcurementAnalysisRun, analysis_id) is None:
        raise AnalysisRunNotFoundError("Procurement analysis was not found")

    feedback = session.scalar(
        select(AnalysisFeedback).where(AnalysisFeedback.analysis_id == analysis_id)
    )
    if feedback is None:
        feedback = AnalysisFeedback(analysis_id=analysis_id, **data.model_dump())
        session.add(feedback)
    else:
        for field_name, value in data.model_dump().items():
            setattr(feedback, field_name, value)

    try:
        session.commit()
        session.refresh(feedback)
    except Exception:
        session.rollback()
        raise
    return feedback


def get_analysis_feedback(
    session: Session,
    analysis_id: uuid.UUID,
) -> AnalysisFeedback:
    feedback = session.scalar(
        select(AnalysisFeedback).where(AnalysisFeedback.analysis_id == analysis_id)
    )
    if feedback is None:
        raise AnalysisFeedbackNotFoundError("Analysis feedback was not found")
    return feedback

