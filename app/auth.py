import os

from clerk_backend_api import AuthenticateRequestOptions, authenticate_request
from fastapi import HTTPException, Request, status


def _authorized_parties() -> list[str]:
    value = os.getenv("CLERK_AUTHORIZED_PARTIES", "")
    return [item.strip().rstrip("/") for item in value.split(",") if item.strip()]


def require_user(request: Request) -> str:
    """Verify a Clerk session token and return its immutable user ID."""
    secret_key = os.getenv("CLERK_SECRET_KEY")
    parties = _authorized_parties()
    if not secret_key or not parties:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        )
    state = authenticate_request(
        request,
        AuthenticateRequestOptions(
            secret_key=secret_key,
            jwt_key=os.getenv("CLERK_JWT_KEY"),
            authorized_parties=parties,
            accepts_token=["session_token"],
        ),
    )
    user_id = state.payload.get("sub") if state.is_signed_in and state.payload else None
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in is required",
        )
    return str(user_id)
