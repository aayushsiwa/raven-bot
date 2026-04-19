import hashlib
import hmac
import re
import time

import jwt

from fastapi import HTTPException

import config
from services.redis import is_token_blacklisted


PASSWORD_UPPER = re.compile(r"[A-Z]")
PASSWORD_LOWER = re.compile(r"[a-z]")
PASSWORD_DIGIT = re.compile(r"\d")
PASSWORD_SYMBOL = re.compile(r"[^A-Za-z0-9]")


def hash_password(password: str) -> str:
    salt = hashlib.sha256(str(time.time_ns()).encode("utf-8")).digest()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 240000)
    return f"pbkdf2_sha256${jwt.utils.base64url_encode(salt).decode('utf-8')}${jwt.utils.base64url_encode(digest).decode('utf-8')}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, salt_raw, digest_raw = password_hash.split("$", 2)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = jwt.utils.base64url_decode(salt_raw.encode("utf-8"))
        expected_digest = jwt.utils.base64url_decode(digest_raw.encode("utf-8"))
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 240000)
        return hmac.compare_digest(digest, expected_digest)
    except Exception:
        return False


def validate_password_or_422(password: str):
    if len(password) < 8 or len(password) > 128:
        raise HTTPException(status_code=422, detail="Password length must be 8..128")
    if " " in password:
        raise HTTPException(status_code=422, detail="Password must not include spaces")
    if not PASSWORD_UPPER.search(password):
        raise HTTPException(status_code=422, detail="Password needs uppercase letter")
    if not PASSWORD_LOWER.search(password):
        raise HTTPException(status_code=422, detail="Password needs lowercase letter")
    if not PASSWORD_DIGIT.search(password):
        raise HTTPException(status_code=422, detail="Password needs digit")
    if not PASSWORD_SYMBOL.search(password):
        raise HTTPException(status_code=422, detail="Password needs symbol")


def sign_session_token(user_id: int, username: str) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": now,
        "exp": now + config.AUTH_ACCESS_TOKEN_TTL_SECONDS,
        "typ": "access",
        "iss": config.AUTH_ISSUER,
    }
    return jwt.encode(payload, config.AUTH_SECRET, algorithm="HS256")


def sign_refresh_token(user_id: int, username: str) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": now,
        "exp": now + config.AUTH_REFRESH_TOKEN_TTL_SECONDS,
        "typ": "refresh",
        "iss": config.AUTH_ISSUER,
    }
    return jwt.encode(payload, config.AUTH_SECRET, algorithm="HS256")


def parse_session_token(token: str) -> dict:
    if is_token_blacklisted(token):
        raise HTTPException(status_code=401, detail="Token has been revoked")
    try:
        payload = jwt.decode(
            token,
            config.AUTH_SECRET,
            algorithms=["HS256"],
            issuer=config.AUTH_ISSUER,
        )
        return {
            "user_id": int(payload["sub"]),
            "username": str(payload["username"]),
            "issued_at": int(payload["iat"]),
            "expires_at": int(payload["exp"]),
        }
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


def parse_refresh_token(token: str) -> dict:
    if is_token_blacklisted(token):
        raise HTTPException(status_code=401, detail="Refresh token has been revoked")
    try:
        payload = jwt.decode(
            token,
            config.AUTH_SECRET,
            algorithms=["HS256"],
            issuer=config.AUTH_ISSUER,
        )
        if payload.get("typ") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        return {
            "user_id": int(payload["sub"]),
            "username": str(payload["username"]),
            "issued_at": int(payload["iat"]),
            "expires_at": int(payload["exp"]),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token") from exc


def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    token = authorization[len(prefix):].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return token
