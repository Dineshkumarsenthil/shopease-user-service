"""JWT validation only. Login/registration stay in the Authentication Service.

The token is verified locally with the secret shared with the Auth Service.
The user identity comes ONLY from the token ("sub"), never from the request body.
"""
from dataclasses import dataclass
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

bearer_scheme = HTTPBearer(auto_error=False)  # we raise our own 401


@dataclass
class AuthUser:
    user_id: int
    role: str


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, message, headers={"WWW-Authenticate": "Bearer"})


def get_current_auth_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> AuthUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("Not authenticated: Bearer token missing")
    try:
        payload = jwt.decode(credentials.credentials, settings.JWT_SECRET_KEY,
                             algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Token has expired")
    except jwt.PyJWTError:
        raise _unauthorized("Invalid token")
    try:
        return AuthUser(user_id=int(payload["sub"]), role=str(payload.get("role", "user")))
    except (KeyError, ValueError, TypeError):
        raise _unauthorized("Invalid token claims")
