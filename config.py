import logging
import os

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger("raven")


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise RuntimeError(f"Missing required env variable: {key}")
    return val


# Required
BOT_TOKEN = _require("BOT_TOKEN")
PUBLIC_KEY = _require("PUBLIC_KEY")
APPLICATION_ID = _require("APPLICATION_ID")
GUILD_ID = _require("GUILD_ID")
GUILD_CHANNEL_ID = _require("GUILD_CHANNEL_ID")
CHANNEL_ID = _require("CHANNEL_ID")

# Optional with defaults
PORT = int(os.getenv("PORT", "8080"))
RSS_FEED_SIZE = int(os.getenv("RSS_FEED_SIZE", "10"))
RSS_CRON_SCHEDULE = os.getenv("RSS_CRON_SCHEDULE", "0 5 * * *")  # stored for reference
RSS_CRON_HOUR = int(os.getenv("RSS_CRON_HOUR", "5"))
RSS_CRON_MIN = int(os.getenv("RSS_CRON_MIN", "0"))

REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_URL = os.getenv("REDIS_URL", f"redis://${REDIS_PASSWORD}@127.0.0.1:6379/1")

# CPU monitor settings
CPU_THRESHOLD = float(os.getenv("CPU_THRESHOLD", "80.0"))
CPU_CHECK_INTERVAL = int(os.getenv("CPU_CHECK_INTERVAL", "30"))  # seconds
CPU_COOLDOWN = int(os.getenv("CPU_COOLDOWN", "120"))  # seconds

# RSS feed URLs
RSS_FEEDS = {
    "tech": "https://feeds.feedburner.com/TechCrunch",
    "news": "https://feeds.bbci.co.uk/news/rss.xml",
    "gaming": "https://www.polygon.com/rss/index.xml",
}

FEED_MAP = {
    "verge": {
        "tech": {
            "android": "https://www.theverge.com/rss/android/index.xml",
            "apple": "https://www.theverge.com/rss/apple/index.xml",
            "google": "https://www.theverge.com/rss/google/index.xml",
            "microsoft": "https://www.theverge.com/rss/microsoft/index.xml",
            "general": "https://www.theverge.com/rss/tech/index.xml",
        },
        "entertainment": {
            "film": "https://www.theverge.com/rss/film/index.xml",
            "tv": "https://www.theverge.com/rss/tv-shows/index.xml",
            "streaming": "https://www.theverge.com/rss/streaming/index.xml",
        },
        "gaming": {
            "gaming": "https://www.theverge.com/rss/gaming/index.xml",
        },
        "science": {
            "science": "https://www.theverge.com/rss/science/index.xml",
            "space": "https://www.theverge.com/rss/space/index.xml",
            "climate": "https://www.theverge.com/rss/climate/index.xml",
        },
        "business": {
            "crypto": "https://www.theverge.com/rss/crypto/index.xml",
            "tesla": "https://www.theverge.com/rss/tesla/index.xml",
            "elon": "https://www.theverge.com/rss/elon-musk/index.xml",
        },
    },
    "hn": {
        "tech": {
            "frontpage": "https://hnrss.org/frontpage",
        }
    },
}
