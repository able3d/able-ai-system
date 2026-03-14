import requests
import pandas as pd
from bs4 import BeautifulSoup


# --------------------------------------------------
# COMPETITOR RESTAURANTS
# --------------------------------------------------

competitors = [
{
"name":"Haile Ethiopian Restaurant",
"lat":40.7216,
"lon":-73.9803
},
{
"name":"Awaze Ethiopian Restaurant",
"lat":40.7487,
"lon":-73.9857
},
{
"name":"Meskerem Ethiopian Restaurant",
"lat":40.7420,
"lon":-73.9836
},
{
"name":"Bunna Cafe",
"lat":40.6893,
"lon":-73.9590
}
]


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

    text = text.lower()

    score = 0

    for dish in dish_keywords:

        score += text.count(dish)

    return score


# --------------------------------------------------
# SCRAPER
# --------------------------------------------------

def scrape_google_reviews():

    restaurants_data = []

    all_text = ""

    headers = {
    "User-Agent":"Mozilla/5.0"
    }

    for r in competitors:

        query = r["name"].replace(" ","+")

        url = f"https://www.google.com/search?q={query}+reviews"

        try:

            response = requests.get(url,headers=headers)

            soup = BeautifulSoup(response.text,"html.parser")

            page_text = soup.get_text()

            demand = calculate_demand(page_text)

            restaurants_data.append({

            "Restaurant": r["name"],
            "Rating": 4.0,
            "lat": r["lat"],
            "lon": r["lon"],
            "demand": demand

            })

            all_text += page_text

        except Exception as e:

            print("Scraper error:",e)

    restaurants_df = pd.DataFrame(restaurants_data)

    # --------------------------------------------------
    # DISH MENTIONS
    # --------------------------------------------------

    dish_counts = {}

    text = all_text.lower()

    for dish in dish_keywords:

        dish_counts[dish] = text.count(dish)

    dishes_df = pd.DataFrame([
    {"dish":k,"mentions":v}
    for k,v in dish_counts.items()
    ])

    return {

    "restaurants": restaurants_df,
    "dishes": dishes_df

    }