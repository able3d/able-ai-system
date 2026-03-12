from playwright.sync_api import sync_playwright
import pandas as pd

# Ethiopian dish keywords
dish_keywords = [
    "doro wat",
    "injera",
    "kitfo",
    "tibs",
    "shiro",
    "lentil",
    "vegetarian combo",
]

def calculate_demand(reviews):

    score = 0

    for review in reviews:
        text = review.lower()

        for dish in dish_keywords:
            if dish in text:
                score += 1

    return score


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

        count = min(cards.count(), 10)

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

                card.click()

                page.wait_for_timeout(3000)

                reviews = []

                review_elements = page.locator("span.wiI7pd")

                for j in range(min(review_elements.count(), 20)):

                    reviews.append(review_elements.nth(j).inner_text())

                demand_score = calculate_demand(reviews)

                if lat and lon:
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

            except:
                pass

        browser.close()

    restaurants_df = pd.DataFrame(restaurants_data)

    dishes_df = extract_dishes(all_reviews)

    return {
        "restaurants": restaurants_df,
        "dishes": dishes_df,
    }

