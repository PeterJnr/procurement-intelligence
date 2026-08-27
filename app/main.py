from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated
import uuid

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db_session
from app.models.market_price_observation_schema import (
    MarketPriceObservationCreate,
    MarketPriceObservationFilters,
    MarketPriceObservationListResponse,
    MarketPriceObservationResponse,
)
from app.models.market_collection_run_schema import (
    MarketCollectionRunFilters,
    MarketCollectionRunListResponse,
    MarketCollectionRunResponse,
    MarketCollectionTriggerResponse,
)
from app.models.procurement_analysis_run_schema import (
    ProcurementAnalysisRunFilters,
    ProcurementAnalysisRunListResponse,
    ProcurementAnalysisRunResponse,
)
from app.models.analysis_feedback_schema import (
    AnalysisFeedbackResponse,
    AnalysisFeedbackUpsert,
)
from app.models.feedback_measurement import FeedbackMeasurementSummary
from app.models.vector_backfill import VectorBackfillResponse
from app.models.semantic_calibration import SemanticCalibrationSummary
from app.models.conversation_schema import ChatMessageInput, ChatResponse
from app.models.procurement_request import (
    ProcurementRequest,
    ProcurementRequestResponse,
)
from app.models.procurement_analysis import ProcurementAnalysisResponse
from app.models.natural_language_procurement import (
    NaturalLanguageProcurementAnalysisResponse,
    NaturalLanguageProcurementInput,
    NaturalLanguageProcurementResponse,
)
from app.services.huggingface_extraction import (
    HuggingFaceExtractionError,
    HuggingFaceNotConfiguredError,
    HuggingFaceTimeoutError,
    extract_procurement_request,
)
from app.services.laptop_normalization import normalize_laptop_request
from app.services.procurement_analysis import analyze_procurement_request
from app.services.market_scheduler import queue_market_collection, start_market_scheduler
from app.security import verify_market_admin_key
from app.repositories.market_price_observation import (
    find_comparable_observations,
    save_market_price_observation,
)
from app.repositories.market_collection_run import list_collection_runs
from app.repositories.procurement_analysis_run import (
    list_procurement_analysis_runs,
    save_procurement_analysis_run,
)
from app.repositories.analysis_feedback import (
    AnalysisFeedbackNotFoundError,
    AnalysisRunNotFoundError,
    get_analysis_feedback,
    upsert_analysis_feedback,
)
from app.repositories.feedback_measurement import list_feedback_with_analyses
from app.services.feedback_measurement import measure_analysis_feedback
from app.services.vector_backfill import (
    VectorBackfillNotConfiguredError,
    backfill_market_observation_vectors,
)
from app.services.semantic_calibration import calibrate_semantic_threshold
from app.services.chat import handle_chat_message
from app.config import cors_allowed_origins, validate_configuration
from app.repositories.conversation import (
    ChatAnalysisNotFoundError,
    ConversationAnalysisConflictError,
    ConversationArchivedError,
    ConversationNotFoundError,
)
from app.rate_limit import enforce_ai_rate_limit


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_configuration()
    scheduler = start_market_scheduler()
    yield
    if scheduler is not None:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title="Procurement Intelligence Platform",
    description=(
        "Evidence-backed business-laptop market analysis, semantic retrieval, "
        "feedback calibration, and contextual procurement chat."
    ),
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Content-Type", "X-Admin-API-Key"],
)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Confirm that the API is running."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(
    data: ChatMessageInput,
    session: Session = Depends(get_db_session),
    _: None = Depends(enforce_ai_rate_limit),
) -> ChatResponse:
    """Create or continue a context-aware procurement conversation."""
    try:
        return handle_chat_message(session, data)
    except (ConversationNotFoundError, ChatAnalysisNotFoundError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (ConversationArchivedError, ConversationAnalysisConflictError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=500,
            detail="Could not process the chat message",
        ) from error


@app.post("/procurement-requests", response_model=ProcurementRequestResponse)
def create_procurement_request(
    request: ProcurementRequest,
) -> ProcurementRequestResponse:
    """Validate and normalize a procurement request."""
    try:
        normalized_product = normalize_laptop_request(request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    message = (
        "Procurement request validated; more product information is needed"
        if normalized_product.analysis_readiness == "needs_more_information"
        else "Procurement request validated and normalized successfully"
    )

    return ProcurementRequestResponse(
        message=message,
        request=request,
        normalized_product=normalized_product,
    )


@app.post(
    "/procurement-requests/extract",
    response_model=NaturalLanguageProcurementResponse,
)
def extract_natural_language_procurement_request(
    request: NaturalLanguageProcurementInput,
    _: None = Depends(enforce_ai_rate_limit),
) -> NaturalLanguageProcurementResponse:
    """Convert a plain-English request into the validated internal structure."""
    try:
        return extract_procurement_request(request.text)
    except HuggingFaceNotConfiguredError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except HuggingFaceTimeoutError as error:
        raise HTTPException(status_code=504, detail=str(error)) from error
    except HuggingFaceExtractionError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.post(
    "/procurement-analysis/natural-language",
    response_model=NaturalLanguageProcurementAnalysisResponse,
)
def create_natural_language_procurement_analysis(
    request: NaturalLanguageProcurementInput,
    session: Session = Depends(get_db_session),
    _: None = Depends(enforce_ai_rate_limit),
) -> NaturalLanguageProcurementAnalysisResponse:
    """Extract, validate, and analyze one plain-English procurement request."""
    try:
        extraction = extract_procurement_request(request.text)
        analysis = (
            analyze_procurement_request(session, extraction.procurement_request)
            if extraction.procurement_request is not None
            else None
        )
        if analysis is not None:
            saved_run = save_procurement_analysis_run(session, analysis)
            analysis = analysis.model_copy(update={"analysis_id": saved_run.id})
        return NaturalLanguageProcurementAnalysisResponse(
            extraction=extraction,
            analysis=analysis,
        )
    except HuggingFaceNotConfiguredError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except HuggingFaceTimeoutError as error:
        raise HTTPException(status_code=504, detail=str(error)) from error
    except HuggingFaceExtractionError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except (SQLAlchemyError, RuntimeError) as error:
        raise HTTPException(
            status_code=500,
            detail="Could not analyze the extracted procurement request",
        ) from error


@app.post(
    "/market-price-observations",
    response_model=MarketPriceObservationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_market_price_observation(
    observation: MarketPriceObservationCreate,
    session: Session = Depends(get_db_session),
    _: None = Depends(verify_market_admin_key),
) -> MarketPriceObservationResponse:
    """Validate and store one market-price observation."""
    try:
        saved_observation = save_market_price_observation(session, observation)
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=500,
            detail="Could not save the market-price observation",
        ) from error

    return MarketPriceObservationResponse.model_validate(saved_observation)


@app.get(
    "/market-price-observations",
    response_model=MarketPriceObservationListResponse,
)
def get_market_price_observations(
    filters: Annotated[MarketPriceObservationFilters, Query()],
    session: Session = Depends(get_db_session),
) -> MarketPriceObservationListResponse:
    """Retrieve recent market observations matching supplied filters."""
    try:
        observations = find_comparable_observations(session, filters)
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve market-price observations",
        ) from error

    return MarketPriceObservationListResponse(
        count=len(observations),
        observations=[
            MarketPriceObservationResponse.model_validate(observation)
            for observation in observations
        ],
    )


@app.get(
    "/market-collection-runs",
    response_model=MarketCollectionRunListResponse,
)
def get_market_collection_runs(
    filters: Annotated[MarketCollectionRunFilters, Query()],
    session: Session = Depends(get_db_session),
    _: None = Depends(verify_market_admin_key),
) -> MarketCollectionRunListResponse:
    """Return recent scheduler collection attempts for operational visibility."""
    try:
        runs = list_collection_runs(session, filters)
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve market collection runs",
        ) from error
    return MarketCollectionRunListResponse(
        count=len(runs),
        runs=[MarketCollectionRunResponse.model_validate(run) for run in runs],
    )


