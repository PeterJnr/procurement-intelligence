import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Callable

import httpx


NEWS_API_URL = "https://newsapi.org/v2/everything"
NEWS_TERMS = re.compile(
    r"\b(latest news|breaking news|trending news|news headlines?|viral content|"
    r"viral stories|what(?:'s| is) trending)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class NewsArticle:
    title: str
    source: str
    url: str
    published_at: str
    description: str | None = None

    def as_prompt_data(self) -> dict[str, Any]:
        return asdict(self)


def live_news_enabled() -> bool:
    return os.getenv("ENABLE_LIVE_NEWS", "false").casefold() in {"true", "1", "yes"}


def is_live_news_request(message: str) -> bool:
    return NEWS_TERMS.search(message) is not None


def _news_query(message: str) -> str:
    cleaned = NEWS_TERMS.sub(" ", message)
    cleaned = re.sub(
        r"\b(please|show|tell|give|me|about|today|right now|currently|in|the|"
        r"around|on|for|what|are|some)\b",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = " ".join(cleaned.strip(" ?.!,").split())
    return cleaned[:100] or os.getenv("NEWS_DEFAULT_QUERY", "Nigeria")


def _default_get(url: str, **kwargs):
    return httpx.get(url, **kwargs)


def fetch_live_news(
    message: str,
    *,
    get: Callable[..., Any] = _default_get,
) -> list[NewsArticle]:
    if not is_live_news_request(message) or not live_news_enabled():
        return []
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key:
        return []
    response = get(
        NEWS_API_URL,
        params={
            "q": _news_query(message),
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": int(os.getenv("NEWS_RESULT_LIMIT", "5")),
        },
        headers={"X-Api-Key": api_key},
        timeout=float(os.getenv("NEWS_API_TIMEOUT_SECONDS", "8")),
    )
    response.raise_for_status()
    payload = response.json()
    articles: list[NewsArticle] = []
    for item in payload.get("articles", []):
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        source = str((item.get("source") or {}).get("name") or "Unknown source").strip()
        published_at = str(item.get("publishedAt") or "").strip()
        if not title or not url.startswith(("https://", "http://")):
            continue
        articles.append(
            NewsArticle(
                title=title[:300],
                source=source[:100],
                url=url,
                published_at=published_at,
                description=(str(item.get("description")).strip()[:500] if item.get("description") else None),
            )
        )
    return articles


def format_live_news(reply: str, articles: list[NewsArticle]) -> str:
    if not articles:
        return reply
    lines = []
    for article in articles:
        date_label = article.published_at
        try:
            date_label = datetime.fromisoformat(article.published_at.replace("Z", "+00:00")).strftime("%d %b %Y, %H:%M UTC")
        except (TypeError, ValueError):
            pass
        lines.append(f"- [{article.title}]({article.url}) — {article.source}, {date_label}")
    return f"{reply.rstrip()}\n\n**Current articles:**\n" + "\n".join(lines)
