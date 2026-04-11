# Raven

Raven is a Discord bot that fetches RSS articles on demand and can post new feed items automatically to subscribed channels.

It includes:
- Discord prefix and slash commands for RSS lookup and subscriptions
- Redis-backed feed caching and per-channel "seen" tracking
- PostgreSQL-backed subscription storage
- A small FastAPI health endpoint (`/health`)

## Features

- Fetch latest feed items by `provider/category/topic`
- Subscribe a channel to periodic updates
- List and remove subscriptions
- Thread-based article delivery in Discord
- Health checks for bot, Redis, and PostgreSQL

## Tech Stack

- Python 3.12
- discord.py
- FastAPI + Uvicorn
- Redis
- PostgreSQL (asyncpg)
- feedparser

## Project Layout

- `main.py` - Bot commands/events, app startup, FastAPI routes
- `config.py` - Environment loading and feed catalog (`FEED_MAP`)
- `skills/rss.py` - RSS command handling + autocomplete
- `skills/rss_cache.py` - Feed fetch/cache and dedupe logic
- `services/db.py` - PostgreSQL connection pool + subscription queries
- `services/worker.py` - Background subscription polling worker
- `services/redis.py` - Redis client setup
- `test_feeds.sh` - Script to verify RSS URLs respond

## Prerequisites

- Python 3.12+
- A Discord application and bot token
- Redis instance
- PostgreSQL instance

## Configuration

Create a `.env` file in the project root.

Required variables (application exits if missing):

```env
BOT_TOKEN=your_discord_bot_token
PUBLIC_KEY=your_discord_public_key
APPLICATION_ID=your_discord_application_id
GUILD_ID=your_test_guild_id
GUILD_CHANNEL_ID=default_guild_channel_id
CHANNEL_ID=default_channel_id
```

Common optional variables:

```env
PORT=8080 # default is 8080
RSS_SUB_INTERVAL=43200 # default is 43200 i.e. 12 hours
RSS_FEED_SIZE=10 # default is 5

# Redis
REDIS_PASSWORD=password
# Optional override
# REDIS_URL=redis://:password@127.0.0.1:6379/1

# PostgreSQL
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DATABASE=postgres
# Optional override
# POSTGRES_DSN=postgres://user:pass@host:5432/dbname
```

Notes:
- `RSS_SUB_INTERVAL` is in seconds (default is 43200 = 12 hours).
- Feed sources are defined in `config.py` under `FEED_MAP`.

## Run Locally

Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Start the bot + API:

```bash
python main.py
```

Health check:

```bash
curl -s http://127.0.0.1:${PORT:-8080}/health
```

## Run With Docker

Build and start:

```bash
docker compose up --build
```

Stop:

```bash
docker compose down
```

The compose file runs the app container and exposes `${PORT}`.
Make sure Redis/PostgreSQL are reachable from the container via your `.env` configuration.

## Discord Commands

Prefix commands:

- `!ping`
- `!rss <provider> <category> [topic]`
- `!subscribe <provider> <category> <topic>`
- `!unsubscribe <provider> <category> <topic>`
- `!subscriptions`

Slash commands:

- `/ping`
- `/rss` (with autocomplete)
- `/subscribe`
- `/unsubscribe`
- `/subscriptions`

## Subscription Worker Behavior

- Worker starts shortly after bot startup.
- Every `RSS_SUB_INTERVAL`, it checks all DB subscriptions.
- For each channel subscription, it fetches feed entries and posts only unseen items.
- Seen item IDs are stored in Redis per channel/provider/category/topic and expire after 7 days.

## Feed Testing Utility

To quickly verify feed URLs in `test_feeds.sh`:

```bash
bash test_feeds.sh
```

## Troubleshooting

- Missing env vars: verify required keys in `.env`.
- Redis connection errors: check `REDIS_URL` and network accessibility.
- PostgreSQL errors: check `POSTGRES_DSN` or host/user/password/database values.
- Bot commands not visible: confirm `GUILD_ID` and bot permissions; restart after syncing commands. # Note: This is only if you want the bot for specific Guild

## Development Notes

- Subscriptions are persisted in table `rss_subscriptions` created at startup.
- `main.py` starts Discord bot, FastAPI server, and RSS worker in one process.
- Health endpoint is available at `GET /health` and `HEAD /health`.
