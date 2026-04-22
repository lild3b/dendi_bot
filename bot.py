import discord
from discord.ext import commands
from datetime import datetime
import calendar
import json
import os
import io
import aiohttp
from openai import AsyncOpenAI
from PIL import Image, ImageDraw, ImageFont

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

pnl_data = {}
DATA_FILE = "pnl_data.json"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
ALLOWED_SUMMARY_CHANNELS = [1491280657387622420]


# =========================
# CHECKLIST SYSTEM (ADDED)
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
            placeholder="☑️ Select checklist items...",
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


@bot.tree.command(name="checklist", description="Pre-trade checklist")
async def checklist(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📊 Pre-Trade Checklist",
        description="Only trade when ALL conditions are met.",
        color=discord.Color.blurple()
    )
    await interaction.response.send_message(embed=embed, view=ChecklistView())


# =========================
# ORIGINAL CODE (UNCHANGED)
# =========================

def load_pnl_data():
    global pnl_data
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                raw = json.load(f)
            if raw and all(k[:4].isdigit() for k in raw.keys()):
                pnl_data = {"legacy": raw}
            else:
                pnl_data = raw
        except:
            pnl_data = {}
    else:
        pnl_data = {}


def save_pnl_data():
    with open(DATA_FILE, "w") as f:
        json.dump(pnl_data, f)


def get_user_pnl(user_id: str) -> dict:
    return pnl_data.get(str(user_id), {})


def set_user_pnl(user_id: str, date_key: str, entry: dict):
    uid = str(user_id)
    if uid not in pnl_data:
        pnl_data[uid] = {}
    pnl_data[uid][date_key] = entry
    save_pnl_data()


