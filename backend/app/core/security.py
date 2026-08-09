import secrets
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.config import settings

bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="BearerAuth",
    description="Bearer token authentication for securing API endpoints. Pass token as `Bearer <your_token>` in the Authorization header.",
)


async def verify_bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)
) -> str:
    """
    Verifies that the incoming request contains a valid Bearer token
    matching the API_BEARER_TOKEN environment variable.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token. Please provide a valid Bearer token in the Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expected_token = settings.API_BEARER_TOKEN
    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API authentication token is not configured on the server. Please set API_BEARER_TOKEN in .env.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(credentials.credentials, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials.credentials
