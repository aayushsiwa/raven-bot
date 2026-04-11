import asyncio
import os
from datetime import datetime

import config
import discord
import uvicorn
from config import GUILD_ID, RSS_SUB_INTERVAL_IN_HOURS, logger
from discord.ext import commands
from fastapi import FastAPI
from services import db
from services.redis import redis_client
from services.worker import rss_worker
from skills import rss as rss_skill

# ------------------------------------------------
# Discord Bot Setup
# ------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None,
)


# ------------------------------------------------
# Prefix Commands
# ------------------------------------------------
@bot.command()
async def ping(ctx: commands.Context):
    latency = round(bot.latency * 1000)

    logger.info(f"Ping from {ctx.author}")
    await ctx.send(f"🏓 pong | {latency}ms")


@bot.command()
async def rss(ctx: commands.Context, provider: str, category: str, topic: str = None):
    await rss_skill.rss(ctx, provider, category, topic)


@bot.command(name="subscribe")
async def subscribe_prefix(ctx, provider: str, category: str, topic: str):
    guild_id = ctx.guild.id if ctx.guild else None

    success = await db.add_subscription(
        ctx.channel.id,
        guild_id,
        provider,
        category,
        topic,
    )

    if not success:
        await ctx.send(f"⚠️ Already subscribed to {provider}/{category}/{topic}")
    else:
        location = "this DM" if guild_id is None else "this server"

        await ctx.send(
            f"✅ Subscribed to {provider}/{category}/{topic} in {location} - will check every {RSS_SUB_INTERVAL_IN_HOURS} hours"
        )


@bot.command(name="unsubscribe")
async def unsubscribe_prefix(ctx, provider: str, category: str, topic: str):
    await db.remove_subscription(
        ctx.channel.id,
        provider,
        category,
        topic,
    )

    await ctx.send(f"🗑️ Unsubscribed from {provider}/{category}/{topic}")


@bot.command(name="subscriptions")
async def subscriptions_prefix(ctx):
    subs = await db.list_subscriptions(ctx.channel.id)

    if not subs:
        await ctx.send("📭 No subscriptions.")
        return

    msg = "\n".join(
        [f"• {s['provider']} / {s['category']} / {s['topic']}" for s in subs]
    )

    await ctx.send(f"📡 Subscriptions:\n{msg}")


# ------------------------------------------------
# Slash Commands
# ------------------------------------------------
@bot.tree.command(name="ping", description="Ping the bot")
async def ping_command(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)

    logger.info(f"Ping from {interaction.user}")
    await interaction.response.send_message(f"🏓 pong | {latency}ms")


@bot.tree.command(name="rss", description="Fetch RSS feed")
@discord.app_commands.describe(
    provider="RSS provider",
    category="Category",
    topic="Topic",
)
@discord.app_commands.autocomplete(
    provider=rss_skill.provider_autocomplete,
    category=rss_skill.category_autocomplete,
    topic=rss_skill.topic_autocomplete,
)
async def rss_slash(
    interaction: discord.Interaction,
    provider: str,
    category: str,
    topic: str,
):
    await rss_skill.rss_slash(interaction, provider, category, topic)


@bot.tree.command(name="subscribe")
async def subscribe(interaction, provider: str, category: str, topic: str):
    success = await db.add_subscription(
        interaction.channel_id,
        interaction.guild_id,
        provider,
        category,
        topic,
    )

    if not success:
        await interaction.response.send_message(
            f"⚠️ Already subscribed to {provider}/{category}/{topic}"
        )
    else:
        location = "this DM" if interaction.guild_id is None else "this server"

        await interaction.response.send_message(
            f"✅ Subscribed to {provider}/{category}/{topic} in {location} - will check every {RSS_SUB_INTERVAL_IN_HOURS} hours"
        )


@bot.tree.command(name="unsubscribe")
async def unsubscribe(interaction, provider: str, category: str, topic: str):
    await db.remove_subscription(
        interaction.channel_id,
        provider,
        category,
        topic,
    )

    await interaction.response.send_message(
        f"🗑️ Unsubscribed from {provider}/{category}/{topic}"
    )


@bot.tree.command(name="subscriptions")
async def subscriptions(interaction):
    subs = await db.list_subscriptions(interaction.channel_id)

    if not subs:
        await interaction.response.send_message("📭 No subscriptions.")
        return

    msg = "\n".join(
        [f"• {s['provider']} / {s['category']} / {s['topic']}" for s in subs]
    )

    await interaction.response.send_message(f"📡 Subscriptions:\n{msg}")


# ------------------------------------------------
# Discord Events
# ------------------------------------------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    logger.info(f"Logged in as {bot.user} ({bot.user.id})")


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.CommandNotFound):
        return

    logger.error(f"Command error: {error}")
    await ctx.send(f"❌ Error: {error}")


# ------------------------------------------------
# Start FastAPI Server
# ------------------------------------------------
app = FastAPI(title="Discord Bot API")


@app.head("/health")
async def health_head():
    return {"status": "ok"}


@app.get("/health")
async def health():
    redis_status = "ok"
    try:
        redis_client.ping()
    except Exception as e:
        redis_status = f"error: {str(e)}"

    db_status = "ok"
    try:
        await db.ping()
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "bot": {
            "ready": bot.is_ready(),
            "user": str(bot.user) if bot.user else None,
            "latency_ms": round(bot.latency * 1000) if bot.is_ready() else None,
        },
        "db": db_status,
        "redis": redis_status,
    }


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
