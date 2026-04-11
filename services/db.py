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


async def ping():
    async with pool.acquire() as conn:
        await conn.execute("SELECT 1")
