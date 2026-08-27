import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.conversation_message import ConversationMessage
from app.models.procurement_analysis_run import ProcurementAnalysisRun


class ConversationNotFoundError(LookupError):
    pass


class ConversationArchivedError(ValueError):
    pass


class ConversationAnalysisConflictError(ValueError):
    pass


class ChatAnalysisNotFoundError(LookupError):
    pass


def _require_analysis(session: Session, analysis_id: uuid.UUID) -> None:
    if session.get(ProcurementAnalysisRun, analysis_id) is None:
        raise ChatAnalysisNotFoundError("Procurement analysis was not found")


def create_conversation(
    session: Session,
    *,
    title: str,
    analysis_id: uuid.UUID | None = None,
) -> Conversation:
    if analysis_id is not None:
        _require_analysis(session, analysis_id)
    conversation = Conversation(title=title[:200], analysis_id=analysis_id)
    session.add(conversation)
    try:
        session.commit()
        session.refresh(conversation)
    except Exception:
        session.rollback()
        raise
    return conversation


def get_conversation(session: Session, conversation_id: uuid.UUID) -> Conversation:
    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        raise ConversationNotFoundError("Conversation was not found")
    if conversation.status != "active":
        raise ConversationArchivedError("Conversation is archived")
    return conversation


def link_conversation_analysis(
    session: Session,
    conversation_id: uuid.UUID,
    analysis_id: uuid.UUID,
) -> Conversation:
    _require_analysis(session, analysis_id)
    conversation = session.scalar(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .with_for_update()
    )
    if conversation is None:
        raise ConversationNotFoundError("Conversation was not found")
    if conversation.analysis_id not in {None, analysis_id}:
        raise ConversationAnalysisConflictError(
            "Conversation is already linked to a different analysis"
        )
    conversation.analysis_id = analysis_id
    conversation.updated_at = datetime.now(timezone.utc)
    try:
        session.commit()
        session.refresh(conversation)
    except Exception:
        session.rollback()
        raise
    return conversation


def append_conversation_message(
    session: Session,
    conversation_id: uuid.UUID,
    *,
    role: str,
    content: str,
    intent: str | None,
) -> ConversationMessage:
    conversation = session.scalar(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .with_for_update()
    )
    if conversation is None:
        raise ConversationNotFoundError("Conversation was not found")
    if conversation.status != "active":
        raise ConversationArchivedError("Conversation is archived")
    last_sequence = session.scalar(
        select(func.max(ConversationMessage.sequence_number)).where(
            ConversationMessage.conversation_id == conversation_id
        )
    )
    message = ConversationMessage(
        conversation_id=conversation_id,
        sequence_number=(last_sequence or 0) + 1,
        role=role,
        content=content,
        intent=intent,
    )
    conversation.updated_at = datetime.now(timezone.utc)
    session.add(message)
    try:
        session.commit()
        session.refresh(message)
    except Exception:
        session.rollback()
        raise
    return message


def list_recent_conversation_messages(
    session: Session,
    conversation_id: uuid.UUID,
    *,
    limit: int = 12,
) -> list[ConversationMessage]:
    statement = (
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.sequence_number.desc())
        .limit(limit)
    )
    return list(reversed(session.scalars(statement).all()))


def get_chat_analysis(
    session: Session,
    analysis_id: uuid.UUID,
) -> ProcurementAnalysisRun:
    analysis = session.get(ProcurementAnalysisRun, analysis_id)
    if analysis is None:
        raise ChatAnalysisNotFoundError("Procurement analysis was not found")
    return analysis
