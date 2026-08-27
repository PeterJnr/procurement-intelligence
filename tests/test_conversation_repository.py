import unittest
import uuid
from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.repositories.conversation import (
    ConversationAnalysisConflictError,
    ConversationNotFoundError,
    append_conversation_message,
    link_conversation_analysis,
)


class ConversationRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session = MagicMock(spec=Session)
        self.conversation_id = uuid.uuid4()

    def test_append_assigns_next_locked_sequence(self) -> None:
        conversation = Conversation(id=self.conversation_id, status="active")
        self.session.scalar.side_effect = [conversation, 2]

        result = append_conversation_message(
            self.session,
            self.conversation_id,
            role="user",
            content="Hello",
            intent="greeting",
        )

        self.assertEqual(result.sequence_number, 3)
        self.session.add.assert_called_once_with(result)
        self.session.commit.assert_called_once_with()
        first_statement = self.session.scalar.call_args_list[0].args[0]
        self.assertTrue(first_statement._for_update_arg is not None)

    def test_append_rejects_unknown_conversation(self) -> None:
        self.session.scalar.return_value = None

        with self.assertRaises(ConversationNotFoundError):
            append_conversation_message(
                self.session,
                self.conversation_id,
                role="user",
                content="Hello",
                intent="greeting",
            )

    def test_existing_analysis_link_cannot_be_replaced(self) -> None:
        existing_analysis_id = uuid.uuid4()
        requested_analysis_id = uuid.uuid4()
        self.session.get.return_value = MagicMock()
        self.session.scalar.return_value = Conversation(
            id=self.conversation_id,
            analysis_id=existing_analysis_id,
            status="active",
        )

        with self.assertRaises(ConversationAnalysisConflictError):
            link_conversation_analysis(
                self.session,
                self.conversation_id,
                requested_analysis_id,
            )


if __name__ == "__main__":
    unittest.main()
