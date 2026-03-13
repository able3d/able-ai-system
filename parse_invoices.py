import os
import re
import pdfplumber
import shutil
from sqlalchemy import create_engine, text

# ----------------------------------------------------
# FOLDERS
# ----------------------------------------------------

INVOICE_FOLDER = "data/invoices"
PROCESSED_FOLDER = "data/processed_invoices"

os.makedirs(INVOICE_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# ----------------------------------------------------
# DATABASE
# ----------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

engine = create_engine(DATABASE_URL)

# ----------------------------------------------------
# INGREDIENT NORMALIZATION
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
# EXTRACT ITEMS
# ----------------------------------------------------

def extract_items(text):

    items = []

    lines = text.split("\n")

    pattern = re.compile(
        r"([A-Za-z\s]+)\s+(\d+)\s*\$?(\d+\.?\d*)"
    )

    for line in lines:

        match = pattern.search(line)

        if not match:
            continue

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
# INSERT PURCHASE
# ----------------------------------------------------

def insert_purchase(item):

    with engine.begin() as conn:

        # ensure ingredient exists
        conn.execute(text("""
        INSERT INTO ingredients (ingredient_name, unit)
        VALUES (:name, 'unit')
        ON CONFLICT (ingredient_name) DO NOTHING
        """), {"name": item["name"]})

        # get ingredient id
        result = conn.execute(text("""
        SELECT ingredient_id
        FROM ingredients
        WHERE ingredient_name = :name
        """), {"name": item["name"]})

        ingredient_id = result.fetchone()[0]

        # insert purchase
        conn.execute(text("""
        INSERT INTO purchases
        (ingredient_name, quantity, unit, price, purchase_date)
        VALUES
        (:name, :quantity, 'unit', :price, CURRENT_DATE)
        """), item)

        # update inventory
        conn.execute(text("""
        INSERT INTO inventory (ingredient_id, quantity)
        VALUES (:ingredient_id, :quantity)

        ON CONFLICT (ingredient_id)
        DO UPDATE SET
        quantity = inventory.quantity + EXCLUDED.quantity
        """), {
            "ingredient_id": ingredient_id,
            "quantity": item["quantity"]
        })

# ----------------------------------------------------
# PROCESS INVOICES
# ----------------------------------------------------

def process_all_invoices():

    print("Processing invoices...")

    files = os.listdir(INVOICE_FOLDER)

    if not files:
        print("No invoices found")

    for file in files:

        if not file.lower().endswith(".pdf"):
            continue

        file_path = os.path.join(INVOICE_FOLDER, file)

        print("Reading invoice:", file)

        try:

            text_content = ""

            with pdfplumber.open(file_path) as pdf:

                for page in pdf.pages:

                    text = page.extract_text()

                    if text:
                        text_content += text + "\n"

                    tables = page.extract_tables()

                    for table in tables:

                        for row in table:

                            if row:
                                row_text = " ".join(
                                    str(cell) for cell in row if cell
                                )

                                text_content += row_text + "\n"

            items = extract_items(text_content)

            print("Items found:", len(items))

            for item in items:

                insert_purchase(item)

                print("Inserted purchase:", item["name"])

            shutil.move(
                file_path,
                os.path.join(PROCESSED_FOLDER, file)
            )

            print("Invoice processed:", file)

        except Exception as e:

            print("Error processing", file)
            print(e)


# ----------------------------------------------------
# RUN SCRIPT
# ----------------------------------------------------

if __name__ == "__main__":

    process_all_invoices()