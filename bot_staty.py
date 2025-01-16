import discord
from discord.ext import commands
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import io
from aiocache import cached, SimpleMemoryCache
import requests
import aiohttp  # Add this import for asynchronous HTTP requests

# Nastavení bota
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Prémioví uživatelé
PREMIUM_USERS = {586540043812864050}  # Změň na své ID

# Funkce pro získání dat z API (s cache)
@cached(ttl=3600, cache=SimpleMemoryCache)
async def get_data(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
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

def create_comparison_embed(player1_name, player1_data, player2_name, player2_data):
    embed = discord.Embed(title="Porovnání hráčů", color=discord.Color.purple())
    
    embed.add_field(name=f"{player1_name} 🆚 {player2_name}", value="\u200b", inline=False)
    
    if "rank" in player1_data and "rank" in player2_data:
        embed.add_field(name="🏆 Rank", value=f"{player1_data['rank']} 🆚 {player2_data['rank']}", inline=True)
    if "average" in player1_data and "average_actual" in player1_data and "average" in player2_data and "average_actual" in player2_data:
        embed.add_field(name="🎯 Average", value=f"{player1_data['average']} (Current: {player1_data['average_actual']}) 🆚 {player2_data['average']} (Current: {player2_data['average_actual']})", inline=False)
    if "checkout_pcnt" in player1_data and "checkout_pcnt_actual" in player1_data and "checkout_pcnt" in player2_data and "checkout_pcnt_actual" in player2_data:
        embed.add_field(name="✅ Checkout %", value=f"{player1_data['checkout_pcnt']} (Current: {player1_data['checkout_pcnt_actual']}) 🆚 {player2_data['checkout_pcnt']} (Current: {player2_data['checkout_pcnt_actual']})", inline=False)
    if "maximum_per_leg" in player1_data and "maximum_per_leg_actual" in player1_data and "maximum_per_leg" in player2_data and "maximum_per_leg_actual" in player2_data:
        embed.add_field(name="💥 Max per Leg", value=f"{player1_data['maximum_per_leg']} (Current: {player1_data['maximum_per_leg_actual']}) 🆚 {player2_data['maximum_per_leg']} (Current: {player2_data['maximum_per_leg_actual']})", inline=False)
    if "maximums" in player1_data and "maximums" in player2_data:
        embed.add_field(name="🎲 Maximums celkem", value=f"{player1_data['maximums']} 🆚 {player2_data['maximums']}", inline=True)

    embed.set_footer(text="Statistiky poskytované vaším botem!")
    embed.set_thumbnail(url="https://www.dropbox.com/scl/fi/9w2gbtba94m24p5rngzzl/Professional_Darts_Corporation_logo.svg.png?rlkey=4bmsph6uakm94ogqfgzwgtk02&st=18fecn4r&raw=1")

    # Generate graph
    graph_buf = generate_graph(player1_name, player1_data, player2_name, player2_data)
    file = discord.File(graph_buf, filename="comparison.png")
    embed.set_image(url="attachment://comparison.png")

    return embed

def generate_graph(player1_name, player1_data, player2_name, player2_data):
    def safe_float(value):
        if isinstance(value, str) and value.endswith('%'):
            return float(value.strip('%'))
        return float(value)

    labels = ['Rank', 'Average', 'Checkout %', 'Max per Leg', 'Maximums']
    player1_values = [
        safe_float(player1_data.get('rank', 0)),
        safe_float(player1_data.get('average', 0)),
        safe_float(player1_data.get('checkout_pcnt', 0)),
        safe_float(player1_data.get('maximum_per_leg', 0)),
        safe_float(player1_data.get('maximums', 0))
    ]
    player2_values = [
        safe_float(player2_data.get('rank', 0)),
        safe_float(player2_data.get('average', 0)),
        safe_float(player2_data.get('checkout_pcnt', 0)),
        safe_float(player2_data.get('maximum_per_leg', 0)),
        safe_float(player2_data.get('maximums', 0))
    ]

    x = range(len(labels))

    fig, ax = plt.subplots()
    ax.bar(x, player1_values, width=0.4, label=player1_name, align='center')
    ax.bar(x, player2_values, width=0.4, label=player2_name, align='edge')

    ax.set_ylabel('Values')
    ax.set_title('Player Comparison')
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    return buf

import numpy as np

async def plot_player_statistics(player_data):
    # Extract data
    player_names = list(player_data.keys())
    averages = [player_data[player]['average'] for player in player_names]
    checkout_pcents = [player_data[player]['checkout_pcnt'] for player in player_names]
    maximums_per_leg = [player_data[player]['maximums_per_leg'] for player in player_names]

    # Create subplots
    fig, axs = plt.subplots(1, 3, figsize=(18, 6))

    # Plot average
    axs[0].bar(player_names, averages, color='blue')
    axs[0].set_title('Average')
    axs[0].set_ylabel('Average')
    axs[0].set_xticklabels(player_names, rotation=45, ha='right')

    # Plot checkout percentage
    axs[1].bar(player_names, checkout_pcents, color='green')
    axs[1].set_title('Checkout Percentage')
    axs[1].set_ylabel('Checkout %')
    axs[1].set_xticklabels(player_names, rotation=45, ha='right')

    # Plot maximums per leg
    axs[2].bar(player_names, maximums_per_leg, color='red')
    axs[2].set_title('Maximums per Leg')
    axs[2].set_ylabel('Maximums per Leg')
    axs[2].set_xticklabels(player_names, rotation=45, ha='right')

    # Adjust layout
    plt.tight_layout()

    # Save the plot to a BytesIO object
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close(fig)

    return buf

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

    buf = await plot_player_statistics(player_data)
    await ctx.send(file=discord.File(buf, 'player_stats.png'))

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
    graph_buf = generate_graph(player1_name, player1_data, player2_name, player2_data)
    file = discord.File(graph_buf, filename="comparison.png")
    await ctx.send(embed=embed, file=file)

# Testovací příkaz
@bot.command(name="ping")
async def ping_command(ctx):
    await ctx.send("Pong!")

# Spuštění bota
bot.run("MTMyNjkxMDY4MjA0NTc0MzE1NA.G4W2-Y.H4jux_lnuRTpkxDJrMXUMgNcQ7nqFkY7qPGZcs")  # Replace with a secure way to load the token
