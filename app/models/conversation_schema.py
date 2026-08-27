import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.procurement_analysis import ProcurementAnalysisResponse


ConversationIntent = Literal[
    "greeting",
    "general_chat",
    "procurement_request",
    "clarification",
    "analysis_follow_up",
    "unsupported",
]


class ConversationMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    sequence_number: int
    role: Literal["user", "assistant"]
    content: str
    intent: ConversationIntent | None
    created_at: datetime


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    analysis_id: uuid.UUID | None
    title: str | None
    status: Literal["active", "archived"]
    created_at: datetime
    updated_at: datetime


class ChatMessageInput(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: uuid.UUID | None = None
    analysis_id: uuid.UUID | None = None

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message must not be blank")
        return value


class ChatResponse(BaseModel):
    conversation: ConversationResponse
    user_message: ConversationMessageResponse
    assistant_message: ConversationMessageResponse
    intent: ConversationIntent
    analysis_id: uuid.UUID | None
    analysis: ProcurementAnalysisResponse | None = None
