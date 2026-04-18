import redis
from config import (
    REDIS_URL,
    AUTH_TOKEN_TTL_SECONDS,
)

redis_client = redis.from_url(REDIS_URL)

TOKEN_BLACKLIST_PREFIX = "auth:token:blacklist:"
RATE_LIMIT_PREFIX = "ratelimit:"
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 10  # requests per window


def blacklist_session_token(token: str) -> None:
    """Add token to blacklist until expiry."""
    key = f"{TOKEN_BLACKLIST_PREFIX}{token}"
    redis_client.setex(key, AUTH_TOKEN_TTL_SECONDS, "1")


def is_token_blacklisted(token: str) -> bool:
    """Check if token is blacklisted."""
    key = f"{TOKEN_BLACKLIST_PREFIX}{token}"
    return redis_client.exists(key) > 0


def check_rate_limit(ip: str) -> bool:
    """Check if IP is within rate limit. Return True if allowed."""
    key = f"{RATE_LIMIT_PREFIX}{ip}"
    count = redis_client.incr(key)
    if count == 1:
        redis_client.expire(key, RATE_LIMIT_WINDOW)
    return count <= RATE_LIMIT_MAX


def get_rate_limit_remaining(ip: str) -> int:
    """Get remaining requests in current window."""
    key = f"{RATE_LIMIT_PREFIX}{ip}"
    count = redis_client.get(key)
    if not count:
        return RATE_LIMIT_MAX
    return max(0, RATE_LIMIT_MAX - int(count))
