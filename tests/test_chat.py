import os
import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models.conversation_schema import ChatMessageInput
from app.models.procurement_request import ProcurementRequest
from app.services.chat import _missing_details_reply, handle_chat_message
from app.services.chat_generation import generate_chat_reply
from app.services.chat_intent import classify_chat_intent


def message(role: str, content: str, intent: str, sequence: int = 1):
    return SimpleNamespace(
        id=uuid.uuid4(),
        conversation_id=CONVERSATION_ID,
        sequence_number=sequence,
        role=role,
        content=content,
        intent=intent,
        created_at=datetime.now(timezone.utc),
    )


CONVERSATION_ID = uuid.uuid4()
USER_ID = "user_test_123"


class ChatTests(unittest.TestCase):
    def test_greeting_and_procurement_intents_are_deterministic(self) -> None:
        self.assertEqual(classify_chat_intent("Hello", [], None), "greeting")
        self.assertEqual(
            classify_chat_intent("I need a Dell laptop quote", [], None),
            "procurement_request",
        )

    def test_laptop_advice_is_general_chat_not_quote_analysis(self) -> None:
        self.assertEqual(
            classify_chat_intent(
                "Talk to me about the right laptop for gaming",
                [],
                None,
            ),
            "general_chat",
        )

    def test_missing_procurement_details_are_explained_naturally(self) -> None:
        result = _missing_details_reply(
            ["product", "condition", "quantity", "quoted_price"]
        )

        self.assertNotIn("quoted_price", result)
        self.assertIn("laptop model or specifications", result)
        self.assertIn("quoted unit price and currency", result)

    def test_process_question_is_general_chat_even_during_procurement(self) -> None:
        history = [message("user", "Analyze a quote", "procurement_request")]

        result = classify_chat_intent("What details do you need from me?", history, None)

        self.assertEqual(result, "general_chat")

    def test_repeated_missing_details_advance_to_first_question(self) -> None:
        history = [
            message(
                "assistant",
                "Please send the laptop model, condition, quantity, and unit price.",
                "procurement_request",
            )
        ]

        result = _missing_details_reply(
            ["product", "condition", "quantity", "quoted_price"],
            history,
        )

        self.assertIn("let’s start with the laptop model or specifications", result)
        self.assertNotIn("how many units", result)

    def test_prior_procurement_message_makes_short_reply_a_clarification(self) -> None:
        history = [message("user", "I need a laptop", "procurement_request")]

        result = classify_chat_intent("50 units, new", history, None)

        self.assertEqual(result, "clarification")

    def test_verified_analysis_enables_follow_up_intent(self) -> None:
        result = classify_chat_intent(
            "Why is the confidence low?",
            [],
            uuid.uuid4(),
        )

        self.assertEqual(result, "analysis_follow_up")

    def test_disabled_chat_ai_returns_safe_fallback(self) -> None:
        with patch.dict(os.environ, {"ENABLE_CHAT_AI": "false"}):
            result = generate_chat_reply("Hello", "greeting", [], None)

        self.assertIn("laptop", result)

    @patch("app.services.chat.get_conversation")
    @patch("app.services.chat.append_conversation_message")
    @patch("app.services.chat.generate_chat_reply", return_value="Hello there!")
    @patch("app.services.chat.list_recent_conversation_messages", return_value=[])
    @patch("app.services.chat.create_conversation")
    def test_new_greeting_conversation_is_persisted(
        self,
        create,
        list_messages,
        generate,
        append,
        get,
    ) -> None:
        conversation = SimpleNamespace(
            id=CONVERSATION_ID,
            analysis_id=None,
            title="Hello",
            status="active",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        create.return_value = conversation
        get.return_value = conversation
        append.side_effect = [
            message("user", "Hello", "greeting", 1),
            message("assistant", "Hello there!", "greeting", 2),
        ]

        result = handle_chat_message(MagicMock(), ChatMessageInput(message="Hello"), USER_ID)

        self.assertEqual(result.intent, "greeting")
        self.assertEqual(result.assistant_message.content, "Hello there!")
        self.assertEqual(append.call_count, 2)
        generate.assert_called_once()

    def test_complete_procurement_message_runs_and_links_analysis(self) -> None:
        initial = SimpleNamespace(
            id=CONVERSATION_ID,
            analysis_id=None,
            title="Dell request",
            status="active",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        analysis_id = uuid.uuid4()
        linked = SimpleNamespace(**{**initial.__dict__, "analysis_id": analysis_id})
        request = ProcurementRequest.model_validate(
            {
                "product": "Dell Latitude 5440",
                "condition": "new",
                "quantity": 50,
                "quoted_price": "850000",
                "currency": "NGN",
            }
        )
        extraction = SimpleNamespace(procurement_request=request, missing_fields=[])
        analysis = SimpleNamespace(analysis_explanation="Analysis complete.")
        saved = SimpleNamespace(id=analysis_id, analysis_snapshot={"match_level": "exact"})

        with (
            patch("app.services.chat.create_conversation", return_value=initial),
            patch("app.services.chat.list_recent_conversation_messages", return_value=[]),
            patch("app.services.chat.extract_procurement_request", return_value=extraction),
            patch("app.services.chat.analyze_procurement_request", return_value=analysis) as analyze,
            patch("app.services.chat.save_procurement_analysis_run", return_value=saved),
            patch("app.services.chat.link_conversation_analysis", return_value=linked) as link,
            patch("app.services.chat.get_conversation", return_value=linked),
            patch("app.services.chat.append_conversation_message") as append,
        ):
            append.side_effect = [
                message("user", "I need a Dell laptop quote", "procurement_request", 1),
                message("assistant", "Analysis complete.", "procurement_request", 2),
            ]
            result = handle_chat_message(
                MagicMock(),
                ChatMessageInput(message="I need a Dell laptop quote"),
                USER_ID,
            )

        analyze.assert_called_once()
        link.assert_called_once_with(unittest.mock.ANY, CONVERSATION_ID, analysis_id, USER_ID)
        self.assertEqual(result.analysis_id, analysis_id)
        self.assertEqual(result.assistant_message.content, "Analysis complete.")


if __name__ == "__main__":
    unittest.main()
