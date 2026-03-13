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
# EXTRACT ITEMS FROM RECEIPT TEXT
# --------------------------------------------------

def extract_items(text):

    items = []

    lines = text.split("\n")

    for line in lines:

        line = line.strip()

        if not line:
            continue

        # Ignore totals / taxes
        if any(x in line.lower() for x in ["subtotal","tax","total","change","balance"]):
            continue

        # Pattern: 2 Doro Wat 15.99
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

        # Pattern: Doro Wat 15.99
        match = re.search(r"(.+?)\s+\$?(\d+\.\d{2})", line)

        if match:

            name = match.group(1).strip()
            price = float(match.group(2))

            items.append({
                "name": name,
                "quantity": 1,
                "price": price
            })

    return items


# --------------------------------------------------
# INSERT OR UPDATE SALES
# --------------------------------------------------

def upsert_sale(item):

    with engine.begin() as conn:

        # Ensure menu item exists
        conn.execute(text("""
        INSERT INTO menu_items (item_name)
        VALUES (:name)
        ON CONFLICT (item_name) DO NOTHING
        """), {"name": item["name"]})

        # Get item_id (case-insensitive)
        result = conn.execute(text("""
        SELECT item_id
        FROM menu_items
        WHERE LOWER(item_name) = LOWER(:name)
        """), {"name": item["name"]})

        row = result.fetchone()

        if not row:
            print("Menu item not found:", item["name"])
            return

        item_id = row[0]

        orders = item["quantity"]
        revenue = item["quantity"] * item["price"]

        print("Revenue calculated:", revenue)

        # UPSERT sales
        conn.execute(text("""
        INSERT INTO menu_sales (item_id, orders, revenue)
        VALUES (:item_id, :orders, :revenue)
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

    for file in files:

        if not file.lower().endswith(".pdf"):
            continue

        file_path = os.path.join(RECEIPT_FOLDER, file)

        print("Reading receipt:", file)

        try:

            text_content = ""

            # Extract PDF text
            with pdfplumber.open(file_path) as pdf:

                for page in pdf.pages:

                    text = page.extract_text()

                    if text:
                        text_content += text + "\n"

            # Parse items
            items = extract_items(text_content)

            print("Parsed items:", items)

            # Insert sales
            for item in items:

                upsert_sale(item)

                print("Updated sales:", item["name"])

            # Move processed receipt
            shutil.move(
                file_path,
                os.path.join(PROCESSED_FOLDER, file)
            )

            print("Receipt processed:", file)

        except Exception as e:

            print("Error processing receipt:", file)
            print(e)