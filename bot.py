import discord
from discord.ext import commands
import discord.ui as ui
import json
import os
import random
import asyncio
from datetime import datetime

TOKEN = os.getenv("DISCORD_TOKEN")
OWNERS = [1429019327054610634, 1454441629950939183]  # your IDs
DATA_FILE = "data.json"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

def load_data():
    if not os.path.exists(DATA_FILE):
        default = {"guilds": {}, "users": {}, "global": {"less_winnings": False}}
        save_data(default)
        return default
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        default = {"guilds": {}, "users": {}, "global": {"less_winnings": False}}
        save_data(default)
        return default

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Save error: {e}")

def get_user_data(user_id):
    data = load_data()
    uid = str(user_id)
    if uid not in data["users"]:
        data["users"][uid] = {"balance": 1000, "stats": {"won": 0, "lost": 0, "games": 0}, "blacklisted": False}
        save_data(data)
    return data["users"][uid]

def get_prefix(bot, message):
    if not message.guild: return "g!"
    data = load_data()
    gid = str(message.guild.id)
    return data.get("guilds", {}).get(gid, {}).get("prefix", "g!")

bot = commands.Bot(command_prefix=get_prefix, intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online! 🎰 BLOX.SPIN ready")
    try:
        await bot.tree.sync()
        print("Slash commands synced")
    except Exception as e:
        print(e)

@bot.event
async def on_message(message):
    if message.author.bot: return
    await bot.process_commands(message)

# Balance & Stats
@bot.hybrid_command(name="balance")
async def balance(ctx):
    d = get_user_data(ctx.author.id)
    await ctx.send(f"💰 {ctx.author.mention} you have **{d['balance']} Robux**")

@bot.hybrid_command(name="stats")
async def stats(ctx):
    d = get_user_data(ctx.author.id)
    s = d["stats"]
    await ctx.send(f"📊 **{ctx.author.name} Stats**\nGames: {s['games']}\nWon: {s['won']}\nLost: {s['lost']}")

# Tip & Rain
@bot.hybrid_command(name="tip")
async def tip(ctx, member: discord.Member, amount: int):
    if amount < 10: return await ctx.send("Min 10 Robux")
    s = get_user_data(ctx.author.id)
    r = get_user_data(member.id)
    if s["balance"] < amount: return await ctx.send("Not enough")
    s["balance"] -= amount
    r["balance"] += amount
    save_data(load_data())
    await ctx.send(f"✅ Tipped **{amount}** to {member.mention}")

@bot.hybrid_command(name="rain")
async def rain(ctx, amount: int):
    if amount < 50: return await ctx.send("Min 50")
    u = get_user_data(ctx.author.id)
    if u["balance"] < amount: return await ctx.send("Not enough")
    members = [m for m in ctx.guild.members if not m.bot]
    share = amount // len(members)
    u["balance"] -= amount
    data = load_data()
    for m in members:
        uid = str(m.id)
        if uid not in data["users"]: data["users"][uid] = {"balance":0,"stats":{"won":0,"lost":0,"games":0},"blacklisted":False}
        data["users"][uid]["balance"] += share
    save_data(data)
    await ctx.send(f"🌧 **RAIN!** Everyone gets **{share} Robux**")

# Slots with cool VFX
@bot.hybrid_command(name="slots")
async def slots(ctx, bet: int = 100):
    if bet < 20 or bet > 5000: return await ctx.send("Bet 20-5000")
    u = get_user_data(ctx.author.id)
    if u["balance"] < bet: return await ctx.send("Not enough")
    u["balance"] -= bet
    u["stats"]["games"] += 1
    save_data(load_data())

    reels = ["🍒","🍋","🍊","🍉","🔔","💎","7️⃣"]
    weights = [30,25,20,15,6,3,1]  # more common lose/fair, rare big

    msg = await ctx.send("🎰 **SLOTS SPINNING...**")
    for _ in range(5):
        r1 = random.choices(reels, weights)[0]
        r2 = random.choices(reels, weights)[0]
        r3 = random.choices(reels, weights)[0]
        await msg.edit(content=f"🎰 **SPINNING...**\n{r1} | {r2} | {r3}")
        await asyncio.sleep(0.7)

    final = [random.choices(reels, weights)[0] for _ in range(3)]
    res = f"{final[0]} | {final[1]} | {final[2]}"

    if len(set(final)) == 1:
        mult = 12 if final[0]=="7️⃣" else 8 if final[0]=="💎" else 4 if final[0]=="🔔" else 3
    elif len(set(final)) == 2:
        mult = 1.5
    else:
        mult = 0

    win = int(bet * mult)
    data = load_data()
    uid = str(ctx.author.id)
    data["users"][uid]["balance"] += win
    if win > bet:
        data["users"][uid]["stats"]["won"] += win - bet
    else:
        data["users"][uid]["stats"]["lost"] += bet
    save_data(data)

    if win > bet:
        await msg.edit(content=f"🎉 **WIN!** {res}\nYou won **{win} Robux** (+{win-bet})")
    else:
        await msg.edit(content=f"😢 {res}\nLost **{bet} Robux**")

# Coinflip 50/50
@bot.hybrid_command(name="coinflip")
async def coinflip(ctx, bet: int, choice: str):
    choice = choice.lower()
    if choice not in ["heads", "tails"] or bet < 20: return await ctx.send("g!coinflip 100 heads")
    u = get_user_data(ctx.author.id)
    if u["balance"] < bet: return await ctx.send("Not enough")
    u["balance"] -= bet
    u["stats"]["games"] += 1
    flip = random.choice(["heads","tails"])
    if flip == choice:
        w = bet * 2
        u["balance"] += w
        u["stats"]["won"] += w - bet
        await ctx.send(f"🪙 **{flip.upper()}** — **WIN** {w} Robux!")
    else:
        u["stats"]["lost"] += bet
        await ctx.send(f"🪙 **{flip.upper()}** — Lost {bet}")
    save_data(load_data())

# Withdraw with modal
@bot.hybrid_command(name="withdraw")
async def withdraw(ctx, amount: int):
    u = get_user_data(ctx.author.id)
    if u.get("blacklisted"): return await ctx.send("You are blacklisted")
    if amount < 20 or amount > 300: return await ctx.send("20-300 Robux only")
    if u["balance"] < amount: return await ctx.send("Not enough")

    class Modal(ui.Modal, title="Withdraw Robux"):
        gp = ui.TextInput(label="Roblox Gamepass ID", required=True)

        async def on_submit(self, interaction):
            data = load_data()
            data["users"][str(interaction.user.id)]["balance"] -= amount
            save_data(data)
            await interaction.response.send_message("✅ Request sent!", ephemeral=True)
            for oid in OWNERS:
                owner = bot.get_user(oid)
                if owner:
                    try:
                        await owner.send(f"🚨 WITHDRAW\nUser: {interaction.user}\nAmount: {amount}\nGamepass: {self.gp.value}")
                    except: pass

    await ctx.interaction.response.send_modal(Modal())

# Admin commands (only owners)
@bot.hybrid_command(name="addbalance")
async def addbalance(ctx, member: discord.Member, amount: int):
    if ctx.author.id not in OWNERS: return
    data = load_data()
    uid = str(member.id)
    if uid not in data["users"]: data["users"][uid] = {"balance":0,"stats":{"won":0,"lost":0,"games":0},"blacklisted":False}
    data["users"][uid]["balance"] += amount
    save_data(data)
    await ctx.send(f"Added {amount} to {member.mention}")

@bot.hybrid_command(name="wipe")
async def wipe(ctx, member: discord.Member):
    if ctx.author.id not in OWNERS: return
    data = load_data()
    uid = str(member.id)
    if uid in data["users"]: del data["users"][uid]
    save_data(data)
    await ctx.send(f"Wiped {member.mention}")

@bot.hybrid_command(name="blacklist")
async def blacklist(ctx, member: discord.Member, action: str = "add"):
    if ctx.author.id not in OWNERS: return
    data = load_data()
    uid = str(member.id)
    if uid not in data["users"]: data["users"][uid] = {"balance":0,"stats":{"won":0,"lost":0,"games":0},"blacklisted":False}
    data["users"][uid]["blacklisted"] = (action.lower() == "add")
    save_data(data)
    await ctx.send(f"Blacklist updated for {member.mention}")

@bot.hybrid_command(name="setprefix")
async def setprefix(ctx, new_prefix: str):
    if not ctx.author.guild_permissions.administrator and ctx.author.id not in OWNERS: return
    data = load_data()
    gid = str(ctx.guild.id)
    if "guilds" not in data: data["guilds"] = {}
    data["guilds"][gid] = {"prefix": new_prefix}
    save_data(data)
    await ctx.send(f"Prefix changed to `{new_prefix}`")

bot.run(TOKEN)
