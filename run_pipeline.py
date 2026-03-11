from etl.google_drive_etl import download_all_files
import parse_invoices
import parse_receipts

from competitor.google_reviews_scraper import scrape_google_reviews
from database.init_db import init_db
from sqlalchemy import create_engine
import pandas as pd
import os

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

print("Pipeline started")


def run_pipeline():

    print("Step 1: Initialize database")
    init_db()

    print("Step 2: Downloading Google Drive files")

    download_all_files(
        "1mLUXpBHo6ki0kICoPLHpaYYKqGDGEW_u",
        "data/invoices"
    )

    download_all_files(
        "10OsCAFFowvrSENlYIfOTWtBZZ4GxLncE",
        "data/receipts"
    )

    print("Step 3: Parsing invoices")
    parse_invoices.process_all_invoices()

    print("Step 4: Parsing receipts")
    parse_receipts.process_receipts()

    print("Step 5: Running competitor intelligence")

    competitor_data = scrape_google_reviews()

    restaurants_df = competitor_data["restaurants"]
    dishes_df = competitor_data["dishes"]

    restaurants_df.to_sql(
        "competitor_restaurants",
        engine,
        if_exists="replace",
        index=False
    )

    dishes_df.to_sql(
        "competitor_dish_mentions",
        engine,
        if_exists="replace",
        index=False
    )

    print("Step 6: Generating demand heatmap")

    demand_query = """
    SELECT item_name, SUM(revenue) as revenue
    FROM menu_sales s
    JOIN menu_items m ON s.item_id = m.item_id
    GROUP BY item_name
    """

    demand_df = pd.read_sql(demand_query, engine)

    demand_df.to_sql(
        "demand_heatmap",
        engine,
        if_exists="replace",
        index=False
    )

    print("Pipeline finished successfully")


if __name__ == "__main__":
    run_pipeline()
