"""Who is calling. Every /api/* route except the Firebase config needs a signed-in user.

Without this, anyone who finds your deployed URL can spend your team's MCP and LLM
quota through it. The browser sends the Firebase ID token it got at sign-in; this
checks Google's signature on it with Google's public keys. No Firebase Admin
credentials are involved, so it behaves the same on your laptop and on Cloud Run.
"""
import jwt
from fastapi import Header, HTTPException

from .config import FIREBASE_PROJECT_ID

# Fetched once, then cached and refreshed by PyJWKClient.
_KEYS = jwt.PyJWKClient(
    "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com")


def require_user(authorization: str = Header(default="")) -> str:
    """The signed-in user's Firebase uid, or 401 with the reason."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Sign in first — no Firebase ID token in Authorization")
    token = authorization.removeprefix("Bearer ")
    try:
        claims = jwt.decode(
            token, _KEYS.get_signing_key_from_jwt(token).key, algorithms=["RS256"],
            audience=FIREBASE_PROJECT_ID,
            issuer=f"https://securetoken.google.com/{FIREBASE_PROJECT_ID}")
    except jwt.PyJWTError as e:
        # Wrong audience/issuer means the token is from a different Firebase project
        # than FIREBASE_PROJECT_ID — the usual cause after switching projects.
        raise HTTPException(401, f"Firebase ID token rejected: {e}")
    return claims["sub"]