def get_font(size: int):
    for name in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "arial.ttf",
        "DejaVuSans.ttf",
        "LiberationSans-Regular.ttf",
    ]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_calendar_image(year: int, month: int, user_data: dict, display_name: str = ""):
    cal = calendar.Calendar(firstweekday=6).monthdayscalendar(year, month)
    month_name = calendar.month_name[month]
    today = datetime.now()

    cell_width = 200
    cell_height = 130
    weekday_header_h = 45
    top_header_h = 70
    width = cell_width * 7
    height = top_header_h + weekday_header_h + len(cal) * cell_height

    image = Image.new("RGB", (width, height), "#16181d")
    draw = ImageDraw.Draw(image)

    title_font = get_font(32)
    stats_font = get_font(22)
    weekday_font = get_font(20)
    day_font = get_font(20)
    pnl_font = get_font(30)
    trades_font = get_font(19)

    total_pnl = sum(data["value"] for data in user_data.values())
    trading_days = len(user_data)
    pnl_color = "#4ade80" if total_pnl >= 0 else "#f87171"

    header_title = f"{month_name} {year}" + (f"  •  {display_name}" if display_name else "")
    draw.text((20, 18), header_title, font=title_font, fill="#ffffff")

    stats_label = "Monthly stats:"
    pnl_val = f"${abs(total_pnl):.2f}" if total_pnl >= 0 else f"-${abs(total_pnl):.2f}"
    days_label = f"Trading days: {trading_days}"

    sl_bbox = draw.textbbox((0, 0), stats_label, font=stats_font)
    sl_w = sl_bbox[2] - sl_bbox[0]
    pv_bbox = draw.textbbox((0, 0), pnl_val, font=stats_font)
    pv_w = pv_bbox[2] - pv_bbox[0]
    dl_bbox = draw.textbbox((0, 0), days_label, font=stats_font)
    dl_w = dl_bbox[2] - dl_bbox[0]

    gap = 12
    total_stats_w = sl_w + gap + pv_w + gap * 2 + dl_w
    sx = width - total_stats_w - 20
    sy = 24

    draw.text((sx, sy), stats_label, font=stats_font, fill="#9ca3af")
    draw.text((sx + sl_w + gap, sy), pnl_val, font=stats_font, fill=pnl_color)
    draw.text((sx + sl_w + gap + pv_w + gap * 2, sy), days_label, font=stats_font, fill="#9ca3af")

    weekday_names = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
    draw.rectangle([0, top_header_h, width, top_header_h + weekday_header_h], fill="#1e2028")
    for i, name in enumerate(weekday_names):
        x = i * cell_width
        draw.text((x + 15, top_header_h + 12), name, font=weekday_font, fill="#6b7280")

    for row_index, week in enumerate(cal):
        y0 = top_header_h + weekday_header_h + row_index * cell_height
        for col_index, day in enumerate(week):
            x0 = col_index * cell_width
            x1 = x0 + cell_width
            y1 = y0 + cell_height

            date_key = f"{year}-{month:02d}-{day:02d}" if day != 0 else None
            has_data = date_key and date_key in user_data

            if has_data:
                value = user_data[date_key]["value"]
                cell_bg = "#0d2e1a" if value >= 0 else "#2e0d0d"
            else:
                cell_bg = "#1e2028"

            draw.rectangle([x0, y0, x1, y1], fill=cell_bg, outline="#2a2d35", width=1)

            if day != 0:
                is_today = (year == today.year and month == today.month and day == today.day)

                if is_today:
                    r = 16
                    cx = x0 + 22
                    cy = y0 + 18

                    # Blue circle
                    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#3b82f6")

                    # Centered day number
                    day_str = str(day)
                    db = draw.textbbox((0, 0), day_str, font=day_font)
                    dw = db[2] - db[0]
                    dh = db[3] - db[1]

                    draw.text((cx - dw // 2, cy - dh // 2), day_str, font=day_font, fill="#ffffff")
                else:
                    draw.text((x0 + 10, y0 + 8), str(day), font=day_font, fill="#6b7280")

                if has_data:
                    value = user_data[date_key]["value"]
                    trades = user_data[date_key].get("trades", 0)
                    pnl_display = f"${value:.2f}" if value >= 0 else f"-${abs(value):.2f}"
                    pnl_clr = "#4ade80" if value >= 0 else "#f87171"
                    trades_display = f"Trades: {trades}"
                    draw.text((x0 + 10, y0 + 42), pnl_display, font=pnl_font, fill=pnl_clr)
                    draw.text((x0 + 10, y0 + 82), trades_display, font=trades_font, fill="#e5e7eb")

    output = io.BytesIO()
    image.save(output, format="PNG")
    output.seek(0)
    return output


@bot.tree.command(name="pnl", description="Show your PnL calendar (or another user's)")
@discord.app_commands.describe(user="View another user's calendar (optional)")
async def pnl(interaction: discord.Interaction, user: discord.Member = None):
    await interaction.response.defer()
    target = user or interaction.user
    now = datetime.now()
    all_user_data = get_user_pnl(str(target.id))
    display_name = target.display_name if user else ""

    image_bytes = render_calendar_image(now.year, now.month, all_user_data, display_name)
    file = discord.File(image_bytes, filename="calendar.png")

    embed = discord.Embed(title="PnL Calendar", color=discord.Color.blue())
    embed.set_image(url="attachment://calendar.png")

    await interaction.followup.send(embed=embed, file=file)


@bot.tree.command(name="addpnl", description="Add PnL for a specific date")
async def add_pnl(interaction: discord.Interaction, date: int, pnl: float, trades: int):
    now = datetime.now()
    date_key = f"{now.year}-{now.month:02d}-{date:02d}"

    set_user_pnl(str(interaction.user.id), date_key, {
        "value": pnl,
        "trades": trades
    })

    await interaction.response.send_message("PnL updated")


@bot.tree.command(name="pnlsum", description="View your PnL summary")
async def pnl_summary(interaction: discord.Interaction):
    data = get_user_pnl(str(interaction.user.id))
    total = sum(d["value"] for d in data.values())

    await interaction.response.send_message(f"Total PnL: ${total:.2f}")


@bot.tree.command(name="summarize", description="AI summary of recent trades")
async def summarize(interaction: discord.Interaction, limit: int = 20):
    await interaction.response.defer()

    messages = []
    async for msg in interaction.channel.history(limit=limit):
        if not msg.author.bot:
            messages.append(msg.content)

    text = "\n".join(messages)

    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": text}]
    )

    await interaction.followup.send(response.choices[0].message.content)


# =========================
# GLOBAL SYNC (UPDATED)
# =========================
@bot.event
async def on_ready():
    load_pnl_data()

    synced = await bot.tree.sync()
    print(f"Global Synced {len(synced)} commands")
    print("REGISTERED:", [cmd.name for cmd in bot.tree.get_commands()])

    print(f"Logged in as {bot.user}")


TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("❌ DISCORD_TOKEN not set!")
    exit(1)

bot.run(TOKEN)