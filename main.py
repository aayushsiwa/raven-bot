import asyncio
from datetime import datetime

import config
import discord
import uvicorn
from config import logger
from discord.ext import commands
from fastapi import FastAPI
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
    provider="RSS provider (verge, hn)",
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
    topic: str = None,
):
    await rss_skill.rss_slash(interaction, provider, category, topic)


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


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "bot": {
            "ready": bot.is_ready(),
            "user": str(bot.user) if bot.user else None,
            "latency_ms": round(bot.latency * 1000) if bot.is_ready() else None,
        },
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

    # Start API server
    asyncio.create_task(start_api())
    logger.info("FastAPI server started")

    # Start discord bot
    await bot.start(config.BOT_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
