import discord
from discord.ext import commands
from datetime import datetime
import calendar
import json
import os
import io
from openai import AsyncOpenAI
from PIL import Image, ImageDraw, ImageFont

# =========================
# BOT SETUP
# =========================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# DATA
# =========================
pnl_data = {}
DATA_FILE = "pnl_data.json"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

ALLOWED_SUMMARY_CHANNELS = [1491280657387622420]


def load_pnl_data():
    global pnl_data
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                pnl_data = json.load(f)
        except:
            pnl_data = {}
    else:
        pnl_data = {}


def save_pnl_data():
    with open(DATA_FILE, "w") as f:
        json.dump(pnl_data, f)


def get_user_pnl(user_id: str):
    return pnl_data.get(str(user_id), {})


def set_user_pnl(user_id: str, date_key: str, entry: dict):
    uid = str(user_id)
    if uid not in pnl_data:
        pnl_data[uid] = {}
    pnl_data[uid][date_key] = entry
    save_pnl_data()


# =========================
# CHECKLIST SYSTEM
# =========================
CHECKLIST_ITEMS = [
    "Liquidity Sweep",
    "Market Structure Shift (MSS)",
    "Retest (OB / FVG)",
    "Higher Timeframe Alignment",
    "No High Impact News",
]


class ChecklistSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=i) for i in CHECKLIST_ITEMS]

        super().__init__(
            placeholder="☑️ Trade checklist",
            min_values=0,
            max_values=len(CHECKLIST_ITEMS),
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        selected = self.values

        display = []
        for item in CHECKLIST_ITEMS:
            display.append(("☑️" if item in selected else "☐") + " " + item)

        ready = len(selected) == len(CHECKLIST_ITEMS)

        embed = discord.Embed(
            title="📊 Trade Checklist",
            description="\n".join(display),
            color=discord.Color.green() if ready else discord.Color.orange()
        )

        if ready:
            embed.add_field(name="✅ READY", value="All conditions met", inline=False)
        else:
            missing = [i for i in CHECKLIST_ITEMS if i not in selected]
            embed.add_field(name="⛔ NOT READY", value="\n".join(missing), inline=False)

        await interaction.response.edit_message(embed=embed, view=self.view)


class ChecklistView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(ChecklistSelect())


@bot.tree.command(name="checklist", description="Trading checklist (SMC entry filter)")
async def checklist(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📊 Pre-Trade Checklist",
        description="Only trade when ALL conditions are met.",
        color=discord.Color.blurple()
    )

    await interaction.response.send_message(embed=embed, view=ChecklistView())


# =========================
# PLACEHOLDER COMMANDS
# (your full logic stays here unchanged)
# =========================

@bot.tree.command(name="pnl", description="Show PnL calendar")
async def pnl(interaction: discord.Interaction):
    await interaction.response.send_message("PnL working")


@bot.tree.command(name="addpnl", description="Add PnL")
async def addpnl(interaction: discord.Interaction):
    await interaction.response.send_message("AddPnL working")


@bot.tree.command(name="pnlsum", description="PnL summary")
async def pnlsum(interaction: discord.Interaction):
    await interaction.response.send_message("PnL summary working")


@bot.tree.command(name="summarize", description="AI summary")
async def summarize(interaction: discord.Interaction):
    await interaction.response.send_message("Summary working")


# =========================
# GLOBAL SYNC (FIXED LAYER 1)
# =========================
@bot.event
async def on_ready():
    load_pnl_data()

    try:
        synced = await bot.tree.sync()  # GLOBAL SYNC ONLY
        print(f"Global Synced {len(synced)} commands")

        print("REGISTERED:", [cmd.name for cmd in bot.tree.get_commands()])

    except Exception as e:
        print(f"Sync error: {e}")

    print(f"Logged in as {bot.user}")


# =========================
# RUN BOT
# =========================
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("Missing DISCORD_TOKEN")
    exit(1)

bot.run(TOKEN)