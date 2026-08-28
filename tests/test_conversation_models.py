import unittest

from pydantic import ValidationError

from app.models.conversation import Conversation
from app.models.conversation_message import ConversationMessage
from app.models.conversation_schema import ChatMessageInput


class ConversationModelTests(unittest.TestCase):
    def test_conversation_has_status_and_analysis_index(self) -> None:
        constraint_names = {
            constraint.name for constraint in Conversation.__table__.constraints
        }
        index_names = {index.name for index in Conversation.__table__.indexes}

        self.assertIn("ck_conversation_status", constraint_names)
        self.assertIn("ix_conversation_analysis_updated", index_names)
        self.assertIn("ix_conversation_owner_updated", index_names)

    def test_messages_are_ordered_and_database_validated(self) -> None:
        constraint_names = {
            constraint.name
            for constraint in ConversationMessage.__table__.constraints
        }

        self.assertIn("uq_conversation_message_sequence", constraint_names)
        self.assertIn("ck_conversation_message_role", constraint_names)
        self.assertIn("ck_conversation_message_intent", constraint_names)
        self.assertIn("ck_conversation_message_content_not_blank", constraint_names)

    def test_chat_input_rejects_blank_message(self) -> None:
        with self.assertRaises(ValidationError):
            ChatMessageInput(message="")


if __name__ == "__main__":
    unittest.main()
