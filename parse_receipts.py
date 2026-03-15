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

    name = name.strip()

    name = re.sub(r"[^a-zA-Z0-9\s]", "", name)

    name = re.sub(r"\s+", " ", name)

    return name.lower()

# --------------------------------------------------
# PDF EXTRACTION
# --------------------------------------------------

def extract_pdf_content(file_path):

    text_content = ""

    with pdfplumber.open(file_path) as pdf:

        for page in pdf.pages:

            tables = page.extract_tables()

            if tables:

                for table in tables:

                    for row in table:

                        if not row:
                            continue

                        row_text = " ".join(str(c) for c in row if c)

                        text_content += row_text + "\n"

            text = page.extract_text()

            if text:
                text_content += text + "\n"

    return text_content

# --------------------------------------------------
# PARSE ITEMS
# --------------------------------------------------

def extract_items(text):

    items = []

    lines = text.split("\n")

    for line in lines:

        line = line.strip()

        if not line:
            continue

        lower = line.lower()

        # skip receipt summary lines
        if any(x in lower for x in [
            "subtotal","tax","total","tip",
            "change","payment","visa","thank",
            "balance","cash","card"
        ]):
            continue

        # Pattern: 2 Doro Wat 15.99
        match = re.search(r"(\d+)\s+([A-Za-z\s]+?)\s+\$?(\d+\.\d{2})", line)

        if match:

            quantity = int(match.group(1))
            name = clean_item_name(match.group(2))
            price = float(match.group(3))

            items.append({
                "name": name,
                "quantity": quantity,
                "price": price
            })

            continue

        # Pattern: Doro Wat 15.99
        match = re.search(r"([A-Za-z\s]+?)\s+\$?(\d+\.\d{2})", line)

        if match:

            name = clean_item_name(match.group(1))
            price = float(match.group(2))

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
        VALUES (LOWER(:name))
        ON CONFLICT (item_name) DO NOTHING
        """), {"name": item["name"]})

        # get item id
        result = conn.execute(text("""
        SELECT item_id
        FROM menu_items
        WHERE TRIM(LOWER(item_name)) = TRIM(LOWER(:name))
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

    print("Processing receipts...")

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

            for item in items:

                upsert_sale(item)

            shutil.move(
                file_path,
                os.path.join(PROCESSED_FOLDER, file)
            )

            print("Receipt processed:", file)

        except Exception as e:

            print("Error:", file)
            print(e)

# --------------------------------------------------
# RUN SCRIPT
# --------------------------------------------------

if __name__ == "__main__":

    process_all_receipts()