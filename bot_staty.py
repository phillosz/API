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
@cached(ttl=3600, cache=SimpleMemoryCache)
async def get_data(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None

async def fetch_player_data(player_name, date_from, date_to):
    timestamp = int(datetime.now().timestamp() * 1000)
    
    base_url = f"https://app.dartsorakel.com/api/stats/player?dateFrom={date_from}&dateTo={date_to}&rankKey=26&organStat=All&tourns=All&minMatches=200&tourCardYear=&showStatsBreakdown=0&_={timestamp}"
    url_response = await get_data(base_url)
    if not url_response:
        return None

    data = url_response.get("data", [])
    player_data = {}

    for player in data:
        player_data[player['player_name']] = {
            'player_name': player['player_name'],
            'player_key': player['player_key'],
            'rank': player['rank'],
            'maximums': player['stat']
        }

    if player_name not in player_data:
        return None

    player_key = player_data[player_name]["player_key"]

    # Další statistiky
    stats_urls = {
        "average": f"https://app.dartsorakel.com/api/stats/player?rankKey=25&showStatsBreakdown=0&playerKeyToHighlight={player_key}&minMatches=200&limit=32&_={timestamp}",
        "average_actual": f"https://app.dartsorakel.com/api/stats/player?dateFrom={date_from}&dateTo={date_to}&rankKey=25&organStat=All&tourns=All&minMatches=200&tourCardYear=&showStatsBreakdown=0&_={timestamp}",
        "checkout_pcnt": f"https://app.dartsorakel.com/api/stats/player?rankKey=1053&showStatsBreakdown=0&playerKeyToHighlight={player_key}&minMatches=200&limit=32&_={timestamp}",
        "checkout_pcnt_actual": f"https://app.dartsorakel.com/api/stats/player?dateFrom={date_from}&dateTo={date_to}&rankKey=1053&organStat=All&tourns=All&minMatches=200&tourCardYear=&showStatsBreakdown=0&_={timestamp}",
        "maximum_per_leg": f"https://app.dartsorakel.com/api/stats/player?rankKey=1055&showStatsBreakdown=0&playerKeyToHighlight={player_key}&minMatches=200&limit=32&_={timestamp}",
        "maximum_per_leg_actual": f"https://app.dartsorakel.com/api/stats/player?dateFrom={date_from}&dateTo={date_to}&rankKey=1055&organStat=All&tourns=All&minMatches=200&tourCardYear=&showStatsBreakdown=0&_={timestamp}"
    }

    for stat_name, url in stats_urls.items():
        stat_data = await get_data(url)
        if stat_data:
            for player in stat_data.get("data", []):
                if player['player_name'] == player_name:
                    player_data[player_name][stat_name] = player["stat"]

    return player_data[player_name]

# Příkaz pro základní statistiky
@bot.command(name="stats")
async def stats_command(ctx, player_name: str, date_from: str, date_to: str):
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
        title=f"Statistiky pro hráče {player_data['player_name']}",
        color=discord.Color.blue()
    )
    embed.add_field(name="Rank", value=player_data.get("rank", "N/A"))
    embed.add_field(name="Maximums", value=player_data.get("maximums", "N/A"))
    embed.add_field(name="Average", value=player_data.get("average", "N/A"))
    embed.add_field(name="Current Average", value=player_data.get("average_actual", "N/A"))
    embed.add_field(name="Checkout %", value=player_data.get("checkout_pcnt", "N/A"))
    embed.add_field(name="Current Checkout %", value=player_data.get("checkout_pcnt_actual", "N/A"))
    embed.add_field(name="Maximums per Leg", value=player_data.get("maximum_per_leg", "N/A"))
    embed.add_field(name="Current Maximums per Leg", value=player_data.get("maximum_per_leg_actual", "N/A"))

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
    embed.add_field(name="Rank", value=player_data.get("rank", "N/A"))
    embed.add_field(name="Maximums", value=player_data.get("maximums", "N/A"))
    embed.add_field(name="Average", value=player_data.get("average", "N/A"))
    embed.add_field(name="Current Average", value=player_data.get("average_actual", "N/A"))
    embed.add_field(name="Checkout %", value=player_data.get("checkout_pcnt", "N/A"))
    embed.add_field(name="Current Checkout %", value=player_data.get("checkout_pcnt_actual", "N/A"))
    embed.add_field(name="Maximums per Leg", value=player_data.get("maximum_per_leg", "N/A"))
    embed.add_field(name="Current Maximums per Leg", value=player_data.get("maximum_per_leg_actual", "N/A"))
    embed.add_field(name="Grafy", value="**Placeholder pro grafy** (bude přidáno později)")

    await ctx.send(embed=embed)

# Testovací příkaz
@bot.command(name="ping")
async def ping_command(ctx):
    await ctx.send("Pong!")

# Spuštění bota
bot.run("Y.H4jux_lnuRTpkxDJrMXUMgNcQ7nqFkY7qPGZcs")
