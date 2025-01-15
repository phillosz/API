import discord
from discord.ext import commands
import requests
import time
import schedule
import time
import os
from datetime import datetime

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

async def fetch_player_data(player_name, date_from, date_to):
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
    
    player_key = player_data[player_name]["player_key"]
    
    # Odkazy na další statistiky
    stats_urls = {
        "average": f"https://app.dartsorakel.com/api/stats/player?rankKey=25&showStatsBreakdown=0&playerKeyToHighlight={player_key}&minMatches=200&limit=32&_={timestamp}",
        "average_actual": f"https://app.dartsorakel.com/api/stats/player?dateFrom={date_from}&dateTo={date_to}&rankKey=25&organStat=All&tourns=All&minMatches=200&tourCardYear=&showStatsBreakdown=0&_={timestamp}",
        "checkout_pcnt": f"https://app.dartsorakel.com/api/stats/player?rankKey=1053&showStatsBreakdown=0&playerKeyToHighlight={player_key}&minMatches=200&limit=32&_={timestamp}",
        "checkout_pcnt_actual": f"https://app.dartsorakel.com/api/stats/player?dateFrom={date_from}&dateTo={date_to}&rankKey=1053&organStat=All&tourns=All&minMatches=200&tourCardYear=&showStatsBreakdown=0&_={timestamp}",
        "maximum_per_leg": f"https://app.dartsorakel.com/api/stats/player?rankKey=1055&showStatsBreakdown=0&playerKeyToHighlight={player_key}&minMatches=200&limit=32&_={timestamp}",
        "maximum_per_leg_actual": f"https://app.dartsorakel.com/api/stats/player?dateFrom={date_from}&dateTo={date_to}&rankKey=1055&organStat=All&tourns=All&minMatches=200&tourCardYear=&showStatsBreakdown=0&_={timestamp}"
        }

    for stat_name, url in stats_urls.items():
        stat_data = get_data(url)["data"]
        for player in stat_data:
            if player['player_name'] == player_name:
                player_data[player_name][stat_name] = player["stat"]

    # Výstup
    player = player_data[player_name]
    result = (
        f"**Statistiky pro hráče {player['player_name']}**\n"
        f"Rank: {player['rank']}\n"
        f"Maximums: {player.get('maximums', 'N/A')}\n"
        f"Average: {player.get('average', 'N/A')} (Actual: {player.get('average_actual', 'N/A')})\n"
        f"Checkout %: {player.get('checkout_pcnt', 'N/A')} (Actual: {player.get('checkout_pcnt_actual', 'N/A')})\n"
        f"Maximums per Leg: {player.get('maximum_per_leg', 'N/A')} (Actual: {player.get('maximum_per_leg_actual', 'N/A')})\n"
    )
    return result

# Příkaz pro získání statistik
@bot.command(name="stats")
async def stats_command(ctx, player_name: str, date_from: str, date_to: str):
    try:
        # Validace data
        datetime.strptime(date_from.strip(), "%Y-%m-%d")
        datetime.strptime(date_to.strip(), "%Y-%m-%d")
    except ValueError as e:
        await ctx.send(f"Chyba ve formátu dat: {e}\nZadejte data ve formátu YYYY-MM-DD.")
        return

    # Opravený způsob předávání celého jména
    result = await fetch_player_data(player_name, date_from, date_to)
    await ctx.send(result)


# Testovací příkaz
@bot.command(name="ping")
async def ping(ctx):
    await ctx.send("Pong!")
    
# Funkce pro vypnutí bota
def stop_bot():
    print("Bot se vypíná...")
    os._exit(0)  # Vypne celý proces a šetří čas na Railway

# Funkce pro spuštění bota
def start_bot():
    print("Bot se spouští...")
    bot.run("MTMyNjkxMDY4MjA0NTc0MzE1NA.G4W2-Y.H4jux_lnuRTpkxDJrMXUMgNcQ7nqFkY7qPGZcs")  # Nahraď token správnou proměnnou nebo proměnnou prostředí

# Naplánuj vypnutí a zapnutí bota
schedule.every().day.at("16:50").do(stop_bot)  # Vypne bota v 1 ráno
schedule.every().day.at("16:52").do(start_bot)  # Spustí bota v 6 ráno

# Spusť bota poprvé
if __name__ == "__main__":
    start_bot()  # Spustí bota při startu
    while True:  # Kontroluje naplánované úkoly
        schedule.run_pending()
        time.sleep(1)
