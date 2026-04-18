from typing import Optional, List

import config
from discord.ext import commands
from fastapi import APIRouter, HTTPException, Query
from services import db
from services.redis import redis_client
from skills.rss_cache import fetch_feed_with_cache
from datetime import datetime

from app.api.deps import normalize_feed_path
from app.api.schemas import SubscriptionDeletePayload, SubscriptionPayload, BatchRssPayload


def create_api_router(bot: commands.Bot) -> APIRouter:
    router = APIRouter()

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
