from etl.google_drive_etl import download_all_files
import parse_invoices
import parse_receipts

from sqlalchemy import create_engine, text
import pandas as pd
import os

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

print("Pipeline starting...")


# -------------------------
# INIT DATABASE
# -------------------------

def init_db():

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
        CREATE TABLE IF NOT EXISTS dish_bom (
            bom_id SERIAL PRIMARY KEY,
            item_id INTEGER REFERENCES menu_items(item_id),
            ingredient_name TEXT,
            quantity FLOAT,
            unit TEXT
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS inventory_usage (
            ingredient_name TEXT,
            quantity_used FLOAT
        )
        """))

        conn.commit()

    print("Database ready")


# -------------------------
# SEED MENU
# -------------------------

def seed_menu():

    with engine.connect() as conn:

        conn.execute(text("""
        INSERT INTO menu_items (item_name)
        VALUES
        ('Doro Wat'),
        ('Kitfo'),
        ('Shiro'),
        ('Tibs'),
        ('Veggie Combo')
        ON CONFLICT (item_name) DO NOTHING
        """))

        conn.commit()


# -------------------------
# SEED INGREDIENTS
# -------------------------

def seed_ingredients():

    with engine.connect() as conn:

        conn.execute(text("""
        INSERT INTO ingredients (ingredient_name, unit)
        VALUES
        ('chicken','g'),
        ('beef','g'),
        ('lentils','g'),
        ('onion','g'),
        ('berbere','g'),
        ('butter','g'),
        ('garlic','g'),
        ('injera','pcs')
        ON CONFLICT (ingredient_name) DO NOTHING
        """))

        conn.commit()


# -------------------------
# SEED BOM
# -------------------------

def seed_bom():

    with engine.connect() as conn:

        conn.execute(text("""

        INSERT INTO dish_bom (item_id, ingredient_name, quantity, unit)

        SELECT item_id,'chicken',500,'g'
        FROM menu_items WHERE item_name='Doro Wat'

        UNION ALL
        SELECT item_id,'onion',200,'g'
        FROM menu_items WHERE item_name='Doro Wat'

        UNION ALL
        SELECT item_id,'berbere',30,'g'
        FROM menu_items WHERE item_name='Doro Wat'

        UNION ALL
        SELECT item_id,'butter',40,'g'
        FROM menu_items WHERE item_name='Doro Wat'

        UNION ALL
        SELECT item_id,'injera',2,'pcs'
        FROM menu_items WHERE item_name='Doro Wat'

        """))

        conn.commit()


# -------------------------
# INVENTORY PURCHASES
# -------------------------

def seed_inventory():

    with engine.connect() as conn:

        conn.execute(text("""
        INSERT INTO purchases (ingredient_name, quantity, price, purchase_date)
        VALUES
        ('chicken',5000,45,'2026-03-01'),
        ('beef',3000,50,'2026-03-01'),
        ('lentils',4000,20,'2026-03-01'),
        ('onion',2000,10,'2026-03-01'),
        ('berbere',1000,15,'2026-03-01'),
        ('butter',500,12,'2026-03-01')
        """))

        conn.commit()


# -------------------------
# AUTOMATIC INVENTORY USAGE
# -------------------------

def update_inventory_from_sales():

    print("Calculating ingredient usage...")

    usage_query = """
    SELECT
        b.ingredient_name,
        SUM(b.quantity * s.orders) AS quantity_used
    FROM dish_bom b
    JOIN menu_sales s
    ON b.item_id = s.item_id
    GROUP BY b.ingredient_name
    """

    usage_df = pd.read_sql(usage_query, engine)

    usage_df.to_sql(
        "inventory_usage",
        engine,
        if_exists="replace",
        index=False
    )

    print("Inventory usage updated")


# -------------------------
# DEMAND HEATMAP
# -------------------------

def generate_demand_heatmap():

    demand_query = """
    SELECT m.item_name, SUM(s.revenue) as revenue
    FROM menu_sales s
    JOIN menu_items m
    ON s.item_id = m.item_id
    GROUP BY m.item_name
    """

    df = pd.read_sql(demand_query, engine)

    df.to_sql(
        "demand_heatmap",
        engine,
        if_exists="replace",
        index=False
    )


# -------------------------
# MAIN PIPELINE
# -------------------------

def run_pipeline():

    print("STEP 1 INIT DB")
    init_db()

    print("STEP 2 SEED MENU")
    seed_menu()

    print("STEP 3 SEED INGREDIENTS")
    seed_ingredients()

    print("STEP 4 SEED BOM")
    seed_bom()

    print("STEP 5 SEED INVENTORY")
    seed_inventory()

    print("STEP 6 DOWNLOAD DATA")

    download_all_files(
        "1mLUXpBHo6ki0kICoPLHpaYYKqGDGEW_u",
        "data/invoices"
    )

    download_all_files(
        "10OsCAFFowvrSENlYIfOTWtBZZ4GxLncE",
        "data/receipts"
    )

    print("STEP 7 PARSE INVOICES")
    parse_invoices.process_all_invoices()

    print("STEP 8 PARSE RECEIPTS")
    parse_receipts.process_receipts()

    print("STEP 9 INVENTORY DEDUCTION")
    update_inventory_from_sales()

    print("STEP 10 DEMAND ANALYTICS")
    generate_demand_heatmap()

    print("Pipeline completed successfully")


# -------------------------
# EXECUTE
# -------------------------

if __name__ == "__main__":
    run_pipeline()
