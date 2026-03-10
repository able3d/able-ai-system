import os
import pdfplumber
import shutil
from sqlalchemy import create_engine, text

# --------------------------------------------------
# FOLDERS
# --------------------------------------------------

RECEIPT_FOLDER = "data/receipts"
PROCESSED_FOLDER = "data/processed_receipts"

os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

engine = create_engine(
    "postgresql://postgres:postgres123@localhost:5432/inventory_ai"
)

# --------------------------------------------------
# EXTRACT ITEMS FROM RECEIPT TEXT
# --------------------------------------------------

def extract_items(text):

    items = []

    lines = text.split("\n")

    for line in lines:

        parts = line.split()

        if len(parts) < 3:
            continue

        try:

            quantity = int(parts[-2])
            price = float(parts[-1].replace("$", ""))

            name = " ".join(parts[:-2])

            items.append({
                "name": name,
                "quantity": quantity,
                "price": price
            })

        except:
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
