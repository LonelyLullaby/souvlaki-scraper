import time
import random
import re
from playwright.sync_api import sync_playwright, Playwright, expect
from bs4 import BeautifulSoup

# --- 1. CONFIGURATION: GET USER INPUT ---

MY_ADDRESS = input("Please enter your address (e.g., Τρίπολη): ")
SEARCH_TERM = input("What do you want to eat? (e.g., Σουβλάκι): ")
MAX_SHOPS_TO_CHECK = 10

# --- 2. OUR MASTER RECON LIST (THE SELECTORS) ---
WOLT_URL = "https://wolt.com/en/grc/"

# Phase 1: Entryway (Pop-ups + Address)
COOKIE_ALLOW_BUTTON = 'button:has-text("Allow")'
GOOGLE_POPUP_IFRAME = 'iframe[src*="accounts.google.com/gsi/iframe"]'
GOOGLE_POPUP_CLOSE_BUTTON = 'div[aria-label="Κλείσιμο"]'
ADDRESS_INPUT = 'input[autocomplete="shipping street-address"]'
ADDRESS_SUGGESTION = "div.sac3j8c"

# Phase 2: Main Search
FOOD_SEARCH_INPUT = 'input[data-test-id="SearchInput"]'
FOOD_SEARCH_BUTTON = "a.sfeyiyl"

# Phase 3: Shop Results
SHOP_LINK = 'a[data-test-id^="venueCard"]'

# Phase 4: Menu
ITEM_NAME = "h3.tj9ydql"
ITEM_PRICE = "span.p1boufgw"


def clean_price(price_text):
    """Turns a messy price string '€ 8,50' into a clean float 8.50."""
    try:
        cleaned = re.sub(r"[€$\s]", "", price_text)
        cleaned = cleaned.replace(",", ".")
        return float(cleaned)
    except (ValueError, TypeError):
        return 9999.99

def human_like_pause(min_sec=1.0, max_sec=2.5):
    """Pauses for a random short time to look human."""
    print(f"Pausing for {min_sec}-{max_sec}s...")
    time.sleep(random.uniform(min_sec, max_sec))

def main():
    print("--- Starting Souvlaki Price Finder (Wolt v19 - Indiscriminate) ---")
    print(f"Address: {MY_ADDRESS}")
    print(f"Food: {SEARCH_TERM}")

    with sync_playwright() as p:
        browser = None
        # This list will hold ALL items from ALL shops
        results = []

        try:
            browser = p.firefox.launch(headless=False)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()

            # --- PHASE 1: THE "ENTRYWAY" (Pop-up Killer) ---
            print(f"Navigating to {WOLT_URL}...")
            page.goto(WOLT_URL, wait_until="domcontentloaded", timeout=30000)
            human_like_pause(2.0, 4.0)

            # --- STEP 1: CLICK COOKIE BUTTON ---
            print("Clicking cookie 'Allow' button...")
            page.wait_for_selector(COOKIE_ALLOW_BUTTON, state="visible", timeout=15000)
            page.locator(COOKIE_ALLOW_BUTTON).first.click()
            print("Cookie banner dismissed.")
            human_like_pause(2.0, 3.0)

            # --- STEP 2: CLOSE GOOGLE SIGN-IN IFRAME ---
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

            # --- STEP 3: INTERACT WITH ADDRESS ---
            print("Pop-ups handled. Looking for main address bar...")
            page.wait_for_selector(ADDRESS_INPUT, timeout=15000)
            print("Main address bar found!")

            print(f"Typing address: {MY_ADDRESS}")
            page.locator(ADDRESS_INPUT).fill(MY_ADDRESS)
            human_like_pause()

            print("Clicking address suggestion...")
            page.locator(ADDRESS_SUGGESTION).first.click()
            print("Address set successfully.")

            page.wait_for_selector(FOOD_SEARCH_INPUT, timeout=15000)
            human_like_pause(2.0, 3.0)

            # --- PHASE 2: SEARCH FOR FOOD ---
            print(f"Typing search term: {SEARCH_TERM}")
            page.locator(FOOD_SEARCH_INPUT).fill(SEARCH_TERM)
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
                    page.wait_for_selector(ITEM_NAME, timeout=10000)
                    human_like_pause(1.5, 2.5)

                    menu_content = page.content()
                    menu_soup = BeautifulSoup(menu_content, "html.parser")

                    shop_name = page.title().split(" – ")[0]
                    print(f"Shop: {shop_name}")

                    item_names = menu_soup.select(ITEM_NAME)
                    item_prices = menu_soup.select(ITEM_PRICE)

                    # --- MODIFIED: "INDISCRIMINATE" LOGIC ---
                    print(f"Scraping all {len(item_names)} items from this menu...")

                    for name, price in zip(item_names, item_prices):
                        current_name = name.get_text(strip=True)
                        current_price_text = price.get_text(strip=True)
                        current_price = clean_price(current_price_text)

                        # We no longer filter. We add EVERY item.
                        results.append((shop_name, current_name, current_price))

                    print(f"Successfully scraped {len(item_names)} items.")

                except Exception as e:
                    print(f"Could not scrape menu {url}. Error: {e}")

                human_like_pause(2.0, 4.0)

            # --- FINAL REPORT ---
            print("\n\n==========================================")
            print(f"     FULL REPORT FOR '{SEARCH_TERM.upper()}' VENDORS     ")
            print(f"         (All items, cheapest first)          ")
            print("==========================================")

            if not results:
                print("No items were found at any shop.")
            else:
                # Sort the main results list by price
                results.sort(key=lambda x: x[2])

                for shop, item, price in results:
                    print(f"€{price:<6.2f} --- {item} --- (at {shop})")

        except Exception as e:
            print("\nAn error occurred:")
            print(f"Error details: {e}")
            print("Saving screenshot...")
            if 'page' in locals():
                page.screenshot(path="error_screenshot_wolt.png")

        finally:
            print("\nScript finished. Closing browser.")
            if browser:
                browser.close()

if __name__ == "__main__":
    main()
