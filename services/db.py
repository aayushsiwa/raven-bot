import asyncpg
import config

pool = None


async def init_db():
    global pool
    pool = await asyncpg.create_pool(dsn=config.POSTGRES_DSN)

    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS rss_subscriptions (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT ,
                channel_id BIGINT NOT NULL,
                provider TEXT NOT NULL,
                category TEXT NOT NULL,
                topic TEXT NOT NULL,
                UNIQUE (guild_id, channel_id, provider, category, topic)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL,
                username_lower TEXT NOT NULL UNIQUE,
                password_hash TEXT,
                email TEXT,
                display_name TEXT,
                avatar_url TEXT,
                auth_source TEXT NOT NULL DEFAULT 'local',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS oauth_accounts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                provider TEXT NOT NULL,
                provider_user_id TEXT NOT NULL,
                email TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (provider, provider_user_id),
                UNIQUE (user_id, provider)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_feed_preferences (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                provider TEXT NOT NULL,
                category TEXT NOT NULL,
                topic TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (user_id, provider, category, topic)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_custom_feeds (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'custom',
                topic TEXT NOT NULL DEFAULT 'user',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (user_id, url)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_oauth_link_requests (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                provider TEXT NOT NULL,
                state_token TEXT NOT NULL,
                expires_at TIMESTAMPTZ NOT NULL,
                used_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_saved_articles (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                summary TEXT,
                source TEXT,
                saved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (user_id, url)
            )
        """)


async def add_subscription(channel_id, guild_id, provider, category, topic):
    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            INSERT INTO rss_subscriptions (guild_id, channel_id, provider, category, topic)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT DO NOTHING
            """,
            guild_id,
            channel_id,
            provider,
            category,
            topic,
        )

        if result == "INSERT 0 0":
            return False  # already exists
        return True  # inserted


async def remove_subscription(channel_id, provider, category, topic):
    async with pool.acquire() as conn:
        await conn.execute(
            """
            DELETE FROM rss_subscriptions
            WHERE channel_id=$1 AND provider=$2 AND category=$3 AND topic=$4
            """,
            channel_id,
            provider,
            category,
            topic,
        )


async def list_subscriptions(channel_id):
    async with pool.acquire() as conn:
        return await conn.fetch(
            """
            SELECT provider, category, topic
            FROM rss_subscriptions
            WHERE channel_id=$1
            """,
            channel_id,
        )


async def get_all_subscriptions():
    async with pool.acquire() as conn:
        return await conn.fetch(
            """
            SELECT guild_id, channel_id, provider, category, topic
            FROM rss_subscriptions
            """
        )


async def create_local_user(username: str, password_hash: str):
    username_norm = username.strip()
    username_lower = username_norm.lower()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO users (username, username_lower, password_hash, auth_source)
            VALUES ($1, $2, $3, 'local')
            ON CONFLICT (username_lower) DO NOTHING
            RETURNING id, username, email, display_name, avatar_url, auth_source, created_at
            """,
            username_norm,
            username_lower,
            password_hash,
        )
        return dict(row) if row else None


async def username_exists(username: str) -> bool:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT 1
            FROM users
            WHERE username_lower = $1
            """,
            username.strip().lower(),
        )
        return bool(row)


async def get_user_by_username(username: str):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, username, username_lower, password_hash, email, display_name, avatar_url, auth_source, created_at
            FROM users
            WHERE username_lower = $1
            """,
            username.strip().lower(),
        )
        return dict(row) if row else None


async def get_user_by_id(user_id: int):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, username, email, display_name, avatar_url, auth_source, created_at
            FROM users
            WHERE id = $1
            """,
            user_id,
        )
        return dict(row) if row else None


async def get_user_by_oauth(provider: str, provider_user_id: str):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT u.id, u.username, u.email, u.display_name, u.avatar_url, u.auth_source, u.created_at
            FROM oauth_accounts oa
            JOIN users u ON u.id = oa.user_id
            WHERE oa.provider = $1 AND oa.provider_user_id = $2
            """,
            provider,
            provider_user_id,
        )
        return dict(row) if row else None


async def create_oauth_user(
    username: str,
    provider: str,
    provider_user_id: str,
    email: str | None = None,
    display_name: str | None = None,
    avatar_url: str | None = None,
):
    username_norm = username.strip()
    username_lower = username_norm.lower()

    async with pool.acquire() as conn:
        async with conn.transaction():
            user_row = await conn.fetchrow(
                """
                INSERT INTO users (username, username_lower, email, display_name, avatar_url, auth_source)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (username_lower) DO NOTHING
                RETURNING id, username, email, display_name, avatar_url, auth_source, created_at
                """,
                username_norm,
                username_lower,
                email,
                display_name,
                avatar_url,
                provider,
            )
            if not user_row:
                return None

            await conn.execute(
                """
                INSERT INTO oauth_accounts (user_id, provider, provider_user_id, email)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (provider, provider_user_id)
                DO UPDATE SET email = EXCLUDED.email
                """,
                user_row["id"],
                provider,
                provider_user_id,
                email,
            )

            return dict(user_row)


async def ping():
    async with pool.acquire() as conn:
        await conn.execute("SELECT 1")


async def list_user_feed_preferences(user_id: int):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT provider, category, topic
            FROM user_feed_preferences
            WHERE user_id = $1
            ORDER BY created_at ASC, id ASC
            """,
            user_id,
        )
        return [dict(row) for row in rows]


