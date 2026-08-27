import os
import unittest
from unittest.mock import MagicMock, patch

from app.services.live_news import fetch_live_news, format_live_news, is_live_news_request


class LiveNewsTests(unittest.TestCase):
    def test_news_and_viral_requests_are_detected(self) -> None:
        self.assertTrue(is_live_news_request("What is the latest news in Nigeria?"))
        self.assertTrue(is_live_news_request("Show me viral content today"))
        self.assertFalse(is_live_news_request("Analyze this Dell quote"))

    def test_fetch_maps_only_valid_articles(self) -> None:
        response = MagicMock()
        response.json.return_value = {
            "articles": [
                {
                    "title": "Example headline",
                    "source": {"name": "Example News"},
                    "url": "https://example.com/story",
                    "publishedAt": "2026-08-27T12:00:00Z",
                    "description": "A short description.",
                },
                {"title": "Missing URL", "source": {"name": "Ignored"}},
            ]
        }
        get = MagicMock(return_value=response)
        with patch.dict(
            os.environ,
            {"ENABLE_LIVE_NEWS": "true", "NEWS_API_KEY": "test-key"},
        ):
            articles = fetch_live_news("Latest news in Nigeria", get=get)

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].source, "Example News")
        self.assertEqual(get.call_args.kwargs["headers"], {"X-Api-Key": "test-key"})
        response.raise_for_status.assert_called_once()

    def test_disabled_integration_does_not_call_provider(self) -> None:
        get = MagicMock()
        with patch.dict(os.environ, {"ENABLE_LIVE_NEWS": "false"}):
            self.assertEqual(fetch_live_news("Breaking news", get=get), [])
        get.assert_not_called()

    def test_articles_are_rendered_as_dated_markdown_links(self) -> None:
        response = MagicMock()
        response.json.return_value = {
            "articles": [{
                "title": "Example headline",
                "source": {"name": "Example News"},
                "url": "https://example.com/story",
                "publishedAt": "2026-08-27T12:00:00Z",
            }]
        }
        with patch.dict(os.environ, {"ENABLE_LIVE_NEWS": "true", "NEWS_API_KEY": "key"}):
            articles = fetch_live_news("Trending news", get=MagicMock(return_value=response))

        result = format_live_news("Summary.", articles)
        self.assertIn("**Current articles:**", result)
        self.assertIn("[Example headline](https://example.com/story)", result)


if __name__ == "__main__":
    unittest.main()
