import asyncio

from config import RSS_FEED_SIZE, RSS_SUB_INTERVAL, logger
from services import db
from skills.rss_cache import get_new_entries


async def rss_worker(bot):
    await asyncio.sleep(5)  # wait for bot ready

    while True:
        try:
            subs = await db.get_all_subscriptions()

            for sub in subs:
                channel_id = sub["channel_id"]
                provider = sub["provider"]
                category = sub["category"]
                topic = sub["topic"]

                channel = bot.get_channel(channel_id)
                if not channel:
                    continue

                feed = get_new_entries(
                    channel_id,
                    provider,
                    category,
                    topic,
                    limit=RSS_FEED_SIZE,
                )

                if not feed:
                    continue

                # Send message
                parent = await channel.send(f"📰 **{provider} / {category} / {topic}**")

                thread = await parent.create_thread(
                    name=f"{provider}-{topic}",
                )

                for entry in feed:
                    await thread.send(entry)

        except Exception as e:
            logger.error(f"[Worker Error] {e}")

        await asyncio.sleep(RSS_SUB_INTERVAL)
