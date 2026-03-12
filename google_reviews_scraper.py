from playwright.sync_api import sync_playwright
import pandas as pd

from sqlalchemy import create_engine, text
import os


# ---------------------------------------------------
# ETHIOPIAN DISH KEYWORDS
# ---------------------------------------------------

dish_keywords = [
    "doro wat",
    "injera",
    "kitfo",
    "tibs",
    "shiro",
    "lentil",
    "vegetarian combo",
]


# ---------------------------------------------------
# CALCULATE DISH DEMAND
# ---------------------------------------------------

def calculate_demand(reviews):

    score = 0

    for review in reviews:

        text = review.lower()

        for dish in dish_keywords:

            if dish in text:
                score += 1

    return score


# ---------------------------------------------------
# EXTRACT DISH MENTIONS
# ---------------------------------------------------

def extract_dishes(reviews):

    dish_count = {}

    for review in reviews:

        text = review.lower()

        for dish in dish_keywords:

            if dish in text:

                dish_count[dish] = dish_count.get(dish, 0) + 1

    dish_df = pd.DataFrame(
        [{"dish": k, "mentions": v} for k, v in dish_count.items()]
    )

    return dish_df


# ---------------------------------------------------
# GOOGLE MAPS SCRAPER
# ---------------------------------------------------

def scrape_google_reviews():

    restaurants_data = []
    all_reviews = []

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)

        page = browser.new_page()

        page.goto(
            "https://www.google.com/maps/search/ethiopian+restaurant+new+york/"
        )

        page.wait_for_timeout(5000)

        cards = page.locator("div.Nv2PK")

        count = min(cards.count(), 5)

        for i in range(count):

            card = cards.nth(i)

            try:

                name = card.locator("div.qBF1Pd").inner_text()

                rating = card.locator("span.MW4etd").inner_text()

                link = card.locator("a.hfpxzc").get_attribute("href")

                lat = None
                lon = None

                if link and "@" in link:

                    coords = link.split("@")[1].split(",")

                    lat = float(coords[0])
                    lon = float(coords[1])

                # open restaurant page
                card.click()

                page.wait_for_timeout(3000)

                reviews = []

                review_elements = page.locator("span.wiI7pd")

                for j in range(min(review_elements.count(), 20)):

                    reviews.append(
                        review_elements.nth(j).inner_text()
                    )

                demand_score = calculate_demand(reviews)

                # ---------------------------------------------------
                # FIXED INDENTATION + SAFE LAT/LON
                # ---------------------------------------------------

                if lat is not None and lon is not None:

                    restaurants_data.append(
                        {
                            "Restaurant": name,
                            "Rating": float(rating),
                            "lat": lat,
                            "lon": lon,
                            "demand": demand_score,
                        }
                    )

                all_reviews.extend(reviews)

            except Exception as e:

                print("Error scraping restaurant:", e)

        browser.close()

    # ---------------------------------------------------
    # CREATE DATAFRAMES
    # ---------------------------------------------------

    restaurants_df = pd.DataFrame(restaurants_data)

    if not restaurants_df.empty:

        restaurants_df = restaurants_df.dropna(
            subset=["lat", "lon"]
        )

    dishes_df = extract_dishes(all_reviews)

    return {
        "restaurants": restaurants_df,
        "dishes": dishes_df,
    }
    
    DATABASE_URL = os.getenv("DATABASE_URL")
    engine = create_engine(DATABASE_URL)

    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable not set")

def save_competitor_data(restaurants_df, dishes_df):

    with engine.begin() as conn:

        conn.execute(text("DELETE FROM competitors"))
        conn.execute(text("DELETE FROM competitor_dishes"))

        for _, row in restaurants_df.iterrows():

            conn.execute(text("""
            INSERT INTO competitors
            (restaurant_name, rating, lat, lon, demand_score)
            VALUES
            (:name, :rating, :lat, :lon, :demand)
            """), {
                "name": row["Restaurant"],
                "rating": row["Rating"],
                "lat": row["lat"],
                "lon": row["lon"],
                "demand": row["demand"]
            })

        for _, row in dishes_df.iterrows():

            conn.execute(text("""
            INSERT INTO competitor_dishes
            (dish, mentions)
            VALUES
            (:dish, :mentions)
            """), {
                "dish": row["dish"],
                "mentions": row["mentions"]
            })

data = scrape_google_reviews()

save_competitor_data(
    data["restaurants"],
    data["dishes"]
)
