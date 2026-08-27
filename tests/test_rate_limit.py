import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException, Request, Response

from app.rate_limit import ai_rate_limiter, enforce_ai_rate_limit


def request(client_ip: str, forwarded_for: str | None = None) -> Request:
    headers = []
    if forwarded_for is not None:
        headers.append((b"x-forwarded-for", forwarded_for.encode("ascii")))
    return Request(
        {
            "type": "http",
            "client": (client_ip, 12345),
            "headers": headers,
        }
    )


class RateLimitTests(unittest.TestCase):
    def setUp(self) -> None:
        ai_rate_limiter.reset()
        self.environment = {
            "ENABLE_RATE_LIMITING": "true",
            "AI_RATE_LIMIT_REQUESTS": "2",
            "AI_RATE_LIMIT_WINDOW_SECONDS": "60",
        }

    def test_limit_returns_headers_then_rejects_with_retry_after(self) -> None:
        with patch.dict(os.environ, self.environment, clear=True):
            first_response = Response()
            enforce_ai_rate_limit(request("127.0.0.1"), first_response)
            enforce_ai_rate_limit(request("127.0.0.1"), Response())
            with self.assertRaises(HTTPException) as context:
                enforce_ai_rate_limit(request("127.0.0.1"), Response())

        self.assertEqual(first_response.headers["X-RateLimit-Limit"], "2")
        self.assertEqual(first_response.headers["X-RateLimit-Remaining"], "1")
        self.assertEqual(context.exception.status_code, 429)
        self.assertIn("Retry-After", context.exception.headers)

    def test_clients_have_separate_budgets(self) -> None:
        with patch.dict(os.environ, self.environment, clear=True):
            enforce_ai_rate_limit(request("127.0.0.1"), Response())
            enforce_ai_rate_limit(request("127.0.0.1"), Response())
            enforce_ai_rate_limit(request("127.0.0.2"), Response())

    def test_proxy_header_is_ignored_unless_explicitly_trusted(self) -> None:
        with patch.dict(os.environ, self.environment, clear=True):
            enforce_ai_rate_limit(request("127.0.0.1", "1.1.1.1"), Response())
            enforce_ai_rate_limit(request("127.0.0.1", "2.2.2.2"), Response())
            with self.assertRaises(HTTPException):
                enforce_ai_rate_limit(
                    request("127.0.0.1", "3.3.3.3"),
                    Response(),
                )

    def test_limiter_can_be_disabled(self) -> None:
        with patch.dict(os.environ, {"ENABLE_RATE_LIMITING": "false"}, clear=True):
            for _ in range(5):
                enforce_ai_rate_limit(request("127.0.0.1"), Response())


if __name__ == "__main__":
    unittest.main()
