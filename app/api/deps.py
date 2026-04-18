from typing import Optional

import config
from fastapi import HTTPException


def normalize_feed_path(provider: str, category: str, topic: Optional[str] = None):
    provider = provider.lower()
    category = category.lower()

    if provider not in config.FEED_MAP:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Unknown provider",
                "available": list(config.FEED_MAP.keys()),
            },
        )

    if category not in config.FEED_MAP[provider]:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Unknown category",
                "available": list(config.FEED_MAP[provider].keys()),
            },
        )

    if topic is None:
        return provider, category, None

    topic = topic.lower()
    if topic not in config.FEED_MAP[provider][category]:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Unknown topic",
                "available": list(config.FEED_MAP[provider][category].keys()),
            },
        )

    return provider, category, topic
