import discord
import feedparser
from config import FEED_MAP, logger
from discord.ext import commands

SEEN_ENTRIES = {}  # key → set


def get_feed_key(provider, category, topic):
    return f"{provider}:{category}:{topic}"


def fetch_feed(provider: str, category: str, topic: str):
    url = FEED_MAP[provider][category][topic]
    feed = feedparser.parse(url)

    if not feed.entries:
        return None

    # return [f"• **{entry.title}**\n{entry.link}" for entry in feed.entries[:5]]
    return feed


def fetch_new_entries(provider: str, category: str, topic: str, limit: int = 5):
    url = FEED_MAP[provider][category][topic]
    feed = feedparser.parse(url)

    if not feed.entries:
        return []

    key = get_feed_key(provider, category, topic)

    if key not in SEEN_ENTRIES:
        SEEN_ENTRIES[key] = set()

    seen = SEEN_ENTRIES[key]
    new_entries = []

    for entry in feed.entries:
        entry_id = getattr(entry, "link", None) or getattr(entry, "id", None)

        if not entry_id or entry_id in seen:
            continue

        seen.add(entry_id)
        new_entries.append(f"• **{entry.title}**\n{entry.link}")

        if len(new_entries) >= limit:
            break

    return new_entries


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

    feed = fetch_new_entries(provider, category, topic)

    if not feed:
        await interaction.followup.send("❌ No entries found.")
        return

    await interaction.followup.send(f"📰 **{provider} / {category} / {topic}**")

    parent_msg = await interaction.original_response()

    thread = await parent_msg.create_thread(
        name=f"{provider}-{topic}",
        # auto_archive_duration=60,
    )

    # await thread.send("\n\n".join(messages))
    for entry in feed[:5]:
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

    feed = fetch_new_entries(provider, category, topic)

    if not feed:
        await ctx.send("❌ No entries found.")
        return

    parent = await ctx.send(f"📰 **{provider} / {category} / {topic}**")

    thread = await parent.create_thread(
        name=f"{provider}-{topic}-{ctx.message.id}",
        # auto_archive_duration=60,
    )

    # await thread.send("\n\n".join(messages))
    for entry in feed[:5]:
        await thread.send(entry)
