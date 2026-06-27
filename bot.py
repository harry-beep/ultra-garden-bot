import os
import discord
from discord.ext import commands, tasks
import aiosqlite
import random
import datetime

TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

DB = "probot.db"


# =========================
# 💾 DATABASE SETUP
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
        CREATE TABLE IF NOT EXISTS tickets (
            user_id INTEGER,
            channel_id INTEGER
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
# 🌿 BOT READY
# =========================
@bot.event
async def on_ready():
    print(f"🌿 Logged in as {bot.user}")
    await init_db()
    await bot.tree.sync()
    stock_loop.start()
    print("🚀 FULL PRO BOT ONLINE")


# =========================
# 🏓 PING
# =========================
@bot.tree.command(name="ping")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"🏓 Pong! {round(bot.latency * 1000)}ms"
    )


# =========================
# 🌱 SERVER SETUP
# =========================
@bot.tree.command(name="setup")
async def setup(interaction: discord.Interaction):
    guild = interaction.guild

    categories = {
        "📢 INFORMATION": ["rules", "announcements", "updates"],
        "🌱 GROW A GARDEN": ["stock-chat", "stock-alerts", "trading", "rare-finds"],
        "🎫 SUPPORT": ["tickets"],
        "💬 COMMUNITY": ["general", "memes"]
    }

    for cat, channels in categories.items():
        category = await guild.create_category(cat)
        for ch in channels:
            await guild.create_text_channel(ch, category=category)

    await interaction.response.send_message("🌿 Server fully built!")


# =========================
# 💰 ECONOMY SYSTEM
# =========================
@bot.tree.command(name="balance")
async def balance(interaction: discord.Interaction):

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT balance FROM economy WHERE user_id=?", (interaction.user.id,))
        row = await cur.fetchone()

        if not row:
            await db.execute("INSERT INTO economy VALUES (?, ?)", (interaction.user.id, 0))
            await db.commit()
            bal = 0
        else:
            bal = row[0]

    await interaction.response.send_message(f"💰 Balance: {bal} coins 🌿")


@bot.tree.command(name="daily")
async def daily(interaction: discord.Interaction):

    reward = random.randint(50, 150)

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT balance FROM economy WHERE user_id=?", (interaction.user.id,))
        row = await cur.fetchone()

        if not row:
            await db.execute("INSERT INTO economy VALUES (?, ?)", (interaction.user.id, reward))
        else:
            await db.execute(
                "UPDATE economy SET balance = balance + ? WHERE user_id=?",
                (reward, interaction.user.id)
            )

        await db.commit()

    await interaction.response.send_message(f"🎁 You earned {reward} coins!")


# =========================
# ⭐ LEVEL SYSTEM
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

        await db.execute(
            "UPDATE levels SET xp=?, level=? WHERE user_id=?",
            (xp, level, message.author.id)
        )
        await db.commit()

    await bot.process_commands(message)


# =========================
# 🎫 TICKET SYSTEM
# =========================
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Open Ticket", style=discord.ButtonStyle.green)
    async def open(self, interaction: discord.Interaction, button: discord.ui.Button):

        guild = interaction.guild

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True),
            guild.me: discord.PermissionOverwrite(view_channel=True)
        }

        channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            overwrites=overwrites
        )

        async with aiosqlite.connect(DB) as db:
            await db.execute("INSERT INTO tickets VALUES (?, ?)", (interaction.user.id, channel.id))
            await db.commit()

        await channel.send("🎫 Support will help you soon.")
        await interaction.response.send_message("Ticket created!", ephemeral=True)


@bot.tree.command(name="ticketpanel")
async def ticketpanel(interaction: discord.Interaction):
    await interaction.channel.send("🎫 Click to open a ticket", view=TicketView())
    await interaction.response.send_message("Panel sent", ephemeral=True)


# =========================
# 📈 STOCK SYSTEM
# =========================
@bot.tree.command(name="stock")
async def stock(interaction: discord.Interaction, item: str, status: str):

    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO stocks (item, status, time) VALUES (?, ?, ?)",
            (item, status, str(datetime.datetime.now()))
        )
        await db.commit()

    channel = discord.utils.get(interaction.guild.text_channels, name="stock-alerts")

    embed = discord.Embed(
        title="📈 Stock Update",
        description=f"{item} → {status}",
        color=discord.Color.green()
    )

    if channel:
        await channel.send(embed=embed)

    await interaction.response.send_message("Stock updated!")


# =========================
# 👋 WELCOME SYSTEM
# =========================
@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="announcements")

    if channel:
        embed = discord.Embed(
            title="🌿 Welcome!",
            description=f"Welcome {member.mention} to Grow a Garden!",
            color=discord.Color.green()
        )
        await channel.send(embed=embed)


# =========================
# 📈 BACKGROUND STOCK LOOP
# =========================
@tasks.loop(minutes=60)
async def stock_loop():
    print("📈 Stock system running...")


# =========================
# 🚀 RUN BOT
# =========================
bot.run(TOKEN)
