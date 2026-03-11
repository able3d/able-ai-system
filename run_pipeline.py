from etl.google_drive_etl import download_all_files
import parse_invoices
import parse_receipts

from sqlalchemy import create_engine, text
import pandas as pd
import os

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

print("Pipeline started")


def init_db():
    print("Initializing database...")

    with engine.connect() as conn:

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS menu_items (
            item_id SERIAL PRIMARY KEY,
            item_name TEXT UNIQUE
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
        CREATE TABLE IF NOT EXISTS ingredients (
            ingredient_id SERIAL PRIMARY KEY,
            ingredient_name TEXT UNIQUE,
            unit TEXT
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS purchases (
            purchase_id SERIAL PRIMARY KEY,
            ingredient_name TEXT,
            quantity FLOAT,
            price FLOAT,
            purchase_date DATE
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS demand_heatmap (
            item_name TEXT,
            revenue FLOAT
        )
        """))

        conn.commit()

    print("Database ready")


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

    print("Step 5: Generating demand heatmap")

    demand_query = """
    SELECT m.item_name, SUM(s.revenue) as revenue
    FROM menu_sales s
    JOIN menu_items m ON s.item_id = m.item_id
    GROUP BY m.item_name
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
