import discord
from discord.ext import commands
from datetime import datetime, timedelta
import calendar
import json
import os
import io
from PIL import Image, ImageDraw, ImageFont

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Store PnL data in memory (use pnl_data.json for persistence)
pnl_data = {}
DATA_FILE = "pnl_data.json"

def load_pnl_data():
    global pnl_data
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                pnl_data = json.load(f)
        except:
            pnl_data = {}
    else:
        pnl_data = {}

def save_pnl_data():
    with open(DATA_FILE, 'w') as f:
        json.dump(pnl_data, f)

def get_font(size: int):
    for name in ["arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()

def render_calendar_image(year: int, month: int):
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    width = 980
    row_height = 100
    header_height = 120
    footer_height = 80
    height = header_height + len(cal) * row_height + footer_height
    image = Image.new("RGB", (width, height), "#0d1117")
    draw = ImageDraw.Draw(image)

    title_font = get_font(44)
    label_font = get_font(20)
    value_font = get_font(18)
    day_font = get_font(24)

    draw.text((30, 20), f"{month_name} {year}", font=title_font, fill="#ffffff")
    draw.text((30, 70), "Current month PnL calendar", font=label_font, fill="#9ca3af")

    cell_width = (width - 40) // 7
    weekday_names = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    for i, name in enumerate(weekday_names):
        x = 20 + i * cell_width
        draw.rectangle([x, header_height - 40, x + cell_width - 10, header_height], fill="#161b22")
        draw.text((x + 10, header_height - 38), name, font=label_font, fill="#c9d1d9")

    for row_index, week in enumerate(cal):
        y0 = header_height + row_index * row_height
        for col_index, day in enumerate(week):
            x0 = 20 + col_index * cell_width
            x1 = x0 + cell_width - 10
            y1 = y0 + row_height - 10
            draw.rectangle([x0, y0, x1, y1], fill="#161b22", outline="#30363d", width=2)
            if day != 0:
                date_key = f"{year}-{month:02d}-{day:02d}"
                if date_key in pnl_data:
                    value = pnl_data[date_key]["value"]
                    pnl_text = f"{value:+.2f}"
                    color = "#7ee787" if value >= 0 else "#ff7b72"
                else:
                    pnl_text = ""
                    color = "#8b949e"

                draw.text((x0 + 10, y0 + 12), pnl_text, font=value_font, fill=color)
                draw.text((x0 + 10, y0 + 46), str(day), font=day_font, fill="#ffffff")

    total_pnl = sum(data["value"] for data in pnl_data.values() if data)
    trading_days = len(pnl_data)
    footer_text = f"Total: {total_pnl:+.2f} | Trading days: {trading_days}"
    draw.text((30, height - footer_height + 20), footer_text, font=label_font, fill="#8b949e")

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

    embed = discord.Embed(
        title=f"📅 {calendar.month_name[now.month]} {now.year}",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="Monthly stats",
        value=f"🟢 `${total_pnl:+.2f}`  📊 Trading days: `{trading_days}`",
        inline=False
    )
    embed.add_field(
        name="ℹ️ Usage",
        value="Use `/addpnl date:[day] pnl:[amount]` to add PnL for the current month",
        inline=False
    )
    embed.set_image(url="attachment://calendar.png")

    await interaction.response.send_message(embed=embed, file=file)

@bot.tree.command(name="addpnl", description="Add PnL for a specific date")
async def add_pnl(interaction: discord.Interaction, date: int, pnl: float, note: str = ""):
    now = datetime.now()
    year = now.year
    month = now.month

    # Validate date
    if date < 1 or date > 31:
        await interaction.response.send_message("❌ Date must be between 1 and 31", ephemeral=True)
        return

    # Create date key
    date_key = f"{year}-{month:02d}-{date:02d}"

    # Save PnL data
    pnl_data[date_key] = {
        "value": pnl,
        "note": note or "No notes",
        "timestamp": datetime.now().isoformat()
    }
    save_pnl_data()

    emoji = "📈" if pnl >= 0 else "📉"
    color_emoji = "🟢" if pnl >= 0 else "🔴"

    await interaction.response.send_message(
        f"{color_emoji} **PnL updated for {date_key}**\n"
        f"{emoji} Value: `${pnl:+.2f}`\n"
        f"📝 Note: {note or 'None'}",
        ephemeral=True
    )

@bot.tree.command(name="pnlsum", description="View total PnL")
async def pnl_summary(interaction: discord.Interaction):
    total = sum(data["value"] for data in pnl_data.values())
    count = len(pnl_data)

    embed = discord.Embed(
        title="📈 PnL Summary",
        color=discord.Color.green() if total >= 0 else discord.Color.red()
    )
    embed.add_field(name="Total PnL", value=f"**${total:.2f}**", inline=False)
    embed.add_field(name="Trading Days", value=f"**{count}**", inline=False)
    embed.add_field(name="Average Daily PnL", value=f"**${total/count:.2f}**" if count > 0 else "N/A", inline=False)

    await interaction.response.send_message(embed=embed)

@bot.event
async def on_ready():
    load_pnl_data()
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    print(f"Logged in as {bot.user}")

# Get token from environment variable
TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    print("❌ DISCORD_TOKEN environment variable not set!")
    exit(1)

bot.run(TOKEN)