from aiocache import cached, SimpleMemoryCache
import discord
from discord.ext import commands
import requests
from datetime import datetime

# Nastavení bota
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Prémioví uživatelé
PREMIUM_USERS = {586540043812864050}  # Změň na své ID

# Funkce pro získání dat z API (s cache)
@cached(ttl=3600, cache=SimpleMemoryCache)  # Použití paměťové cache
def get_data(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None

async def fetch_player_data(player_name, date_from, date_to):
    # Základní API volání
    timestamp = int(datetime.now().timestamp() * 1000)
    base_url = f"https://app.dartsorakel.com/api/stats/player?dateFrom={date_from}&dateTo={date_to}&rankKey=26&organStat=All&tourns=All&minMatches=200&tourCardYear=&showStatsBreakdown=0&_={timestamp}"
    url_response = get_data(base_url)
    if not url_response:
        return None

    # Vyhledání hráče
    data = url_response.get("data", [])
    for player in data:
        if player["player_name"] == player_name:
            return {
                "player_name": player["player_name"],
                "rank": player["rank"],
                "maximums": player["stat"],
            }
    return None

# Příkaz pro základní statistiky
@bot.command(name="stats")
async def stats_command(ctx, player_name: str, date_from: str, date_to: str):
    try:
        # Validace dat
        datetime.strptime(date_from, "%Y-%m-%d")
        datetime.strptime(date_to, "%Y-%m-%d")
    except ValueError as e:
        await ctx.send(f"Chyba ve formátu dat: {e}")
        return

    player_data = await fetch_player_data(player_name, date_from, date_to)
    if not player_data:
        await ctx.send(f"Data pro hráče {player_name} nebyla nalezena.")
        return

    embed = discord.Embed(
        title=f"Statistiky pro hráče {player_data['player_name']}",
        color=discord.Color.blue()
    )
    embed.add_field(name="Rank", value=player_data["rank"])
    embed.add_field(name="Maximums", value=player_data["maximums"])
    await ctx.send(embed=embed)

# Příkaz pro prémiové statistiky
@bot.command(name="premium_stats")
async def premium_stats_command(ctx, player_name: str, date_from: str, date_to: str):
    if ctx.author.id not in PREMIUM_USERS:
        await ctx.send("Tento příkaz je dostupný pouze pro prémiové uživatele.")
        return

    try:
        datetime.strptime(date_from, "%Y-%m-%d")
        datetime.strptime(date_to, "%Y-%m-%d")
    except ValueError as e:
        await ctx.send(f"Chyba ve formátu dat: {e}")
        return

    player_data = await fetch_player_data(player_name, date_from, date_to)
    if not player_data:
        await ctx.send(f"Data pro hráče {player_name} nebyla nalezena.")
        return

    embed = discord.Embed(
        title=f"Prémiové statistiky pro hráče {player_data['player_name']}",
        color=discord.Color.gold()
    )
    embed.add_field(name="Rank", value=player_data["rank"])
    embed.add_field(name="Maximums", value=player_data["maximums"])
    embed.add_field(name="Grafy", value="**Placeholder pro grafy** (bude přidáno později)")
    await ctx.send(embed=embed)

# Testovací příkaz
@bot.command(name="ping")
async def ping_command(ctx):
    await ctx.send("Pong!")

# Spuštění bota
bot.run("MTMyNjkxMDY4MjA0NTc0MzE1NA.G4W2-Y.H4jux_lnuRTpkxDJrMXUMgNcQ7nqFkY7qPGZcs")
