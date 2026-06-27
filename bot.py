import os
import discord
from discord.ext import commands, tasks
import aiosqlite
import asyncio
from datetime import datetime

TOKEN = "YOUR_BOT_TOKEN_HERE"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

DB_PATH = "growgarden.db"


# =========================
# 💾 DATABASE
# =========================
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            channel_id INTEGER,
            user_id INTEGER
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS stock_logs (
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
    stock_task.start()
    print("🚀 PRO BOT ONLINE")


# =========================
# 🏓 PING
# =========================
@bot.tree.command(name="ping")
async def ping(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"🌱 {round(bot.latency * 1000)}ms",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)


# =========================
# 🌱 SERVER SETUP
# =========================
@bot.tree.command(name="setup")
async def setup(interaction: discord.Interaction):
    guild = interaction.guild

    embed = discord.Embed(
        title="🌿 Grow a Garden Setup",
        description="Building full server system...",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

    # Roles
    roles = ["👑 Owner", "🛠 Admin", "🌿 Moderator", "👤 Member"]
    for r in roles:
        if not discord.utils.get(guild.roles, name=r):
            await guild.create_role(name=r)

    # Categories
    info = await guild.create_category("📢 INFORMATION")
    garden = await guild.create_category("🌱 GROW A GARDEN")
    support = await guild.create_category("🎫 SUPPORT")

    await guild.create_text_channel("📜rules", category=info)
    await guild.create_text_channel("📢announcements", category=info)

    await guild.create_text_channel("📈stock-chat", category=garden)
    await guild.create_text_channel("🚨stock-alerts", category=garden)
    await guild.create_text_channel("💰trading", category=garden)

    ticket = await guild.create_text_channel("🎫create-ticket", category=support)

    await interaction.followup.send("🌿 Setup complete!")


# =========================
# 🎫 TICKET SYSTEM (PRO)
# =========================
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Create Ticket", style=discord.ButtonStyle.green)
    async def create(self, interaction: discord.Interaction, button: discord.ui.Button):

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

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT INTO tickets VALUES (?, ?)", (channel.id, interaction.user.id))
            await db.commit()

        embed = discord.Embed(
            title="🎫 Support Ticket",
            description="A staff member will assist you.\n🔴 Press close when done.",
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
    await interaction.response.send_message("🎫 Panel sent", ephemeral=True)


# =========================
# 📈 STOCK SYSTEM (PRO)
# =========================
@bot.tree.command(name="stock")
async def stock(interaction: discord.Interaction, item: str, status: str):

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO stock_logs (item, status, time) VALUES (?, ?, ?)",
            (item, status, datetime.now().strftime("%Y-%m-%d %H:%M"))
        )
        await db.commit()

    embed = discord.Embed(
        title="📈 Grow a Garden Stock Update",
        color=discord.Color.green()
    )
    embed.add_field(name="🌱 Item", value=item, inline=False)
    embed.add_field(name="📊 Status", value=status, inline=False)
    embed.set_footer(text="🌿 Live Stock System")

    channel = discord.utils.get(interaction.guild.text_channels, name="🚨stock-alerts")

    if channel:
        await channel.send(embed=embed)

    await interaction.response.send_message("🚨 Stock updated!", ephemeral=True)


# =========================
# 🛡️ MODERATION LOGGING
# =========================
@bot.tree.command(name="kick")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    await member.kick(reason=reason)

    embed = discord.Embed(
        title="🛡️ Kick",
        description=f"{member} kicked\nReason: {reason}",
        color=discord.Color.orange()
    )

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="ban")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    await member.ban(reason=reason)

    embed = discord.Embed(
        title="⛔ Ban",
        description=f"{member} banned\nReason: {reason}",
        color=discord.Color.red()
    )

    await interaction.response.send_message(embed=embed)


# =========================
# 👋 WELCOME SYSTEM
# =========================
@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="📢announcements")

    if channel:
        embed = discord.Embed(
            title="🌿 Welcome!",
            description=f"Welcome {member.mention} to Grow a Garden 🌱",
            color=discord.Color.green()
        )
        await channel.send(embed=embed)


# =========================
# 🔁 BACKGROUND STOCK TASK
# =========================
@tasks.loop(minutes=60)
async def stock_task():
    print("📈 Stock system running (placeholder update loop)")


# =========================
# 🚀 RUN BOT
# =========================
bot.run(TOKEN)
