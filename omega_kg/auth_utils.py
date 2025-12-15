import hmac
from datetime import datetime, timedelta, timezone
from typing import Optional, Set, Dict, Any
from fastapi import Depends, HTTPException, status, Security, Request
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel

from omega_kg.settings import settings

# SECURITY HARDENING: JWT Algorithm Validation (AUTH-001)
# Only allow secure algorithms - reject 'none' and weak algorithms
SECURE_JWT_ALGORITHMS: Set[str] = {"HS256", "HS384", "HS512", "RS256", "RS384", "RS512", "ES256", "ES384", "ES512"}
INSECURE_ALGORITHMS: Set[str] = {"none", "None", "NONE", "HS1", "HS224"}

# CONFIG
SECRET_KEY = settings.jwt_secret_key
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.jwt_expiration_minutes
EXTENSION_API_KEY = settings.extension_api_key

# Rate limiting for API key validation
API_KEY_ATTEMPTS_LIMIT = 5
API_KEY_WINDOW_SECONDS = 300  # 5 minutes

# Validate JWT algorithm at startup
if ALGORITHM not in SECURE_JWT_ALGORITHMS:
    raise ValueError(f"INSECURE JWT algorithm configured: {ALGORITHM}. Must be one of: {SECURE_JWT_ALGORITHMS}")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")
API_KEY_HEADER = APIKeyHeader(name="X-API-Key")


# MODELS
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


# UTILS
# Rate limiting storage (in production, use Redis or similar)
_attempts_storage = {}

def _check_rate_limit(client_ip: str) -> bool:
    """
    SECURITY HARDENING (AUTH-004): Check rate limiting for API key attempts.
    
    Args:
        client_ip: Client IP address for rate limiting
        
    Returns:
        bool: True if request should be allowed, False if rate limited
    """
    import time
    
    current_time = time.time()
    client_key = f"api_key_attempts_{client_ip}"
    
    # Get or initialize attempt tracking
    if client_key not in _attempts_storage:
        _attempts_storage[client_key] = {"count": 0, "first_attempt": current_time}
    
    client_data = _attempts_storage[client_key]
    
    # Reset if outside time window
    if current_time - client_data["first_attempt"] > API_KEY_WINDOW_SECONDS:
        _attempts_storage[client_key] = {"count": 0, "first_attempt": current_time}
        client_data = _attempts_storage[client_key]
    
    # Check if rate limit exceeded
    if client_data["count"] >= API_KEY_ATTEMPTS_LIMIT:
        return False
    
    # Increment attempt counter
    client_data["count"] += 1
    return True

def get_static_api_key(
    request: Request,
    api_key_header: str = Security(API_KEY_HEADER),
) -> str:
    """
    SECURITY HARDENING (AUTH-004): Validates the static X-API-Key with rate limiting.
    
    Args:
        api_key_header: X-API-Key header value
        request: FastAPI request object for IP extraction
        
    Returns:
        str: Validated API key
        
    Raises:
        HTTPException: For invalid keys, missing headers, or rate limiting
    """
    # Get client IP for rate limiting
    client_ip = request.client.host if request.client else "unknown"
    
    # Check rate limiting
    if not _check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please try again later.",
        )
    
    # Validate API key configuration
    if not EXTENSION_API_KEY:
        # Log critical configuration error
        import logging
        logger = logging.getLogger(__name__)
        logger.critical("EXTENSION_API_KEY not configured - server misconfiguration")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server misconfiguration: Authentication unavailable",
        )

    # Validate header presence
    if not api_key_header:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing authentication credentials",
        )

    # Use constant-time comparison to prevent timing attacks
    try:
        if hmac.compare_digest(api_key_header, EXTENSION_API_KEY):
            # Successful authentication - reset rate limit
            client_key = f"api_key_attempts_{client_ip}"
            if client_key in _attempts_storage:
                del _attempts_storage[client_key]
            return api_key_header
    except Exception:
        # Log validation error without leaking API key details
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("API key validation error for IP: %s", client_ip)
    
    # Failed authentication - don't reveal specific error details
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid or missing authentication credentials",
    )


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    SECURITY HARDENING (AUTH-001): Create JWT token with strict algorithm validation.
    
    Args:
        data: Dictionary containing token payload
        expires_delta: Optional custom expiration time
        
    Returns:
        str: Encoded JWT token
        
    Raises:
        ValueError: If algorithm is insecure or data is invalid
    """
    # Create payload with expiration
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta
        else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    
    # Double-check algorithm validation before encoding
    if ALGORITHM not in SECURE_JWT_ALGORITHMS:
        raise ValueError(f"INSECURE JWT algorithm: {ALGORITHM}")
    
    # Create token with secure algorithm
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def validate_access_token(token: str = Depends(oauth2_scheme)) -> TokenData:
    """
    SECURITY HARDENING (AUTH-001): Validate JWT token with strict algorithm validation.
    
    Args:
        token: JWT token to validate
        
    Returns:
        TokenData: Validated token data
        
    Raises:
        HTTPException: If token is invalid, expired, or uses insecure algorithm
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode with strict algorithm validation
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Extract and validate username/subject
        username = payload.get("sub")
        if username is None or not isinstance(username, str):
            raise credentials_exception
            
        # Additional validation: check for required fields
        if not payload.get("exp"):
            raise credentials_exception
            
        return TokenData(username=username)
        
    except JWTError as e:
        # Log failed validation attempt (security monitoring)
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("JWT validation failed: %s", str(e))
        raise credentials_exception from e