@app.post(
    "/market-collection-runs/trigger",
    response_model=MarketCollectionTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def trigger_market_collection(
    background_tasks: BackgroundTasks,
    _: None = Depends(verify_market_admin_key),
) -> MarketCollectionTriggerResponse:
    """Queue one protected market refresh without blocking the HTTP request."""
    if not queue_market_collection(background_tasks):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A market collection is already running",
        )
    return MarketCollectionTriggerResponse(
        message="Market collection was queued successfully"
    )


@app.post(
    "/market-vectors/backfill",
    response_model=VectorBackfillResponse,
)
def backfill_market_vectors(
    limit: int = Query(default=5, ge=1, le=25),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db_session),
    _: None = Depends(verify_market_admin_key),
) -> VectorBackfillResponse:
    """Synchronize one bounded page of historical observations to Pinecone."""
    try:
        return backfill_market_observation_vectors(
            session,
            limit=limit,
            offset=offset,
        )
    except VectorBackfillNotConfiguredError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve observations for vector backfill",
        ) from error


@app.post(
    "/procurement-analysis",
    response_model=ProcurementAnalysisResponse,
)
def create_procurement_analysis(
    request: ProcurementRequest,
    session: Session = Depends(get_db_session),
    _: None = Depends(enforce_ai_rate_limit),
) -> ProcurementAnalysisResponse:
    """Run the current end-to-end procurement evidence workflow."""
    try:
        analysis = analyze_procurement_request(session, request)
        saved_run = save_procurement_analysis_run(session, analysis)
        return analysis.model_copy(update={"analysis_id": saved_run.id})
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=500,
            detail="Could not analyze the procurement request",
        ) from error


