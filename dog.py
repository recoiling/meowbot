
import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime, timezone
import aiohttp
import pytz
import time
import asyncio
from dotenv import load_dotenv
from colorama import init, Fore
from discord.ui import View, Button
from discord import ButtonStyle
import random
from collections import defaultdict, deque
from typing import Deque, Dict, Optional, Tuple

init(autoreset=True)
load_dotenv()

TOKEN = os.getenv("TOKEN")
EMBED_COLOR = os.getenv("COLOR")
OWNER_ID = os.getenv("OWNER")
PREFIX = os.getenv("PREFIX")

MEOW_STATS_FILE = "data/meow_stats.json"
MEOWS_FILE = 'data/meows.json'


init(autoreset=True)
load_dotenv()




intents = discord.Intents.default()
intents.members = True
intents.message_content = True
gmt2 = pytz.timezone("Etc/GMT-2")
timestamp = datetime.now(gmt2)
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)




JSON_FILE = 'data/meows.json'
with open(JSON_FILE, 'r') as f:
    meow_list = json.load(f)


def load_json(file_name):
    if os.path.exists(file_name):
        try:
            with open(file_name, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except json.JSONDecodeError:
            pass
    return {}


def save_json(file_name, data):
    with open(file_name, "w") as f:
        json.dump(data, f, indent=4)




def load_meow_stats():
    if os.path.exists(MEOW_STATS_FILE):
        try:
            with open(MEOW_STATS_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    return {}


meow_stats = load_meow_stats()

def save_meow_stats(stats):
    with open(MEOW_STATS_FILE, "w") as f:
        json.dump(stats, f, indent=4)




@bot.event
async def on_ready():
    await bot.wait_until_ready()
    for cmd in bot.tree.get_commands():
        cmd.dm_permission = True
    await bot.tree.sync()



@bot.command(help="refresh server metadata for the panel")
async def refreshpanel(ctx):
    if not ctx.guild:
        return await ctx.send("this command must be used in a server.")
    update_server_metadata(ctx.guild)
    await ctx.send(f"👍")


@bot.tree.command(name="refreshpanel", description="refresh server metadata for the panel")
async def refreshpanel_slash(interaction: discord.Interaction):
    if not interaction.guild:
        return await interaction.response.send_message("this command must be used in a server.", ephemeral=True)
    update_server_metadata(interaction.guild)
    await interaction.response.send_message(f"👍")


def has_permissions(**perms):
    
    return commands.has_permissions(**perms)



@bot.tree.command(name="serverinfo", description="show server information")
async def serverinfo_slash(interaction: discord.Interaction):
    if not interaction.guild:
        return await interaction.response.send_message("this command must be used in a server.", ephemeral=True)
    server = interaction.guild
    embed = discord.Embed(title=server.name.lower(), color=EMBED_COLOR, timestamp=timestamp)
    channels_count = len([c for c in server.channels if isinstance(c, (discord.TextChannel, discord.VoiceChannel))])
    info = {
        'owner': server.owner,
        'created': server.created_at.strftime('%Y-%m-%d'),
        'members': server.member_count,
        'channels': channels_count,
        'roles': len(server.roles),
        'boost level': server.premium_tier,
        'verification': server.verification_level,
    }
    for name, value in info.items():
        embed.add_field(name=name, value=str(value).lower(), inline=True)
    await interaction.response.send_message(embed=embed)




@bot.command(help="read the bot's latency")
async def ping(ctx):
    start = time.time()
    ping_msg = await ctx.send('pong')
    end = time.time()
    message_latency = round((end - start) * 1000)
    ws_latency = round(bot.latency * 1000)
    embed = discord.Embed(
        colour=EMBED_COLOR,
        description=f'client ping:\n```{ws_latency}ms```\nmessage latency:\n```{message_latency}ms```'
    )
    await ping_msg.edit(content='', embed=embed)


@bot.command(name="meowlb")
async def meowleaderboard(ctx):
    if not meow_stats:
        return await ctx.send("no meows yet :/")

    
    sorted_stats = sorted(meow_stats.items(), key=lambda x: x[1], reverse=True)

    embed = discord.Embed(
        title="meow leaderboard :3",
        color=EMBED_COLOR
    )

    place = 1
    for user_id, count in sorted_stats[:10]:
        user = ctx.guild.get_member(int(user_id))
        username = user.name if user else f"unknown user ({user_id})"
        embed.add_field(name=f"#{place} — {username}", value=f"{count} meows", inline=False)
        place += 1

    await ctx.send(embed=embed)

@bot.command(name="meow")
async def meow(ctx):
    global meow_stats
    
    # usage for nichihjou cuz ig
    user_id = str(ctx.author.id)
    meow_stats[user_id] = meow_stats.get(user_id, 0) + 1
    save_meow_stats(meow_stats)

    if not meow_list:
        await ctx.send("there's no more meows")
        return

    selected_meow = random.choice(meow_list)
    await ctx.send(selected_meow)





@bot.command(name="help", help="show commands")
async def help_prefix(ctx):
    categories = {
        "fun": [], "moderation": [], "utilities": [], "misc": []
    }

    for cmd in bot.commands:
        if cmd.hidden:
            continue
        help_text = cmd.help.lower() if cmd.help else ""
        if any(word in help_text for word in ["fun", "game", "love", "flip", "dice", "8-ball", "fact", "slots"]):
            categories["fun"].append(cmd)
        elif any(word in help_text for word in ["mod", "kick", "ban", "mute", "history", "purge", "slowmode", "lock", "unlock"]):
            categories["moderation"].append(cmd)
        elif any(word in help_text for word in ["utility", "define", "ud", "shorten", "avatar", "userinfo", "ping", "uptime"]):
            categories["utilities"].append(cmd)
        else:
            categories["misc"].append(cmd)

    view = View()
    for cat_name in categories.keys():
        button = Button(label=cat_name, style=ButtonStyle.primary)
        async def button_callback(interaction: discord.Interaction, category=cat_name):
            cmds = categories[category]
            desc = "\n".join(f"**.{c.name}** - {c.help.lower() if c.help else 'no description'}" for c in cmds) if cmds else "nothing here yet."
            embed = discord.Embed(title=f"{category} commands", description=desc, color=EMBED_COLOR)
            embed.set_footer(text="made with ❤")
            await interaction.response.edit_message(embed=embed, view=view)
        button.callback = button_callback
        view.add_item(button)
    
    # Send the initial message with an embed
    initial_embed = discord.Embed(
        title="help menu",
        description="please select a category below.",
        color=EMBED_COLOR
    )
    await ctx.send(embed=initial_embed, view=view)




@bot.command(name="meowstats")
async def meowstats(ctx):
    user_id = str(ctx.author.id)
    count = meow_stats.get(user_id, 0)

    embed = discord.Embed(
        color=EMBED_COLOR,
        description=f"you have **{count}** meows, keep it up!"
    )
    await ctx.send(embed=embed)

@bot.command(name="addmeow")
async def addsen(ctx, *, new_sentence: str):
    if ctx.author.id != OWNER_ID:
        
        await ctx.send(embed=discord.Embed(description="what are you doing.", color=EMBED_COLOR))
        return
    meow_list.append(new_sentence)
    with open(MEOWS_FILE, 'w') as f:
        json.dump(meow_list, f, indent=4)
    await ctx.send(f"👍")




@bot.command(name="slots", aliases=["slot"], help="play a slot machine 🎰")
async def slots(ctx):
    symbols = ["🍒", "🍋", "🍇", "🍉", "💎", "⭐"]
    result = [random.choice(symbols) for _ in range(3)]
    message = " ".join(result)

    if len(set(result)) == 1:
        outcome = "🎉 JACKPOT"
    elif len(set(result)) == 2:
        outcome = "😎 almost."
    else:
        outcome = "💀 try again."

    embed = discord.Embed(title="Las Vegas Simulator", description=f"{message}\n\n{outcome}", color=0xfbF12b)
    await ctx.send(embed=embed)


@bot.command(name="slowmode", help="set slowmode for the channel in seconds")
@has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int):
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f"slowmode set to `{seconds}` seconds in {ctx.channel.mention}")


