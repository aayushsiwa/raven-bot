import json
import time
from datetime import datetime, timezone

import feedparser
from config import FEED_MAP
from services.redis import redis_client

REFETCH_INTERVAL_SECONDS = 60 * 60 * 12
RETENTION_SECONDS = 60 * 60 * 24 * 7
MAX_ENTRIES_PER_FEED = 1000


def get_seen_key(channel_id, provider, category, topic):
    return f"rss:seen:{channel_id}:{provider}:{category}:{topic}"


def get_feed_key(provider, category, topic):
    return f"rss:{provider}:{category}:{topic}"


def get_cache_key(provider, category, topic):
    return f"rss:cache:{provider}:{category}:{topic}"


def get_feed_meta_key(provider: str, category: str, topic: str) -> str:
    return f"rss:meta:{provider}:{category}:{topic}"


def get_cached_feed(provider, category, topic):
    payload = fetch_feed_with_cache_paginated(
        provider=provider,
        category=category,
        topic=topic,
        limit=30,
    )
    return payload["entries"]


def set_cached_feed(provider, category, topic, entries):
    now_ts = int(time.time())
    threshold = now_ts - RETENTION_SECONDS
    cache_key = get_cache_key(provider, category, topic)
    meta_key = get_feed_meta_key(provider, category, topic)

    pipeline = redis_client.pipeline()
    for entry in entries:
        score = entry_timestamp(entry, now_ts)
        pipeline.zadd(cache_key, {json.dumps(entry, separators=(",", ":")): score})

    pipeline.zremrangebyscore(cache_key, "-inf", threshold)
    pipeline.hset(meta_key, mapping={"last_fetched": str(now_ts)})
    pipeline.expire(cache_key, RETENTION_SECONDS * 2)
    pipeline.expire(meta_key, RETENTION_SECONDS * 2)
    pipeline.execute()
    trim_cache_to_limit(cache_key)


def trim_cache_to_limit(cache_key: str) -> None:
    total = redis_client.zcard(cache_key)
    if total <= MAX_ENTRIES_PER_FEED:
        return
    redis_client.zremrangebyrank(cache_key, 0, total - MAX_ENTRIES_PER_FEED - 1)


def entry_timestamp(entry: dict, fallback_ts: int) -> int:
    published_iso = entry.get("published_iso")
    if isinstance(published_iso, str) and published_iso:
        try:
            return int(datetime.fromisoformat(published_iso).timestamp())
        except ValueError:
            pass

    published_value = entry.get("published")
    if isinstance(published_value, str) and published_value:
        try:
            return int(datetime.fromisoformat(published_value).timestamp())
        except ValueError:
            pass

    return fallback_ts


def should_refetch(provider: str, category: str, topic: str) -> bool:
    cache_key = get_cache_key(provider, category, topic)
    meta_key = get_feed_meta_key(provider, category, topic)

    if redis_client.zcard(cache_key) == 0:
        return True

    last_fetched_raw = redis_client.hget(meta_key, "last_fetched")
    if not last_fetched_raw:
        return True

    try:
        last_fetched = int(last_fetched_raw)
    except (TypeError, ValueError):
        return True

    return (int(time.time()) - last_fetched) >= REFETCH_INTERVAL_SECONDS


def parse_feed_entries(feed) -> list[dict]:
    if not feed.entries:
        return []

    entries = []
    for entry in feed.entries[:100]:
        published_iso = None
        published_value = entry.get("published")
        parsed = entry.get("published_parsed") or entry.get("updated_parsed")

        if parsed:
            try:
                published_iso = datetime(*parsed[:6], tzinfo=timezone.utc).isoformat()
            except Exception:
                published_iso = None

        content_text = ""
        if entry.get("content") and isinstance(entry.get("content"), list):
            first = entry.get("content")[0]
            if isinstance(first, dict):
                content_text = str(first.get("value") or "")

        if not content_text:
            content_text = str(entry.get("summary") or "")

        entries.append(
            {
                "title": entry.get("title"),
                "link": entry.get("link"),
                "published": published_value,
                "published_iso": published_iso,
                "summary": entry.get("summary"),
                "content_text": content_text,
                "source": entry.get("source", {}).get("title")
                if isinstance(entry.get("source"), dict)
                else None,
            }
        )

    return entries


def fetch_feed_with_url(url: str, limit: int = 5):
    """Fetch arbitrary RSS/Atom URL (no caching)."""
    feed = feedparser.parse(url)

    return parse_feed_entries(feed)[:limit]


def fetch_feed_with_cache_paginated(
    provider: str,
    category: str,
    topic: str,
    limit: int = 5,
    cursor: int | None = None,
    from_ts: int | None = None,
    to_ts: int | None = None,
):
    now_ts = int(time.time())
    threshold = now_ts - RETENTION_SECONDS

    if should_refetch(provider, category, topic):
        url = FEED_MAP[provider][category][topic]
        feed = feedparser.parse(url)
        entries = parse_feed_entries(feed)
        if entries:
            set_cached_feed(provider, category, topic, entries)

    cache_key = get_cache_key(provider, category, topic)
    upper_bound = cursor if cursor is not None else now_ts
    if to_ts is not None:
        upper_bound = min(upper_bound, to_ts)
    lower_bound = from_ts if from_ts is not None else threshold
    lower_bound = max(lower_bound, threshold)

    raw_items = redis_client.zrevrangebyscore(
        cache_key,
        upper_bound,
        lower_bound,
        start=0,
        num=limit,
        withscores=True,
    )

    entries = []
    next_cursor = None
    for raw, score in raw_items:
        payload = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        entries.append(json.loads(payload))
        next_cursor = int(score) - 1

    has_more = False
    if next_cursor is not None:
        remaining = redis_client.zcount(cache_key, lower_bound, next_cursor)
        has_more = remaining > 0

    return {
        "entries": entries,
        "next_cursor": next_cursor,
        "has_more": has_more,
    }


def fetch_feed_with_cache(provider: str, category: str, topic: str, limit: int = 5):
    payload = fetch_feed_with_cache_paginated(
        provider=provider,
        category=category,
        topic=topic,
        limit=limit,
    )
    return payload["entries"]


def get_new_entries(channel_id, provider, category, topic, limit=5):
    entries = fetch_feed_with_cache(provider, category, topic, limit=30)

    key = get_seen_key(channel_id, provider, category, topic)
    new_entries = []

    for entry in entries:
        entry_id = entry["link"]

        if redis_client.sismember(key, entry_id):
            continue

        redis_client.sadd(key, entry_id)

        new_entries.append(f"• **{entry['title']}**\n{entry['link']}")

        if len(new_entries) >= limit:
            break

    redis_client.expire(key, 60 * 60 * 24 * 7)  # 7 days

    return new_entries


# async def warm_cache():
#     while True:
#         for provider in FEED_MAP:
#             for category in FEED_MAP[provider]:
#                 for topic in FEED_MAP[provider][category]:
#                     fetch_feed_with_cache(provider, category, topic)

#         await asyncio.sleep(60 * 30)  # every 30 min
