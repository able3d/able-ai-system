from etl.google_drive_etl import download_all_files
from parse_invoices import process_all_invoices
from parse_receipts import process_all_receipts

from sqlalchemy import create_engine, text
import os


DATABASE_URL = os.getenv("DATABASE_URL")

INVOICE_FOLDER_ID = os.getenv("INVOICE_FOLDER_ID")
RECEIPT_FOLDER_ID = os.getenv("RECEIPT_FOLDER_ID")

INVOICE_FOLDER = "data/invoices"
RECEIPT_FOLDER = "data/receipts"

engine = create_engine(DATABASE_URL)


# --------------------------------------------------
# INIT DATABASE
# --------------------------------------------------

def init_db():

    with engine.connect() as conn:

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

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS competitors (
        competitor_id SERIAL PRIMARY KEY,
        restaurant_name TEXT,
        rating FLOAT,
        lat FLOAT,
        lon FLOAT,
        demand_score INT,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS competitor_dishes (
        dish TEXT,
        mentions INT
        )
        """))

        conn.commit()


# --------------------------------------------------
# GOOGLE DRIVE ETL
# --------------------------------------------------

def run_drive_etl():

    print("Running Google Drive ETL...")

    os.makedirs(INVOICE_FOLDER, exist_ok=True)
    os.makedirs(RECEIPT_FOLDER, exist_ok=True)

    # -----------------------
    # DOWNLOAD INVOICES
    # -----------------------

    if INVOICE_FOLDER_ID:

        print("Downloading invoices...")

        download_all_files(
            INVOICE_FOLDER_ID,
            INVOICE_FOLDER
        )

        print("Processing invoices...")
        process_all_invoices()

    else:

        print("INVOICE_FOLDER_ID not configured")


    # -----------------------
    # DOWNLOAD RECEIPTS
    # -----------------------

    if RECEIPT_FOLDER_ID:

        print("Downloading receipts...")

        download_all_files(
            RECEIPT_FOLDER_ID,
            RECEIPT_FOLDER
        )

        print("Processing receipts...")
        process_all_receipts()

    else:

        print("RECEIPT_FOLDER_ID not configured")


# --------------------------------------------------
# INVENTORY DEDUCTION
# --------------------------------------------------

def deduct_inventory():

    with engine.connect() as conn:

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

        conn.commit()


# --------------------------------------------------
# RUN PIPELINE
# --------------------------------------------------

def run_pipeline():

    print("Initializing database...")
    init_db()

    run_drive_etl()

    print("Updating inventory usage...")
    deduct_inventory()

    print("Pipeline completed successfully.")


if __name__ == "__main__":
    run_pipeline()