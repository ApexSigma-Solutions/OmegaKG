"""
Authentication utilities for JWT token management.

Provides functions for:
- Static API key validation (bootstrap authentication)
- JWT token creation and validation
- Bearer token extraction and validation

Security features:
- Uses hmac.compare_digest for constant-time comparison
- Proper error handling with meaningful messages
- Timezone-aware datetime operations
"""

import hmac
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from jose import JWTError, jwt
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from omega_kg.settings import settings


# --- Static API Key (Bootstrap Authentication) ---

API_KEY_HEADER = APIKeyHeader(name="X-API-Key")


def get_static_api_key(api_key_header: str = Security(API_KEY_HEADER)) -> str:
    """
    Validates the static X-API-Key for the /auth/token endpoint.

    This is the bootstrap mechanism: clients exchange a static API key for a
    short-lived JWT token. Only the /auth/token endpoint uses this validation.

    Args:
        api_key_header: API key from X-API-Key header

    Returns:
        The validated API key

    Raises:
        HTTPException: 403 Forbidden if API key is invalid or missing
    """
    if hmac.compare_digest(api_key_header, settings.extension_api_key):
        return api_key_header

    raise HTTPException(
        status_code=HTTP_403_FORBIDDEN,
        detail="Invalid or missing Bootstrap API Key",
    )


# --- JWT (Dynamic Token Authentication) ---

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def create_access_token(data: Dict[str, Any]) -> str:
    """
    Creates a new JWT access token with expiration.

    The token includes all data from the input dict plus an expiration time
    calculated from JWT_EXPIRATION_MINUTES setting.

    Args:
        data: Dictionary to encode in the token (e.g., {"sub": "username"})

    Returns:
        Encoded JWT token string

    Example:
        >>> token = create_access_token({"sub": "extension-client"})
        >>> # token can now be sent in Authorization: Bearer <token>
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_expiration_minutes
    )
    to_encode.update({"exp": expire})

    encoded_jwt: str = jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def validate_access_token(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    Validates a JWT Bearer token and returns its payload.

    This function is used as a dependency in FastAPI routes to automatically
    extract and validate the Bearer token from the Authorization header.

    Args:
        token: JWT token from Authorization: Bearer header

    Returns:
        Decoded token payload (dict)

    Raises:
        HTTPException: 401 Unauthorized if token is invalid or expired

    Example:
        >>> @app.get("/protected")
        >>> async def protected_route(payload: dict = Depends(validate_access_token)):
        ...     return {"user": payload.get("sub")}
    """
    credentials_exception = HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload: Dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception
