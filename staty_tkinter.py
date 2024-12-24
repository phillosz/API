import requests
import time
from tkinter import Tk, Label, Entry, Button, Text, END


def get_data(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return None


def fetch_player_data(player_name, date_from, date_to, output_text):
    output_text.delete(1.0, END)  # Vyčistí textové pole
    timestamp = int(time.time() * 1000)
    
    base_url = f"https://app.dartsorakel.com/api/stats/player?dateFrom={date_from}&dateTo={date_to}&rankKey=26&organStat=All&tourns=All&minMatches=200&tourCardYear=&showStatsBreakdown=0&_={timestamp}"
    url_response = get_data(base_url)
    if not url_response:
        output_text.insert(END, "Chyba při načítání dat.\n")
        return

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
        output_text.insert(END, f"Hráč {player_name} nebyl nalezen.\n")
        return
    
    player_key = player_data[player_name]["player_key"]
    
    # Odkazy na další statistiky
    stats_urls = {
        "average": f"https://app.dartsorakel.com/api/stats/player?rankKey=25&showStatsBreakdown=0&playerKeyToHighlight={player_key}&minMatches=200&limit=32&_={timestamp}",
        "average_actual": f"https://app.dartsorakel.com/api/stats/player?rankKey=1054&showStatsBreakdown=0&playerKeyToHighlight={player_key}&minMatches=200&limit=32&_={timestamp}",
        "checkout_pcnt": f"https://app.dartsorakel.com/api/stats/player?rankKey=1053&showStatsBreakdown=0&playerKeyToHighlight={player_key}&minMatches=200&limit=32&_={timestamp}",
        "checkout_pcnt_actual": f"https://app.dartsorakel.com/api/stats/player?rankKey=1057&showStatsBreakdown=0&playerKeyToHighlight={player_key}&minMatches=200&limit=32&_={timestamp}",
        "maximum_per_leg": f"https://app.dartsorakel.com/api/stats/player?rankKey=1055&showStatsBreakdown=0&playerKeyToHighlight={player_key}&minMatches=200&limit=32&_={timestamp}",
        "maximum_per_leg_actual": f"https://app.dartsorakel.com/api/stats/player?rankKey=1056&showStatsBreakdown=0&playerKeyToHighlight={player_key}&minMatches=200&limit=32&_={timestamp}"
    }

    for stat_name, url in stats_urls.items():
        stat_data = get_data(url)["data"]
        for player in stat_data:
            if player['player_name'] == player_name:
                player_data[player_name][stat_name] = player["stat"]

    # Zobrazení výsledků v textovém poli
    player = player_data[player_name]
    output_text.insert(END, f"Player Name: {player['player_name']}\n")
    output_text.insert(END, f"Rank: {player['rank']}\n")
    output_text.insert(END, f"Maximums: {player.get('maximums', 'N/A')}\n")
    output_text.insert(END, f"Average: {player.get('average', 'N/A')} (Actual: {player.get('average_actual', 'N/A')})\n")
    output_text.insert(END, f"Checkout %: {player.get('checkout_pcnt', 'N/A')} (Actual: {player.get('checkout_pcnt_actual', 'N/A')})\n")
    output_text.insert(END, f"Maximums per Leg: {player.get('maximum_per_leg', 'N/A')} (Actual: {player.get('maximum_per_leg_actual', 'N/A')})\n")


# GUI aplikace
def create_gui():
    root = Tk()
    root.title("Darts Stats App")

    # Jméno hráče
    Label(root, text="Player Name:").grid(row=0, column=0, padx=10, pady=5)
    player_name_entry = Entry(root, width=30)
    player_name_entry.grid(row=0, column=1, padx=10, pady=5)

    # Datum od
    Label(root, text="Date From (YYYY-MM-DD):").grid(row=1, column=0, padx=10, pady=5)
    date_from_entry = Entry(root, width=30)
    date_from_entry.grid(row=1, column=1, padx=10, pady=5)

    # Datum do
    Label(root, text="Date To (YYYY-MM-DD):").grid(row=2, column=0, padx=10, pady=5)
    date_to_entry = Entry(root, width=30)
    date_to_entry.grid(row=2, column=1, padx=10, pady=5)

    # Tlačítko pro spuštění
    output_text = Text(root, width=60, height=20)
    output_text.grid(row=4, column=0, columnspan=2, padx=10, pady=5)

    def on_submit():
        player_name = player_name_entry.get()
        date_from = date_from_entry.get()
        date_to = date_to_entry.get()
        fetch_player_data(player_name, date_from, date_to, output_text)

    Button(root, text="Get Stats", command=on_submit).grid(row=3, column=0, columnspan=2, pady=10)

    root.mainloop()


# Spuštění aplikace
if __name__ == "__main__":
    create_gui()
