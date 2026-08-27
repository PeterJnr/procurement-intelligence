from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.procurement_analysis import ProcurementAnalysisResponse
from app.models.procurement_analysis_run import ProcurementAnalysisRun
from app.models.procurement_analysis_run_schema import ProcurementAnalysisRunFilters


def save_procurement_analysis_run(
    session: Session,
    analysis: ProcurementAnalysisResponse,
) -> ProcurementAnalysisRun:
    normalized = analysis.normalized_product
    request = analysis.request
    recommendation = analysis.recommendation
    run = ProcurementAnalysisRun(
        product_name=normalized.product_name,
        manufacturer=normalized.manufacturer,
        product_line=normalized.product_line,
        model_number=normalized.model_number,
        condition=request.condition,
        quantity=request.quantity,
        quoted_price=request.quoted_price,
        currency=request.currency,
        market_data_status=analysis.market_data_status,
        match_level=analysis.match_level,
        evidence_count=analysis.evidence.observation_count,
        assessment=recommendation.assessment,
        recommended_action=recommendation.recommended_action,
        confidence=recommendation.confidence,
        request_snapshot=request.model_dump(mode="json"),
        analysis_snapshot=analysis.model_dump(mode="json", exclude={"analysis_id"}),
    )
    session.add(run)
    try:
        session.commit()
        session.refresh(run)
    except Exception:
        session.rollback()
        raise
    return run


def list_procurement_analysis_runs(
    session: Session,
    filters: ProcurementAnalysisRunFilters,
) -> list[ProcurementAnalysisRun]:
    statement = select(ProcurementAnalysisRun)
    if filters.product_name is not None:
        statement = statement.where(
            func.lower(ProcurementAnalysisRun.product_name)
            == filters.product_name.strip().lower()
        )
    if filters.assessment is not None:
        statement = statement.where(
            ProcurementAnalysisRun.assessment == filters.assessment
        )
    statement = statement.order_by(ProcurementAnalysisRun.created_at.desc()).limit(
        filters.limit
    )
    return list(session.scalars(statement).all())

