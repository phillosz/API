import discord
from discord.ext import commands
from datetime import datetime, timedelta
import aiohttp
from bs4 import BeautifulSoup  # Add this import

# Bot Setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Premium users
PREMIUM_USERS = {586540043812864050, 833783091003785266, 738811763101007923}

# Cache for storing fetched player data and API responses within the same command execution
player_data_cache = {}
api_response_cache = {}
cache_ttl = 3600  # Time-to-live for cache in seconds (1 hour)
cache_timestamp = {}

async def get_data(url):
    current_time = datetime.now().timestamp()
    if url in api_response_cache and (current_time - cache_timestamp[url]) < cache_ttl:
        return api_response_cache[url]
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                api_response_cache[url] = data
                cache_timestamp[url] = current_time
                return data
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

async def fetch_last_matches(player_key, limit=10):
    timestamp = int(datetime.now().timestamp() * 1000)
    
    url = f"https://app.dartsorakel.com/api/player/matches/{player_key}?rankKey=26&organStat=All&tourns=All&limit={limit}&_={timestamp}"
    url_response = await get_data(url)

    data = url_response.copy()
    last_matches = []
    
    for match in data["data"]:
        # Extract opponent's name from HTML link
        soup = BeautifulSoup(match["opponent"], "html.parser")
        opponent_name = soup.get_text()
        
        legs = match["loser_score"] + match["winner_score"]
        last_matches.append({
            "opponent": opponent_name,
            "date": match["match_date"],
            "legs": legs,
            "180s": match["stat1"]
        })

    return last_matches

async def fetch_player_data(player_name, date_from, date_to):
    timestamp = int(datetime.now().timestamp() * 1000)
    
    base_url = f"https://app.dartsorakel.com/api/stats/player?dateFrom={date_from}&dateTo={date_to}&rankKey=26&organStat=All&tourns=All&minMatches=200&tourCardYear=&showStatsBreakdown=0&_={timestamp}"
    players_url = "https://app.dartsorakel.com/dropdownDataSearch"
    url_response = await get_data(players_url)
    if not url_response:
        return None

    data = url_response.copy()
    player_data = {}

    for player in data:
        player_data[player['player_name']] = {
            'player_name': player['player_name'],
            'player_key': player['player_key']
        }

    if player_name not in player_data:
        return None

    player_key = player_data[player_name]["player_key"]

    # Fetch additional statistics
    additional_stats = await fetch_additional_stats(player_key)
    if additional_stats:
        player_data[player_name]['additional_stats'] = additional_stats

    # Fetch last matches
    last_matches = await fetch_last_matches(player_key)
    if last_matches:
        player_data[player_name]['last_matches'] = last_matches

    # More detailed statistics URLs
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
        valid_values = [v for v in values if v is not None]  # Filter out None values
        return sum(float(v.strip('%')) if isinstance(v, str) and v.endswith('%') else float(v) for v in valid_values) / len(valid_values)

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
        title=f"Statistics for player {player_name}",
        description=description,
        color=color  # Colour of the embed
    )

    # Add pairs of statistics
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
        embed.add_field(name="🎲 Maximums Total", value=data["maximums"], inline=True)
        
    if "last_matches" in data:
        for match in data["last_matches"]:
            embed.add_field(
                name=f"Match vs {match['opponent']} on {match['date']}",
                value=f"Legs: {match['legs']}, 180s: {match['180s']}",
                inline=False
            )

    embed.set_footer(text="For further information use !help, or contact the dev.")
    embed.set_thumbnail(url="https://www.dropbox.com/scl/fi/9w2gbtba94m24p5rngzzl/Professional_Darts_Corporation_logo.svg.png?rlkey=4bmsph6uakm94ogqfgzwgtk02&st=18fecn4r&raw=1")  # Add a relevant thumbnail URL

    return embed

def create_premium_embed(player_name, data):
    fill_missing_stats(data)

    embed = discord.Embed(
        title=f"Premium statistics for player {player_name}",
        description="In-depth statistics.",
        color=discord.Color.gold()  # Colour of the embed
    )

    # Add pairs of statistics
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
        embed.add_field(name="🎲 Maximums Total", value=data["maximums"], inline=True)

    # Add additional stats if available
    if "additional_stats" in data:
        additional_stats = data["additional_stats"]
        for stat_name, stat_values in additional_stats.items():
            # Convert None values to empty strings
            stat_values = [str(value) if value is not None else '' for value in stat_values]
            embed.add_field(name=stat_name, value=", ".join(stat_values), inline=False)

    embed.set_footer(text="For further information use !help, or contact the dev.")
    embed.set_thumbnail(url="https://www.dropbox.com/scl/fi/9w2gbtba94m24p5rngzzl/Professional_Darts_Corporation_logo.svg.png?rlkey=4bmsph6uakm94ogqfgzwgtk02&st=18fecn4r&raw=1")  # Add a relevant thumbnail URL

    return embed

