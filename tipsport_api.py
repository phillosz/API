from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def get_match_links(url):
    """Načte seznam zápasů a odkazy na jejich podstránky pomocí Selenium."""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Pro běh bez zobrazení okna prohlížeče
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    
    service = Service('/usr/bin/safaridriver')  # Cesta k `safaridriver`
    driver = webdriver.Safari(service=service)
    driver.get(url)

    # Čekání, než se stránka načte
    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".row.row-small.middle-lg"))
    )

    matches = []
    match_elements = driver.find_elements(By.CSS_SELECTOR, ".row.row-small.middle-lg")
    for match in match_elements:
        try:
            title = match.find_element(By.CSS_SELECTOR, ".SubHeaderstyled__SubHeader-sc-16ewjs7-0.fJFZok").text
            link_element = match.find_element(By.CSS_SELECTOR, "a")  # Najde první odkaz
            link = link_element.get_attribute("href")
            matches.append({"title": title, "link": link})
        except Exception as e:
            print(f"Chyba při zpracování zápasu: {e}")

    driver.quit()
    return matches

def scrape_match_details(match_url):
    """Načte detaily zápasu (kurzy) z podstránky pomocí Selenium."""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    
    service = Service('path_to_chromedriver')  # Nahraď 'path_to_chromedriver' cestou k WebDriveru
    driver = webdriver.Chrome(service=service, options=options)
    driver.get(match_url)

    # Čekání, než se načtou kurzy
    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".BetButtonstyled__BetButton-sc-1tviux5-0"))
    )

    odds = []
    try:
        odds_elements = driver.find_elements(By.CSS_SELECTOR, ".BetButtonstyled__BetButton-sc-1tviux5-0")
        odds = [odd.text for odd in odds_elements]
    except Exception as e:
        print(f"Chyba při načítání kurzů: {e}")

    driver.quit()
    return odds

if __name__ == "__main__":
    base_url = "https://www.tipsport.cz/kurzy/sipky-42"

    # Krok 1: Získat seznam zápasů a jejich odkazy
    matches = get_match_links(base_url)

    # Krok 2: Iterovat přes zápasy a získat detaily
    for match in matches:
        print(f"Zápas: {match['title']}")
        match_url = match['link']
        try:
            odds = scrape_match_details(match_url)
            print(f"Kurzy: {', '.join(odds)}\n")
            time.sleep(1)  # Pauza mezi požadavky
        except Exception as e:
            print(f"Chyba při načítání detailů zápasu: {e}")
