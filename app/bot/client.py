import discord
from discord.ext import commands


def create_bot_client() -> commands.Bot:
    intents = discord.Intents.default()
    intents.message_content = True

    return commands.Bot(
        command_prefix="!",
        intents=intents,
        help_command=None,
    )
