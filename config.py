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

RSS_SUB_INTERVAL = int(os.getenv("RSS_SUB_INTERVAL", 43200))
RSS_SUB_INTERVAL_IN_HOURS = RSS_SUB_INTERVAL // 3600

REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_URL = os.getenv("REDIS_URL")

if not REDIS_URL:
    REDIS_URL = f"redis://:{REDIS_PASSWORD}@127.0.0.1:6379/1"


POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DATABASE = os.getenv("POSTGRES_DATABASE", "postgres")
POSTGRES_DSN = os.getenv("POSTGRES_DSN")

if not POSTGRES_DSN:
    POSTGRES_DSN = f"postgres://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DATABASE}"
    print(POSTGRES_DSN)

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
            "streaming": "https://www.theverge.com/rss/streaming/index.xml",
        },
        "science": {
            "general": "https://www.theverge.com/rss/science/index.xml",
            "space": "https://www.theverge.com/rss/space/index.xml",
        },
        "business": {
            "tesla": "https://www.theverge.com/rss/tesla/index.xml",
            "elon": "https://www.theverge.com/rss/elon-musk/index.xml",
            "general": "https://www.theverge.com/rss/business/index.xml",
        },
    },
    "hn": {
        "tech": {
            "latest": "https://hnrss.org/newest",
            "frontpage": "https://hnrss.org/frontpage",
        },
        "career": {
            "jobs": "https://hnrss.org/jobs",
        },
    },
    "xda": {
        "news": {
            "general": "https://www.xda-developers.com/feed/",
            "latest": "https://www.xda-developers.com/feed/news/",
        },
        "hardware": {
            "general": "https://www.xda-developers.com/feed/category/pc-hardware/",
            "cpu": "https://www.xda-developers.com/feed/processor/",
            "storage": "https://www.xda-developers.com/feed/storage/",
            "monitor": "https://www.xda-developers.com/feed/monitor/",
            "input": "https://www.xda-developers.com/feed/input-device/",
        },
        "software": {
            "general": "https://www.xda-developers.com/feed/software-and-services/",
            "productivity": "https://www.xda-developers.com/feed/productivity/",
            "self_hosting": "https://www.xda-developers.com/feed/self-hosting/",
            "home_lab": "https://www.xda-developers.com/feed/home-lab/",
        },
        "systems": {
            "windows": "https://www.xda-developers.com/feed/windows/",
            "linux": "https://www.xda-developers.com/feed/category/linux-hub/",
            "macos": "https://www.xda-developers.com/feed/category/macos/",
        },
        "devices": {
            "general": "https://www.xda-developers.com/feed/devices/",
            "sbc": "https://www.xda-developers.com/feed/single-board-computers/",
            "laptops": "https://www.xda-developers.com/feed/laptops/",
            "handheld": "https://www.xda-developers.com/feed/gaming-handhelds/",
            "prebuilt": "https://www.xda-developers.com/feed/prebuilt-pc/",
        },
        "network": {
            "networking": "https://www.xda-developers.com/feed/networking/",
            "smart_home": "https://www.xda-developers.com/feed/smart-home/",
        },
        "entertainment": {
            "general": "https://www.xda-developers.com/feed/entertainment/",
            "segment": "https://www.xda-developers.com/feed/entertainment-segment/",
            "gaming": "https://www.xda-developers.com/feed/gaming/",
            "tv": "https://www.xda-developers.com/feed/tv/",
        },
    },
    "howtogeek": {
        "general": {
            "general": "https://www.howtogeek.com/feed/",
            "news": "https://www.howtogeek.com/feed/news/",
        },
        "systems": {
            "desktop": "https://www.howtogeek.com/feed/category/desktop/",
            "windows": "https://www.howtogeek.com/feed/category/windows/",
            "mac": "https://www.howtogeek.com/feed/category/mac/",
            "linux": "https://www.howtogeek.com/feed/category/linux/",
        },
        "mobile": {
            "android": "https://www.howtogeek.com/feed/category/android/",
            "ios": "https://www.howtogeek.com/feed/category/ios/",
            "general": "https://www.howtogeek.com/feed/category/mobile/",
        },
        "hardware": {
            "general": "https://www.howtogeek.com/feed/category/hardware/",
            "smart_home": "https://www.howtogeek.com/feed/category/smart-home/",
        },
        "buying": {
            "deals": "https://www.howtogeek.com/feed/tag/deals/",
            "guides": "https://www.howtogeek.com/feed/buying-guides/",
            "reviews": "https://www.howtogeek.com/feed/category/product-reviews/",
        },
        "companies": {
            "microsoft": "https://www.howtogeek.com/feed/category/microsoft/",
            "google": "https://www.howtogeek.com/feed/tag/google/",
        },
        "security": {
            "cybersecurity": "https://www.howtogeek.com/feed/category/cybersecurity/",
        },
        "web": {
            "general": "https://www.howtogeek.com/feed/category/web/",
        },
        "entertainment": {
            "streaming": "https://www.howtogeek.com/feed/category/streaming/",
            "gaming": "https://www.howtogeek.com/feed/category/video-games/",
        },
        "science": {
            "space": "https://www.howtogeek.com/feed/category/space/",
            "cutting_edge": "https://www.howtogeek.com/feed/category/cutting-edge/",
        },
        "lifestyle": {
            "hobbies": "https://www.howtogeek.com/feed/category/hobbies/",
            "automotive": "https://www.howtogeek.com/feed/category/automotive/",
        },
        "dev": {
            "programming": "https://www.howtogeek.com/feed/category/programming/",
        },
    },
}
