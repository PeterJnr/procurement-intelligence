import re

from app.models.conversation_message import ConversationMessage
from app.models.conversation_schema import ConversationIntent


GREETINGS = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"}
PROCUREMENT_REQUEST_TERMS = re.compile(
    r"\b(procure|procurement|quotation|quoted|quote|supplier|vendor|unit price|"
    r"bulk order|purchase order|rfq)\b",
    re.IGNORECASE,
)
FOLLOW_UP_TERMS = re.compile(
    r"\b(why|explain|confidence|evidence|median|match|recommend|comparison|"
    r"price|source|supplier|result|analysis)\b",
    re.IGNORECASE,
)


def classify_chat_intent(
    text: str,
    history: list[ConversationMessage],
    analysis_id,
) -> ConversationIntent:
    normalized = " ".join(text.casefold().strip(" .!?" ).split())
    if normalized in GREETINGS:
        return "greeting"
    if analysis_id is not None and FOLLOW_UP_TERMS.search(text):
        return "analysis_follow_up"
    if PROCUREMENT_REQUEST_TERMS.search(text):
        return "procurement_request"
    previous_user_intents = {
        message.intent
        for message in history
        if message.role == "user" and message.intent is not None
    }
    if analysis_id is None and previous_user_intents.intersection(
        {"procurement_request", "clarification"}
    ):
        return "clarification"
    return "general_chat"
