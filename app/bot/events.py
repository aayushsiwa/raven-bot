import discord
from config import logger
from discord.ext import commands


def register_events(bot: commands.Bot) -> None:
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
