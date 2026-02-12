from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import csv
import time
import re

###############
# Configuration
###############
BASE_URL = "https://www.zameen.com/Flats_Apartments/Karachi-2-{}.html"
MAX_PAGES = 20  
HEADLESS = True

# TESTING MODE: Set to True to scrape only 1 listing and quit (for testing)
SINGLE_LISTING_MODE = True

# ENHANCED MODE: Visit agency profile pages for better contact data (slower but more complete)
VISIT_AGENCY_PROFILES = True

##################
# Helper functions
##################
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

def extract_phone_number(driver, wait):
    try:
        try:
            close_buttons = driver.find_elements(By.XPATH, 
                "//button[contains(@aria-label, 'close') or contains(@class, 'close')]"
            )
            for btn in close_buttons[:2]:
                try:
                    btn.click()
                    time.sleep(0.3)
                except:
                    pass
        except:
            pass
        
        call_button = None
        try:
            call_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Call')]")
        except:
            pass
        if not call_button:
            try:
                call_button = driver.find_element(By.XPATH, "//a[contains(text(), 'Call')]")
            except:
                pass
        
        if call_button:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", call_button)
            time.sleep(0.5)
            try:
                call_button.click()
            except:
                driver.execute_script("arguments[0].click();", call_button)
            time.sleep(2)
            
            page_source = driver.page_source
            phone_patterns = [
                r'\+92[\s-]?(\d{3})[\s-]?(\d{7})',
                r'0(\d{3})[\s-]?(\d{7})',
                r'(\d{4})[\s-]?(\d{7})',
            ]
            for pattern in phone_patterns:
                matches = re.findall(pattern, page_source)
                if matches:
                    phone = ''.join(matches[0])
                    if phone.startswith('0'):
                        phone = '+92' + phone[1:]
                    elif not phone.startswith('+92'):
                        phone = '+92' + phone
                    return phone
        return None
    except Exception as e:
        print(f"      Error extracting phone: {e}")
        return None

def extract_email(driver):
    
    try:
        page_source = driver.page_source
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, page_source)
        valid_emails = [
            e for e in emails
            if not any(x in e.lower() for x in ['example.com', 'test.com', 'schema.org', 'sentry.io', 'w3.org'])
        ]
        return valid_emails[0] if valid_emails else None
    except Exception as e:
        print(f"      Error extracting email: {e}")
        return None

def get_agency_profile_data(driver, wait, agency_url):
    
    if not agency_url:
        return {}

    try:
        print(f"      Visiting agency profile: {agency_url}")
        driver.get(agency_url)
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        data = {}

        ######################
        # TOTAL AGENT LISTINGS
        ######################
        total_agent_listings = None
        try:
            # Look for divs with class "fw-700 u-mb4" which contain the listing counts
            count_divs = soup.find_all("div", class_="fw-700 u-mb4")
            sale_count = 0
            rent_count = 0
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

        ##############
        # PHONE NUMBER
        ##############
        phone = extract_phone_number(driver, wait)
        if phone:
            data['phone_number'] = phone

        #######
        # EMAIL 
        #######
        email = extract_email(driver)
        if email:
            data['email'] = email

        return data

    except Exception as e:
        print(f"      Error visiting agency profile: {e}")
        return {}

#####################
# Initialize Selenium
#####################
options = Options()
if HEADLESS:
    options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
options.add_argument("--disable-blink-features=AutomationControlled")

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 10)

all_listings = []

if SINGLE_LISTING_MODE:
    print("\n" + "="*60)
    print("⚡ SINGLE LISTING MODE ENABLED")
    print("Script will scrape only 1 complete listing and exit")
    print("="*60 + "\n")

