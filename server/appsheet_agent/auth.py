"""
Authentication & Token Validation Module for Google OAuth and OIDC Tokens.

This module provides ContextVar-based header isolation and user validation,
extracting user identity (email) to pass into the AppSheet API 'RunAsUserEmail' property.

AI ASSISTANT GUIDE:
-------------------
Use `validate_jwt(token)` to extract claims. For Google OAuth opaque tokens (ya29...),
it queries Google's userinfo endpoint to obtain the authenticated user's email.
"""

import contextvars
import json
import os
import urllib.request
import jwt
from jwt import PyJWKClient

OAUTH_AUDIENCE: str = os.environ.get("OAUTH_AUDIENCE", "")
OAUTH_ISSUER: str = os.environ.get("OAUTH_ISSUER", "")

_jwks_client = None

def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None and OAUTH_ISSUER:
        issuer = OAUTH_ISSUER.rstrip("/")
        try:
            with urllib.request.urlopen(f"{issuer}/.well-known/openid-configuration") as r:
                jwks_uri = json.loads(r.read()).get("jwks_uri")
            if not jwks_uri:
                jwks_uri = f"{issuer}/.well-known/jwks.json"
        except Exception:
            jwks_uri = f"{issuer}/.well-known/jwks.json"
        _jwks_client = PyJWKClient(jwks_uri)
    return _jwks_client

# ContextVar storing the authorization token for the current HTTP request lifecycle
auth_token_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "auth_token", default=""
)

def validate_jwt(token: str) -> dict:
    """
    Validates a Bearer JWT or Google access token.
    
    Returns:
        dict: Claims dictionary containing 'email', 'sub', etc.
    """
    # 1. Google Opaque Access Token (starts with ya29.)
    if token.startswith("ya29."):
        try:
            req = urllib.request.Request(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {token}"}
            )
            with urllib.request.urlopen(req) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            raise jwt.PyJWTError(f"Invalid Google access token: {e}")

    # 2. Standard JWT validation
    jwks = _get_jwks_client()
    if not jwks:
        # If no issuer configured and not ya29, attempt unverified decode for email extraction in dev
        try:
            return jwt.decode(token, options={"verify_signature": False})
        except Exception as e:
            raise jwt.PyJWTError(f"Unable to parse token: {e}")

    signing_key = jwks.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=OAUTH_AUDIENCE or None,
        issuer=OAUTH_ISSUER or None,
    )
