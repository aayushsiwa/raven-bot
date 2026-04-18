from typing import Optional, List
from urllib.parse import urlencode

import config
from discord.ext import commands
from fastapi import APIRouter, HTTPException, Query, Header
from config import logger
from fastapi.responses import RedirectResponse
from services import db
from services.redis import blacklist_session_token, redis_client
from skills.rss_cache import fetch_feed_with_cache
from datetime import datetime

from app.api.deps import normalize_feed_path
from app.api.schemas import SubscriptionDeletePayload, SubscriptionPayload, BatchRssPayload, CustomFeedPayload, CustomFeedUpdatePayload, LinkProviderPayload, SaveArticlePayload
from app.api.auth import (
    extract_bearer_token,
    hash_password,
    parse_session_token,
    sign_session_token,
    validate_password_or_422,
    verify_password,
)
from app.api.oauth import (
    build_oauth_start_url,
    create_oauth_state,
    exchange_code_for_profile,
    normalized_username_candidates,
    parse_oauth_state,
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

    async def auth_user_from_header(authorization: Optional[str]):
        token = extract_bearer_token(authorization)
        claims = parse_session_token(token)
        user = await db.get_user_by_id(claims["user_id"])
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user, claims

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
        logger.info(f"Signup attempt for username: {payload.username}")
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
        logger.info(f"Login attempt for username: {payload.username}")
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

    @router.get("/api/v1/auth/oauth/{provider}/start")
    async def oauth_start(provider: str, next: str = Query("/")):
        provider = provider.strip().lower()
        if provider not in allowed_oauth_providers:
            raise HTTPException(status_code=422, detail="Unsupported provider")

        state = create_oauth_state(provider, next_path=next)
        return {"url": build_oauth_start_url(provider, state)}

    @router.get("/api/v1/auth/oauth/{provider}/callback")
    async def oauth_callback(provider: str, code: str = Query(...), state: str = Query(...)):
        provider = provider.strip().lower()
        if provider not in allowed_oauth_providers:
            raise HTTPException(status_code=422, detail="Unsupported provider")

        state_payload = parse_oauth_state(provider, state)
        profile = await exchange_code_for_profile(provider, code)
        provider_user_id = str(profile.get("provider_user_id") or "")
        if not provider_user_id:
            raise HTTPException(status_code=401, detail="OAuth profile missing id")

        existing = await db.get_user_by_oauth(provider, provider_user_id)
        if existing:
            token = sign_session_token(existing["id"], existing["username"])
            query = urlencode({"token": token})
            target = f"{config.FRONTEND_URL}{state_payload.get('next', '/') }"
            joiner = "&" if "?" in target else "?"
            return RedirectResponse(url=f"{target}{joiner}{query}", status_code=302)

        chosen_user = None
        for candidate in normalized_username_candidates(provider, str(profile.get("username_seed") or provider)):
            try:
                chosen_user = await db.create_oauth_user(
                    username=sanitize_username(candidate),
                    provider=provider,
                    provider_user_id=provider_user_id,
                    email=profile.get("email"),
                    display_name=profile.get("display_name"),
                    avatar_url=profile.get("avatar_url"),
                )
            except Exception:
                chosen_user = None
            if chosen_user:
                break

        if not chosen_user:
            raise HTTPException(status_code=409, detail="Could not allocate username")

        token = sign_session_token(chosen_user["id"], chosen_user["username"])
        query = urlencode({"token": token})
        target = f"{config.FRONTEND_URL}{state_payload.get('next', '/') }"
        joiner = "&" if "?" in target else "?"
        return RedirectResponse(url=f"{target}{joiner}{query}", status_code=302)

    @router.get("/api/v1/auth/me")
    async def auth_me(authorization: Optional[str] = Header(default=None)):
        user, _ = await auth_user_from_header(authorization)
        return {"user": user}

    @router.post("/api/v1/auth/logout")
    async def logout(authorization: Optional[str] = Header(default=None)):
        """Blacklist current token and log out."""
        user, claims = await auth_user_from_header(authorization)
        token = extract_bearer_token(authorization)
        blacklist_session_token(token)
        return {"status": "logged out", "user_id": user["id"]}

    @router.get("/api/v1/user/feed-preferences")
    async def get_user_feed_preferences(authorization: Optional[str] = Header(default=None)):
        _, claims = await auth_user_from_header(authorization)

        choices = await db.list_user_feed_preferences(claims["user_id"])
        return {"choices": choices}

    @router.put("/api/v1/user/feed-preferences")
    async def put_user_feed_preferences(
        payload: FeedPreferencesPayload,
        authorization: Optional[str] = Header(default=None),
    ):
        _, claims = await auth_user_from_header(authorization)

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

    @router.post("/api/v1/user/feed-preferences/sync-local")
    async def sync_local_preferences_once(
        payload: FeedPreferencesPayload,
        authorization: Optional[str] = Header(default=None),
    ):
        _, claims = await auth_user_from_header(authorization)
        current = await db.list_user_feed_preferences(claims["user_id"])
        if current:
            return {"choices": current, "used": "db"}

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
        return {"choices": normalized, "used": "local"}

    @router.get("/api/v1/user/feed")
    async def get_user_personal_feed(
        authorization: Optional[str] = Header(default=None),
        limit: int = Query(12, ge=1, le=30),
    ):
        _, claims = await auth_user_from_header(authorization)

        choices = await db.list_user_feed_preferences(claims["user_id"])
        custom_feeds = await db.list_user_custom_feeds(claims["user_id"])

        results = []
        for choice in choices:
            try:
                p, c, t = normalize_feed_path(choice["provider"], choice["category"], choice["topic"])
                entries = fetch_feed_with_cache(p, c, t, limit=limit)
                results.append(
                    {
                        "provider": p,
                        "category": c,
                        "topic": t,
                        "count": len(entries),
                        "entries": entries,
                    }
                )
            except Exception:
                continue

        for feed in custom_feeds:
            if not feed.get("is_active"):
                continue
            try:
                entries = fetch_feed_with_url(feed["url"], limit=limit)
                results.append(
                    {
                        "provider": "custom",
                        "category": feed.get("category", "custom"),
                        "topic": feed.get("topic", "user"),
                        "feed_url": feed["url"],
                        "count": len(entries),
                        "entries": entries,
                    }
                )
            except Exception:
                continue

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "results": results,
        }

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

    @router.get("/api/v1/user/custom-feeds")
    async def get_custom_feeds(authorization: Optional[str] = Header(default=None)):
        user, claims = await auth_user_from_header(authorization)
        feeds = await db.list_user_custom_feeds(claims["user_id"])
        return {"feeds": feeds}

    @router.post("/api/v1/user/custom-feeds")
    async def create_custom_feed(
        payload: CustomFeedPayload,
        authorization: Optional[str] = Header(default=None),
    ):
        user, claims = await auth_user_from_header(authorization)
        feed = await db.add_user_custom_feed(
            claims["user_id"],
            payload.title,
            payload.url,
            payload.category,
            payload.topic,
        )
        if not feed:
            raise HTTPException(status_code=409, detail="Feed URL already exists")
        return {"feed": feed}

    @router.put("/api/v1/user/custom-feeds/{feed_id}")
    async def update_custom_feed(
        feed_id: int,
        payload: CustomFeedUpdatePayload,
        authorization: Optional[str] = Header(default=None),
    ):
        user, claims = await auth_user_from_header(authorization)
        feed = await db.update_user_custom_feed(
            claims["user_id"],
            feed_id,
            payload.title,
            payload.is_active,
        )
        if not feed:
            raise HTTPException(status_code=404, detail="Feed not found")
        return {"feed": feed}

    @router.delete("/api/v1/user/custom-feeds/{feed_id}")
    async def delete_custom_feed(
        feed_id: int,
        authorization: Optional[str] = Header(default=None),
    ):
        user, claims = await auth_user_from_header(authorization)
        deleted = await db.delete_user_custom_feed(claims["user_id"], feed_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Feed not found")
        return {"status": "deleted"}

    @router.get("/api/v1/user/link-provider/start")
    async def start_link_provider(
        provider: str,
        authorization: Optional[str] = Header(default=None),
    ):
        user, claims = await auth_user_from_header(authorization)
        provider = provider.strip().lower()
        if provider not in allowed_oauth_providers:
            raise HTTPException(status_code=422, detail="Unsupported provider")

        state = create_oauth_state(provider, next_path="/api/v1/user/link-provider/callback")
        await db.create_oauth_link_request(claims["user_id"], provider, state)
        return {"url": build_oauth_start_url(provider, state)}

    @router.post("/api/v1/user/link-provider")
    async def link_provider(
        payload: LinkProviderPayload,
        authorization: Optional[str] = Header(default=None),
    ):
        user, claims = await auth_user_from_header(authorization)
        provider = payload.provider.strip().lower()
        if provider not in allowed_oauth_providers:
            raise HTTPException(status_code=422, detail="Unsupported provider")

        request = await db.consume_oauth_link_request(provider, payload.state)
        if not request:
            raise HTTPException(status_code=400, detail="Invalid or expired link request")

        profile = await exchange_code_for_profile(provider, payload.code)
        provider_user_id = str(profile.get("provider_user_id") or "")
        if not provider_user_id:
            raise HTTPException(status_code=400, detail="OAuth profile missing id")

        linked = await db.link_oauth_account(
            claims["user_id"],
            provider,
            provider_user_id,
            profile.get("email"),
        )
        if not linked:
            raise HTTPException(status_code=409, detail="Account already linked to another user")

        return {"status": "linked", "provider": provider}

    @router.get("/api/v1/user/linked-accounts")
    async def get_linked_accounts(authorization: Optional[str] = Header(default=None)):
        user, claims = await auth_user_from_header(authorization)
        accounts = await db.list_oauth_accounts_for_user(claims["user_id"])
        return {"accounts": accounts}

    @router.get("/api/v1/user/saved-articles")
    async def get_saved_articles(authorization: Optional[str] = Header(default=None)):
        user, claims = await auth_user_from_header(authorization)
        articles = await db.list_user_saved_articles(claims["user_id"])
        return {"articles": articles}

    @router.post("/api/v1/user/saved-articles")
    async def save_article(
        payload: SaveArticlePayload,
        authorization: Optional[str] = Header(default=None),
    ):
        user, claims = await auth_user_from_header(authorization)
        article = await db.save_article(
            claims["user_id"],
            payload.title,
            payload.url,
            payload.summary,
            payload.source,
        )
        if not article:
            raise HTTPException(status_code=409, detail="Article already saved")
        return {"article": article}

    @router.delete("/api/v1/user/saved-articles/{article_id}")
    async def delete_saved_article(
        article_id: int,
        authorization: Optional[str] = Header(default=None),
    ):
        user, claims = await auth_user_from_header(authorization)
        deleted = await db.delete_saved_article(claims["user_id"], article_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Article not found")
        return {"status": "deleted"}

    return router
