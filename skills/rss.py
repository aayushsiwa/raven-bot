import discord
from config import FEED_MAP, logger
from discord.ext import commands
from skills.rss_cache import get_new_entries


async def provider_autocomplete(interaction, current):
    return [
        discord.app_commands.Choice(name=k, value=k)
        for k in FEED_MAP.keys()
        if current.lower() in k
    ]


async def category_autocomplete(interaction, current):
    provider = interaction.namespace.provider
    if provider not in FEED_MAP:
        return []

    return [
        discord.app_commands.Choice(name=k, value=k)
        for k in FEED_MAP[provider].keys()
        if current.lower() in k
    ]


async def topic_autocomplete(interaction, current):
    provider = interaction.namespace.provider
    category = interaction.namespace.category

    if provider not in FEED_MAP or category not in FEED_MAP[provider]:
        return []

    return [
        discord.app_commands.Choice(name=k, value=k)
        for k in FEED_MAP[provider][category].keys()
        if current.lower() in k
    ]


async def rss_slash(
    interaction: discord.Interaction,
    provider: str,
    category: str,
    topic: str = None,
):
    provider = provider.lower()
    category = category.lower()

    logger.info(f"RSS request from {interaction.user} → {provider}/{category}/{topic}")

    if provider not in FEED_MAP:
        await interaction.response.send_message(
            f"❌ Unknown provider. Available: {', '.join(FEED_MAP.keys())}",
            ephemeral=True,
        )
        return

    if category not in FEED_MAP[provider]:
        await interaction.response.send_message(
            f"❌ Unknown category. Available: {', '.join(FEED_MAP[provider].keys())}",
            ephemeral=True,
        )
        return

    if topic is None:
        topics = ", ".join(FEED_MAP[provider][category].keys())
        await interaction.response.send_message(
            f"📂 Topics in **{provider}/{category}**: {topics}",
            ephemeral=True,
        )
        return

    topic = topic.lower()

    if topic not in FEED_MAP[provider][category]:
        await interaction.response.send_message(
            f"❌ Unknown topic. Available: {', '.join(FEED_MAP[provider][category].keys())}",
            ephemeral=True,
        )
        return

    await interaction.response.defer()

    feed = get_new_entries(
        interaction.channel_id,
        provider,
        category,
        topic,
    )

    if not feed:
        await interaction.followup.send("📭 No new articles right now.")
        return

    await interaction.followup.send(f"📰 **{provider} / {category} / {topic}**")

    parent_msg = await interaction.original_response()

    thread = await parent_msg.create_thread(
        name=f"{provider}-{topic}",
        # auto_archive_duration=60,
    )

    # await thread.send("\n\n".join(messages))
    for entry in feed:
        await thread.send(entry)


async def rss(ctx: commands.Context, provider: str, category: str, topic: str = None):
    provider = provider.lower()
    category = category.lower()

    if provider not in FEED_MAP:
        await ctx.send(f"❌ Unknown provider. Available: {', '.join(FEED_MAP.keys())}")
        return

    if category not in FEED_MAP[provider]:
        await ctx.send(
            f"❌ Unknown category. Available: {', '.join(FEED_MAP[provider].keys())}"
        )
        return

    if topic is None:
        topics = ", ".join(FEED_MAP[provider][category].keys())
        await ctx.send(f"📂 Topics in **{provider}/{category}**: {topics}")
        return

    topic = topic.lower()

    if topic not in FEED_MAP[provider][category]:
        await ctx.send(
            f"❌ Unknown topic. Available: {', '.join(FEED_MAP[provider][category].keys())}"
        )
        return

    feed = get_new_entries(
        ctx.channel.id,
        provider,
        category,
        topic,
    )

    if not feed:
        await ctx.send("📭 No new articles right now.")
        return

    parent = await ctx.send(f"📰 **{provider} / {category} / {topic}**")

    thread = await parent.create_thread(
        name=f"{provider}-{topic}-{ctx.message.id}",
        # auto_archive_duration=60,
    )

    # await thread.send("\n\n".join(messages))
    for entry in feed:
        await thread.send(entry)
