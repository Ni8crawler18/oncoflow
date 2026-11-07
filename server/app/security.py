"""Password hashing (stdlib PBKDF2) and JWT token helpers.

No external crypto deps — uses hashlib for hashing and PyJWT (already a
dependency) for signed tokens.
"""
import hashlib
import hmac
import os
import base64
from datetime import datetime, timedelta, timezone

import jwt

from .config import settings

_ITER = 200_000
_ALGO = "HS256"
TOKEN_TTL_HOURS = 24 * 7


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITER)
    return f"pbkdf2_sha256${_ITER}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, b64salt, b64hash = stored.split("$")
        salt = base64.b64decode(b64salt)
        expected = base64.b64decode(b64hash)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iters))
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


def create_token(user_id: int, email: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGO)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[_ALGO])
    except Exception:
        return None
