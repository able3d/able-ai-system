from etl.google_drive_etl import download_all_files

from parse_invoices import process_all_invoices
from parse_receipts import process_all_receipts

from sqlalchemy import create_engine, text
import os



DATABASE_URL = os.getenv("DATABASE_URL")
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")

LOCAL_DATA_FOLDER = "data/invoices"

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

        conn.commit()


# --------------------------------------------------
# GOOGLE DRIVE ETL
# --------------------------------------------------

def run_drive_etl():

    if not DRIVE_FOLDER_ID:

        print("No Google Drive folder configured")
        return


    print("Downloading files from Google Drive...")

    download_all_files(
        DRIVE_FOLDER_ID,
        LOCAL_DATA_FOLDER
    )


    print("Processing invoices...")
    process_all_invoices()


    print("Processing receipts...")
    process_all_receipts()



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


    print("Running Google Drive ETL...")
    run_drive_etl()


    print("Updating inventory usage...")
    deduct_inventory()


    print("Pipeline completed successfully.")


if __name__ == "__main__":
    run_pipeline()