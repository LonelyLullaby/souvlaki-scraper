import time
import random
import re
from playwright.sync_api import sync_playwright, Playwright, expect
from bs4 import BeautifulSoup

# --- OUR SELECTORS (No changes here) ---
WOLT_URL = "https://wolt.com/en/grc/"
COOKIE_ALLOW_BUTTON = 'button:has-text("Allow")'
GOOGLE_POPUP_IFRAME = 'iframe[src*="accounts.google.com/gsi/iframe"]'
GOOGLE_POPUP_CLOSE_BUTTON = 'div[aria-label="Κλείσιμο"]'
ADDRESS_INPUT = 'input[autocomplete="shipping street-address"]'
ADDRESS_SUGGESTION = "div.sac3j8c"
FOOD_SEARCH_INPUT = 'input[data-test-id="SearchInput"]'
FOOD_SEARCH_BUTTON = "a.sfeyiyl"
SHOP_LINK = 'a[data-test-id^="venueCard"]'

# --- NEW, "SMART" MENU SELECTORS ---
ITEM_CARD = 'div[data-test-id="horizontal-item-card"]'
ITEM_NAME = "h3.tj9ydql"
DEAL_PRICE = "span.dhz2cdy"
REGULAR_PRICE = "span.p1boufgw"

MAX_SHOPS_TO_CHECK = 10

def clean_price(price_text):
    """Turns a messy price string '€ 8,50' into a clean float 8.50."""
    try:
        cleaned = re.sub(r"[^0-9,.]", "", price_text)
        cleaned = cleaned.replace(",", ".")
        return float(cleaned)
    except (ValueError, TypeError):
        return 9999.99

def human_like_pause(min_sec=1.0, max_sec=2.5):
    """Pauses for a random short time to look human."""
    print(f"Pausing for {min_sec}-{max_sec}s...")
    time.sleep(random.uniform(min_sec, max_sec))

