"""
auth_middleware.py — JWT verification for protected FastAPI routes.

Usage in any route:
    from auth_middleware import get_current_user
    @router.get("/protected")
    async def protected(user = Depends(get_current_user)):
        return {"email": user["email"]}
"""

import logging
from typing import Dict, Any

import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import get_settings

log = logging.getLogger(__name__)
bearer = HTTPBearer()
settings = get_settings()

jwks_url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
jwks_client = PyJWKClient(jwks_url)

def _decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify a Supabase JWT.
    Supports both legacy HS256 (symmetric) and new ES256/RS256 (asymmetric JWKS).
    """
    try:
        unverified_header = jwt.get_unverified_header(token)
        if 'kid' in unverified_header:
            # New Asymmetric Key (ECC / RS256)
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256", "HS256"],
                options={"verify_aud": False},
            )
        else:
            # Legacy HS256 Symmetric Key
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> Dict[str, Any]:
    """
    FastAPI dependency — extracts and validates the JWT from the
    Authorization: Bearer <token> header.

    Returns the decoded payload which contains:
        sub  → user UUID
        email
        role → "authenticated"
    """
    payload = _decode_token(credentials.credentials)
    user_id = payload.get("sub")
    email   = payload.get("email")

    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing required fields.",
        )

    return {
        "id":    user_id,
        "email": email,
        "role":  payload.get("role", "authenticated"),
        "_token": credentials.credentials,   # raw JWT for forwarding to Supabase
    }


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
) -> Dict[str, Any] | None:
    """
    Same as get_current_user but returns None instead of 401 when no
    token is provided. For endpoints that work both logged-in and anonymous.
    """
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None