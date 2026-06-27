import os
import discord
from discord.ext import commands
import aiosqlite
import random
import datetime

TOKEN = "YOUR_BOT_TOKEN"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

DB = "garden.db"

balances = {}  # fallback economy cache


# =========================
# 💾 DATABASE
# =========================
async def init_db():
    async with aiosqlite.connect(DB) as db:

        await db.execute("""
        CREATE TABLE IF NOT EXISTS economy (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS levels (
            user_id INTEGER PRIMARY KEY,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS stocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT,
            status TEXT,
            time TEXT
        )
        """)

        await db.commit()


# =========================
# 🚀 READY
# =========================
@bot.event
async def on_ready():
    print(f"🌿 Logged in as {bot.user}")
    await init_db()
    await bot.tree.sync()
    print("✅ Slash commands synced!")


# =========================
# 🏓 PING
# =========================
@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 {round(bot.latency * 1000)}ms")


# =========================
# 🌱 SETUP SERVER
# =========================
@bot.tree.command(name="setup", description="Create Grow a Garden server")
async def setup(interaction: discord.Interaction):

    guild = interaction.guild

    categories = {
        "📢 INFO": ["rules", "announcements"],
        "🌱 GARDEN": ["stock-chat", "stock-alerts", "trading"],
        "🎫 SUPPORT": ["tickets"]
    }

    for cat, chans in categories.items():
        c = await guild.create_category(cat)
        for ch in chans:
            await guild.create_text_channel(ch, category=c)

    await interaction.response.send_message("🌿 Server setup complete!")


# =========================
# 📈 STOCK SYSTEM
# =========================
@bot.tree.command(name="stock", description="Post stock update")
async def stock(interaction: discord.Interaction, item: str, status: str):

    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO stocks (item, status, time) VALUES (?, ?, ?)",
            (item, status, str(datetime.datetime.now()))
        )
        await db.commit()

    embed = discord.Embed(
        title="📈 Grow a Garden Stock",
        description=f"🌿 **{item}** → {status}",
        color=discord.Color.green()
    )

    await interaction.response.send_message(embed=embed)


# =========================
# 💰 ECONOMY
# =========================
@bot.tree.command(name="balance", description="Check balance")
async def balance(interaction: discord.Interaction):

    user = interaction.user.id

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT balance FROM economy WHERE user_id=?", (user,))
        row = await cur.fetchone()

        if not row:
            await db.execute("INSERT INTO economy VALUES (?, ?)", (user, 0))
            await db.commit()
            bal = 0
        else:
            bal = row[0]

    await interaction.response.send_message(f"💰 Balance: {bal}")


@bot.tree.command(name="daily", description="Get daily coins")
async def daily(interaction: discord.Interaction):

    reward = random.randint(50, 200)
    user = interaction.user.id

    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT OR IGNORE INTO economy VALUES (?, 0)", (user,))
        await db.execute("UPDATE economy SET balance = balance + ? WHERE user_id=?", (reward, user))
        await db.commit()

    await interaction.response.send_message(f"🎁 You got {reward} coins!")


# =========================
# ⭐ LEVELING SYSTEM
# =========================
@bot.event
async def on_message(message):

    if message.author.bot:
        return

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT xp, level FROM levels WHERE user_id=?", (message.author.id,))
        row = await cur.fetchone()

        if not row:
            xp, level = 0, 1
            await db.execute("INSERT INTO levels VALUES (?, ?, ?)", (message.author.id, xp, level))
        else:
            xp, level = row

        xp += 5

        if xp >= level * 100:
            level += 1
            xp = 0
            await message.channel.send(f"⭐ {message.author.mention} leveled up to **{level}**!")

        await db.execute("UPDATE levels SET xp=?, level=? WHERE user_id=?", (xp, level, message.author.id))
        await db.commit()

    await bot.process_commands(message)


# =========================
# 🎫 TICKET SYSTEM
# =========================
class TicketView(discord.ui.View):
    @discord.ui.button(label="🎫 Create Ticket", style=discord.ButtonStyle.green)
    async def ticket(self, interaction: discord.Interaction, button: discord.ui.Button):

        guild = interaction.guild

        channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}"
        )

        await channel.send("🎫 Support will help you soon.")
        await interaction.response.send_message("Ticket created!", ephemeral=True)


@bot.tree.command(name="ticketpanel", description="Open ticket panel")
async def ticketpanel(interaction: discord.Interaction):
    await interaction.channel.send("🎫 Click below", view=TicketView())
    await interaction.response.send_message("Panel sent!", ephemeral=True)


# =========================
# 🛡️ MODERATION
# =========================
@bot.tree.command(name="kick", description="Kick a user")
async def kick(interaction: discord.Interaction, member: discord.Member):
    await member.kick()
    await interaction.response.send_message(f"🛡️ Kicked {member}")


@bot.tree.command(name="ban", description="Ban a user")
async def ban(interaction: discord.Interaction, member: discord.Member):
    await member.ban()
    await interaction.response.send_message(f"⛔ Banned {member}")


# =========================
# 👋 WELCOME
# =========================
@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="announcements")

    if channel:
        await channel.send(f"🌿 Welcome {member.mention}!")


# =========================
# 🚀 RUN BOT
# =========================
bot.run(TOKEN)
