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

os.makedirs(INVOICE_FOLDER, exist_ok=True)
os.makedirs(RECEIPT_FOLDER, exist_ok=True)

engine = create_engine(DATABASE_URL)


# --------------------------------------------------
# INIT DATABASE
# --------------------------------------------------

def init_db():

    print("Initializing database tables...")

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
            item_id INTEGER PRIMARY KEY REFERENCES menu_items(item_id),
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

    print("Database ready\n")


# --------------------------------------------------
# GOOGLE DRIVE ETL
# --------------------------------------------------

def run_drive_etl():

    print("\nRunning Google Drive ETL...\n")

    # ---------------------------
    # INVOICES
    # ---------------------------

    if INVOICE_FOLDER_ID:

        print("Downloading invoices from Google Drive...")

        download_all_files(INVOICE_FOLDER_ID, INVOICE_FOLDER)

        files = os.listdir(INVOICE_FOLDER)

        print("Invoices downloaded:", files)

        if files:
            print("\nProcessing invoices...\n")
            process_all_invoices()

    else:

        print("No invoice folder configured\n")

    # ---------------------------
    # RECEIPTS
    # ---------------------------

    if RECEIPT_FOLDER_ID:

        print("Downloading receipts from Google Drive...")

        download_all_files(RECEIPT_FOLDER_ID, RECEIPT_FOLDER)

        files = os.listdir(RECEIPT_FOLDER)

        print("Receipts downloaded:", files)

        if files:
            print("\nProcessing receipts...\n")
            process_all_receipts()

    else:

        print("No receipt folder configured\n")


# --------------------------------------------------
# COMPETITOR SCRAPER
# --------------------------------------------------

def run_competitor_etl():

    print("\nRunning competitor scraper...\n")

    try:

        data = scrape_google_reviews()

        restaurants = data.get("restaurants")
        dishes = data.get("dishes")

        if restaurants is not None:
            print("Restaurants scraped:", len(restaurants))

        if dishes is not None:
            print("Dish mentions scraped:", len(dishes))

    except Exception as e:

        print("Competitor scraping failed:", e)


# --------------------------------------------------
# INVENTORY DEDUCTION
# --------------------------------------------------

def deduct_inventory():

    print("\nUpdating inventory usage from menu sales...\n")

    try:

        with engine.begin() as conn:

            conn.execute(text("""
            UPDATE inventory
            SET quantity = GREATEST(quantity - usage.total_used, 0)

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

        print("Inventory updated\n")

    except Exception as e:

        print("Inventory update failed:", e)


# --------------------------------------------------
# MAIN PIPELINE
# --------------------------------------------------

def run_pipeline():

    print("\n===================================")
    print("STARTING ABLE AI DATA PIPELINE")
    print("===================================\n")

    # Step 1
    print("Step 1: Initializing database...\n")
    init_db()

    # Step 2
    print("Step 2: Running Google Drive ETL...\n")
    run_drive_etl()

    # Step 3
    print("Step 3: Scraping competitor reviews...\n")
    run_competitor_etl()

    # Step 4
    print("Step 4: Updating inventory consumption...\n")
    deduct_inventory()

    print("\n===================================")
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print("===================================\n")


# --------------------------------------------------
# MAIN
# --------------------------------------------------

if __name__ == "__main__":

    run_pipeline()