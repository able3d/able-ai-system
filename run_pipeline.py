from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)


# --------------------------------------------------
# INIT DATABASE
# --------------------------------------------------

def init_db():

    with engine.connect() as conn:

        # -----------------------------
        # MENU ITEMS
        # -----------------------------

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS menu_items (
            item_id SERIAL PRIMARY KEY,
            item_name TEXT UNIQUE
        )
        """))

        conn.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_menu_item
        ON menu_items(item_name)
        """))

        # -----------------------------
        # INGREDIENTS
        # -----------------------------

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ingredients (
            ingredient_id SERIAL PRIMARY KEY,
            ingredient_name TEXT UNIQUE,
            unit TEXT
        )
        """))

        conn.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_ingredient
        ON ingredients(ingredient_name)
        """))

        # -----------------------------
        # DISH BOM
        # -----------------------------

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS dish_bom (
            bom_id SERIAL PRIMARY KEY,
            item_id INTEGER REFERENCES menu_items(item_id),
            ingredient_id INTEGER REFERENCES ingredients(ingredient_id),
            quantity FLOAT
        )
        """))

        # -----------------------------
        # INVENTORY
        # -----------------------------

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS inventory (
            ingredient_id INTEGER PRIMARY KEY REFERENCES ingredients(ingredient_id),
            quantity FLOAT
        )
        """))

        # -----------------------------
        # MENU SALES
        # -----------------------------

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS menu_sales (
            sale_id SERIAL PRIMARY KEY,
            item_id INTEGER REFERENCES menu_items(item_id),
            orders INTEGER DEFAULT 0,
            revenue FLOAT DEFAULT 0
        )
        """))

        # -----------------------------
        # PURCHASES
        # -----------------------------

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
# SEED DATA
# --------------------------------------------------

def seed_data():

    with engine.connect() as conn:

        # -----------------------------
        # MENU
        # -----------------------------

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

        # -----------------------------
        # INGREDIENTS
        # -----------------------------

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

        # -----------------------------
        # INITIAL INVENTORY
        # -----------------------------

        conn.execute(text("""
        INSERT INTO inventory (ingredient_id, quantity)
        SELECT ingredient_id, 5000
        FROM ingredients
        ON CONFLICT (ingredient_id) DO NOTHING
        """))

        # -----------------------------
        # MENU SALES INIT
        # -----------------------------

        conn.execute(text("""
        INSERT INTO menu_sales (item_id, orders, revenue)
        SELECT item_id, 0, 0
        FROM menu_items
        ON CONFLICT DO NOTHING
        """))

        conn.commit()


# --------------------------------------------------
# CREATE DISH BOM
# --------------------------------------------------

def create_bom():

    with engine.connect() as conn:

        # Clear existing BOM
        conn.execute(text("DELETE FROM dish_bom"))

        # DORO WAT
        conn.execute(text("""
        INSERT INTO dish_bom (item_id, ingredient_id, quantity)
        SELECT m.item_id, i.ingredient_id, 500
        FROM menu_items m, ingredients i
        WHERE m.item_name='Doro Wat'
        AND i.ingredient_name='chicken'
        """))

        conn.execute(text("""
        INSERT INTO dish_bom (item_id, ingredient_id, quantity)
        SELECT m.item_id, i.ingredient_id, 100
        FROM menu_items m, ingredients i
        WHERE m.item_name='Doro Wat'
        AND i.ingredient_name='onion'
        """))

        # KITFO
        conn.execute(text("""
        INSERT INTO dish_bom (item_id, ingredient_id, quantity)
        SELECT m.item_id, i.ingredient_id, 300
        FROM menu_items m, ingredients i
        WHERE m.item_name='Kitfo'
        AND i.ingredient_name='beef'
        """))

        # SHIRO
        conn.execute(text("""
        INSERT INTO dish_bom (item_id, ingredient_id, quantity)
        SELECT m.item_id, i.ingredient_id, 200
        FROM menu_items m, ingredients i
        WHERE m.item_name='Shiro'
        AND i.ingredient_name='lentils'
        """))

        conn.commit()


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

    print("Seeding data...")
    seed_data()

    print("Creating BOM...")
    create_bom()

    print("Updating inventory usage...")
    deduct_inventory()

    print("Pipeline completed successfully.")
