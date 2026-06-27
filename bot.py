import os
import discord
from discord.ext import commands
import random

TOKEN = os.getenv('DISCORD_TOKEN')


intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# 🌿 SAMPLE VALUE DATABASE
# =========================
values = {
    "dragon": 1000,
    "leo": 750,
    "kitsune": 500,
    "bunny": 100,
}


# =========================
# 🚀 READY
# =========================
@bot.event
async def on_ready():
    print(f"🌿 SenZ Clone Online as {bot.user}")
    await bot.tree.sync()


# =========================
# 📊 VALUE COMMAND (LIKE SENZ)
# =========================
@bot.tree.command(name="value", description="Check item value")
async def value(interaction: discord.Interaction, item: str):

    item = item.lower()

    if item in values:
        val = values[item]
        rarity = "Legendary" if val > 800 else "Rare" if val > 300 else "Common"

        embed = discord.Embed(
            title="🌿 Grow a Garden Value Check",
            description=f"📦 Item: **{item}**\n💰 Value: **{val}**\n⭐ Rarity: **{rarity}**",
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            title="❌ Not Found",
            description="Item not in database",
            color=discord.Color.red()
        )

    await interaction.response.send_message(embed=embed)


# =========================
# ⚖️ TRADE CALCULATOR (SENZ STYLE)
# =========================
@bot.tree.command(name="trade", description="Check win/loss trade")
async def trade(interaction: discord.Interaction, your_item: str, their_item: str):

    your = values.get(your_item.lower(), 0)
    theirs = values.get(their_item.lower(), 0)

    diff = your - theirs

    if diff > 200:
        result = "🟢 HUGE WIN"
    elif diff > 0:
        result = "🟢 WIN"
    elif diff == 0:
        result = "🟡 FAIR"
    elif diff > -200:
        result = "🔴 LOSS"
    else:
        result = "🔴 HUGE LOSS"

    embed = discord.Embed(
        title="⚖️ Trade Calculator",
        description=f"""
📦 You: {your_item} ({your})
📦 Them: {their_item} ({theirs})

📊 Result: **{result}**
""",
        color=discord.Color.blurple()
    )

    await interaction.response.send_message(embed=embed)


# =========================
# 📈 STOCK SYSTEM (SENZ STYLE SIMULATION)
# =========================
@bot.tree.command(name="stock", description="Check current stock")
async def stock(interaction: discord.Interaction):

    items = ["dragon", "leo", "kitsune", "bunny"]
    current = random.choice(items)

    embed = discord.Embed(
        title="📈 Grow a Garden Stock",
        description=f"🌿 Current Stock: **{current.upper()}**",
        color=discord.Color.green()
    )

    await interaction.response.send_message(embed=embed)


# =========================
# 🔔 ALERT SYSTEM
# =========================
@bot.tree.command(name="alert", description="Set stock alert")
async def alert(interaction: discord.Interaction, item: str):

    await interaction.response.send_message(
        f"🔔 Alert set for **{item}** (demo system)"
    )


# =========================
# 📊 HISTORY (FAKE SIMULATION)
# =========================
@bot.tree.command(name="history", description="View item history")
async def history(interaction: discord.Interaction, item: str):

    embed = discord.Embed(
        title=f"📊 {item} History",
        description="📉 900 → 950 → 1000 → 1100\n📈 Trend: Rising",
        color=discord.Color.gold()
    )

    await interaction.response.send_message(embed=embed)


# =========================
# 🚀 RUN
# =========================
bot.run(TOKEN)
