from aiocache import cached, SimpleMemoryCache
import discord
from discord.ext import commands
import requests
from datetime import datetime, timedelta

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

def create_embed(player_name, data, color, description):
    embed = discord.Embed(
        title=f"Statistiky pro hráče {player_name}",
        description=description,
        color=color  # Barva embedu
    )

    # Přidáme dvojice statistik
    if "rank" in data:
        embed.add_field(name="🏆 Rank", value=data["rank"], inline=True)
    if "average" in data and "average_actual" in data:
        embed.add_field(name="🎯 Average", value=f"{data['average']} (Current: {data['average_actual']})", inline=False)
    if "checkout_pcnt" in data and "checkout_pcnt_actual" in data:
        embed.add_field(name="✅ Checkout %", value=f"{data['checkout_pcnt']} (Current: {data['checkout_pcnt_actual']})", inline=False)
    if "maximum_per_leg" in data and "maximum_per_leg_actual" in data:
        embed.add_field(name="💥 Max per Leg", value=f"{data['maximum_per_leg']} (Current: {data['maximum_per_leg_actual']})", inline=False)
    if "maximums" in data:
        embed.add_field(name="🎲 Maximums celkem", value=data["maximums"], inline=True)

    embed.set_footer(text="Statistiky poskytované vaším botem!")
    embed.set_thumbnail(url="https://www.dropbox.com/scl/fi/9w2gbtba94m24p5rngzzl/Professional_Darts_Corporation_logo.svg.png?rlkey=4bmsph6uakm94ogqfgzwgtk02&st=18fecn4r&raw=1")  # Add a relevant thumbnail URL

    return embed

# Příkaz pro základní statistiky
@bot.command(name="stats")
async def stats_command(ctx, player_name: str, date_from: str = None, date_to: str = None):
    if date_from is None:
        date_from = (datetime.now() - timedelta(days=80)).strftime("%Y-%m-%d")
    if date_to is None:
        date_to = datetime.now().strftime("%Y-%m-%d")

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

    embed = create_embed(player_name, player_data, discord.Color.blue(), "Základní zobrazení statistik")
    await ctx.send(embed=embed)

def create_premium_embed(player_name, data):
    return create_embed(player_name, data, discord.Color.gold(), "Prémiové zobrazení statistik")

# Příkaz pro prémiové statistiky
@bot.command(name="premiumstats")
async def premium_stats_command(ctx, player_name: str, date_from: str = None, date_to: str = None):
    if date_from is None:
        date_from = (datetime.now() - timedelta(days=80)).strftime("%Y-%m-%d")
    if date_to is None:
        date_to = datetime.now().strftime("%Y-%m-%d")

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

    embed = create_premium_embed(player_name, player_data)
    await ctx.send(embed=embed)

# Testovací příkaz
@bot.command(name="ping")
async def ping_command(ctx):
    await ctx.send("Pong!")

# Spuštění bota
bot.run("MTMyNjkxMDY4MjA0NTc0MzE1NA.G4W2-Y.H4jux_lnuRTpkxDJrMXUMgNcQ7nqFkY7qPGZcs")