def scrape_wolt(my_address, search_term):
    print(f"--- Starting Wolt Engine (v21 - Unbreakable) ---")
    print(f"Address: {my_address}")
    print(f"Food: {search_term}")

    with sync_playwright() as p:
        browser = None
        results = []

        try:
            # --- THIS IS THE FIX ---
            # Tell Playwright to use the system's "chromium" channel
            browser = p.chromium.launch(
                headless=True,
                executable_path="/usr/bin/chromium"
            )

            # --- AND HERE IS THE MISSING PART ---
            context = browser.new_context(
                user_agent="Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()

            # --- PHASE 1: THE "ENTRYWAY" (Pop-up Killer) ---
            print(f"Navigating to {WOLT_URL}...")
            page.goto(WOLT_URL, wait_until="domcontentloaded", timeout=30000)
            human_like_pause(2.0, 4.0)

            print("Clicking cookie 'Allow' button...")
            page.wait_for_selector(COOKIE_ALLOW_BUTTON, state="visible", timeout=15000)
            page.locator(COOKIE_ALLOW_BUTTON).first.click()
            print("Cookie banner dismissed.")
            human_like_pause(2.0, 3.0)

            print("Looking for Google Sign-in iframe (waiting up to 15s)...")
            try:
                page.wait_for_selector(GOOGLE_POPUP_IFRAME, state="visible", timeout=15000)
                print("Google iframe found. Reaching into it...")
                frame_locator = page.frame_locator(GOOGLE_POPUP_IFRAME)
                close_button = frame_locator.locator(GOOGLE_POPUP_CLOSE_BUTTON)
                print("Clicking 'Close' button inside iframe (patiently)...")
                close_button.click(timeout=5000)
                print("Google pop-up closed.")
                human_like_pause(1.0, 2.0)
            except Exception as e:
                print(f"No Google pop-up found (or error closing it). Continuing...")

            print("Pop-ups handled. Looking for main address bar...")
            page.wait_for_selector(ADDRESS_INPUT, timeout=15000)
            print("Main address bar found!")

            print(f"Typing address: {my_address}")
            page.locator(ADDRESS_INPUT).fill(my_address)
            human_like_pause()

            print("Clicking address suggestion...")
            page.locator(ADDRESS_SUGGESTION).first.click()
            print("Address set successfully.")

            page.wait_for_selector(FOOD_SEARCH_INPUT, timeout=15000)
            human_like_pause(2.0, 3.0)

            # --- PHASE 2: SEARCH FOR FOOD ---
            print(f"Typing search term: {search_term}")
            page.locator(FOOD_SEARCH_INPUT).fill(search_term)
            human_like_pause()

            print("Clicking search button...")
            page.locator(FOOD_SEARCH_BUTTON).first.click()
            print("Search submitted.")

            page.wait_for_selector(SHOP_LINK, timeout=15000)
            human_like_pause(2.0, 4.0)

            # --- PHASE 3: SCRAPE SHOP LINKS FROM RESULTS PAGE ---
            print("Finding shop links on results page...")
            page_content = page.content()
            soup = BeautifulSoup(page_content, "html.parser")

            shop_links_elements = soup.select(SHOP_LINK)
            shop_urls = []
            for link in shop_links_elements:
                href = link.get('href')
                if href and 'restaurant' in href:
                    full_url = "https://wolt.com" + href
                    if full_url not in shop_urls:
                        shop_urls.append(full_url)

            shop_urls = shop_urls[:MAX_SHOPS_TO_CHECK]
            print(f"Found {len(shop_urls)} shop menus to check.")

            # --- PHASE 4: LOOP MENUS AND SCRAPE ALL ITEMS ---
            for url in shop_urls:
                print(f"\n--- Scraping Menu: {url} ---")
                page.goto(url, wait_until="domcontentloaded", timeout=20000)

                try:
                    # Wait for the *first card* to appear
                    page.wait_for_selector(ITEM_CARD, timeout=10000)
                    human_like_pause(1.5, 2.5)

                    menu_content = page.content()
                    menu_soup = BeautifulSoup(menu_content, "html.parser")

                    shop_name = page.title().split(" – ")[0]
                    print(f"Shop: {shop_name}")

                    # --- NEW "SMART" LOGIC ---
                    item_cards = menu_soup.select(ITEM_CARD)
                    print(f"Found {len(item_cards)} item cards. Scraping...")

                    for card in item_cards:
                        name_element = card.select_one(ITEM_NAME)
                        item_name = name_element.get_text(strip=True) if name_element else "Name Not Found"

                        price_text = ""
                        deal_price_element = card.select_one(DEAL_PRICE)
                        if deal_price_element:
                            price_text = deal_price_element.get_text(strip=True)
                        else:
                            regular_price_element = card.select_one(REGULAR_PRICE)
                            if regular_price_element:
                                price_text = regular_price_element.get_text(strip=True)

                        if not price_text:
                            continue

                        item_price = clean_price(price_text)

                        results.append((shop_name, url, item_name, item_price))

                    print(f"Successfully scraped {len(item_cards)} items.")

                except Exception as e:
                    print(f"Could not scrape menu {url}. Error: {e}")

                human_like_pause(2.0, 4.0)

        except Exception as e:
            print("\nAn error occurred:")
            print(f"Error details: {e}")
            if 'page' in locals():
                page.screenshot(path="error_screenshot_wolt.png")

        finally:
            print("\nScript finished. Closing browser.")
            if browser:
                browser.close()

        print(f"\n--- Engine finished. Returning {len(results)} items. ---")
        return results

# --- TEST BLOCK (No changes here) ---
if __name__ == "__main__":
    print("--- RUNNING ENGINE IN TEST MODE ---")

    test_address = input("Please enter your address (e.g., Τρίπολη): ")
    test_food = input("What do you want to eat? (e.g., Σουβλάκι): ")

    scraped_results = scrape_wolt(test_address, test_food)

    print("\n\n==========================================")
    print(f"     TEST REPORT FOR '{test_food.upper()}' VENDORS     ")
    print(f"         (All items, cheapest first)          ")
    print("==========================================")

    if not scraped_results:
        print("No items were found at any shop.")
    else:
        scraped_results.sort(key=lambda x: x[3])

        for shop, shop_url, item, price in scraped_results:
            print(f"€{price:<6.2f} --- {item} --- (at {shop})")
