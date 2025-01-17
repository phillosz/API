import discord
from discord.ext import commands
from datetime import datetime, timedelta
import io
from aiocache import cached, SimpleMemoryCache
import aiohttp  # Add this import for asynchronous HTTP requests
import json  # Add this import for JSON handling
from cachetools import cached, TTLCache

# Nastavení bota
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Prémioví uživatelé
PREMIUM_USERS = {586540043812864050}  # Změň na své ID

# Funkce pro získání dat z API (s cache)
@cached(cache=TTLCache(maxsize=100, ttl=3600))
async def get_data(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
    return None

async def fetch_additional_stats(player_key):
    url = f"https://app.dartsorakel.com/api/tools/performancePortalPlayerData?playerId={player_key}"
    data = await get_data(url)
    if not data:
        return None

    additional_stats = {}
    for stat in data:
        stat_name = stat[0]
        stat_values = stat[1:]
        additional_stats[stat_name] = stat_values

    return additional_stats

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

    # Fetch additional statistics
    additional_stats = await fetch_additional_stats(player_key)
    if additional_stats:
        player_data[player_name]['additional_stats'] = additional_stats

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

def fill_missing_stats(data):
    if "additional_stats" not in data:
        return

    additional_stats = data["additional_stats"]

    def calculate_average(values):
        return sum(float(v.strip('%')) if isinstance(v, str) and v.endswith('%') else float(v) for v in values) / len(values)

    if "average" not in data and "Averages" in additional_stats:
        data["average"] = calculate_average(additional_stats["Averages"])
    if "average_actual" not in data and "Averages" in additional_stats:
        data["average_actual"] = additional_stats["Averages"][-1]
    if "checkout_pcnt" not in data and "Checkout Pcnt" in additional_stats:
        data["checkout_pcnt"] = f"{calculate_average(additional_stats['Checkout Pcnt']):.2f}%"
    if "checkout_pcnt_actual" not in data and "Checkout Pcnt" in additional_stats:
        data["checkout_pcnt_actual"] = additional_stats["Checkout Pcnt"][-1]
    if "maximum_per_leg" not in data and "180's per leg" in additional_stats:
        data["maximum_per_leg"] = calculate_average(additional_stats["180's per leg"])
    if "maximum_per_leg_actual" not in data and "180's per leg" in additional_stats:
        data["maximum_per_leg_actual"] = additional_stats["180's per leg"][-1]

def create_embed(player_name, data, color, description):
    fill_missing_stats(data)

    embed = discord.Embed(
        title=f"Statistiky pro hráče {player_name}",
        description=description,
        color=color  # Barva embedu
    )

    # Přidáme dvojice statistik
    if "rank" in data:
        embed.add_field(name="🏆 Rank", value=data["rank"], inline=True)
    if "average" in data or "average_actual" in data:
        average = data.get('average', 'N/A')
        average_actual = data.get('average_actual', 'N/A')
        embed.add_field(name="🎯 Average", value=f"{average} (Current: {average_actual})", inline=False)
    if "checkout_pcnt" in data or "checkout_pcnt_actual" in data:
        checkout_pcnt = data.get('checkout_pcnt', 'N/A')
        checkout_pcnt_actual = data.get('checkout_pcnt_actual', 'N/A')
        embed.add_field(name="✅ Checkout %", value=f"{checkout_pcnt} (Current: {checkout_pcnt_actual})", inline=False)
    if "maximum_per_leg" in data or "maximum_per_leg_actual" in data:
        maximum_per_leg = data.get('maximum_per_leg', 'N/A')
        maximum_per_leg_actual = data.get('maximum_per_leg_actual', 'N/A')
        embed.add_field(name="💥 Max per Leg", value=f"{maximum_per_leg} (Current: {maximum_per_leg_actual})", inline=False)
    if "maximums" in data:
        embed.add_field(name="🎲 Maximums celkem", value=data["maximums"], inline=True)

    embed.set_footer(text="Pro další informace použijte !help, nebo kontaktujte vývojáře.")
    embed.set_thumbnail(url="https://www.dropbox.com/scl/fi/9w2gbtba94m24p5rngzzl/Professional_Darts_Corporation_logo.svg.png?rlkey=4bmsph6uakm94ogqfgzwgtk02&st=18fecn4r&raw=1")  # Add a relevant thumbnail URL

    return embed

def create_premium_embed(player_name, data):
    fill_missing_stats(data)

    embed = discord.Embed(
        title=f"Prémiové statistiky pro hráče {player_name}",
        description="Prémiové zobrazení statistik",
        color=discord.Color.gold()  # Barva embedu
    )

    # Přidáme dvojice statistik
    if "rank" in data:
        embed.add_field(name="🏆 Rank", value=data["rank"], inline=True)
    if "average" in data or "average_actual" in data:
        average = data.get('average', 'N/A')
        average_actual = data.get('average_actual', 'N/A')
        embed.add_field(name="🎯 Average", value=f"{average} (Current: {average_actual})", inline=False)
    if "checkout_pcnt" in data or "checkout_pcnt_actual" in data:
        checkout_pcnt = data.get('checkout_pcnt', 'N/A')
        checkout_pcnt_actual = data.get('checkout_pcnt_actual', 'N/A')
        embed.add_field(name="✅ Checkout %", value=f"{checkout_pcnt} (Current: {checkout_pcnt_actual})", inline=False)
    if "maximum_per_leg" in data or "maximum_per_leg_actual" in data:
        maximum_per_leg = data.get('maximum_per_leg', 'N/A')
        maximum_per_leg_actual = data.get('maximum_per_leg_actual', 'N/A')
        embed.add_field(name="💥 Max per Leg", value=f"{maximum_per_leg} (Current: {maximum_per_leg_actual})", inline=False)
    if "maximums" in data:
        embed.add_field(name="🎲 Maximums celkem", value=data["maximums"], inline=True)

    # Add additional stats if available
    if "additional_stats" in data:
        additional_stats = data["additional_stats"]
        for stat_name, stat_values in additional_stats.items():
            # Convert None values to empty strings
            stat_values = [str(value) if value is not None else '' for value in stat_values]
            embed.add_field(name=stat_name, value=", ".join(stat_values), inline=False)

    embed.set_footer(text="Pro další informace použijte !help, nebo kontaktujte vývojáře.")
    embed.set_thumbnail(url="https://www.dropbox.com/scl/fi/9w2gbtba94m24p5rngzzl/Professional_Darts_Corporation_logo.svg.png?rlkey=4bmsph6uakm94ogqfgzwgtk02&st=18fecn4r&raw=1")  # Add a relevant thumbnail URL

    return embed

def create_comparison_embed(player1_name, player1_data, player2_name, player2_data):
    fill_missing_stats(player1_data)
    fill_missing_stats(player2_data)

    embed = discord.Embed(title="Porovnání hráčů", color=discord.Color.purple())
    
    embed.add_field(name=f"{player1_name} 🆚 {player2_name}", value="\u200b", inline=False)
    
    if "rank" in player1_data and "rank" in player2_data:
        embed.add_field(name="🏆 Rank", value=f"{player1_data['rank']} 🆚 {player2_data['rank']}", inline=True)
    if ("average" in player1_data or "average_actual" in player1_data) and ("average" in player2_data or "average_actual" in player2_data):
        average1 = player1_data.get('average', 'N/A')
        average_actual1 = player1_data.get('average_actual', 'N/A')
        average2 = player2_data.get('average', 'N/A')
        average_actual2 = player2_data.get('average_actual', 'N/A')
        embed.add_field(name="🎯 Average", value=f"{average1} (Current: {average_actual1}) 🆚 {average2} (Current: {average_actual2})", inline=False)
    if ("checkout_pcnt" in player1_data or "checkout_pcnt_actual" in player1_data) and ("checkout_pcnt" in player2_data or "checkout_pcnt_actual" in player2_data):
        checkout_pcnt1 = player1_data.get('checkout_pcnt', 'N/A')
        checkout_pcnt_actual1 = player1_data.get('checkout_pcnt_actual', 'N/A')
        checkout_pcnt2 = player2_data.get('checkout_pcnt', 'N/A')
        checkout_pcnt_actual2 = player2_data.get('checkout_pcnt_actual', 'N/A')
        embed.add_field(name="✅ Checkout %", value=f"{checkout_pcnt1} (Current: {checkout_pcnt_actual1}) 🆚 {checkout_pcnt2} (Current: {checkout_pcnt_actual2})", inline=False)
    if ("maximum_per_leg" in player1_data or "maximum_per_leg_actual" in player1_data) and ("maximum_per_leg" in player2_data or "maximum_per_leg_actual" in player2_data):
        maximum_per_leg1 = player1_data.get('maximum_per_leg', 'N/A')
        maximum_per_leg_actual1 = player1_data.get('maximum_per_leg_actual', 'N/A')
        maximum_per_leg2 = player2_data.get('maximum_per_leg', 'N/A')
        maximum_per_leg_actual2 = player2_data.get('maximum_per_leg_actual', 'N/A')
        embed.add_field(name="💥 Max per Leg", value=f"{maximum_per_leg1} (Current: {maximum_per_leg_actual1}) 🆚 {maximum_per_leg2} (Current: {maximum_per_leg_actual2})", inline=False)
    if "maximums" in player1_data and "maximums" in player2_data:
        embed.add_field(name="🎲 Maximums celkem", value=f"{player1_data['maximums']} 🆚 {player2_data['maximums']}", inline=True)

    embed.set_footer(text="Statistiky poskytované vaším botem!")
    embed.set_thumbnail(url="https://www.dropbox.com/scl/fi/9w2gbtba94m24p5rngzzl/Professional_Darts_Corporation_logo.svg.png?rlkey=4bmsph6uakm94ogqfgzwgtk02&st=18fecn4r&raw=1")

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
    fill_missing_stats(data)

    embed = discord.Embed(
        title=f"Prémiové statistiky pro hráče {player_name}",
        description="Prémiové zobrazení statistik",
        color=discord.Color.gold()  # Barva embedu
    )

    # Přidáme dvojice statistik
    if "rank" in data:
        embed.add_field(name="🏆 Rank", value=data["rank"], inline=True)
    if "average" in data or "average_actual" in data:
        average = data.get('average', 'N/A')
        average_actual = data.get('average_actual', 'N/A')
        embed.add_field(name="🎯 Average", value=f"{average} (Current: {average_actual})", inline=False)
    if "checkout_pcnt" in data or "checkout_pcnt_actual" in data:
        checkout_pcnt = data.get('checkout_pcnt', 'N/A')
        checkout_pcnt_actual = data.get('checkout_pcnt_actual', 'N/A')
        embed.add_field(name="✅ Checkout %", value=f"{checkout_pcnt} (Current: {checkout_pcnt_actual})", inline=False)
    if "maximum_per_leg" in data or "maximum_per_leg_actual" in data:
        maximum_per_leg = data.get('maximum_per_leg', 'N/A')
        maximum_per_leg_actual = data.get('maximum_per_leg_actual', 'N/A')
        embed.add_field(name="💥 Max per Leg", value=f"{maximum_per_leg} (Current: {maximum_per_leg_actual})", inline=False)
    if "maximums" in data:
        embed.add_field(name="🎲 Maximums celkem", value=data["maximums"], inline=True)

    # Add additional stats if available
    if "additional_stats" in data:
        additional_stats = data["additional_stats"]
        for stat_name, stat_values in additional_stats.items():
            # Convert None values to empty strings
            stat_values = [str(value) if value is not None else '' for value in stat_values]
            embed.add_field(name=stat_name, value=", ".join(stat_values), inline=False)

    embed.set_footer(text="Pro další informace použijte !help, nebo kontaktujte vývojáře.")
    embed.set_thumbnail(url="https://www.dropbox.com/scl/fi/9w2gbtba94m24p5rngzzl/Professional_Darts_Corporation_logo.svg.png?rlkey=4bmsph6uakm94ogqfgzwgtk02&st=18fecn4r&raw=1")  # Add a relevant thumbnail URL

    return embed

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

@bot.command(name="compare")
async def compare_command(ctx, player1_name: str, player2_name: str, date_from: str = None, date_to: str = None):
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

    player1_data = await fetch_player_data(player1_name, date_from, date_to)
    player2_data = await fetch_player_data(player2_name, date_from, date_to)
    
    if not player1_data:
        await ctx.send(f"Data pro hráče {player1_name} nebyla nalezena.")
        return
    if not player2_data:
        await ctx.send(f"Data pro hráče {player2_name} nebyla nalezena.")
        return

    embed = create_comparison_embed(player1_name, player1_data, player2_name, player2_data)
    await ctx.send(embed=embed)

@cached(cache=TTLCache(maxsize=100, ttl=3600))
async def get_tournaments():
    url = "https://api.assendelftmedia.nl/api/events?status%5B%5D=inprogress&status%5B%5D=scheduled&order_by=start_date&order_dir=asc"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
    return None

@cached(cache=TTLCache(maxsize=100, ttl=3600))
async def get_matches(tournament_id):
    url = f"https://api.assendelftmedia.nl/api/games?event_id={tournament_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
    return None

@bot.command(name="tournament")
async def tournament_command(ctx, tournament_name: str):
    tournaments_response = await get_tournaments()
    if not tournaments_response:
        await ctx.send("Unable to fetch tournaments data.")
        return
    
    tournament_id = None
    for tournament in tournaments_response:
        if tournament['name'].lower() == tournament_name.lower():
            tournament_id = tournament['id']
            break
    
    if not tournament_id:
        await ctx.send(f"Tournament '{tournament_name}' not found.")
        return
    
    matches_response = await get_matches(tournament_id)
    if not matches_response:
        await ctx.send("Unable to fetch matches data.")
        return
    
    matches = matches_response  # Directly use the response as a list
    output = [f"Tournament: {tournament_name}"]
    scheduled_matches = [match for match in matches if match['status'] == 0]
    played_matches = [match for match in matches if match['status'] == 4]
    
    output.append("Scheduled Matches:")
    for match in scheduled_matches:
        output.append(f"  - {match['players'][0]['name']} vs {match['players'][1]['name']} at {match['game_time']}")
    
    output.append("Played Matches:")
    for match in played_matches:
        output.append(f"  - {match['players'][0]['name']} vs {match['players'][1]['name']} at {match['game_time']}")
    
    await ctx.send("\n".join(output))

# Testovací příkaz
@bot.command(name="ping")
async def ping_command(ctx):
    await ctx.send("Pong!")

@bot.command(name="shutdown")
@commands.is_owner()
async def shutdown(ctx):
    await ctx.send("Shutting down...")
    await bot.close()

# Spuštění bota
bot.run("MTMyNjkxMDY4MjA0NTc0MzE1NA.G4W2-Y.H4jux_lnuRTpkxDJrMXUMgNcQ7nqFkY7qPGZcs")  # Replace with a secure way to load the token