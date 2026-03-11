# automated_scraper.py

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup
import csv
import time
import re
from datetime import datetime, timedelta
import os
import pandas as pd

###############
# Configuration
###############
BASE_URL = "https://www.zameen.com/Flats_Apartments/Karachi-2-{}.html"
HEADLESS = True
VISIT_AGENCY_PROFILES = True
SINGLE_LISTING_MODE = False
MAX_PAGES = 15   

DAILY_CSV = "zameen_karachi_flats_today.csv"
WEEKLY_CSV = "zameen_karachi_flats_last_7_days.csv"

#####################
# Selenium Setup
#####################
options = Options()

options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--disable-extensions")
options.add_argument("--disable-infobars")
options.page_load_strategy = "eager"

# Block heavy resources
prefs = {
    "profile.managed_default_content_settings.images": 2,
    "profile.managed_default_content_settings.stylesheets": 2,
    "profile.managed_default_content_settings.fonts": 2
}
options.add_experimental_option("prefs", prefs)

options.add_argument(
    "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
)

driver = webdriver.Chrome(
    service=Service("/usr/bin/chromedriver"),
    options=options
)

driver.set_page_load_timeout(20)

#####################
# Retry / Timeout Logic
#####################
MAX_RETRIES = 3
RETRY_DELAY = 2   


def load_url_with_retry(driver, url, retries=MAX_RETRIES, delay=RETRY_DELAY):

    for attempt in range(1, retries + 1):
        try:
            driver.get(url)
            return True

        except TimeoutException:

            print(f"  ⚠ Timeout on attempt {attempt}/{retries} for: {url}")

            try:
                driver.execute_script("window.stop();")
            except:
                pass

            if attempt < retries:
                print(f"  ↻ Retrying in {delay}s...")
                time.sleep(delay)
            else:
                print(f"  ✗ All retries failed. Skipping.")
                return False

        except WebDriverException as e:

            print(f"  ⚠ WebDriverException: {e}")

            if attempt < retries:
                time.sleep(delay)
            else:
                return False

    return False


#####################
# Helper Functions
#####################
def price_to_number(price_text):

    if not price_text:
        return None

    price_text = price_text.replace(",", "").strip()

    match = re.match(r"([\d.]+)\s*(Crore|Lakh)", price_text, re.I)

    if match:

        num, unit = match.groups()
        num = float(num)

        if unit.lower() == "crore":
            return int(num * 10_000_000)

        elif unit.lower() == "lakh":
            return int(num * 100_000)

    try:
        return int(price_text)
    except:
        return None


def safe_text(element):
    return element.text.strip() if element else None


def is_posted_today(posted_date_text):

    if not posted_date_text:
        return False

    posted_date_text = posted_date_text.lower()

    if "minute" in posted_date_text or "hour" in posted_date_text or "today" in posted_date_text:
        return True

    elif "yesterday" in posted_date_text:
        return False

    try:

        dt = pd.to_datetime(posted_date_text, errors='coerce')

        if pd.isna(dt):
            return False

        return dt.date() == datetime.now().date()

    except:
        return False


#####################
# Scraping Logic
#####################

all_listings_today = []
page = 1

while page <= MAX_PAGES:

    url = BASE_URL.format(page)

    print(f"\nScraping page {page}/{MAX_PAGES} → {url}")

    if not load_url_with_retry(driver, url):
        break

    time.sleep(2)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    listings = soup.find_all("article")

    if not listings:
        print("No listings found.")
        break

    todays_listing_found = False

    for listing in listings:

        link_tag = listing.find("a", href=True)

        if not link_tag:
            continue

        link = "https://www.zameen.com" + link_tag["href"]

        if "/new-projects/" in link:
            continue

        if not load_url_with_retry(driver, link):
            continue

        time.sleep(1)

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

        detail_soup = BeautifulSoup(driver.page_source, "html.parser")

        posted_date_tag = detail_soup.find("span", {"aria-label": "Creation date"})
        posted_date = posted_date_tag.get_text(strip=True) if posted_date_tag else None

        if not is_posted_today(posted_date):
            continue

        todays_listing_found = True

        title = safe_text(detail_soup.find("h1"))

        price = price_to_number(
            detail_soup.select_one("span[aria-label='Price']").get_text(strip=True)
            if detail_soup.select_one("span[aria-label='Price']")
            else None
        )

        location = safe_text(detail_soup.find("span", {"aria-label": "Location"}))

        all_listings_today.append({
            "title": title,
            "price": price,
            "link": link,
            "posted_date": posted_date,
            "location": location
        })

        print(f"  ✓ Scraped: {title} | {location}")

        time.sleep(1)

        if SINGLE_LISTING_MODE:
            break

    if not todays_listing_found:
        print("No listings posted today. Stopping.")
        break

    page += 1

    time.sleep(2)  


print(f"\nTotal listings scraped today: {len(all_listings_today)}")


#################
# Save daily CSV
#################

fieldnames = ["title", "price", "link", "posted_date", "location"]

with open(DAILY_CSV, "w", newline="", encoding="utf-8") as f:

    writer = csv.DictWriter(f, fieldnames=fieldnames)

    writer.writeheader()
    writer.writerows(all_listings_today)


print(f"Saved to {DAILY_CSV}")

driver.quit()
