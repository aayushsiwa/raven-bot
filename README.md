# Raven Backend: API & Discord Bot

Raven is a multi-modal RSS platform that powers both a premium web dashboard and a robust Discord bot. It handles feed aggregation, high-performance caching with Redis, persistent user storage with PostgreSQL, and secure OAuth 2.0 authentication.

## 🚀 Key Features

- **Multi-Source Aggregation**: Curated registry of tech, news, and specialized feeds.
- **OAuth 2.0 Ecosystem**: Seamless sign-in via Google, GitHub, and Discord.
- **Discord Bot**: Slash commands, feed subscriptions, and channel-based thread delivery.
- **REST API v1**: Complete programmatic access to providers, categories, topics, and user content.
- **Smart Caching**: Redis-backed feed deduplication and channel-level "seen" tracking.

## 🛠 Tech Stack

- **Core**: Python 3.12, FastAPI, Uvicorn
- **Bot**: discord.py
- **Database**: PostgreSQL (via `asyncpg`), Redis
- **Auth**: JWT (PyJWT), Google/GitHub/Discord OAuth
- **Parsing**: `feedparser`

## 📋 Prerequisites

- Python 3.12+
- Redis Server
- PostgreSQL Server
- Discord Developer Application & Bot Token
- OAuth Client Credentials (Google, GitHub, and/or Discord)

## ⚙️ Configuration

Create a `.env` file in the `backend/` directory referencing the `.env.example` or the keys below.

### Discord & Infrastructure
```env
BOT_TOKEN=...
PUBLIC_KEY=...
APPLICATION_ID=...
GUILD_ID=...
REDIS_URL=redis://localhost:6379/1
POSTGRES_DSN=postgres://user:pass@localhost:5432/raven
```

### Authentication (OAuth)
```env
AUTH_SECRET=your_jwt_signing_secret
FRONTEND_URL=http://localhost:5173
OAUTH_CALLBACK_BASE=http://localhost:8080

# Google
OAUTH_GOOGLE_CLIENT_ID=...
OAUTH_GOOGLE_CLIENT_SECRET=...

# GitHub
OAUTH_GITHUB_CLIENT_ID=...
OAUTH_GITHUB_CLIENT_SECRET=...

# Discord
OAUTH_DISCORD_CLIENT_ID=...
OAUTH_DISCORD_CLIENT_SECRET=...
```

## 🏗 Project Layout

- `main.py`: Main entry point (starts Bot, API, and Worker).
- `config.py`: Centralized configuration, `Provider` enums, and `FEED_MAP`.
- `app/api/`: FastAPI route handlers and route logic.
- `app/bot/`: Discord bot client and command registration.
- `services/`: Database and Redis connection management.
- `skills/`: Core logic for RSS fetching, caching, and deduplication.
- `test_feeds.sh`: Diagnostic script to verify all RSS source URLs.

## 📡 API Reference (v1)

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/health` | `GET` | System health check (Bot, Redis, DB). |
| `/api/v1/auth/me` | `GET` | Get current authenticated user session. |
| `/api/v1/auth/oauth/{provider}/login` | `GET` | Initiate OAuth flow. |
| `/api/v1/providers` | `GET` | List all available feed providers. |
| `/api/v1/rss?provider=...` | `GET` | Fetch stories for a specific provider/topic. |
| `/api/v1/saved-articles` | `GET/POST` | Manage user's saved article archive. |

## 💻 Running Locally

1. **Setup Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Initialize Database**:
   Raven automatically creates the necessary tables on first start.

3. **Start the Service**:
   ```bash
   python main.py
   ```

4. **Verify Feeds**:
   ```bash
   bash test_feeds.sh
   ```

## 🐳 Running with Docker

```bash
docker compose up --build
```
This will start the API, Bot, Redis, and PostgreSQL containers as defined in the root `docker-compose.yml`.

---
> [!TIP]
> Use the `python main.py --watch` flag during development to automatically restart the service when files change.
