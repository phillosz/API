import os
import discord
from discord.ext import commands
from datetime import datetime, timedelta
import aiohttp
import asyncio
from bs4 import BeautifulSoup

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

PREMIUM_USERS = {586540043812864050, 833783091003785266, 738811763101007923}

player_data_cache = {}
api_response_cache = {}
cache_ttl = 3600
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
        if len(last_matches) >= limit:
            break
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

    additional_stats = await fetch_additional_stats(player_key)
    if additional_stats:
        player_data[player_name]['additional_stats'] = additional_stats

    last_matches = await fetch_last_matches(player_key)
    if last_matches:
        player_data[player_name]['last_matches'] = last_matches

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
        valid_values = [v for v in values if v is not None]
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
        color=color
    )

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
                name=f"vs {match['opponent']} on {match['date']}",
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
        color=discord.Color.gold()
    )

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

    if "additional_stats" in data:
        additional_stats = data["additional_stats"]
        for stat_name, stat_values in additional_stats.items():
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

@bot.command(name="stats")
async def stats_command(ctx, player_name: str, date_from: str = None, date_to: str = None):
    global player_data_cache, api_response_cache, cache_timestamp
    player_data_cache = {}
    api_response_cache = {}
    cache_timestamp = {}

    if date_from is None:
        date_from = (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d")
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

@bot.command(name="premiumstats")
async def premium_stats_command(ctx, player_name: str, date_from: str = None, date_to: str = None):
    global player_data_cache, api_response_cache
    player_data_cache = {}
    api_response_cache = {}

    if date_from is None:
        date_from = (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d")
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
    
    if "last_matches" in player_data:
        matches = player_data["last_matches"][:10]
        embeds = []
        matches_embed = discord.Embed(
            title=f"Last 10 Matches for {player_name}",
            color=discord.Color.gold()
        )
        for match in matches:
            if len(matches_embed.fields) >= 25:
                embeds.append(matches_embed)
                matches_embed = discord.Embed(
                    title=f"Last 10 Matches for {player_name} (cont.)",
                    color=discord.Color.gold()
                )
            matches_embed.add_field(
                name=f"vs {match['opponent']} on {match['date']}",
                value=f"Legs: {match['legs']}, 180s: {match['180s']}",
                inline=False
            )
        embeds.append(matches_embed)
        for em in embeds:
            await ctx.send(embed=em)

@bot.command(name="compare")
async def compare_command(ctx, player1_name: str, player2_name: str, date_from: str = None, date_to: str = None):
    global player_data_cache, api_response_cache
    player_data_cache = {}
    api_response_cache = {}
    if date_from is None:
        date_from = (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d")
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

async def last_matches_command(ctx, player_name: str):
    global player_data_cache, api_response_cache, cache_timestamp
    player_data_cache = {}
    api_response_cache = {}
    cache_timestamp = {}
    
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
    
    matches = matches_response.copy()
    matches.sort(key=lambda x: x['game_time'])
    
    embeds = []
    embed = discord.Embed(
        title=f"Tournament: {tournament_name}",
        description="",
        color=discord.Color.blue()
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

class MonthSelectView(discord.ui.View):
    def __init__(self, month_data: dict):
        super().__init__(timeout=None)
        self.month_data = month_data
        for month in self.month_data:
            self.add_item(MonthButton(month))

class MonthButton(discord.ui.Button):
    def __init__(self, month: str):
        super().__init__(label=month, style=discord.ButtonStyle.blurple)
        self.month = month

    async def callback(self, interaction: discord.Interaction):
        tournaments = self.view.month_data[self.month]
        embed = discord.Embed(title=f"Tournaments in {self.month}", color=discord.Color.blue())
        if tournaments:
            embed.description = "\n".join([
                f"{t['eventName']} from {t['startDate']} to {t['endDate']} at {t['venueName']}"
                for t in tournaments
            ])
        else:
            embed.description = "No tournaments found"
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.command(name="futuretournament")
async def futuretournament_command(ctx):
    new_endpoint_url = "https://www.bbc.com/wc-data/container/sport-calendar?endDate=2025-12-31&shouldHideEventsBeforeToday=false&sport=darts&startDate=2025-02-01&todayDate=2025-01-22"  # every year the URL needs to be updated
    async with aiohttp.ClientSession() as session:
        async with session.get(new_endpoint_url) as resp:
            new_data = await resp.json()

    month_data = {}
    today = datetime.now().date()
    for group in new_data.get("eventGroups", []):
        group_name = group.get("groupName", "Unknown Month")
        for event in group.get("events", []):
            if "startDate" in event:
                start_date = datetime.strptime(event["startDate"], "%Y-%m-%d").date()
                if start_date > today and not event.get("isCancelled", False):
                    if group_name not in month_data:
                        month_data[group_name] = []
                    month_data[group_name].append({
                        "eventName": event.get("eventName", "Unknown Event"),
                        "startDate": event.get("startDate"),
                        "endDate": event.get("endDate", event.get("startDate")),
                        "venueName": event.get("venueName", "Unknown Venue"),
                        "month": group_name
                    })

    view = MonthSelectView(month_data)
    await ctx.send("Select a month to view tournaments:", view=view)

@bot.command(name="shutdown")
@commands.is_owner()
async def shutdown(ctx):
    await ctx.send("Shutting down...")
    await bot.close()

def run_bot():
    bot.run(DISCORD_TOKEN)



@bot.command(name="playerstats")
async def playerstats_command(ctx, player_name: str):
    """Fetch stats for a specific player in two time ranges: last 45 days and last year."""

    base_url = "https://api-igamedc.igamemedia.com/api/mss-web/results-fixtures?week="
    detail_url = "https://api-igamedc.igamemedia.com/api/mss-web/fixtures"

    now = datetime.now()
    last_45_days = now - timedelta(days=45)
    last_year = now - timedelta(days=365)

    async def get_json(session, url):
        async with session.get(url) as resp:
            return await resp.json()

    # Separate lists to store stats
    gathered_45 = []
    gathered_year = []

    async with aiohttp.ClientSession() as session:
        # 1) Load all weeks in parallel (1..197)
        tasks = [get_json(session, f"{base_url}{week}") for week in range(1, 198)]
        weeks_responses = await asyncio.gather(*tasks)

        # Collect match IDs for the last year (larger window)
        match_ids_year = []
        for data in weeks_responses:
            for fixture in data.get("fixtures", []):
                fixture_time_str = fixture.get("fixture")
                if fixture_time_str:
                    fixture_date = datetime.fromisoformat(fixture_time_str.replace("Z","")).date()
                    print(f"[DEBUG] fixture_date={fixture_date}, last_year={last_year.date()}")
                    if fixture_date >= last_year.date():
                        match_ids_year.append(fixture["gameId"])

        # 2) For each match in the last year, load detailed stats
        detail_tasks_year = [get_json(session, f"{detail_url}/{m_id}") for m_id in match_ids_year]
        matches_details_year = await asyncio.gather(*detail_tasks_year)

        # 3) Extract stats for the requested player within last year
        for match in matches_details_year:
            ps = match.get("playersStatistics", {})
            players = ps.get("players", [])
            stats = ps.get("statistics", [])
            # Also parse date again for last-45-days check
            match_date_str = match.get("startDateTime")
            match_date = datetime.fromisoformat(match_date_str.replace("Z","")) if match_date_str else None
            for i, p in enumerate(players):
                if p.get("name") == player_name and i < len(stats):
                    # Always add to the 'year' group
                    gathered_year.append(stats[i])
                    # Additionally add to the '45' group if match_date qualifies
                    if match_date and match_date >= last_45_days:
                        gathered_45.append(stats[i])

    # Helper to compute aggregated stats
    def aggregate_stats(stats_list):
        if not stats_list:
            return (0, 0, 0.0, 0.0, 0.0)

        total_legs = sum(s.get("totalScore", 0) for s in stats_list)
        total_180 = sum(s.get("turns180", 0) for s in stats_list)
        count = len(stats_list)

        avg_avg = sum(s.get("average", 0) for s in stats_list) / count
        avg_checkout = sum(s.get("checkoutPercentage", 0) for s in stats_list) / count
        ratio_180_per_leg = (total_180 / total_legs) if total_legs else 0

        return (count, total_legs, ratio_180_per_leg, avg_avg, avg_checkout)

    c45, legs45, ratio45, avg45, chk45 = aggregate_stats(gathered_45)
    cYear, legsYear, ratioYear, avgYear, chkYear = aggregate_stats(gathered_year)

    msg = f"**Stats for {player_name}**\n\n"
    msg += f"**Last 45 days**\n- Matches: {c45}\n- Legs played: {legs45}\n- 180s/leg: {ratio45:.2f}\n- Avg: {avg45:.2f}\n- Checkout %: {chk45:.2f}\n\n"
    msg += f"**Last year**\n- Matches: {cYear}\n- Legs played: {legsYear}\n- 180s/leg: {ratioYear:.2f}\n- Avg: {avgYear:.2f}\n- Checkout %: {chkYear:.2f}"

    await ctx.send(msg)