def create_comparison_embed(player1_name, player1_data, player2_name, player2_data):
    fill_missing_stats(player1_data)
    fill_missing_stats(player2_data)

    embed = discord.Embed(title="Player Comparison", color=discord.Color.purple())
    
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
        embed.add_field(name="🎲 Maximums Total", value=f"{player1_data['maximums']} 🆚 {player2_data['maximums']}", inline=True)

    embed.set_footer(text="For further information use !help, or contact the dev.")
    embed.set_thumbnail(url="https://www.dropbox.com/scl/fi/9w2gbtba94m24p5rngzzl/Professional_Darts_Corporation_logo.svg.png?rlkey=4bmsph6uakm94ogqfgzwgtk02&st=18fecn4r&raw=1")

    return embed

# Příkaz pro základní statistiky
@bot.command(name="stats")
async def stats_command(ctx, player_name: str, date_from: str = None, date_to: str = None):
    global player_data_cache, api_response_cache, cache_timestamp
    player_data_cache = {}  # Clear cache at the start of each command execution
    api_response_cache = {}  # Clear API response cache at the start of each command execution
    cache_timestamp = {}  # Clear cache timestamps at the start of each command execution

    if date_from is None:
        date_from = (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d")  # Change to 45 days
    if date_to is None:
        date_to = datetime.now().strftime("%Y-%m-%d")

    try:
        datetime.strptime(date_from, "%Y-%m-%d")
        datetime.strptime(date_to, "%Y-%m-%d")
    except ValueError as e:
        await ctx.send(f"Error in formatting: {e}")
        return

    player_data = await fetch_player_data(player_name, date_from, date_to)
    if not player_data:
        await ctx.send(f"Statistics for player {player_name} could not been loaded.")
        return

    embed = create_embed(player_name, player_data, discord.Color.blue(), "Basic statistics overview.")
    await ctx.send(embed=embed)

# Command for premium users
@bot.command(name="premiumstats")
async def premium_stats_command(ctx, player_name: str, date_from: str = None, date_to: str = None):
    global player_data_cache, api_response_cache
    player_data_cache = {}  # Clear cache at the start of each command execution
    api_response_cache = {}  # Clear API response cache at the start of each command execution

    if date_from is None:
        date_from = (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d")  # Change to 45 days
    if date_to is None:
        date_to = datetime.now().strftime("%Y-%m-%d")

    try:
        datetime.strptime(date_from, "%Y-%m-%d")
        datetime.strptime(date_to, "%Y-%m-%d")
    except ValueError as e:
        await ctx.send(f"Error in formatting: {e}")
        return

    player_data = await fetch_player_data(player_name, date_from, date_to)
    if not player_data:
        await ctx.send(f"Statistics for player {player_name} could not been loaded.")
        return

    embed = create_premium_embed(player_name, player_data)
    await ctx.send(embed=embed)

@bot.command(name="compare")
async def compare_command(ctx, player1_name: str, player2_name: str, date_from: str = None, date_to: str = None):
    global player_data_cache, api_response_cache
    player_data_cache = {}  # Clear cache at the start of each command execution
    api_response_cache = {}  # Clear API response cache at the start of each command execution

    if date_from is None:
        date_from = (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d")  # Change to 45 days
    if date_to is None:
        date_to = datetime.now().strftime("%Y-%m-%d")

    try:
        datetime.strptime(date_from, "%Y-%m-%d")
        datetime.strptime(date_to, "%Y-%m-%d")
    except ValueError as e:
        await ctx.send(f"Error in formatting: {e}")
        return

    player1_data = await fetch_player_data(player1_name, date_from, date_to)
    player2_data = await fetch_player_data(player2_name, date_from, date_to)
    
    if not player1_data:
        await ctx.send(f"Statistics for player {player1_name} could not been loaded.")
        return
    if not player2_data:
        await ctx.send(f"Statistics for player {player2_name} could not been loaded.")
        return

    embed = create_comparison_embed(player1_name, player1_data, player2_name, player2_data)
    await ctx.send(embed=embed)

@bot.command(name="lastmatches")
async def last_matches_command(ctx, player_name: str):
    global player_data_cache, api_response_cache, cache_timestamp
    player_data_cache = {}  # Clear cache at the start of each command execution
    api_response_cache = {}  # Clear API response cache at the start of each command execution
    cache_timestamp = {}  # Clear cache timestamps at the start of each command execution

    player_data = await fetch_last_matches(player_name)
    if not player_data:
        await ctx.send(f"Statistics for player {player_name} could not been loaded.")
        return

    embed = create_embed(player_name, player_data, discord.Color.blue(), "Last matches overview.")
    await ctx.send(embed=embed)

async def get_tournaments():
    url = "https://api.assendelftmedia.nl/api/events?status%5B%5D=inprogress&status%5B%5D=scheduled&order_by=start_date&order_dir=asc"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
    return None

async def get_completed_tournaments():
    url = "https://api.assendelftmedia.nl/api/events?status%5B%5D=completed&order_by=end_date&order_dir=desc"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
    return None

async def get_matches(tournament_id):
    url = f"https://api.assendelftmedia.nl/api/games?event_id={tournament_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
    return None

async def send_paginated_embeds(ctx, embeds):
    for embed in embeds:
        await ctx.send(embed=embed)

@bot.command(name="tournament")
async def tournament_command(ctx, tournament_name: str, player1_name: str = None, player2_name: str = None):
    tournaments_response = await get_tournaments()
    completed_tournaments_response = await get_completed_tournaments()
    
    if not tournaments_response and not completed_tournaments_response:
        await ctx.send("Unable to fetch tournaments data.")
        return
    
    all_tournaments = tournaments_response.get("data", []) + completed_tournaments_response.get("data", [])
    
    tournament_id = None
    for tournament in all_tournaments:
        if tournament['name'].lower() == tournament_name.lower():
            tournament_id = tournament['id']
            break
    
    if not tournament_id:
        # Provide hints for 5 past and 5 future tournaments
        past_tournaments = [t for t in completed_tournaments_response.get("data", [])[:5]]
        future_tournaments = [t for t in tournaments_response.get("data", [])[:5]]
        
        embed = discord.Embed(
            title="Tournament not found",
            description="Here are some suggestions:",
            color=discord.Color.red()
        )
        
        embed.add_field(name="**Past Tournaments:**", value="\n".join([f"- {t['name']} (Ended: {t['end_dt']})" for t in past_tournaments]), inline=False)
        embed.add_field(name="**Upcoming Tournaments:**", value="\n".join([f"- {t['name']} (Starts: {t['start_dt']})" for t in future_tournaments]), inline=False)
        
        await ctx.send(embed=embed)
        return
    
    matches_response = await get_matches(tournament_id)
    if not matches_response:
        await ctx.send("Unable to fetch matches data.")
        return
    
    matches = matches_response.get("matches", [])  # Adjust to new data structure
    matches.sort(key=lambda x: x['game_time'])  # Order matches by game_time
    
    embeds = []
    embed = discord.Embed(
        title=f"Tournament: {tournament_name}",
        description="",
        color=discord.Color.blue()  # Set the color of the embed
    )
    
    if player1_name and player2_name:
        for match in matches:
            players = match['players']
            if (players[0]['name'].lower() == player1_name.lower() and players[1]['name'].lower() == player2_name.lower()) or \
               (players[0]['name'].lower() == player2_name.lower() and players[1]['name'].lower() == player1_name.lower()):
                embed.title = f"Match: {players[0]['name']} vs {players[1]['name']}"
                embed.add_field(name="Game Time", value=match['game_time'], inline=False)
                for player in players:
                    stats = player['game_stats']['stats']
                    embed.add_field(
                        name=player['name'],
                        value=(
                            f"Legs Won: {player['game_stats']['legs_won']}\n"
                            f"Three Dart Average: {stats['three_dart_average']}\n"
                            f"100+ Thrown: {stats['100_plus_thrown']}\n"
                            f"140+ Thrown: {stats['140_plus_thrown']}\n"
                            f"180+ Thrown: {stats['180_plus_thrown']}\n"
                            f"Highest Checkout: {stats['highest_checkout']}\n"
                            f"Checkout Percentage: {stats['checkout_percentage']}%\n"
                            f"Checkouts Made: {stats['checkouts_made']}\n"
                            f"Checkouts Total: {stats['checkout_total']}"
                        ),
                        inline=False
                    )
                await ctx.send(embed=embed)
                return
    
    scheduled_matches = [match for match in matches if match['status'] == 0]
    played_matches = [match for match in matches if match['status'] == 4]
    
    embed.add_field(name="Scheduled Matches", value="\u200b", inline=False)
    for match in scheduled_matches:
        if len(embed.fields) == 25:
            embeds.append(embed)
            embed = discord.Embed(
                title=f"Tournament: {tournament_name}",
                description="",
                color=discord.Color.blue()
            )
        embed.add_field(
            name=f"{match['players'][0]['name']} vs {match['players'][1]['name']}",
            value=f"At {match['game_time']}",
            inline=False
        )
    
    embed.add_field(name="Played Matches", value="\u200b", inline=False)
    for match in played_matches:
        if len(embed.fields) == 25:
            embeds.append(embed)
            embed = discord.Embed(
                title=f"Tournament: {tournament_name}",
                description="",
                color=discord.Color.blue()
            )
        embed.add_field(
            name=f"{match['players'][0]['name']} vs {match['players'][1]['name']}",
            value=f"At {match['game_time']}",
            inline=False
        )
    
    embeds.append(embed)
    await send_paginated_embeds(ctx, embeds)

@bot.command(name="shutdown")
@commands.is_owner()
async def shutdown(ctx):
    await ctx.send("Shutting down...")
    await bot.close()

# Spuštění bota
bot.run("MTMyNjkxMDY4MjA0NTc0MzE1NA.G4W2-Y.H4jux_lnuRTpkxDJrMXUMgNcQ7nqFkY7qPGZcs")  # Replace with a secure way to load the token