from etl.google_drive_etl import download_all_files
from parse_invoices import process_all_invoices
from parse_receipts import process_all_receipts

from google_reviews_scraper import scrape_google_reviews

from sqlalchemy import create_engine, text
import os


# --------------------------------------------------
# ENVIRONMENT VARIABLES
# --------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

INVOICE_FOLDER_ID = os.getenv("INVOICE_FOLDER_ID")
RECEIPT_FOLDER_ID = os.getenv("RECEIPT_FOLDER_ID")

INVOICE_FOLDER = "data/invoices"
RECEIPT_FOLDER = "data/receipts"

engine = create_engine(DATABASE_URL)


# --------------------------------------------------
# INIT DATABASE
# --------------------------------------------------

def init_db():

    with engine.begin() as conn:

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS menu_items (
            item_id SERIAL PRIMARY KEY,
            item_name TEXT UNIQUE
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ingredients (
            ingredient_id SERIAL PRIMARY KEY,
            ingredient_name TEXT UNIQUE,
            unit TEXT
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS dish_bom (
            bom_id SERIAL PRIMARY KEY,
            item_id INTEGER REFERENCES menu_items(item_id),
            ingredient_id INTEGER REFERENCES ingredients(ingredient_id),
            quantity FLOAT
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS inventory (
            ingredient_id INTEGER PRIMARY KEY REFERENCES ingredients(ingredient_id),
            quantity FLOAT
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS menu_sales (
            sale_id SERIAL PRIMARY KEY,
            item_id INTEGER REFERENCES menu_items(item_id),
            orders INTEGER,
            revenue FLOAT
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS purchases (
            purchase_id SERIAL PRIMARY KEY,
            ingredient_name TEXT,
            quantity FLOAT,
            unit TEXT,
            price FLOAT,
            purchase_date DATE
        )
        """))


# --------------------------------------------------
# GOOGLE DRIVE ETL
# --------------------------------------------------

def run_drive_etl():

    print("Running Google Drive ETL...")

    os.makedirs(INVOICE_FOLDER, exist_ok=True)
    os.makedirs(RECEIPT_FOLDER, exist_ok=True)

    if INVOICE_FOLDER_ID:

        print("Downloading invoices...")

        download_all_files(INVOICE_FOLDER_ID, INVOICE_FOLDER)

        print("Processing invoices...")

        process_all_invoices()

    else:

        print("No invoice folder configured")

    if RECEIPT_FOLDER_ID:

        print("Downloading receipts...")

        download_all_files(RECEIPT_FOLDER_ID, RECEIPT_FOLDER)

        print("Processing receipts...")

        process_all_receipts()

    else:

        print("No receipt folder configured")


# --------------------------------------------------
# COMPETITOR SCRAPER
# --------------------------------------------------

def run_competitor_etl():

    print("Running competitor scraper...")

    try:

        data = scrape_google_reviews()

        restaurants = data["restaurants"]
        dishes = data["dishes"]

        print("Restaurants scraped:", len(restaurants))
        print("Dishes scraped:", len(dishes))

    except Exception as e:

        print("Competitor scraping failed:", e)


# --------------------------------------------------
# INVENTORY DEDUCTION
# --------------------------------------------------

def deduct_inventory():

    print("Updating inventory usage...")

    with engine.begin() as conn:

        conn.execute(text("""
        UPDATE inventory
        SET quantity = quantity - usage.total_used
        FROM (
            SELECT
                b.ingredient_id,
                SUM(b.quantity * s.orders) AS total_used
            FROM dish_bom b
            JOIN menu_sales s
            ON b.item_id = s.item_id
            GROUP BY b.ingredient_id
        ) usage
        WHERE inventory.ingredient_id = usage.ingredient_id
        """))


# --------------------------------------------------
# RUN PIPELINE
# --------------------------------------------------

def run_pipeline():

    print("Initializing database...")
    init_db()

    print("Running ETL pipelines...")

    run_drive_etl()

    run_competitor_etl()

    deduct_inventory()

    print("Pipeline completed successfully.")


# --------------------------------------------------
# MAIN
# --------------------------------------------------

if __name__ == "__main__":

    run_pipeline()