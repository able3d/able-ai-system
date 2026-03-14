import os
import re
import pdfplumber
import shutil
import pytesseract
import cv2
from PIL import Image
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
# CLEAN INGREDIENT NAME
# ----------------------------------------------------

def clean_name(name):

    name = name.lower().strip()

    name = re.sub(r"[^a-z\s]", "", name)

    name = re.sub(r"\s+", " ", name)

    return INGREDIENT_MAP.get(name, name)

# ----------------------------------------------------
# OCR IMAGE INVOICES
# ----------------------------------------------------

def extract_text_from_image(path):

    img = cv2.imread(path)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    gray = cv2.threshold(gray,150,255,cv2.THRESH_BINARY)[1]

    text = pytesseract.image_to_string(gray)

    return text

# ----------------------------------------------------
# EXTRACT PDF CONTENT
# ----------------------------------------------------

def extract_pdf_content(path):

    text_content = ""

    with pdfplumber.open(path) as pdf:

        for page in pdf.pages:

            # table extraction
            tables = page.extract_tables()

            if tables:

                for table in tables:

                    for row in table:

                        if not row:
                            continue

                        row_text = " ".join(
                            str(c) for c in row if c
                        )

                        text_content += row_text + "\n"

            # text extraction
            text = page.extract_text()

            if text:
                text_content += text + "\n"

    return text_content

# ----------------------------------------------------
# PARSE ITEMS
# ----------------------------------------------------

def extract_items(text):

    items = []

    lines = text.split("\n")

    for line in lines:

        line = line.strip()

        if not line:
            continue

        lower = line.lower()

        if any(x in lower for x in [
            "subtotal","tax","total",
            "balance","invoice","date",
            "amount","payment","bill"
        ]):
            continue

        match = re.search(
            r"([A-Za-z\s]+)\s+(\d+)\s*\$?(\d+\.?\d*)",
            line
        )

        if not match:
            continue

        name = clean_name(match.group(1))
        quantity = int(match.group(2))
        price = float(match.group(3))

        items.append({
            "name": name,
            "quantity": quantity,
            "price": price
        })

    return items

# ----------------------------------------------------
# INSERT PURCHASE + UPDATE INVENTORY
# ----------------------------------------------------

def insert_purchase(item):

    with engine.begin() as conn:

        conn.execute(text("""
        INSERT INTO ingredients (ingredient_name, unit)
        VALUES (:name, 'unit')
        ON CONFLICT (ingredient_name) DO NOTHING
        """), {"name": item["name"]})

        result = conn.execute(text("""
        SELECT ingredient_id
        FROM ingredients
        WHERE ingredient_name = :name
        """), {"name": item["name"]})

        row = result.fetchone()

        if not row:
            print("Ingredient not found:", item["name"])
            return

        ingredient_id = row[0]

        # record purchase
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
        return

    for file in files:

        path = os.path.join(INVOICE_FOLDER, file)

        try:

            print("Processing invoice:", file)

            text_content = ""

            if file.lower().endswith(".pdf"):

                text_content = extract_pdf_content(path)

            elif file.lower().endswith((".png",".jpg",".jpeg")):

                text_content = extract_text_from_image(path)

            else:
                continue

            items = extract_items(text_content)

            print("Items detected:", items)

            for item in items:

                insert_purchase(item)

            shutil.move(
                path,
                os.path.join(PROCESSED_FOLDER, file)
            )

            print("Invoice processed:", file)

        except Exception as e:

            print("Error processing invoice:", file)
            print(e)


# ----------------------------------------------------
# RUN
# ----------------------------------------------------

if __name__ == "__main__":

    process_all_invoices()