async def replace_user_feed_preferences(user_id: int, choices: list[dict]):
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                DELETE FROM user_feed_preferences
                WHERE user_id = $1
                """,
                user_id,
            )

            if choices:
                await conn.executemany(
                    """
                    INSERT INTO user_feed_preferences (user_id, provider, category, topic)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (user_id, provider, category, topic) DO NOTHING
                    """,
                    [
                        (user_id, choice["provider"], choice["category"], choice["topic"])
                        for choice in choices
                    ],
                )


async def list_user_custom_feeds(user_id: int):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, title, url, category, topic, is_active, created_at
            FROM user_custom_feeds
            WHERE user_id = $1
            ORDER BY created_at DESC
            """,
            user_id,
        )
        return [dict(row) for row in rows]


async def add_user_custom_feed(user_id: int, title: str, url: str, category: str = "custom", topic: str = "user"):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO user_custom_feeds (user_id, title, url, category, topic)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (user_id, url) DO NOTHING
            RETURNING id, title, url, category, topic, is_active, created_at
            """,
            user_id, title, url, category, topic,
        )
        return dict(row) if row else None


async def update_user_custom_feed(user_id: int, feed_id: int, title: str = None, is_active: bool = None):
    async with pool.acquire() as conn:
        updates = []
        params = [user_id, feed_id]
        param_cnt = 2
        if title is not None:
            param_cnt += 1
            updates.append(f"title = ${param_cnt}")
            params.append(title)
        if is_active is not None:
            param_cnt += 1
            updates.append(f"is_active = ${param_cnt}")
            params.append(is_active)

        if not updates:
            return None

        query = f"""
            UPDATE user_custom_feeds
            SET {', '.join(updates)}
            WHERE user_id = $1 AND id = $2
            RETURNING id, title, url, category, topic, is_active, created_at
        """
        row = await conn.fetchrow(query, *params)
        return dict(row) if row else None


async def delete_user_custom_feed(user_id: int, feed_id: int):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            DELETE FROM user_custom_feeds
            WHERE user_id = $1 AND id = $2
            RETURNING id
            """,
            user_id, feed_id,
        )
        return row is not None


async def create_oauth_link_request(user_id: int, provider: str, state_token: str):
    from datetime import datetime, timedelta
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO user_oauth_link_requests (user_id, provider, state_token, expires_at)
            VALUES ($1, $2, $3, $4)
            RETURNING id, user_id, provider, state_token, expires_at, used_at, created_at
            """,
            user_id, provider, state_token, datetime.utcnow() + timedelta(minutes=10),
        )
        return dict(row) if row else None


async def consume_oauth_link_request(provider: str, state_token: str):
    from datetime import datetime
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE user_oauth_link_requests
            SET used_at = NOW()
            WHERE provider = $1 AND state_token = $2
            AND used_at IS NULL AND expires_at > NOW()
            RETURNING id, user_id, provider
            """,
            provider, state_token,
        )
        return dict(row) if row else None


async def list_oauth_accounts_for_user(user_id: int):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT provider, provider_user_id, email, created_at
            FROM oauth_accounts
            WHERE user_id = $1
            """,
            user_id,
        )
        return [dict(row) for row in rows]


async def link_oauth_account(user_id: int, provider: str, provider_user_id: str, email: str = None):
    async with pool.acquire() as conn:
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO oauth_accounts (user_id, provider, provider_user_id, email)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (provider, provider_user_id) DO NOTHING
                ON CONFLICT (user_id, provider) DO NOTHING
                RETURNING id, user_id, provider, provider_user_id, email, created_at
                """,
                user_id, provider, provider_user_id, email,
            )
            return dict(row) if row else None
        except Exception:
            return None


async def list_user_saved_articles(user_id: int):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, title, url, summary, source, saved_at
            FROM user_saved_articles
            WHERE user_id = $1
            ORDER BY saved_at DESC
            """,
            user_id,
        )
        return [dict(row) for row in rows]


async def save_article(user_id: int, title: str, url: str, summary: str = None, source: str = None):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO user_saved_articles (user_id, title, url, summary, source)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (user_id, url) DO NOTHING
            RETURNING id, title, url, summary, source, saved_at
            """,
            user_id, title, url, summary, source,
        )
        return dict(row) if row else None


async def delete_saved_article(user_id: int, article_id: int):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            DELETE FROM user_saved_articles
            WHERE user_id = $1 AND id = $2
            RETURNING id
            """,
            user_id, article_id,
        )
        return row is not None
