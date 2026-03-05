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
MAX_PAGES = 10

DAILY_CSV = "zameen_karachi_flats_today.csv"
WEEKLY_CSV = "zameen_karachi_flats_last_7_days.csv"

#####################
# Selenium Setup
#####################
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
options.add_argument("--disable-blink-features=AutomationControlled")

# Use system chromedriver installed by the workflow
driver = webdriver.Chrome(
    service=Service("/usr/bin/chromedriver"),
    options=options
)
driver.set_page_load_timeout(30)

#####################
# Retry / Timeout Logic
#####################
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds to wait between retries

def load_url_with_retry(driver, url, retries=MAX_RETRIES, delay=RETRY_DELAY):
    """
    Attempts to load a URL up to `retries` times.
    On TimeoutException, executes document.stop() to halt the load and
    work with whatever content has already arrived, then retries if needed.
    Returns True if the page loaded successfully (or partially), False if all retries fail.
    """
    for attempt in range(1, retries + 1):
        try:
            driver.get(url)
            return True
        except TimeoutException:
            print(f"  ⚠ Timeout on attempt {attempt}/{retries} for: {url}")
            try:
                driver.execute_script("window.stop();")  # stop further loading
            except Exception:
                pass
            if attempt < retries:
                print(f"  ↻ Retrying in {delay}s...")
                time.sleep(delay)
            else:
                print(f"  ✗ All {retries} attempts timed out. Skipping: {url}")
                return False
        except WebDriverException as e:
            print(f"  ⚠ WebDriverException on attempt {attempt}/{retries}: {e}")
            if attempt < retries:
                print(f"  ↻ Retrying in {delay}s...")
                time.sleep(delay)
            else:
                print(f"  ✗ All {retries} attempts failed. Skipping: {url}")
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

def extract_phone_number(driver):
    try:
        page_source = driver.page_source
        patterns = [
            r'\+92[\s-]?(\d{3})[\s-]?(\d{7})',
            r'0(\d{3})[\s-]?(\d{7})',
            r'(\d{4})[\s-]?(\d{7})'
        ]
        for pattern in patterns:
            matches = re.findall(pattern, page_source)
            if matches:
                phone = ''.join(matches[0])
                if phone.startswith('0'):
                    phone = '+92' + phone[1:]
                elif not phone.startswith('+92'):
                    phone = '+92' + phone
                return phone
        return None
    except:
        return None

def extract_email(driver):
    try:
        page_source = driver.page_source
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, page_source)
        valid = [e for e in emails if not any(x in e.lower() for x in ['example.com', 'test.com'])]
        return valid[0] if valid else None
    except:
        return None

def get_agency_profile_data(driver, agency_url):
    if not agency_url:
        return {}
    try:
        if not load_url_with_retry(driver, agency_url):
            return {}
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        data = {}

        total_agent_listings = None
        try:
            count_divs = soup.find_all("div", class_="fw-700 u-mb4")
            sale_count = rent_count = 0
            for div in count_divs:
                span = div.find("span")
                if span and span.text.strip().isdigit():
                    count = int(span.text.strip())
                    parent_text = div.get_text()
                    if "Sale" in parent_text:
                        sale_count = count
                    elif "Rent" in parent_text:
                        rent_count = count
            if sale_count or rent_count:
                total_agent_listings = str(sale_count + rent_count)
        except:
            total_agent_listings = None

        if total_agent_listings:
            data['total_agent_listings'] = total_agent_listings
        phone = extract_phone_number(driver)
        if phone:
            data['phone_number'] = phone
        email = extract_email(driver)
        if email:
            data['email'] = email
        return data
    except:
        return {}

#####################
# Scraping Logic
#####################
all_listings_today = []
page = 1

