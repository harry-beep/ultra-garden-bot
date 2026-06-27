import os
import discord
from discord.ext import commands, tasks
import aiosqlite
import random
import datetime

TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

DB = "garden.db"


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
        CREATE TABLE IF NOT EXISTS tickets (
            user_id INTEGER,
            channel_id INTEGER
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS warns (
            user_id INTEGER,
            count INTEGER DEFAULT 0
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
    stats_loop.start()
    print("✅ FULL SYSTEM ONLINE")


# =========================
# 🌱 ONE COMMAND SETUP (FULL SERVER)
# =========================
@bot.tree.command(name="setup")
async def setup(interaction: discord.Interaction):

    guild = interaction.guild

    roles = [
        "👑 Owner", "🛠 Admin", "⚡ Moderator",
        "🌱 Garden Expert", "⭐ VIP", "🎮 Member", "🤖 Bots"
    ]

    for r in roles:
        await guild.create_role(name=r)

    categories = {
        "📢 INFORMATION": ["📜 rules", "📢 announcements", "📢 news"],
        "🌱 GARDEN": ["📈 stock-predictor", "📈 stock-alerts", "🌱 garden-chat", "💰 trading", "⭐ rare-finds"],
        "🎫 SUPPORT": ["🎫 tickets", "📋 ticket-logs"],
        "👥 COMMUNITY": ["💬 general", "😂 memes", "🎮 roblox"],
        "🚨 ALERTS": ["🚨 alerts"]
    }

    for cat, channels in categories.items():
        category = await guild.create_category(cat)
        for ch in channels:
            await guild.create_text_channel(ch, category=category)

    await interaction.response.send_message("🌿 FULL SERVER CREATED!")


# =========================
# 📈 STOCK PREDICTOR
# =========================
@bot.tree.command(name="predict")
async def predict(interaction: discord.Interaction, mode: str = "all"):

    items = ["Golden Pumpkin", "Sugar Apple", "Star Carrot", "Moon Mango"]

    def make_item():
        return random.choice(items)

    if mode == "rare":
        item = "🌟 " + make_item()
        chance = "VERY LOW STOCK"
    elif mode == "all":
        item = make_item()
        chance = random.choice(["HIGH", "MEDIUM", "LOW"])
    else:
        item = make_item()
        chance = "UNKNOWN"

    embed = discord.Embed(
        title="📈 Stock Predictor",
        description=f"""
🌱 Item: {item}
📊 Chance: {chance}
🔮 Time: {datetime.datetime.now().strftime("%H:%M")}
""",
        color=discord.Color.green()
    )

    await interaction.response.send_message(embed=embed)


# =========================
# 🚨 ALERT SYSTEM
# =========================
@bot.tree.command(name="alert")
async def alert(interaction: discord.Interaction, message: str):

    role = discord.utils.get(interaction.guild.roles, name="⭐ VIP")
    channel = discord.utils.get(interaction.guild.text_channels, name="🚨 alerts")

    if channel:
        await channel.send(f"🚨 {role.mention if role else ''} {message}")

    await interaction.response.send_message("Alert sent!")


# =========================
# 💰 ECONOMY
# =========================
@bot.tree.command(name="daily")
async def daily(interaction: discord.Interaction):

    reward = random.randint(50, 300)

    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT OR IGNORE INTO economy VALUES (?, 0)", (interaction.user.id,))
        await db.execute("UPDATE economy SET balance = balance + ? WHERE user_id=?", (reward, interaction.user.id))
        await db.commit()

    await interaction.response.send_message(f"🎁 +{reward} coins")


@bot.tree.command(name="balance")
async def balance(interaction: discord.Interaction):

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT balance FROM economy WHERE user_id=?", (interaction.user.id,))
        row = await cur.fetchone()

    bal = row[0] if row else 0
    await interaction.response.send_message(f"💰 {bal}")


# =========================
# 🎫 TICKET SYSTEM (FULL)
# =========================
class TicketView(discord.ui.View):

    @discord.ui.button(label="🎫 Create Ticket", style=discord.ButtonStyle.green)
    async def create(self, interaction: discord.Interaction, button: discord.ui.Button):

        guild = interaction.guild

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True),
            guild.me: discord.PermissionOverwrite(view_channel=True)
        }

        channel = await guild.create_text_channel(
            f"ticket-{interaction.user.name}",
            overwrites=overwrites
        )

        await channel.send(
            "🎫 Support Ticket\n"
            "Buttons: Close / Claim / Transcript (simulated)"
        )

        await interaction.response.send_message("Ticket created!", ephemeral=True)


@bot.tree.command(name="ticket")
async def ticket(interaction: discord.Interaction):
    await interaction.channel.send("🎫 Create a ticket:", view=TicketView())
    await interaction.response.send_message("Panel sent", ephemeral=True)


# =========================
# 🛡️ MODERATION
# =========================
@bot.tree.command(name="ban")
async def ban(interaction: discord.Interaction, member: discord.Member):
    await member.ban()
    await interaction.response.send_message("⛔ banned")


@bot.tree.command(name="kick")
async def kick(interaction: discord.Interaction, member: discord.Member):
    await member.kick()
    await interaction.response.send_message("🛡️ kicked")


@bot.tree.command(name="timeout")
async def timeout(interaction: discord.Interaction, member: discord.Member, minutes: int):
    await member.timeout(discord.utils.utcnow() + datetime.timedelta(minutes=minutes))
    await interaction.response.send_message("⏳ timed out")


@bot.tree.command(name="purge")
async def purge(interaction: discord.Interaction, amount: int):
    await interaction.channel.purge(limit=amount)
    await interaction.response.send_message("🧹 cleared", ephemeral=True)


# =========================
# 📊 SERVER STATS
# =========================
@tasks.loop(seconds=60)
async def stats_loop():
    for guild in bot.guilds:
        members = guild.member_count

        channel = discord.utils.get(guild.text_channels, name="📢 announcements")

        if channel:
            await channel.edit(name=f"📢 Members: {members}")


# =========================
# 🚀 RUN
# =========================
bot.run(TOKEN)
