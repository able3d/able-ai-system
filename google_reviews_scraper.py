from playwright.sync_api import sync_playwright
import pandas as pd
import time

SEARCH_URL = "https://www.google.com/maps/search/ethiopian+restaurant+new+york+city"

MAX_RESTAURANTS = 5

dish_keywords = [
    "injera",
    "doro wat",
    "kitfo",
    "tibs",
    "shiro",
    "misir",
    "vegetarian",
    "coffee"
]


def scrape_google_reviews():

    dish_counter = {dish: 0 for dish in dish_keywords}

    restaurants_data = []

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        print("Opening Google Maps...")
        page.goto(SEARCH_URL)

        page.wait_for_selector('div[role="feed"]')

        results_panel = page.locator('div[role="feed"]')

        # scroll to load restaurants
        for _ in range(6):
            results_panel.evaluate("el => el.scrollBy(0,2000)")
            time.sleep(2)

        restaurants = results_panel.locator("div.Nv2PK")

        total = restaurants.count()

        print("Restaurants found:", total)

        for i in range(min(total, MAX_RESTAURANTS)):

            card = restaurants.nth(i)

            try:
                name = card.locator("a.hfpxzc").get_attribute("aria-label")
                rating = card.locator("span.MW4etd").inner_text()
            except:
                continue

            print("Opening:", name)

            card.click()

            time.sleep(5)

            # open reviews tab
            try:
                page.get_by_role("tab", name="Reviews").click()
                time.sleep(4)
            except:
                print("Reviews tab not found")
                page.go_back()
                time.sleep(3)
                continue

            # scroll reviews
            for _ in range(8):
                page.mouse.wheel(0, 5000)
                time.sleep(2)

            reviews = page.locator("span.wiI7pd").all_inner_texts()

            print("Reviews collected:", len(reviews))

            for review in reviews:

                text = review.lower()

                for dish in dish_keywords:

                    if dish in text:
                        dish_counter[dish] += 1

            restaurants_data.append({
                "Restaurant": name,
                "Rating": rating
            })

            page.go_back()

            time.sleep(3)

        restaurants_df = pd.DataFrame(restaurants_data)

        restaurants_df.index = restaurants_df.index + 1

        dishes_df = pd.DataFrame({
            "dish": list(dish_counter.keys()),
            "mentions": list(dish_counter.values())
        })

        dishes_df = dishes_df.sort_values(
            "mentions",
            ascending=False
        )

        browser.close()

        return {
            "restaurants": restaurants_df,
            "dishes": dishes_df
        }
