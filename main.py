import asyncio
import os

import config
import uvicorn
from config import logger
from app.app_factory import create_fastapi_app
from app.bot.client import create_bot_client
from app.bot.commands import register_prefix_commands, register_slash_commands
from app.bot.events import register_events
from services import db
from services.redis import redis_client
from services.worker import rss_worker

bot = create_bot_client()
register_prefix_commands(bot)
register_slash_commands(bot)
register_events(bot)

app = create_fastapi_app(bot)


async def start_api():
    config_uvicorn = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=config.PORT,
        log_level="info",
    )

    server = uvicorn.Server(config_uvicorn)
    await server.serve()


# ------------------------------------------------
# Main Runner
# ------------------------------------------------
async def main():

    try:
        redis_client.ping()
        logger.info("✅ Redis connected")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        os._exit(1)

    await db.init_db()

    try:
        await db.ping()
        logger.info("✅ DB connected")
    except Exception as e:
        logger.error(f"❌ DB connection failed: {e}")
        os._exit(1)

    asyncio.create_task(rss_worker(bot))

    # Start API server
    asyncio.create_task(start_api())
    logger.info("FastAPI server started")

    # Start discord bot
    await bot.start(config.BOT_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
