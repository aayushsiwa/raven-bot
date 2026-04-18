import hashlib
import hmac
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode

from fastapi import HTTPException

import config


def _b64url_encode(data: bytes) -> str:
    return urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return urlsafe_b64decode(f"{data}{pad}")


def hash_password(password: str) -> str:
    salt = hashlib.sha256(str(time.time_ns()).encode("utf-8")).digest()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 240000)
    return f"pbkdf2_sha256${_b64url_encode(salt)}${_b64url_encode(digest)}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, salt_raw, digest_raw = password_hash.split("$", 2)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = _b64url_decode(salt_raw)
        expected_digest = _b64url_decode(digest_raw)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 240000)
        return hmac.compare_digest(digest, expected_digest)
    except Exception:
        return False


def sign_session_token(user_id: int, username: str) -> str:
    issued_at = int(time.time())
    expires_at = issued_at + config.AUTH_TOKEN_TTL_SECONDS
    payload = f"{user_id}:{username}:{issued_at}:{expires_at}".encode("utf-8")
    sig = hmac.new(config.AUTH_SECRET.encode("utf-8"), payload, hashlib.sha256).digest()
    return f"{_b64url_encode(payload)}.{_b64url_encode(sig)}"


def parse_session_token(token: str) -> dict:
    try:
        payload_part, sig_part = token.split(".", 1)
        payload = _b64url_decode(payload_part)
        sig = _b64url_decode(sig_part)
        expected = hmac.new(config.AUTH_SECRET.encode("utf-8"), payload, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            raise ValueError("Invalid signature")

        user_id_str, username, issued_at_str, expires_at_str = payload.decode("utf-8").split(":", 3)
        expires_at = int(expires_at_str)
        if expires_at < int(time.time()):
            raise ValueError("Token expired")

        return {
            "user_id": int(user_id_str),
            "username": username,
            "issued_at": int(issued_at_str),
            "expires_at": expires_at,
        }
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


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