while page <= MAX_PAGES:
    url = BASE_URL.format(page)
    print(f"\nScraping page {page}/{MAX_PAGES} → {url}")

    if not load_url_with_retry(driver, url):
        print(f"Failed to load page {page} after all retries. Stopping.")
        break

    time.sleep(3)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    listings = soup.find_all("article")
    if not listings:
        print("No listings found on this page. Stopping.")
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
            print(f"Failed to load listing after all retries. Skipping.")
            continue

        time.sleep(2)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

        detail_soup = BeautifulSoup(driver.page_source, "html.parser")
        posted_date_tag = detail_soup.find("span", {"aria-label": "Creation date"})
        posted_date = posted_date_tag.get_text(strip=True) if posted_date_tag else None

        if not is_posted_today(posted_date):
            continue
        todays_listing_found = True

        title = safe_text(detail_soup.find("h1"))
        price = price_to_number(detail_soup.select_one("span[aria-label='Price']").get_text(strip=True)
                                if detail_soup.select_one("span[aria-label='Price']") else None)
        bedrooms = safe_text(detail_soup.find("span", {"aria-label": "Beds"}))
        bathrooms = safe_text(detail_soup.find("span", {"aria-label": "Baths"}))
        area_sqft = safe_text(detail_soup.select_one('span[aria-label="Area"] span'))
        description = safe_text(detail_soup.find("div", {"aria-label": "Property description"}))
        location = safe_text(detail_soup.find("span", {"aria-label": "Location"}))
        property_id = None
        contact_message = detail_soup.find("textarea", {"id": "contactFormMessage"})
        if contact_message:
            match = re.search(r'ID(\d+)', contact_message.get_text(strip=True))
            if match:
                property_id = match.group(1)
        agent_name = safe_text(detail_soup.find("span", class_="d10ba6ac"))
        agency_name = safe_text(detail_soup.find("div", class_="_0a8efec2"))
        agency_url = None
        agency_profile_link = detail_soup.find("a", href=re.compile(r'/Profile/'))
        if agency_profile_link:
            agency_url = "https://www.zameen.com" + agency_profile_link.get('href')
        verified_agency = None
        badge_tag = detail_soup.find("span", class_="fw-700")
        if badge_tag:
            verified_agency = badge_tag.get_text(strip=True)
        elif detail_soup.find(string=re.compile(r'Verified|Trusted|Certified', re.I)):
            verified_agency = "Verified"

        phone_number = extract_phone_number(driver)
        email = extract_email(driver)

        if VISIT_AGENCY_PROFILES and agency_url:
            agency_data = get_agency_profile_data(driver, agency_url)
            total_agent_listings = agency_data.get('total_agent_listings', None)
            if agency_data.get('phone_number') and not phone_number:
                phone_number = agency_data['phone_number']
            if agency_data.get('email') and not email:
                email = agency_data['email']
            if not load_url_with_retry(driver, link):
                pass
            time.sleep(1)
        else:
            total_agent_listings = None

        all_listings_today.append({
            "title": title,
            "price": price,
            "link": link,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "area_sqft": area_sqft,
            "description": description,
            "posted_date": posted_date,
            "location": location,
            "property_id": property_id,
            "agent_name": agent_name,
            "agency_name": agency_name,
            "agency_url": agency_url,
            "verified_agency": verified_agency,
            "total_agent_listings": total_agent_listings,
            "phone_number": phone_number,
            "email": email
        })

        print(f"  ✓ Scraped: {title} | {location}")

        if SINGLE_LISTING_MODE:
            print("⚡ SINGLE LISTING MODE: Stopping after 1 listing")
            break

    if SINGLE_LISTING_MODE and all_listings_today:
        break

    if not todays_listing_found:
        print("No listings posted today on this page. Stopping.")
        break

    page += 1

print(f"\nTotal listings scraped today: {len(all_listings_today)}")

#################
# Save daily CSV
#################
fieldnames = ["title", "price", "link", "bedrooms", "bathrooms", "area_sqft",
              "description", "posted_date", "location", "property_id",
              "agent_name", "agency_name", "agency_url", "verified_agency",
              "total_agent_listings", "phone_number", "email"]

with open(DAILY_CSV, "w", newline="", encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(all_listings_today)

print(f"Saved to {DAILY_CSV}")

#################
# Update weekly CSV
#################
weekly_listings = []
if os.path.exists(WEEKLY_CSV):
    df_week = pd.read_csv(WEEKLY_CSV)
    df_week['posted_date_parsed'] = pd.to_datetime(df_week['posted_date'], errors='coerce')
    cutoff = datetime.now() - timedelta(days=7)
    weekly_listings = df_week[df_week['posted_date_parsed'] >= cutoff].to_dict('records')

existing_ids = {l['property_id'] for l in weekly_listings if l.get('property_id')}
for l in all_listings_today:
    if l['property_id'] not in existing_ids:
        weekly_listings.append(l)

df_weekly = pd.DataFrame(weekly_listings)
df_weekly.to_csv(WEEKLY_CSV, index=False, encoding='utf-8')
print(f"Weekly CSV updated: {WEEKLY_CSV} ({len(df_weekly)} listings)")

driver.quit()
