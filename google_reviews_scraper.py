import pandas as pd
from playwright.sync_api import sync_playwright
import time


# --------------------------------------------------
# DISH KEYWORDS
# --------------------------------------------------

dish_keywords = [
    "doro wat",
    "injera",
    "kitfo",
    "tibs",
    "shiro",
    "lentil",
    "vegetarian combo"
]


# --------------------------------------------------
# DEMAND SCORE
# --------------------------------------------------

def calculate_demand(reviews):

    score = 0

    for review in reviews:

        text = review.lower()

        for dish in dish_keywords:

            if dish in text:
                score += 1

    return score


# --------------------------------------------------
# DISH EXTRACTION
# --------------------------------------------------

def extract_dishes(reviews):

    dish_count = {}

    for review in reviews:

        text = review.lower()

        for dish in dish_keywords:

            if dish in text:

                dish_count[dish] = dish_count.get(dish, 0) + 1

    if not dish_count:
        return pd.DataFrame(columns=["dish", "mentions"])

    return pd.DataFrame(
        [{"dish": k, "mentions": v} for k, v in dish_count.items()]
    )


# --------------------------------------------------
# MAIN SCRAPER
# --------------------------------------------------

def scrape_google_reviews():

    restaurants_data = []
    all_reviews = []

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled"
            ]
        )

        page = browser.new_page()

        print("Opening Google Maps...")

        page.goto(
            "https://www.google.com/maps/search/ethiopian+restaurant+new+york/",
            timeout=60000
        )

        page.wait_for_timeout(5000)

        # --------------------------------------------------
        # Scroll to load restaurants
        # --------------------------------------------------

        for _ in range(3):

            page.mouse.wheel(0, 5000)
            page.wait_for_timeout(2000)

        cards = page.locator("div.Nv2PK")

        count = min(cards.count(), 3)

        print("Restaurants detected:", count)

        for i in range(count):

            try:

                card = cards.nth(i)

                name = card.locator("div.qBF1Pd").inner_text()

                rating = card.locator("span.MW4etd").inner_text()

                link = card.locator("a.hfpxzc").get_attribute("href")

                lat = None
                lon = None

                if link and "@" in link:

                    coords = link.split("@")[1].split(",")

                    lat = float(coords[0])
                    lon = float(coords[1])

                print("Scraping:", name)

                card.click()

                page.wait_for_timeout(4000)

                reviews = []

                review_elements = page.locator("span.wiI7pd")

                review_count = min(review_elements.count(), 15)

                for j in range(review_count):

                    try:

                        text = review_elements.nth(j).inner_text()

                        reviews.append(text)

                    except:
                        pass

                demand_score = calculate_demand(reviews)

                restaurants_data.append({

                    "Restaurant": name,
                    "Rating": float(rating),
                    "lat": lat,
                    "lon": lon,
                    "demand": demand_score

                })

                all_reviews.extend(reviews)

            except Exception as e:

                print("Scrape error:", e)

        browser.close()

    restaurants_df = pd.DataFrame(restaurants_data)

    dishes_df = extract_dishes(all_reviews)

    return {

        "restaurants": restaurants_df,
        "dishes": dishes_df

    }