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
