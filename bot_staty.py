import discord
from discord.ext import commands
import requests
import time
from datetime import datetime
from aiocache import Cache
import matplotlib.pyplot as plt

# Nastavení cache
cache = Cache(Cache.MEMORY)

# Nastavení bota
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Funkce pro získání dat z API
def get_data(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return None

# Generování grafu
def plot_player_stats(player_name, player_data):
    categories = ['Rank', 'Maximums', 'Average', 'Checkout %']
    values = [
        player_data.get('rank', 0),
        player_data.get('maximums', 0),
        player_data.get('average', 0),
        player_data.get('checkout_pcnt', 0)
    ]
    plt.bar(categories, values, color=['blue', 'green', 'orange', 'red'])
    plt.title(f"Statistiky: {player_name}")
    plt.ylabel("Hodnota")
    plt.savefig("stats.png")
    plt.close()

# Funkce pro získání statistik hráče
async def fetch_player_data(player_name, date_from, date_to):
    cache_key = f"{player_name}_{date_from}_{date_to}"
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    timestamp = int(time.time() * 1000)
    base_url = f"https://app.dartsorakel.com/api/stats/player?dateFrom={date_from}&dateTo={date_to}&rankKey=26&organStat=All&tourns=All&minMatches=200&tourCardYear=&showStatsBreakdown=0&_={timestamp}"
    url_response = get_data(base_url)
    if not url_response:
        return "Chyba při načítání dat."

    data = url_response["data"]
    player_data = {}
    for player in data:
        player_data[player['player_name']] = {
            'player_name': player['player_name'],
            'player_key': player['player_key'],
            'rank': player['rank'],
            'maximums': player['stat']
        }

    if player_name not in player_data:
        return f"Hráč {player_name} nebyl nalezen."

    player = player_data[player_name]

    result_embed = discord.Embed(
        title=f"Statistiky pro hráče {player['player_name']}",
        color=0x00ff00,
    )
    result_embed.add_field(name="Rank", value=player['rank'], inline=False)
    result_embed.add_field(name="Maximums", value=player.get('maximums', 'N/A'), inline=True)

    # Uložení do cache
    await cache.set(cache_key, result_embed, ttl=3600)  # Cache na 1 hodinu
    return result_embed

# Příkaz pro získání statistik
@bot.command(name="stats")
async def stats_command(ctx, player_name: str, date_from: str, date_to: str):
    try:
        datetime.strptime(date_from.strip(), "%Y-%m-%d")
        datetime.strptime(date_to.strip(), "%Y-%m-%d")
    except ValueError as e:
        await ctx.send(f"Chyba ve formátu dat: {e}\nZadejte data ve formátu YYYY-MM-DD.")
        return

    result_embed = await fetch_player_data(player_name, date_from, date_to)
    await ctx.send(embed=result_embed)

# Prémiový příkaz pro generování grafů
premium_users = [586540043812864050]  # Nahraďte ID uživatelů prémiového přístupu

@bot.command(name="premium_stats")
async def premium_stats(ctx, player_name: str, date_from: str, date_to: str):
    if ctx.author.id not in premium_users:
        await ctx.send("Tento příkaz je dostupný pouze pro prémiové uživatele.")
        return

    result_embed = await fetch_player_data(player_name, date_from, date_to)
    if isinstance(result_embed, discord.Embed):
        player_data = {
            'rank': result_embed.fields[0].value,
            'maximums': result_embed.fields[1].value,
            'average': 50,  # Příkladová data
            'checkout_pcnt': 80  # Příkladová data
        }
        plot_player_stats(player_name, player_data)
        await ctx.send(embed=result_embed)
        await ctx.send(file=discord.File("stats.png"))
    else:
        await ctx.send(result_embed)

# Testovací příkaz
@bot.command(name="ping")
async def ping(ctx):
    await ctx.send("Pong!")

# Spuštění bota
bot.run("MTMyNjkxMDY4MjA0NTc0MzE1NA.G4W2-Y.H4jux_lnuRTpkxDJrMXUMgNcQ7nqFkY7qPGZcs")
