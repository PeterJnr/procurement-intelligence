from sqlalchemy.orm import Session

from app.models.conversation_schema import (
    ChatMessageInput,
    ChatResponse,
    ConversationMessageResponse,
    ConversationResponse,
)
from app.models.procurement_analysis import ProcurementAnalysisResponse
from app.repositories.conversation import (
    append_conversation_message,
    create_conversation,
    get_chat_analysis,
    get_conversation,
    link_conversation_analysis,
    list_recent_conversation_messages,
)
from app.repositories.procurement_analysis_run import save_procurement_analysis_run
from app.services.chat_generation import generate_chat_reply
from app.services.chat_intent import classify_chat_intent
from app.services.huggingface_extraction import (
    HuggingFaceExtractionError,
    HuggingFaceNotConfiguredError,
    HuggingFaceTimeoutError,
    extract_procurement_request,
)
from app.services.procurement_analysis import analyze_procurement_request


def _procurement_context(history, current_message: str) -> str:
    user_messages = [item.content for item in history if item.role == "user"]
    return "\n".join([*user_messages[-5:], current_message])


def _missing_details_reply(missing_fields: list[str], history=()) -> str:
    labels = {
        "product": "the laptop model or specifications",
        "condition": "whether it is new, used, or refurbished",
        "quantity": "how many units you need",
        "quoted_price": "the quoted unit price and currency",
    }
    details = [labels.get(field, field.replace("_", " ")) for field in missing_fields]
    if not details:
        return "Tell me a little more about the purchase you want me to assess."
    previous_assistant_replies = [
        item.content.casefold() for item in history if item.role == "assistant"
    ]
    already_explained = any(
        "laptop model" in reply and "unit price" in reply
        for reply in previous_assistant_replies[-3:]
    )
    if already_explained:
        return f"Absolutely—let’s start with {details[0]}. What do you have in mind?"
    if len(details) == 1:
        joined = details[0]
    else:
        joined = ", ".join(details[:-1]) + f", and {details[-1]}"
    return f"To assess this quote properly, please tell me {joined}."


def handle_chat_message(
    session: Session,
    data: ChatMessageInput,
    user_id: str,
) -> ChatResponse:
    response_analysis: ProcurementAnalysisResponse | None = None
    if data.conversation_id is None:
        conversation = create_conversation(
            session,
            owner_id=user_id,
            title=data.message,
            analysis_id=data.analysis_id,
        )
    else:
        conversation = get_conversation(session, data.conversation_id, user_id)
        if data.analysis_id is not None:
            conversation = link_conversation_analysis(
                session,
                conversation.id,
                data.analysis_id,
                user_id,
            )

    history = list_recent_conversation_messages(session, conversation.id, owner_id=user_id)
    intent = classify_chat_intent(data.message, history, conversation.analysis_id)
    user_message = append_conversation_message(
        session,
        conversation.id,
        owner_id=user_id,
        role="user",
        content=data.message,
        intent=intent,
    )

    analysis_run = (
        get_chat_analysis(session, conversation.analysis_id, user_id)
        if conversation.analysis_id is not None
        else None
    )
    analysis_snapshot = analysis_run.analysis_snapshot if analysis_run else None

    if intent in {"procurement_request", "clarification"} and analysis_run is None:
        try:
            extraction = extract_procurement_request(
                _procurement_context(history, data.message)
            )
            if extraction.procurement_request is None:
                reply = _missing_details_reply(extraction.missing_fields, history)
            else:
                analysis = analyze_procurement_request(
                    session,
                    extraction.procurement_request,
                )
                saved_run = save_procurement_analysis_run(session, analysis, owner_id=user_id)
                conversation = link_conversation_analysis(
                    session,
                    conversation.id,
                    saved_run.id,
                    user_id,
                )
                analysis_run = saved_run
                analysis_snapshot = saved_run.analysis_snapshot
                if isinstance(analysis, ProcurementAnalysisResponse):
                    response_analysis = analysis.model_copy(
                        update={"analysis_id": saved_run.id}
                    )
                reply = analysis.analysis_explanation
        except (
            HuggingFaceExtractionError,
            HuggingFaceNotConfiguredError,
            HuggingFaceTimeoutError,
        ):
            reply = (
                "I could not reliably extract the procurement details right now. "
                "Please try again or provide the product, condition, quantity, and "
                "quoted unit price explicitly."
            )
    else:
        reply = generate_chat_reply(
            data.message,
            intent,
            history,
            analysis_snapshot,
        )

    assistant_message = append_conversation_message(
        session,
        conversation.id,
        owner_id=user_id,
        role="assistant",
        content=reply,
        intent=intent,
    )
    conversation = get_conversation(session, conversation.id, user_id)
    return ChatResponse(
        conversation=ConversationResponse.model_validate(conversation),
        user_message=ConversationMessageResponse.model_validate(user_message),
        assistant_message=ConversationMessageResponse.model_validate(
            assistant_message
        ),
        intent=intent,
        analysis_id=conversation.analysis_id,
        analysis=response_analysis,
    )
