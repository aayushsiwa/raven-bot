import discord
from config import RSS_SUB_INTERVAL_IN_HOURS, logger
from discord.ext import commands
from services import db
from skills import rss as rss_skill


def register_prefix_commands(bot: commands.Bot) -> None:
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


def register_slash_commands(bot: commands.Bot) -> None:
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
