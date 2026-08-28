import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.auth import require_user


class AuthenticationTests(unittest.TestCase):
    def test_missing_configuration_returns_service_unavailable(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(HTTPException) as caught:
                require_user(MagicMock())

        self.assertEqual(caught.exception.status_code, 503)

    def test_verified_subject_is_returned(self) -> None:
        state = SimpleNamespace(is_signed_in=True, payload={"sub": "user_123"})
        environment = {
            "CLERK_SECRET_KEY": "sk_test_value",
            "CLERK_AUTHORIZED_PARTIES": "https://app.example.com",
        }
        with (
            patch.dict(os.environ, environment, clear=True),
            patch("app.auth.authenticate_request", return_value=state) as authenticate,
        ):
            result = require_user(MagicMock())

        self.assertEqual(result, "user_123")
        options = authenticate.call_args.args[1]
        self.assertEqual(options.authorized_parties, ["https://app.example.com"])

    def test_invalid_session_returns_unauthorized(self) -> None:
        state = SimpleNamespace(is_signed_in=False, payload=None)
        environment = {
            "CLERK_SECRET_KEY": "sk_test_value",
            "CLERK_AUTHORIZED_PARTIES": "https://app.example.com",
        }
        with (
            patch.dict(os.environ, environment, clear=True),
            patch("app.auth.authenticate_request", return_value=state),
        ):
            with self.assertRaises(HTTPException) as caught:
                require_user(MagicMock())

        self.assertEqual(caught.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
