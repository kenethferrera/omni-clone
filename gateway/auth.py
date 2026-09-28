from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from gateway.config import get_settings
import time

settings = get_settings()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
security_bearer = HTTPBearer(auto_error=False)


def create_jwt_token(data: dict) -> str:
    """Generate a JWT token for authorized API access."""
    to_encode = data.copy()
    expire = time.time() + (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def verify_authentication(
    api_key: str = Security(api_key_header),
    credentials: HTTPAuthorizationCredentials = Security(security_bearer)
):
    """
    Validate client access using either X-API-Key header or Bearer JWT token.
    Raises HTTP 401 if authentication fails.
    """
    # 1. Check API Key
    if api_key and api_key == settings.API_KEY:
        return {"auth_type": "api_key", "sub": "api_key_client"}

    # 2. Check Bearer JWT Token
    if credentials:
        token = credentials.credentials
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM]
            )
            return {"auth_type": "jwt", "sub": payload.get("sub", "authenticated_user")}
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 3. Fallback error if no valid auth provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid authentication credentials (API Key or Bearer token required)",
        headers={"WWW-Authenticate": "Bearer / X-API-Key"},
    )