@app.get(
    "/procurement-analysis-runs",
    response_model=ProcurementAnalysisRunListResponse,
)
def get_procurement_analysis_runs(
    filters: Annotated[ProcurementAnalysisRunFilters, Query()],
    session: Session = Depends(get_db_session),
    _: None = Depends(verify_market_admin_key),
) -> ProcurementAnalysisRunListResponse:
    """Return protected summaries of completed procurement analyses."""
    try:
        runs = list_procurement_analysis_runs(session, filters)
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve procurement analysis history",
        ) from error
    return ProcurementAnalysisRunListResponse(
        count=len(runs),
        runs=[ProcurementAnalysisRunResponse.model_validate(run) for run in runs],
    )


@app.put(
    "/procurement-analysis-runs/{analysis_id}/feedback",
    response_model=AnalysisFeedbackResponse,
)
def put_analysis_feedback(
    analysis_id: uuid.UUID,
    data: AnalysisFeedbackUpsert,
    session: Session = Depends(get_db_session),
    _: None = Depends(verify_market_admin_key),
) -> AnalysisFeedbackResponse:
    """Create or replace human quality feedback for one analysis."""
    try:
        feedback = upsert_analysis_feedback(session, analysis_id, data)
    except AnalysisRunNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except SQLAlchemyError as error:
        raise HTTPException(status_code=500, detail="Could not save feedback") from error
    return AnalysisFeedbackResponse.model_validate(feedback)


@app.get(
    "/procurement-analysis-runs/{analysis_id}/feedback",
    response_model=AnalysisFeedbackResponse,
)
def read_analysis_feedback(
    analysis_id: uuid.UUID,
    session: Session = Depends(get_db_session),
    _: None = Depends(verify_market_admin_key),
) -> AnalysisFeedbackResponse:
    """Return the recorded quality feedback for one analysis."""
    try:
        feedback = get_analysis_feedback(session, analysis_id)
    except AnalysisFeedbackNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except SQLAlchemyError as error:
        raise HTTPException(status_code=500, detail="Could not retrieve feedback") from error
    return AnalysisFeedbackResponse.model_validate(feedback)


@app.get(
    "/analysis-feedback/summary",
    response_model=FeedbackMeasurementSummary,
)
def get_analysis_feedback_summary(
    session: Session = Depends(get_db_session),
    _: None = Depends(verify_market_admin_key),
) -> FeedbackMeasurementSummary:
    """Measure accumulated feedback without automatically changing behavior."""
    try:
        records = list_feedback_with_analyses(session)
        return measure_analysis_feedback(records)
    except (SQLAlchemyError, ValueError) as error:
        raise HTTPException(
            status_code=500,
            detail="Could not measure analysis feedback",
        ) from error


@app.get(
    "/analysis-feedback/semantic-calibration",
    response_model=SemanticCalibrationSummary,
)
def get_semantic_calibration(
    session: Session = Depends(get_db_session),
    _: None = Depends(verify_market_admin_key),
) -> SemanticCalibrationSummary:
    """Recommend, but never automatically apply, a semantic match threshold."""
    try:
        records = list_feedback_with_analyses(session)
        return calibrate_semantic_threshold(records)
    except (SQLAlchemyError, ValueError) as error:
        raise HTTPException(
            status_code=500,
            detail="Could not calibrate semantic matching",
        ) from error


# In production the frontend is compiled into this directory and served from the
# same origin as the API. Keeping this mount last ensures API routes win first.
frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
