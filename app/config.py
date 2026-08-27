import os

from dotenv import load_dotenv


load_dotenv()


TRUTHY_VALUES = {"true", "1", "yes"}
DEFAULT_CORS_ORIGINS = "http://localhost:3000,http://localhost:5173"


def feature_enabled(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).casefold() in TRUTHY_VALUES


def cors_allowed_origins() -> list[str]:
    raw_value = os.getenv("CORS_ALLOWED_ORIGINS", DEFAULT_CORS_ORIGINS)
    origins = [value.strip().rstrip("/") for value in raw_value.split(",") if value.strip()]
    if not origins:
        raise RuntimeError("CORS_ALLOWED_ORIGINS must contain at least one origin")
    if "*" in origins:
        raise RuntimeError("Wildcard CORS origins are not allowed")
    return origins


def _require(settings: list[str], errors: list[str], feature: str) -> None:
    missing = [name for name in settings if not os.getenv(name)]
    if missing:
        errors.append(f"{feature} requires: {', '.join(missing)}")


def validate_configuration() -> None:
    """Fail startup with setting names only; never expose secret values."""
    errors: list[str] = []
    _require(["DATABASE_URL", "MARKET_ADMIN_API_KEY"], errors, "Core API")

    if feature_enabled("ENABLE_MARKET_SCHEDULER", "true"):
        _require(["CRAWLER_CONTACT"], errors, "Market scheduler")

    if feature_enabled("ENABLE_VECTOR_SYNC"):
        _require(
            [
                "HF_TOKEN",
                "HF_EMBEDDING_MODEL",
                "PINECONE_API_KEY",
                "PINECONE_INDEX_NAME",
                "PINECONE_NAMESPACE",
            ],
            errors,
            "Vector synchronization",
        )

    if feature_enabled("ENABLE_SEMANTIC_RETRIEVAL"):
        _require(
            [
                "HF_TOKEN",
                "HF_EMBEDDING_MODEL",
                "PINECONE_API_KEY",
                "PINECONE_INDEX_NAME",
                "PINECONE_NAMESPACE",
            ],
            errors,
            "Semantic retrieval",
        )
        try:
            threshold = float(os.getenv("PINECONE_MIN_SIMILARITY", "0.65"))
            if not 0 <= threshold <= 1:
                raise ValueError
        except ValueError:
            errors.append("PINECONE_MIN_SIMILARITY must be between 0 and 1")

    if feature_enabled("ENABLE_LANGCHAIN_EXPLANATION"):
        _require(["HF_TOKEN"], errors, "LangChain explanation")

    if feature_enabled("ENABLE_CHAT_AI"):
        _require(["HF_TOKEN"], errors, "AI chat")

    if feature_enabled("ENABLE_LIVE_NEWS"):
        _require(["NEWS_API_KEY"], errors, "Live news")
        for name, default, minimum, maximum in (
            ("NEWS_RESULT_LIMIT", "5", 1, 10),
            ("NEWS_API_TIMEOUT_SECONDS", "8", 1, 30),
        ):
            try:
                value = float(os.getenv(name, default))
                if not minimum <= value <= maximum:
                    raise ValueError
            except ValueError:
                errors.append(f"{name} must be between {minimum} and {maximum}")

    if feature_enabled("ENABLE_RATE_LIMITING", "true"):
        for name, default, minimum, maximum in (
            ("AI_RATE_LIMIT_REQUESTS", "20", 1, 10000),
            ("AI_RATE_LIMIT_WINDOW_SECONDS", "60", 1, 86400),
        ):
            try:
                value = int(os.getenv(name, default))
                if not minimum <= value <= maximum:
                    raise ValueError
            except ValueError:
                errors.append(
                    f"{name} must be an integer between {minimum} and {maximum}"
                )

    try:
        cors_allowed_origins()
    except RuntimeError as error:
        errors.append(str(error))

    if errors:
        raise RuntimeError("Invalid application configuration: " + "; ".join(errors))
