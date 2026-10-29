"""Invite-only access: verify Supabase Auth access tokens on API requests.

Supabase signs access tokens with an asymmetric key and publishes the public
half as a JWKS, so tokens are verified locally without calling Supabase on
every request. Sign-ups are disabled in Supabase, so only invited users can
get a token (see tools/invite.py).
"""
import logging
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings

log = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)


def jwks_client(settings: Settings) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(f"{settings.supabase_issuer}/.well-known/jwks.json", cache_keys=True, lifespan=3600)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"})


def require_user(
    request: Request, credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer)
) -> dict:
    """FastAPI dependency: the verified token claims, or 401.

    A plain function, so FastAPI runs it in a thread pool and the occasional
    JWKS fetch doesn't block the event loop.
    """
    if credentials is None:
        raise _unauthorized("Sign in required")
    settings: Settings = request.app.state.settings
    token = credentials.credentials
    try:
        key = request.app.state.jwks.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            key.key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
            issuer=settings.supabase_issuer,
        )
    except jwt.PyJWKClientConnectionError:
        log.exception("Could not fetch signing keys from Supabase")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Authentication unavailable")
    except jwt.PyJWTError:
        raise _unauthorized("Invalid or expired session")
