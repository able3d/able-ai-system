import os
import pdfplumber
import shutil
import re
from sqlalchemy import create_engine, text

# --------------------------------------------------
# FOLDERS
# --------------------------------------------------

RECEIPT_FOLDER = "data/receipts"
PROCESSED_FOLDER = "data/processed_receipts"

os.makedirs(RECEIPT_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# --------------------------------------------------
# DATABASE
# --------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

engine = create_engine(DATABASE_URL)

# --------------------------------------------------
# CLEAN ITEM NAME
# --------------------------------------------------

def clean_item_name(name):

    name = name.lower().strip()

    # remove special characters
    name = re.sub(r"[^a-z0-9\s]", "", name)

    # remove extra spaces
    name = re.sub(r"\s+", " ", name)

    # normalize common dishes
    dish_map = {
        "doro wat": "doro wat",
        "doro": "doro wat",
        "kitfo": "kitfo",
        "shiro": "shiro",
        "vegan combo": "vegan combo",
        "vegetarian combo": "vegan combo",
        "veg combo": "vegan combo",
        "injera": "injera",
        "tibs": "tibs"
    }

    for key in dish_map:
        if key in name:
            return dish_map[key]

    return name.strip()

# --------------------------------------------------
# PDF EXTRACTION
# --------------------------------------------------

def extract_pdf_content(file_path):

    text_content = ""

    with pdfplumber.open(file_path) as pdf:

        for page in pdf.pages:

            # extract tables
            tables = page.extract_tables()

            if tables:
                for table in tables:
                    for row in table:

                        if not row:
                            continue

                        row_text = " ".join(str(c) for c in row if c)

                        text_content += row_text + "\n"

            # extract normal text
            text = page.extract_text()

            if text:
                text_content += text + "\n"

    return text_content

# --------------------------------------------------
# PARSE ITEMS FROM RECEIPT TEXT
# --------------------------------------------------

def extract_items(text):

    items = []

    lines = text.split("\n")

    for line in lines:

        line = line.strip()

        if not line:
            continue

        lower = line.lower()

        # skip summary lines
        if any(x in lower for x in [
            "subtotal","tax","total","tip",
            "change","payment","visa","thank",
            "balance","cash","card"
        ]):
            continue

        print("Checking line:", line)

        # pattern: 2 Doro Wat 15.99
        match = re.search(r"(\d+)\s+([A-Za-z\s]+?)[\.\s]*\$?(\d+\.\d{2})", line)

        if match:

            quantity = int(match.group(1))
            name = clean_item_name(match.group(2))
            price = float(match.group(3))

            print("MATCH:", name, price, "qty:", quantity)

            items.append({
                "name": name,
                "quantity": quantity,
                "price": price
            })

            continue

        # pattern: Doro Wat........15.99
        match = re.search(r"([A-Za-z\s]+)[\.\s]*\$?(\d+\.\d{2})", line)

        if match:

            name = clean_item_name(match.group(1))
            price = float(match.group(2))

            print("MATCH:", name, price)

            items.append({
                "name": name,
                "quantity": 1,
                "price": price
            })

    return items

# --------------------------------------------------
# UPSERT SALES
# --------------------------------------------------

def upsert_sale(item):

    with engine.begin() as conn:

        # ensure menu item exists
        conn.execute(text("""
        INSERT INTO menu_items (item_name)
        VALUES (:name)
        ON CONFLICT (item_name) DO NOTHING
        """), {"name": item["name"]})

        # get item id
        result = conn.execute(text("""
        SELECT item_id
        FROM menu_items
        WHERE LOWER(TRIM(item_name)) = LOWER(TRIM(:name))
        """), {"name": item["name"]})

        row = result.fetchone()

        if not row:
            print("Menu item not found:", item["name"])
            return

        item_id = row[0]

        orders = item["quantity"]
        revenue = item["quantity"] * item["price"]

        print("Updating:", item["name"], "Orders:", orders, "Revenue:", revenue)

        conn.execute(text("""
        INSERT INTO menu_sales (item_id,orders,revenue)
        VALUES (:item_id,:orders,:revenue)

        ON CONFLICT (item_id)
        DO UPDATE SET
        orders = menu_sales.orders + EXCLUDED.orders,
        revenue = menu_sales.revenue + EXCLUDED.revenue
        """), {
            "item_id": item_id,
            "orders": orders,
            "revenue": revenue
        })

# --------------------------------------------------
# PROCESS RECEIPTS
# --------------------------------------------------

def process_all_receipts():

    print("\nProcessing receipts...\n")

    files = os.listdir(RECEIPT_FOLDER)

    if not files:
        print("No receipts found")
        return

    for file in files:

        file_path = os.path.join(RECEIPT_FOLDER, file)

        try:

            print("Processing:", file)

            if not file.lower().endswith(".pdf"):
                print("Skipping non-PDF:", file)
                continue

            text_content = extract_pdf_content(file_path)

            items = extract_items(text_content)

            print("Items detected:", items)

            if not items:
                print("No menu items detected in receipt")

            for item in items:

                upsert_sale(item)

            shutil.move(
                file_path,
                os.path.join(PROCESSED_FOLDER, file)
            )

            print("Receipt processed:", file)

        except Exception as e:

            print("Error processing:", file)
            print(e)

# --------------------------------------------------
# RUN SCRIPT
# --------------------------------------------------

if __name__ == "__main__":

    process_all_receipts()