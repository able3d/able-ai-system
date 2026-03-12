import os
import re
import pdfplumber
import shutil
from sqlalchemy import create_engine, text

# ----------------------------------------------------
# FOLDERS
# ----------------------------------------------------

INVOICE_FOLDER = "data"
PROCESSED_FOLDER = "data/processed_invoices"

os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# ----------------------------------------------------
# DATABASE CONNECTION
# ----------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

# ----------------------------------------------------
# INGREDIENT NAME MAPPING
# ----------------------------------------------------

INGREDIENT_MAP = {
    "beef stew meat": "beef",
    "ground beef": "beef",
    "beef cubes": "beef",
    "whole chicken": "chicken",
    "chicken drumsticks": "chicken",
    "lamb cubes": "lamb",

    "teff flour": "teff flour",
    "white teff flour": "teff flour",
    "barley flour": "barley flour",
    "wheat flour": "wheat flour",

    "red lentils": "lentils",
    "yellow split peas": "split peas",

    "red onions": "onion",
    "onions": "onion",
    "fresh tomatoes": "tomato",
    "tomatoes": "tomato",

    "garlic": "garlic",
    "ginger": "ginger",
    "cabbage": "cabbage",
    "potatoes": "potato",
    "carrots": "carrot",

    "berbere spice": "berbere",
    "mitmita": "mitmita",

    "green coffee beans": "coffee beans",

    "injera bread": "injera"
}

# ----------------------------------------------------
# EXTRACT ITEMS FROM TEXT
# ----------------------------------------------------

def extract_items(text):

    items = []
    lines = text.split("\n")

    pattern = re.compile(
        r"([A-Za-z\s]+)\s+(\d+)\s+\$?(\d+\.\d+)"
    )

    for line in lines:

        match = pattern.search(line)

        if match:

            name = match.group(1).strip().lower()
            quantity = int(match.group(2))
            price = float(match.group(3))

            name = INGREDIENT_MAP.get(name, name)

            items.append({
                "name": name,
                "quantity": quantity,
                "price": price
            })

    return items


# ----------------------------------------------------
# INSERT INTO DATABASE
# ----------------------------------------------------

def insert_purchase(item):

    with engine.begin() as conn:

        # Ensure ingredient exists
        ingredient_query = text("""
            INSERT INTO ingredients (ingredient_name, unit)
            VALUES (:name, 'unit')
            ON CONFLICT (ingredient_name) DO NOTHING
        """)

        conn.execute(ingredient_query, {"name": item["name"]})

        # Insert purchase record
        purchase_query = text("""
            INSERT INTO purchases
            (ingredient_name, quantity, unit, price, purchase_date)

            VALUES
            (:name, :quantity, 'unit', :price, CURRENT_DATE)
        """)

        conn.execute(purchase_query, item)

        # Update inventory
        inventory_query = text("""
            INSERT INTO inventory (ingredient_id, quantity)

            SELECT ingredient_id, :quantity
            FROM ingredients
            WHERE ingredient_name = :name

            ON CONFLICT (ingredient_id)
            DO UPDATE SET quantity = inventory.quantity + EXCLUDED.quantity
        """)

        conn.execute(inventory_query, item)


# ----------------------------------------------------
# CHECK IF INGREDIENT EXISTS
# ----------------------------------------------------

def ingredient_exists(name):

    query = text("""
        SELECT 1
        FROM ingredients
        WHERE ingredient_name = :name
    """)

    with engine.connect() as conn:

        result = conn.execute(query, {"name": name}).fetchone()

        return result is not None


# ----------------------------------------------------
# PROCESS ALL INVOICES
# ----------------------------------------------------

def process_all_invoices():

    print("Processing invoices...")

    for file in os.listdir(INVOICE_FOLDER):

        if not file.endswith(".pdf"):
            continue

        file_path = os.path.join(INVOICE_FOLDER, file)

        print("Reading invoice:", file)

        try:

            with pdfplumber.open(file_path) as pdf:

                text_content = ""

                for page in pdf.pages:

                    page_text = page.extract_text()

                    if page_text:
                        text_content += page_text + "\n"

                    tables = page.extract_tables()

                    for table in tables:

                        for row in table:

                            if row:
                                row_text = " ".join(
                                    [str(cell) for cell in row if cell]
                                )
                                text_content += row_text + "\n"

            print("------ RAW TEXT ------")
            print(text_content)

            items = extract_items(text_content)

            print("Items found:", len(items))

            for item in items:

                print("Processing item:", item)

                if ingredient_exists(item["name"]):

                    insert_purchase(item)
                    print("Inserted:", item["name"])

                else:

                    print("Unknown ingredient:", item["name"])
                    insert_purchase(item)

            # Move processed file
            shutil.move(
                file_path,
                os.path.join(PROCESSED_FOLDER, file)
            )

            print("Moved to processed folder\n")

        except Exception as e:

            print("Error processing", file)
            print(e)


# ----------------------------------------------------
# RUN SCRIPT
# ----------------------------------------------------

if __name__ == "__main__":
    process_all_invoices()