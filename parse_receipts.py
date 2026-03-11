import os
import pdfplumber
import shutil
from sqlalchemy import create_engine, text
import pandas as pd

# --------------------------------------------------
# FOLDERS
# --------------------------------------------------

RECEIPT_FOLDER = "data/receipts"
PROCESSED_FOLDER = "data/processed_receipts"

os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)


def load_csv_receipts():

    folder = "data/receipts"

    for file in os.listdir(folder):

        df = pd.read_csv(os.path.join(folder, file))

        df.rename(columns={
            "Item": "item_name",
            "Quantity": "quantity",
            "Price": "price"
        }, inplace=True)

        df.to_sql(
            "receipts",
            engine,
            if_exists="append",
            index=False
        )

        print("Inserted receipt data:", file)

# --------------------------------------------------
# EXTRACT ITEMS FROM RECEIPT TEXT
# --------------------------------------------------

import re

def extract_items(text):

    items = []

    lines = text.split("\n")

    for line in lines:

        line = line.strip()

        if not line:
            continue

        # -----------------------------------
        # Pattern 1: "2 Doro Wat 15.99"
        # -----------------------------------

        match = re.search(r"(\d+)\s+(.+?)\s+\$?(\d+\.\d{2})", line)

        if match:

            quantity = int(match.group(1))
            name = match.group(2).strip()
            price = float(match.group(3))

            items.append({
                "name": name,
                "quantity": quantity,
                "price": price
            })

            continue


        # -----------------------------------
        # Pattern 2: "Doro Wat 15.99"
        # -----------------------------------

        match = re.search(r"(.+?)\s+\$?(\d+\.\d{2})", line)

        if match:

            name = match.group(1).strip()
            price = float(match.group(2))

            items.append({
                "name": name,
                "quantity": 1,
                "price": price
            })

            continue

    return items


# --------------------------------------------------
# INSERT SALE INTO DATABASE
# --------------------------------------------------

def insert_sale(item):

    query = text("""
        INSERT INTO receipts (item_name, quantity, price)
        VALUES (:name, :quantity, :price)
    """)

    with engine.connect() as conn:

        conn.execute(query, {
            "name": item["name"],
            "quantity": item["quantity"],
            "price": item["price"]
        })

        conn.commit()


# --------------------------------------------------
# INVENTORY DEDUCTION ENGINE
# --------------------------------------------------

def deduct_inventory(dish_name, quantity_sold):

    print("Updating inventory for:", dish_name)

    with engine.connect() as conn:

        # --------------------------------------------------
        # FIND DISH ID
        # --------------------------------------------------

        dish_query = text("""
            SELECT dish_id
            FROM dishes
            WHERE LOWER(dish_name) = LOWER(:dish)
        """)

        dish = conn.execute(dish_query, {"dish": dish_name}).fetchone()

        if not dish:
            print("Dish not found:", dish_name)
            return

        dish_id = dish[0]

        # --------------------------------------------------
        # GET BOM INGREDIENTS
        # --------------------------------------------------

        bom_query = text("""
            SELECT ingredient_id, quantity_required
            FROM bom
            WHERE dish_id = :dish_id
        """)

        bom_items = conn.execute(
            bom_query,
            {"dish_id": dish_id}
        ).fetchall()

        if not bom_items:
            print("No BOM found for:", dish_name)
            return

        # --------------------------------------------------
        # DEDUCT INVENTORY
        # --------------------------------------------------

        for ingredient_id, qty_required in bom_items:

            total_used = qty_required * quantity_sold

            update_query = text("""
                UPDATE inventory
                SET stock_quantity = stock_quantity - :used
                WHERE ingredient_id = :ingredient_id
            """)

            conn.execute(update_query, {
                "used": total_used,
                "ingredient_id": ingredient_id
            })

        conn.commit()

        print("Inventory updated for", dish_name)

# ------------------------
def create_tables(engine):

    with engine.connect() as conn:

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS dishes (
            dish_id SERIAL PRIMARY KEY,
            dish_name TEXT UNIQUE
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS receipts (
            receipt_id SERIAL PRIMARY KEY,
            item_name TEXT,
            quantity INT,
            price FLOAT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS inventory (
            ingredient_id SERIAL PRIMARY KEY,
            ingredient_name TEXT,
            stock_quantity FLOAT
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS bom (
            bom_id SERIAL PRIMARY KEY,
            dish_id INT,
            ingredient_id INT,
            quantity_required FLOAT
        )
        """))

        conn.commit()

    print("Database tables created")

# --------------------------------------------------
# PROCESS RECEIPTS
# --------------------------------------------------

def process_receipts():

    print("Processing receipts...\n")

    for file in os.listdir(RECEIPT_FOLDER):

        if not file.endswith(".pdf"):
            continue

        file_path = os.path.join(RECEIPT_FOLDER, file)

        print("Reading receipt:", file)

        try:

            # --------------------------------------------------
            # EXTRACT TEXT FROM PDF
            # --------------------------------------------------

            with pdfplumber.open(file_path) as pdf:

                text_content = ""

                for page in pdf.pages:

                    page_text = page.extract_text(
                        x_tolerance=2,
                        y_tolerance=2
                    )

                    if page_text:
                        text_content += page_text + "\n"

            # --------------------------------------------------
            # PARSE ITEMS
            # --------------------------------------------------

            items = extract_items(text_content)

            print("Items detected:", len(items))

            # --------------------------------------------------
            # INSERT SALES + UPDATE INVENTORY
            # --------------------------------------------------

            for item in items:

                insert_sale(item)

                print("Inserted sale:", item["name"])

                deduct_inventory(
                    item["name"],
                    item["quantity"]
                )

            # --------------------------------------------------
            # MOVE FILE AFTER PROCESSING
            # --------------------------------------------------

            shutil.move(
                file_path,
                os.path.join(PROCESSED_FOLDER, file)
            )

            print("Moved to processed_receipts\n")

        except Exception as e:

            print("Error processing", file)
            print(e)


# --------------------------------------------------
# RUN SCRIPT
# --------------------------------------------------

if __name__ == "__main__":

    process_receipts()
