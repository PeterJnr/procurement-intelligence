import os
import secrets

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader


market_admin_key_header = APIKeyHeader(
    name="X-Admin-API-Key",
    auto_error=False,
)


def verify_market_admin_key(
    api_key: str | None = Security(market_admin_key_header),
) -> None:
    """Protect operational market-data endpoints with a minimal MVP key."""
    expected_key = os.getenv("MARKET_ADMIN_API_KEY")
    if not expected_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Market administration is not configured",
        )
    if api_key is None or not secrets.compare_digest(api_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing market administration key",
        )

