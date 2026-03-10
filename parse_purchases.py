import os
import psycopg2
from services_pdf_service import extract_text_from_pdf
from services_revenue_service import extract_items

def process_invoices():

    conn = psycopg2.connect(
        dbname="inventory_ai",
        user="postgres",
        password="postgres123",
        host="localhost",
        port="5432"
    )

    cursor = conn.cursor()

    folder = "data/invoices"

    for file in os.listdir(folder):

        if file.endswith(".pdf"):

            path = os.path.join(folder, file)

            print("Processing invoice:", file)

            text = extract_text_from_pdf(path)

            items = extract_items(text)

            for item in items:

                cursor.execute(
                    """
                    INSERT INTO purchase_data
                    (invoice_number,item_name,quantity,item_price)
                    VALUES (%s,%s,%s,%s)
                    """,
                    (
                        file,
                        item["name"],
                        item["qty"],
                        item["price"]
                    )
                )

    conn.commit()
    cursor.close()
    conn.close()

    print("Invoices processed")
