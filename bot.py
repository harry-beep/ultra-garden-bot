import os
import discord
from discord.ext import commands, tasks
import aiosqlite
import asyncio
import datetime

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

DB = "ultra_garden.db"

# =========================
# 💾 DATABASE INIT
# =========================
async def init_db():
    async with aiosqlite.connect(DB) as db:

        await db.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            channel_id INTEGER,
            user_id INTEGER
        )
        """)

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
# 🌿 BOT READY
# =========================
@bot.event
async def on_ready():
    print(f"🌿 ULTRA PRO BOT ONLINE: {bot.user}")
    await init_db()
    await bot.tree.sync()
    anti_spam.start()
    stock_loop.start()


# =========================
# 🏓 PING
# =========================
@bot.tree.command(name="ping")
async def ping(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"🌿 {round(bot.latency * 1000)}ms",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)


# =========================
# 🌱 SERVER SETUP
# =========================
@bot.tree.command(name="setup")
async def setup(interaction: discord.Interaction):
    guild = interaction.guild

    roles = ["👑 Owner", "🛠 Admin", "🧑‍🌾 Mod", "🌿 Member"]
    for r in roles:
        if not discord.utils.get(guild.roles, name=r):
            await guild.create_role(name=r)

    info = await guild.create_category("📢 INFORMATION")
    garden = await guild.create_category("🌱 GROW A GARDEN")
    support = await guild.create_category("🎫 SUPPORT")

    await guild.create_text_channel("📜rules", category=info)
    await guild.create_text_channel("📢announcements", category=info)

    await guild.create_text_channel("📈stock-chat", category=garden)
    await guild.create_text_channel("🚨stock-alerts", category=garden)

    await guild.create_text_channel("🎫tickets", category=support)

    await interaction.response.send_message("🌿 Setup complete!")


# =========================
# 🎫 ULTRA TICKET SYSTEM
# =========================
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Open Ticket", style=discord.ButtonStyle.green)
    async def open(self, interaction: discord.Interaction, button: discord.ui.Button):

        guild = interaction.guild

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True)
        }

        channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            overwrites=overwrites
        )

        async with aiosqlite.connect(DB) as db:
            await db.execute("INSERT INTO tickets VALUES (?, ?)", (channel.id, interaction.user.id))
            await db.commit()

        embed = discord.Embed(
            title="🎫 Support Ticket",
            description="Staff will assist you.\n🔴 Click close when done.",
            color=discord.Color.green()
        )

        await channel.send(embed=embed, view=CloseTicket())
        await interaction.response.send_message("🎫 Ticket created!", ephemeral=True)


class CloseTicket(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔴 Close", style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.send("🔴 Closing ticket...")
        await interaction.channel.delete()


@bot.tree.command(name="ticketpanel")
async def panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎫 Support Center",
        description="Click below to open a ticket",
        color=discord.Color.green()
    )
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("Sent", ephemeral=True)


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

    embed = discord.Embed(
        title="💰 Balance",
        description=f"{interaction.user.mention}: **{bal} coins 🌿**",
        color=discord.Color.green()
    )

    await interaction.response.send_message(embed=embed)


# =========================
# 📊 LEVEL SYSTEM
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
            await message.channel.send(f"🌿 {message.author.mention} leveled up to **{level}**!")

        await db.execute("UPDATE levels SET xp=?, level=? WHERE user_id=?", (xp, level, message.author.id))
        await db.commit()

    await bot.process_commands(message)


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

    embed = discord.Embed(
        title="📈 Stock Update",
        description=f"🌱 {item} → {status}",
        color=discord.Color.green()
    )

    channel = discord.utils.get(interaction.guild.text_channels, name="🚨stock-alerts")

    if channel:
        await channel.send(embed=embed)

    await interaction.response.send_message("🚨 Stock updated", ephemeral=True)


# =========================
# 🛡️ ANTI SPAM
# =========================
spam_tracker = {}

@tasks.loop(seconds=5)
async def anti_spam():
    spam_tracker.clear()


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user = message.author.id
    spam_tracker[user] = spam_tracker.get(user, 0) + 1

    if spam_tracker[user] > 6:
        await message.channel.send(f"🛡️ {message.author.mention} stop spamming!")
        return

    await bot.process_commands(message)


# =========================
# 👋 WELCOME SYSTEM
# =========================
@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="📢announcements")

    if channel:
        embed = discord.Embed(
            title="🌿 Welcome!",
            description=f"{member.mention} joined Grow a Garden!",
            color=discord.Color.green()
        )
        await channel.send(embed=embed)


# =========================
# 📈 STOCK AUTO LOOP (SIMULATION)
# =========================
@tasks.loop(minutes=60)
async def stock_loop():
    print("📈 Stock system running...")


# =========================
# 🚀 RUN BOT
# =========================
bot.run(TOKEN)