##############
# Scrape pages
##############
for page in range(1, MAX_PAGES + 1):
    url = BASE_URL.format(page)
    print(f"\nScraping page {page} → {url}")
    driver.get(url)
    time.sleep(3)

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
        if "/new-projects/" in link:
            continue

        title_tag = listing.find("h2")
        title = safe_text(title_tag)

        price_tag = listing.select_one("span[aria-label='Price']")
        price = price_to_number(price_tag.get_text(strip=True) if price_tag else None)

        driver.get(link)
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        detail_soup = BeautifulSoup(driver.page_source, "html.parser")

        desc_tag = detail_soup.find("div", {"aria-label": "Property description"})
        description = desc_tag.get_text(strip=True) if desc_tag else None
        bed_tag = detail_soup.find("span", {"aria-label": "Beds"})
        bedrooms = bed_tag.get_text(strip=True) if bed_tag else None
        bath_tag = detail_soup.find("span", {"aria-label": "Baths"})
        bathrooms = bath_tag.get_text(strip=True) if bath_tag else None
        area_tag = detail_soup.select_one('span[aria-label="Area"] span')
        area = area_tag.get_text(strip=True) if area_tag else None
        posted_date_tag = detail_soup.find("span", {"aria-label": "Creation date"})
        posted_date = posted_date_tag.get_text(strip=True) if posted_date_tag else None
        location_tag = detail_soup.find("span", {"aria-label": "Location"})
        location = location_tag.get_text(strip=True) if location_tag else None
        property_id = None
        contact_message = detail_soup.find("textarea", {"id": "contactFormMessage"})
        if contact_message:
            message_text = contact_message.get_text(strip=True)
            id_match = re.search(r'ID(\d+)', message_text)
            property_id = id_match.group(1) if id_match else None
        agent_name_tag = detail_soup.find("span", class_="d10ba6ac")
        agent_name = agent_name_tag.get_text(strip=True) if agent_name_tag else None
        agency_name_tag = detail_soup.find("div", class_="_0a8efec2")
        agency_name = agency_name_tag.get_text(strip=True) if agency_name_tag else None
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
        total_agent_listings = None

        print(f"  Extracting contacts for: {title[:50]}...")

        phone_number = extract_phone_number(driver, wait)
        email = extract_email(driver)

        # Enhanced agency data
        if VISIT_AGENCY_PROFILES and agency_url:
            agency_data = get_agency_profile_data(driver, wait, agency_url)
            if agency_data.get('total_agent_listings'):
                total_agent_listings = agency_data['total_agent_listings']
            if agency_data.get('phone_number') and not phone_number:
                phone_number = agency_data['phone_number']
            if agency_data.get('email') and not email:
                email = agency_data['email']
            driver.get(link)
            time.sleep(1)

        all_listings.append({
            "title": title,
            "price": price,
            "link": link,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "area": area,
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
        print(f"Scraped: {title} | Area: {area}")
        print(f"  Agent: {agent_name} | Agency: {agency_name}")
        print(f"  Location: {location}")
        print(f"  Phone: {phone_number or 'N/A'} | Email: {email or 'N/A'}")

        if SINGLE_LISTING_MODE:
            print(f"\n⚡ SINGLE LISTING MODE: Stopping after 1 complete listing")
            break

    if SINGLE_LISTING_MODE and len(all_listings) > 0:
        break

#############
# Save to CSV
#############
fieldnames = ["title", "price", "link", "bedrooms", "bathrooms", "area", "description", 
              "posted_date", "location", "property_id", "agent_name", "agency_name",
              "agency_url", "verified_agency", "total_agent_listings",
              "phone_number", "email"]

with open("zameen_karachi_flats_full.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(all_listings)

print(f"\nTotal listings scraped: {len(all_listings)}")
print("Data saved to zameen_karachi_flats_full.csv")

with_phone = sum(1 for l in all_listings if l.get('phone_number'))
with_email = sum(1 for l in all_listings if l.get('email'))
print(f"\nContact Extraction Success:")
print(f"  Phone numbers: {with_phone}/{len(all_listings)} ({with_phone/len(all_listings)*100:.1f}%)")
print(f"  Emails: {with_email}/{len(all_listings)} ({with_email/len(all_listings)*100:.1f}%)")

driver.quit()
