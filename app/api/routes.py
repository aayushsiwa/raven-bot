from typing import Optional, List

import config
from discord.ext import commands
from fastapi import APIRouter, HTTPException, Query, Header
from services import db
from services.redis import redis_client
from skills.rss_cache import fetch_feed_with_cache
from datetime import datetime

from app.api.deps import normalize_feed_path
from app.api.schemas import SubscriptionDeletePayload, SubscriptionPayload, BatchRssPayload
from app.api.auth import (
    extract_bearer_token,
    hash_password,
    parse_session_token,
    sign_session_token,
    validate_password_or_422,
    verify_password,
)
from app.api.schemas import FeedPreferencesPayload, LoginPayload, OAuthLoginPayload, SignupPayload


def create_api_router(bot: commands.Bot) -> APIRouter:
    router = APIRouter()

    allowed_oauth_providers = {"google", "github", "discord"}

    def sanitize_username(value: str) -> str:
        normalized = value.strip()
        if not (3 <= len(normalized) <= 32):
            raise HTTPException(status_code=422, detail="Username length must be 3..32")
        if not all(ch.isalnum() or ch in {"_", "-", "."} for ch in normalized):
            raise HTTPException(status_code=422, detail="Username has invalid characters")
        return normalized

    @router.head("/health")
    async def health_head():
        return {"status": "ok"}

    @router.get("/health")
    async def health():
        redis_status = "ok"
        try:
            redis_client.ping()
        except Exception as e:
            redis_status = f"error: {str(e)}"

        db_status = "ok"
        try:
            await db.ping()
        except Exception as e:
            db_status = f"error: {str(e)}"

        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "bot": {
                "ready": bot.is_ready(),
                "user": str(bot.user) if bot.user else None,
                "latency_ms": round(bot.latency * 1000) if bot.is_ready() else None,
            },
            "db": db_status,
            "redis": redis_status,
        }

    @router.post("/api/v1/auth/signup")
    async def signup(payload: SignupPayload):
        username = sanitize_username(payload.username)
        validate_password_or_422(payload.password)
        exists = await db.username_exists(username)
        if exists:
            raise HTTPException(status_code=409, detail="Username already exists")

        user = await db.create_local_user(username, hash_password(payload.password))
        if not user:
            raise HTTPException(status_code=409, detail="Username already exists")

        token = sign_session_token(user["id"], user["username"])
        return {
            "token": token,
            "user": user,
        }

    @router.post("/api/v1/auth/login")
    async def login(payload: LoginPayload):
        username = sanitize_username(payload.username)
        user = await db.get_user_by_username(username)
        if not user or not user.get("password_hash"):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not verify_password(payload.password, str(user["password_hash"])):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = sign_session_token(user["id"], user["username"])
        return {
            "token": token,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user.get("email"),
                "display_name": user.get("display_name"),
                "avatar_url": user.get("avatar_url"),
                "auth_source": user.get("auth_source"),
                "created_at": user.get("created_at"),
            },
        }

    @router.post("/api/v1/auth/oauth")
    async def oauth_login(payload: OAuthLoginPayload):
        provider = payload.provider.strip().lower()
        if provider not in allowed_oauth_providers:
            raise HTTPException(status_code=422, detail="Unsupported provider")

        username = sanitize_username(payload.username)

        existing = await db.get_user_by_oauth(provider, payload.provider_user_id)
        if existing:
            token = sign_session_token(existing["id"], existing["username"])
            return {"token": token, "user": existing}

        user = await db.create_oauth_user(
            username=username,
            provider=provider,
            provider_user_id=payload.provider_user_id,
            email=payload.email,
            display_name=payload.display_name,
            avatar_url=payload.avatar_url,
        )
        if not user:
            raise HTTPException(status_code=409, detail="Username already exists")

        token = sign_session_token(user["id"], user["username"])
        return {"token": token, "user": user}

    @router.get("/api/v1/auth/me")
    async def auth_me(authorization: Optional[str] = Header(default=None)):
        token = extract_bearer_token(authorization)
        claims = parse_session_token(token)
        user = await db.get_user_by_id(claims["user_id"])
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return {"user": user}

    @router.get("/api/v1/user/feed-preferences")
    async def get_user_feed_preferences(authorization: Optional[str] = Header(default=None)):
        token = extract_bearer_token(authorization)
        claims = parse_session_token(token)
        user = await db.get_user_by_id(claims["user_id"])
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        choices = await db.list_user_feed_preferences(claims["user_id"])
        return {"choices": choices}

    @router.put("/api/v1/user/feed-preferences")
    async def put_user_feed_preferences(
        payload: FeedPreferencesPayload,
        authorization: Optional[str] = Header(default=None),
    ):
        token = extract_bearer_token(authorization)
        claims = parse_session_token(token)
        user = await db.get_user_by_id(claims["user_id"])
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        normalized = []
        seen = set()
        for choice in payload.choices:
            provider, category, topic = normalize_feed_path(choice.provider, choice.category, choice.topic)
            dedupe_key = f"{provider}:{category}:{topic}"
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            normalized.append({
                "provider": provider,
                "category": category,
                "topic": topic,
            })

        await db.replace_user_feed_preferences(claims["user_id"], normalized)
        return {"choices": normalized}

    @router.get("/api/v1/tree")
    async def get_feed_tree():
        """Returns the full provider/category/topic tree in one request."""
        tree = {}
        for provider, categories in config.FEED_MAP.items():
            tree[provider] = {}
            for category, topics in categories.items():
                tree[provider][category] = list(topics.keys())
        return {"tree": tree}

    @router.get("/api/v1/providers")
    async def list_providers():
        return {"providers": list(config.FEED_MAP.keys())}

    @router.get("/api/v1/providers/{provider}/categories")
    async def list_categories(provider: str):
        provider = provider.lower()

        if provider not in config.FEED_MAP:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Unknown provider",
                    "available": list(config.FEED_MAP.keys()),
                },
            )

        return {
            "provider": provider,
            "categories": list(config.FEED_MAP[provider].keys()),
        }

    @router.get("/api/v1/providers/{provider}/categories/{category}/topics")
    async def list_topics(provider: str, category: str):
        provider, category, _ = normalize_feed_path(provider, category)

        return {
            "provider": provider,
            "category": category,
            "topics": list(config.FEED_MAP[provider][category].keys()),
        }

    @router.get("/api/v1/rss")
    async def fetch_rss_entries(
        provider: str = Query(..., description="RSS provider"),
        category: str = Query(..., description="RSS category"),
        topic: str = Query(..., description="RSS topic"),
        limit: int = Query(5, ge=1, le=30),
    ):
        provider, category, topic = normalize_feed_path(provider, category, topic)

        entries = fetch_feed_with_cache(provider, category, topic, limit=limit)

        return {
            "provider": provider,
            "category": category,
            "topic": topic,
            "generated_at": datetime.utcnow().isoformat(),
            "count": len(entries),
            "entries": entries,
        }

    @router.post("/api/v1/batch/rss")
    async def fetch_batch_rss_entries(payload: BatchRssPayload):
        """Fetches multiple RSS feeds in one request."""
        results = []
        for feed in payload.feeds:
            try:
                p, c, t = normalize_feed_path(feed.provider, feed.category, feed.topic)
                entries = fetch_feed_with_cache(p, c, t, limit=payload.limit)
                results.append({
                    "provider": p,
                    "category": c,
                    "topic": t,
                    "count": len(entries),
                    "entries": entries,
                })
            except Exception:
                # Skip failed feeds in batch
                continue
        
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "results": results
        }

    @router.post("/api/v1/subscriptions")
    async def create_subscription(payload: SubscriptionPayload):
        provider, category, topic = normalize_feed_path(
            payload.provider,
            payload.category,
            payload.topic,
        )

        success = await db.add_subscription(
            payload.channel_id,
            payload.guild_id,
            provider,
            category,
            topic,
        )

        if not success:
            raise HTTPException(
                status_code=409,
                detail="Subscription already exists",
            )

        return {
            "status": "created",
            "subscription": {
                "channel_id": payload.channel_id,
                "guild_id": payload.guild_id,
                "provider": provider,
                "category": category,
                "topic": topic,
            },
        }

    @router.delete("/api/v1/subscriptions")
    async def delete_subscription(payload: SubscriptionDeletePayload):
        provider, category, topic = normalize_feed_path(
            payload.provider,
            payload.category,
            payload.topic,
        )

        await db.remove_subscription(
            payload.channel_id,
            provider,
            category,
            topic,
        )

        return {
            "status": "deleted",
            "subscription": {
                "channel_id": payload.channel_id,
                "provider": provider,
                "category": category,
                "topic": topic,
            },
        }

    @router.get("/api/v1/subscriptions")
    async def list_subscriptions(channel_id: Optional[int] = Query(None, gt=0)):
        if channel_id is not None:
            subs = await db.list_subscriptions(channel_id)
            return {
                "channel_id": channel_id,
                "subscriptions": [dict(sub) for sub in subs],
            }

        subs = await db.get_all_subscriptions()
        return {
            "subscriptions": [dict(sub) for sub in subs],
        }

    return router
