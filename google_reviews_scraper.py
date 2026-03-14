import requests
import pandas as pd
from bs4 import BeautifulSoup


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

def calculate_demand(text):

    score = 0

    text = text.lower()

    for dish in dish_keywords:

        if dish in text:
            score += text.count(dish)

    return score


# --------------------------------------------------
# SCRAPER
# --------------------------------------------------

def scrape_google_reviews():

    url = "https://www.google.com/search?q=ethiopian+restaurant+new+york"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers)

    soup = BeautifulSoup(response.text, "html.parser")

    restaurants = []

    results = soup.select("div.BNeawe")

    for i, result in enumerate(results[:5]):

        name = result.get_text()

        demand = calculate_demand(name)

        restaurants.append({
            "Restaurant": name,
            "Rating": 4.0,
            "lat": None,
            "lon": None,
            "demand": demand
        })

    restaurants_df = pd.DataFrame(restaurants)

    dishes_df = pd.DataFrame(columns=["dish", "mentions"])

    return {
        "restaurants": restaurants_df,
        "dishes": dishes_df
    }