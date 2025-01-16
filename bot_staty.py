import discord
from discord.ext import commands
import requests
from datetime import datetime
from aiocache import Cache
from aiocache.decorators import cached

# Nastavení bota
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Cache nastavení
cache = Cache(Cache.MEMORY)

# Prémioví uživatelé
PREMIUM_USERS = ["586540043812864050"]

# Funkce pro získání dat z API
@cached(ttl=3600, cache=cache)
def get_data(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return None

async def fetch_player_data(player_name, date_from, date_to):
    timestamp = int(datetime.now().timestamp() * 1000)

    base_url = f"https://app.dartsorakel.com/api/stats/player?dateFrom={date_from}&dateTo={date_to}&rankKey=26&organStat=All&tourns=All&minMatches=200&tourCardYear=&showStatsBreakdown=0&_={timestamp}"
    url_response = get_data(base_url)
    if not url_response:
        return None

    data = url_response["data"]
    player_data = {}
    for player in data:
        if player['player_name'] == player_name:
            player_data = {
                'player_name': player['player_name'],
                'rank': player['rank'],
                'maximums': player['stat']
            }
            break

    if not player_data:
        return None

    return player_data

# Příkaz pro běžné statistiky
@bot.command(name="stats")
async def stats_command(ctx, player_name: str, date_from: str, date_to: str):
    try:
        datetime.strptime(date_from.strip(), "%Y-%m-%d")
        datetime.strptime(date_to.strip(), "%Y-%m-%d")
    except ValueError:
        await ctx.send("Chyba ve formátu data. Použijte YYYY-MM-DD.")
        return

    player_data = await fetch_player_data(player_name, date_from, date_to)
    if not player_data:
        await ctx.send("Hráč nebyl nalezen nebo došlo k chybě při načítání dat.")
        return

    embed = discord.Embed(title=f"Statistiky hráče {player_data['player_name']}", color=0x3498db)
    embed.add_field(name="Rank", value=player_data['rank'], inline=False)
    embed.add_field(name="Počet 180", value=player_data['maximums'], inline=False)

    await ctx.send(embed=embed)

# Příkaz pro prémiové statistiky
@bot.command(name="premium_stats")
async def premium_stats_command(ctx, player_name: str, date_from: str, date_to: str):
    if str(ctx.author.id) not in PREMIUM_USERS:
        await ctx.send("Tento příkaz je dostupný pouze pro prémiové uživatele.")
        return

    try:
        datetime.strptime(date_from.strip(), "%Y-%m-%d")
        datetime.strptime(date_to.strip(), "%Y-%m-%d")
    except ValueError:
        await ctx.send("Chyba ve formátu data. Použijte YYYY-MM-DD.")
        return

    player_data = await fetch_player_data(player_name, date_from, date_to)
    if not player_data:
        await ctx.send("Hráč nebyl nalezen nebo došlo k chybě při načítání dat.")
        return

    embed = discord.Embed(title=f"Prémiové statistiky hráče {player_data['player_name']}", color=0xf1c40f)
    embed.add_field(name="Rank", value=player_data['rank'], inline=False)
    embed.add_field(name="Počet 180", value=player_data['maximums'], inline=False)

    # Placeholder pro graf
    embed.add_field(name="Graf", value="(Graf bude přidán brzy)", inline=False)

    await ctx.send(embed=embed)

# Testovací příkaz
@bot.command(name="ping")
async def ping(ctx):
    await ctx.send("Pong!")

# Spuštění bota
bot.run("MTMyNjkxMDY4MjA0NTc0MzE1NA.G4W2-Y.H4jux_lnuRTpkxDJrMXUMgNcQ7nqFkY7qPGZcs")
