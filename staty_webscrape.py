import requests
import time
from tabulate import tabulate

def get_data(url):
    """Funkce pro zpracování API požadavků."""
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Chyba při stahování dat: {response.status_code}")
        exit()

def main(player_name, date_from, date_to):
    """Hlavní funkce pro zpracování dat."""
    timestamp = int(time.time() * 1000)
    
    # Základní URL pro hráče
    base_url = f"https://app.dartsorakel.com/api/stats/player?dateFrom={date_from}&dateTo={date_to}&rankKey=26&organStat=All&tourns=All&minMatches=200&tourCardYear=&showStatsBreakdown=0&_={timestamp}"
    url_response = get_data(base_url)
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
        print(f"Hráč {player_name} nebyl nalezen.")
        return
    
    player_key = player_data[player_name]["player_key"]

    # Další statistiky
    stats_urls = {
        "average": f"https://app.dartsorakel.com/api/stats/player?rankKey=25&showStatsBreakdown=0&playerKeyToHighlight={player_key}&minMatches=200&limit=300&_={timestamp}",
        "average_actual": f"https://app.dartsorakel.com/api/stats/player?dateFrom={date_from}&dateTo={date_to}&rankKey=25&organStat=All&tourns=All&minMatches=200&tourCardYear=&showStatsBreakdown=0&_={timestamp}",
        "checkout_pcnt": f"https://app.dartsorakel.com/api/stats/player?rankKey=1053&showStatsBreakdown=0&playerKeyToHighlight={player_key}&minMatches=200&limit=300&_={timestamp}",
        "checkout_pcnt_actual": f"https://app.dartsorakel.com/api/stats/player?dateFrom={date_from}&dateTo={date_to}&rankKey=1053&organStat=All&tourns=All&minMatches=200&tourCardYear=&showStatsBreakdown=0&_={timestamp}",
        "maximum_per_leg": f"https://app.dartsorakel.com/api/stats/player?rankKey=1055&showStatsBreakdown=0&playerKeyToHighlight={player_key}&minMatches=200&limit=300&_={timestamp}",
        "maximum_per_leg_actual": f"https://app.dartsorakel.com/api/stats/player?dateFrom={date_from}&dateTo={date_to}&rankKey=1055&organStat=All&tourns=All&minMatches=200&tourCardYear=&showStatsBreakdown=0&_={timestamp}"
    }

    for stat_name, url in stats_urls.items():
        stat_data = get_data(url)["data"]
        for player in stat_data:
            if player['player_name'] == player_name:
                player_data[player_name][stat_name] = player["stat"]

    # Formátovaný výstup
    player = player_data[player_name]
    table = [
        ["Player Name", player["player_name"]],
        ["Player Key", player["player_key"]],
        ["Rank", player["rank"]],
        ["Maximums", player.get("maximums", "N/A")],
        ["Average", f"{player.get('average', 'N/A')} (Actual: {player.get('average_actual', 'N/A')})"],
        ["Checkout %", f"{player.get('checkout_pcnt', 'N/A')} (Actual: {player.get('checkout_pcnt_actual', 'N/A')})"],
        ["Maximums per Leg", f"{player.get('maximum_per_leg', 'N/A')} (Actual: {player.get('maximum_per_leg_actual', 'N/A')})"]
    ]
    print(tabulate(table, headers=["Stat", "Value"], tablefmt="grid"))

# Test
main("Max Hopp", "2024-4-18", "2024-12-21")
