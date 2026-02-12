from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import csv
import time
import re

# -----------------------------
# Settings
# -----------------------------
BASE_URL = "https://www.zameen.com/Flats_Apartments/Karachi-2-{}.html"
MAX_PAGES = 1  # adjust as needed
HEADLESS = True

# -----------------------------
# Helper functions
# -----------------------------
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

# -----------------------------
# Initialize Selenium
# -----------------------------
options = Options()
if HEADLESS:
    options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(options=options)

all_listings = []

# -----------------------------
# Scrape pages
# -----------------------------
for page in range(1, MAX_PAGES + 1):
    url = BASE_URL.format(page)
    print(f"\nScraping page {page} → {url}")
    driver.get(url)
    time.sleep(3)  # wait for JS to load

    soup = BeautifulSoup(driver.page_source, "html.parser")
    listings = soup.find_all("article")

    if not listings:
        print("No listings found on page.")
        continue

    for listing in listings:
        link_tag = listing.find("a", href=True)
        if not link_tag:
            continue
        link = "https://www.zameen.com" + link_tag["href"]

        # Skip projects
        if "/new-projects/" in link:
            continue

        title_tag = listing.find("h2")
        title = safe_text(title_tag)

        price_tag = listing.select_one("span[aria-label='Price']")
        price = price_to_number(price_tag.get_text(strip=True) if price_tag else None)

        # -----------------------------
        # Scrape detail page
        # -----------------------------
        driver.get(link)
        time.sleep(2)
        detail_soup = BeautifulSoup(driver.page_source, "html.parser")

        # Description
        desc_tag = detail_soup.find("div", {"aria-label": "Property description"})
        description = desc_tag.get_text(strip=True) if desc_tag else None

        # Bedrooms
        bed_tag = detail_soup.find("span", {"aria-label": "Beds"})
        bedrooms = bed_tag.get_text(strip=True) if bed_tag else None

        # Bathrooms
        bath_tag = detail_soup.find("span", {"aria-label": "Baths"})
        bathrooms = bath_tag.get_text(strip=True) if bath_tag else None

        # Area
        area_tag = detail_soup.select_one('span[aria-label="Area"] span')
        area = area_tag.get_text(strip=True) if area_tag else None

        all_listings.append({
            "title": title,
            "price": price,
            "link": link,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "area": area,
            "description": description
        })
        print(f"Scraped: {title} | Area: {area}")

# -----------------------------
# Save to CSV
# -----------------------------
fieldnames = ["title", "price", "link", "bedrooms", "bathrooms", "area", "description"]

with open("zameen_karachi_flats_full.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(all_listings)

print(f"\nTotal listings scraped: {len(all_listings)}")
print("Data saved to zameen_karachi_flats_full.csv")

driver.quit()
