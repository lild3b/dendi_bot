import discord
from discord.ext import commands
from datetime import datetime
import calendar
import json
import os
import io
import uuid
import aiohttp
from PIL import Image, ImageDraw, ImageFont

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

pnl_data = {}
DATA_FILE = "pnl_data.json"

QUICKCHAT_API_KEY = os.getenv("QUICKCHAT_API_KEY")
QUICKCHAT_SCENARIO_ID = "u5nco0jde0"
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


def render_calendar_image(year: int, month: int):
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
    # --- Top header ---
    total_pnl = sum(data["value"] for data in pnl_data.values())
    trading_days = len(pnl_data)
    pnl_color = "#4ade80" if total_pnl >= 0 else "#f87171"
    draw.text((20, 18), f"{month_name} {year}", font=title_font, fill="#ffffff")
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
    draw.text(
        (sx + sl_w + gap + pv_w + gap * 2, sy),
        days_label,
        font=stats_font,
        fill="#9ca3af",
    )
    # --- Weekday header row ---
    weekday_names = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
    draw.rectangle(
        [0, top_header_h, width, top_header_h + weekday_header_h], fill="#1e2028"
    )
    for i, name in enumerate(weekday_names):
        x = i * cell_width
        draw.text((x + 15, top_header_h + 12), name, font=weekday_font, fill="#6b7280")
    # --- Cells ---
    for row_index, week in enumerate(cal):
        y0 = top_header_h + weekday_header_h + row_index * cell_height
        for col_index, day in enumerate(week):
            x0 = col_index * cell_width
            x1 = x0 + cell_width
            y1 = y0 + cell_height
            date_key = f"{year}-{month:02d}-{day:02d}" if day != 0 else None
            has_data = date_key and date_key in pnl_data
            if has_data:
                value = pnl_data[date_key]["value"]
                cell_bg = "#0d2e1a" if value >= 0 else "#2e0d0d"
            else:
                cell_bg = "#1e2028"
            draw.rectangle([x0, y0, x1, y1], fill=cell_bg, outline="#2a2d35", width=1)
            if day != 0:
                is_today = (
                    year == today.year and month == today.month and day == today.day
                )
                if is_today:
                    r = 16
                    cx = x0 + 22
                    cy = y0 + 18
                    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#3b82f6")
                    day_str = str(day)
                    db = draw.textbbox((0, 0), day_str, font=day_font)
                    dw = db[2] - db[0]
                    dh = db[3] - db[1]
                    draw.text(
                        (cx - dw // 2, cy - dh // 2),
                        day_str,
                        font=day_font,
                        fill="#ffffff",
                    )
                else:
                    draw.text(
                        (x0 + 10, y0 + 8), str(day), font=day_font, fill="#6b7280"
                    )
                if has_data:
                    value = pnl_data[date_key]["value"]
                    trades = pnl_data[date_key].get("trades", 0)
                    pnl_display = (
                        f"${value:.2f}" if value >= 0 else f"-${abs(value):.2f}"
                    )
                    pnl_clr = "#4ade80" if value >= 0 else "#f87171"
                    trades_display = f"Trades: {trades}"
                    draw.text(
                        (x0 + 10, y0 + 42), pnl_display, font=pnl_font, fill=pnl_clr
                    )
                    draw.text(
                        (x0 + 10, y0 + 82),
                        trades_display,
                        font=trades_font,
                        fill="#e5e7eb",
                    )
    output = io.BytesIO()
    image.save(output, format="PNG")
    output.seek(0)
    return output


@bot.tree.command(name="pnl", description="Show current month PnL calendar")
async def pnl(interaction: discord.Interaction):
    now = datetime.now()
    image_bytes = render_calendar_image(now.year, now.month)
    file = discord.File(image_bytes, filename="calendar.png")
    total_pnl = sum(data["value"] for data in pnl_data.values())
    trading_days = len(pnl_data)
    total_trades = sum(data.get("trades", 0) for data in pnl_data.values())
    embed = discord.Embed(
        title=f"📅 {calendar.month_name[now.month]} {now.year}",
        color=discord.Color.blue(),
    )
    embed.add_field(
        name="Monthly stats",
        value=f"🟢 `${total_pnl:+.2f}`  📊 Days: `{trading_days}`  🔢 Trades: `{total_trades}`",
        inline=False,
    )
    embed.set_image(url="attachment://calendar.png")
    await interaction.response.send_message(embed=embed, file=file)


@bot.tree.command(name="addpnl", description="Add PnL for a specific date")
async def add_pnl(
    interaction: discord.Interaction, date: int, pnl: float, trades: int, note: str = ""
):
    now = datetime.now()
    year = now.year
    month = now.month
    if date < 1 or date > 31:
        await interaction.response.send_message(
            "❌ Date must be between 1 and 31", ephemeral=True
        )
        return
    date_key = f"{year}-{month:02d}-{date:02d}"
    pnl_data[date_key] = {
        "value": pnl,
        "trades": trades,
        "note": note or "No notes",
        "timestamp": datetime.now().isoformat(),
    }
    save_pnl_data()
    emoji = "📈" if pnl >= 0 else "📉"
    color_emoji = "🟢" if pnl >= 0 else "🔴"
    await interaction.response.send_message(
        f"{color_emoji} **PnL updated for {date_key}**\n"
        f"{emoji} Value: `${pnl:+.2f}`\n"
        f"🔢 Trades: `{trades}`\n"
        f"📝 Note: {note or 'None'}",
        ephemeral=True,
    )


@bot.tree.command(name="pnlsum", description="View total PnL")
async def pnl_summary(interaction: discord.Interaction):
    total = sum(data["value"] for data in pnl_data.values())
    count = len(pnl_data)
    total_trades = sum(data.get("trades", 0) for data in pnl_data.values())
    embed = discord.Embed(
        title="📈 PnL Summary",
        color=discord.Color.green() if total >= 0 else discord.Color.red(),
    )
    embed.add_field(name="Total PnL", value=f"**${total:.2f}**", inline=False)
    embed.add_field(name="Trading Days", value=f"**{count}**", inline=False)
    embed.add_field(name="Total Trades", value=f"**{total_trades}**", inline=False)
    embed.add_field(
        name="Average Daily PnL",
        value=f"**${total / count:.2f}**" if count > 0 else "N/A",
        inline=False,
    )
    await interaction.response.send_message(embed=embed)


@bot.tree.command(
    name="summarize",
    description="Summarize recent messages from #trade-result using AI",
)
@discord.app_commands.describe(
    limit="Number of recent messages to summarize (default 20, max 50)"
)
async def summarize(interaction: discord.Interaction, limit: int = 20):
    try:
        await interaction.response.defer()
    except Exception as e:
        print(f"[summarize] defer failed: {e}")
        return

    print(f"[summarize] invoked by {interaction.user} in channel id={interaction.channel.id if interaction.channel else 'None'}")

    channel_id = interaction.channel.id if interaction.channel else None
    if channel_id not in ALLOWED_SUMMARY_CHANNELS:
        await interaction.followup.send(
            "❌ This command is not allowed in this channel.", ephemeral=True
        )
        return

    channel_name = interaction.channel.name if interaction.channel else "unknown"

    if not QUICKCHAT_API_KEY:
        await interaction.followup.send(
            "❌ QuickChat API key is not configured.", ephemeral=True
        )
        return

    limit = max(1, min(limit, 50))

    messages = []
    async for msg in interaction.channel.history(limit=limit):
        if not msg.author.bot and msg.content.strip():
            ts = msg.created_at.strftime("%Y-%m-%d %H:%M")
            messages.append(f"[{ts}] {msg.author.display_name}: {msg.content}")

    messages.reverse()

    if not messages:
        await interaction.followup.send(
            "❌ No messages found to summarize.", ephemeral=True
        )
        return

    messages_text = "\n".join(messages)
    prompt = (
        f"Here are the recent messages from a trading Discord channel called #{channel_name}. "
        f"Please summarize the key trading results, notable wins/losses, and any important patterns or insights:\n\n"
        f"{messages_text}"
    )

    conv_id = str(uuid.uuid4())[:8]

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                "https://chat.quickchat.ai/chat",
                json={
                    "api_key": QUICKCHAT_API_KEY,
                    "scenario_id": QUICKCHAT_SCENARIO_ID,
                    "text": prompt,
                    "conv_id": conv_id,
                },
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    print(f"QuickChat error {resp.status}: {body}")
                    await interaction.followup.send(
                        f"❌ AI returned an error (status {resp.status}): {body[:300]}",
                        ephemeral=True,
                    )
                    return
                data = await resp.json()
                reply = data.get("reply", "No response from AI.")
        except Exception as e:
            await interaction.followup.send(
                f"❌ Failed to reach AI: {e}", ephemeral=True
            )
            return

    embed = discord.Embed(
        title=f"🤖 AI Summary — #{channel_name}",
        description=reply,
        color=discord.Color.blurple(),
    )
    embed.set_footer(
        text=f"Based on last {len(messages)} messages • Powered by QuickChat AI"
    )
    await interaction.followup.send(embed=embed)


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    print(f"[tree error] {error}")
    try:
        if interaction.response.is_done():
            await interaction.followup.send(f"❌ Error: {error}", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Error: {error}", ephemeral=True)
    except Exception as e:
        print(f"[tree error] failed to send error message: {e}")


@bot.event
async def on_ready():
    load_pnl_data()
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    print(f"Logged in as {bot.user}")


TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("❌ DISCORD_TOKEN environment variable not set!")
    exit(1)
bot.run(TOKEN)