@bot.command(name="temprole", help="give a role temporarily")
@has_permissions(manage_roles=True)
async def temprole(ctx, member: discord.Member, role: discord.Role, duration: int):
    await member.add_roles(role)
    await ctx.send(f" {member.mention} has now {role.mention} for {duration} seconds.")
    await asyncio.sleep(duration)
    await member.remove_roles(role)
    await ctx.send(f" {role.mention} has now been removed from {member.mention} after {duration} seconds.")



@bot.command(name="servericon", aliases=["si"], help="shows the server icon")
async def servericon(ctx):
    guild = ctx.guild
    if not guild.icon:
        return await ctx.send("this server has no icon")
    embed = discord.Embed(title=f"{guild.name}'s icon, color=0xfbF12b")
    embed.set_Image(url=guild.icon.url)
    await ctx.send(embed=embed)

@bot.command(name="lock", help="lock a channel")
@commands.has_permissions(manage_channels=True)
async def lock(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send(f"🔒")

@bot.command(name="unlock", help="unlock a channel")
@commands.has_permissions(manage_channels=True)
async def unlock(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send(f"🔓")

@bot.command(name="reverse", aliases=["rev"], help="reverses your text")
async def reverse(ctx, *, text: str):
    await ctx.send(text[::-1])




@bot.command(name="ship", aliases=["love"], help="shows love percentage from two people")
async def ship(ctx, user1: discord.Member, user2: discord.Member):
    love = random.randint(0, 100)
    hearts = "" * (love // 20)
    embed = discord.Embed(
        title="compatibility test",
        description=f"{user1.mention} ❤️ {user2.mention}\nlove Score: **{love}%**\n{hearts or '💔'}",
        color=0xfbF12b
    )
    await ctx.send(embed=embed)




@bot.command(name="fact", aliases=["rf"], help="get a random fact")
async def fact(ctx):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://uselessfacts.jsph.pl/random.json?language=en") as r:
            data = await r.json()
            fact = data["text"]
            await ctx.send(embed=discord.Embed(title="random fact", description=fact, color=0xfbF12b))




@bot.command(name="serverage", aliases=["sage"], help="shows how old the server is")
async def serverage(ctx):
    guild = ctx.guild
    age = datetime.now(timezone.utc) - guild.created_at
    await ctx.send(f"{guild.name} was created {age.days} days ago")


@bot.command(name="define", aliases=["def"], help="define a word. usage: .define hello")
async def define(ctx, *, word: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}") as r:
            if r.status != 200:
                return await ctx.send("word not found.")
            data = await r.json()
            meaning = data[0]["meanings"][0]["definitions"][0]["definition"]
            await ctx.send(embed=discord.Embed(title=f" {word}", description=meaning, color=0xfbF12b))










@bot.command(name="urban", aliases=["ud"], help="urban dictionary usage: .urban word")
async def urban(ctx, *, term: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.urbandictionary.com/v0/define?term={term}") as r:
            if r.status != 200:
                return await ctx.send("couldnt connect to urban dictionary.")
            
            data = await r.json()

            if not data["list"]:
                return await ctx.send(f"no results found for **{term}**.")

            entry = data["list"][0]
            definition = entry["definition"].replace("[", "").replace("]", "")
            example = entry.get("example", "").replace("[", "").replace("]", "")
            thumbs_up = entry.get("thumbs_up", 0)
            thumbs_down = entry.get("thumbs_down", 0)
            permalink = entry.get("permalink", "")

            embed = discord.Embed(
                title=f" Urban Dictionary - {term}",
                description=definition[:1000],  # truncate if too long
                color=0xfbF12b,
                url=permalink
            )
            if example:
                embed.add_field(name="💬 Example", value=example[:500], inline=False)
            embed.set_footer(text=f"👍 {thumbs_up} | 👎 {thumbs_down}")

            await ctx.send(embed=embed)

@bot.command(name="userinfo", aliases=["ui"], help="displays info about a user")
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"user information for {member}", color=EMBED_COLOR, timestamp=datetime.now())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Joined", value=member.joined_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Created", value=member.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Bot", value=member.bot, inline=True)
    await ctx.send(embed=embed)

@bot.command(name="uptime", help="shows the status of the bot")
async def uptime(ctx):
    seconds = int(time.time() - start_time)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    await ctx.send(f" 👍 uptime: {hours}h {minutes}m and {seconds}s")

@bot.command(name="servers", aliases=["guilds"], help="shows all servers the bot is currently in")
async def servers(ctx):
    if ctx.author.id != OWNER_ID:
        return await ctx.send(embed=discord.Embed(description="you can't use this command.", color=EMBED_COLOR))
    guilds = [g.name for g in bot.guilds]
    await ctx.send(embed=discord.Embed(title="server list", description="\n".join(guilds), color=EMBED_COLOR))

@bot.command(name="cat", aliases=["kitty"], help="shows a random cat")
async def cat(ctx):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.thecatapi.com/v1/images/search") as r:
            data = await r.json()
            await ctx.send(data[0]['url'])

@bot.command(name="clearbot", aliases=["cb"], help="clears bot messages in the channel")
@has_permissions(manage_messages=True)
async def clearbot(ctx, limit: int = 50):
    await ctx.channel.purge(limit=limit, check=lambda m: m.author == bot.user)
    await ctx.send("👍", delete_after=3)

@bot.command(name="say", help="make the bot say something")
async def say(ctx, *, message: str):
    await ctx.message.delete()
    await ctx.send(message)



@bot.command(help="purge messages. usage: .purge amount @user")
@has_permissions(manage_messages=True)
async def purge(ctx, amount: int, member: discord.Member = None):
    check = (lambda msg: msg.author == member) if member else (lambda msg: True)
    deleted = await ctx.channel.purge(limit=amount + 1, check=check)
    deleted_count = len(deleted) - 1
    description = f"purged {deleted_count} messages from {member.mention}" if member else f"purged {deleted_count} messages"
    await ctx.send(
        embed=discord.Embed(
            title="messages purged",
            description=description,
            color=EMBED_COLOR
        ),
        delete_after=3
    )



@bot.command(name="time", aliases=["tz", "timezone"], help="shows your current timezone")
async def time(ctx, *, location: str = None):
    try:
        if not location:
            tz = gmt2
            loc_display = "GMT-2"\
        
        
        else:
            location = location.replace(" ", "_").title()
            matched_tz = None



            if location in pytz.all_timezones:
                matched_tz = location
            else:
                for tzname in pytz.all_timezones:
                    matched_tz = location
                else:

                    for tzname in pytz.all_timezones:
                        if location.lower() in tzname.lower():
                            matched_tz = tzname
                            break

            if not matched_tz:
                return await ctx.send("couldn't find your timezone.")

            tz = pytz.timezone(matched_tz)
            loc_display = matched_tz.replace("_", " ")


            now = datetime.now(tz)
            embed = discord.Embed(
            title="current time",
            description=f"**{loc_display}**\n`{now.strftime('%Y-%m-%d %H:%M:%S %Z')}`",
            color=0xfbF12b
        )
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(embed=discord.Embed(
            description="try `.time Berlin`",
            color=0xfbF12b
        ))  
        





bot.run(TOKEN)