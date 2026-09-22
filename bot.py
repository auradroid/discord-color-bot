import os
import json
import random
from datetime import time
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands, tasks

# =========================
# COLOR HUNT SETTINGS
# =========================

COLORS = [
    ("Red", "❤️"),
    ("Orange", "🧡"),
    ("Yellow", "💛"),
    ("Lime Green", "💚"),
    ("Emerald Green", "💚"),
    ("Forest Green", "🌲"),
    ("Mint Green", "🌿"),
    ("Teal", "🩵"),
    ("Turquoise", "🩵"),
    ("Sky Blue", "💙"),
    ("Royal Blue", "💙"),
    ("Navy Blue", "🔵"),
    ("Purple", "💜"),
    ("Lavender", "💜"),
    ("Violet", "🟣"),
    ("Pink", "🩷"),
    ("Hot Pink", "🩷"),
    ("Coral", "🪸"),
    ("Peach", "🍑"),
    ("Burgundy", "🍷"),
    ("Brown", "🤎"),
    ("Beige", "🤍"),
    ("Gold", "✨"),
    ("Silver", "🩶"),
    ("Black", "🖤"),
    ("White", "🤍"),
    ("Grey", "🩶"),
]

STATE_FILE = "state.json"
TZ = ZoneInfo("Europe/Berlin")


def load_state():
    if not os.path.exists(STATE_FILE):
        return {"channel_id": None, "today": None, "last_date": None}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"channel_id": None, "today": None, "last_date": None}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


state = load_state()

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


def choose_color():
    name, emoji = random.choice(COLORS)
    return {"name": name, "emoji": emoji}


def color_message(color):
    return f"🎨 **Today's Color: {color['name']} {color['emoji']}**\n\nFind **1–3 real-life photos** matching today's color! 📸"


async def post_new_color(channel, force=False):
    from datetime import datetime

    today = datetime.now(TZ).date().isoformat()

    if not force and state.get("last_date") == today and state.get("today"):
        return False

    color = choose_color()

    # Avoid repeating yesterday's color when possible.
    if state.get("today") and len(COLORS) > 1:
        old_name = state["today"].get("name")
        while color["name"] == old_name:
            color = choose_color()

    state["today"] = color
    state["last_date"] = today
    save_state(state)

    await channel.send(color_message(color))
    return True


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s).")
    except Exception as e:
        print(f"Slash command sync failed: {e}")

    if not daily_color.is_running():
        daily_color.start()


@tasks.loop(time=time(hour=0, minute=0, tzinfo=TZ))
async def daily_color():
    channel_id = state.get("channel_id")
    if not channel_id:
        return

    channel = bot.get_channel(int(channel_id))
    if channel is None:
        try:
            channel = await bot.fetch_channel(int(channel_id))
        except Exception as e:
            print(f"Could not find color channel: {e}")
            return

    await post_new_color(channel)


@bot.tree.command(name="color", description="Pick a random color for Color Hunt.")
async def color(interaction: discord.Interaction):
    chosen = choose_color()
    await interaction.response.send_message(
        f"🎨 **Color Hunt: {chosen['name']} {chosen['emoji']}**"
    )


@bot.tree.command(name="today", description="Show today's Color Hunt color.")
async def today(interaction: discord.Interaction):
    if not state.get("today"):
        await interaction.response.send_message(
            "🎨 No color has been selected yet. Use `/color` or set the daily channel with `/setcolorchannel`."
        )
        return

    await interaction.response.send_message(color_message(state["today"]))


@bot.tree.command(name="colors", description="Show all available Color Hunt colors.")
async def colors(interaction: discord.Interaction):
    text = "🎨 **Color Hunt Color List**\n\n" + "\n".join(
        f"{emoji} {name}" for name, emoji in COLORS
    )
    await interaction.response.send_message(text)


@bot.tree.command(
    name="setcolorchannel",
    description="Set this channel as the automatic daily Color Hunt channel."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def setcolorchannel(interaction: discord.Interaction):
    state["channel_id"] = interaction.channel_id
    save_state(state)

    await interaction.response.send_message(
        "✅ This channel is now the **Color Hunt daily channel**.\n"
        "A new color will be posted automatically every day at **00:00 Europe/Berlin time**."
    )


@setcolorchannel.error
async def setcolorchannel_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message(
            "❌ Only members with **Manage Server** can set the Color Hunt channel.",
            ephemeral=True,
        )
    else:
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ Something went wrong while setting the channel.",
                ephemeral=True,
            )


TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN is missing. Add your Discord bot token as an environment variable."
    )

bot.run(TOKEN)
