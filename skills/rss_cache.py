import json

import feedparser
from config import FEED_MAP
from services.redis import redis_client

CACHE_TTL = 60 * 60 * 6  # 6 hours


def get_seen_key(channel_id, provider, category, topic):
    return f"rss:seen:{channel_id}:{provider}:{category}:{topic}"


def get_feed_key(provider, category, topic):
    return f"rss:{provider}:{category}:{topic}"


def get_cache_key(provider, category, topic):
    return f"rss:cache:{provider}:{category}:{topic}"


def get_cached_feed(provider, category, topic):
    key = get_cache_key(provider, category, topic)

    data = redis_client.get(key)
    if not data:
        return None

    return json.loads(data)


def set_cached_feed(provider, category, topic, entries):
    key = get_cache_key(provider, category, topic)

    redis_client.setex(
        key,
        CACHE_TTL,
        json.dumps(entries),
    )


def fetch_feed_with_cache(provider: str, category: str, topic: str, limit: int = 5):
    # 1️⃣ Try cache
    cached = get_cached_feed(provider, category, topic)

    if cached:
        return cached[:limit]

    # 2️⃣ Cache miss → fetch
    url = FEED_MAP[provider][category][topic]
    feed = feedparser.parse(url)

    if not feed.entries:
        return []

    entries = [
        {
            "title": entry.title,
            "link": entry.link,
        }
        for entry in feed.entries[:30]  # cache 30
    ]

    # 3️⃣ Store in cache
    set_cached_feed(provider, category, topic, entries)

    return entries[:limit]


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
