import os
import re
import json
import pdfplumber
import easyocr
import pandas as pd
from etl import google_drive_etl


def extract_text_from_file(path):

    import pdfplumber
    import easyocr
    import numpy as np
    from PIL import Image

    text = ""

    # -------- PDF --------
    if path.lower().endswith(".pdf"):

        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

    # -------- IMAGE (PNG/JPG) --------
    elif path.lower().endswith((".png", ".jpg", ".jpeg")):

        reader = easyocr.Reader(['en'], gpu=False)

        img = Image.open(path)
        img = np.array(img)

        results = reader.readtext(img)

        for r in results:
            text += r[1] + "\n"

    return text





# Initialize OCR once (important for performance)
reader = easyocr.Reader(['en'])

RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"

os.makedirs(PROCESSED_DIR, exist_ok=True)


def extract_fields(text):
    # Invoice number detection
    invoice_match = re.search(
        r"(invoice\s*(no|number)?[:\s]*([A-Z]*[-]?\d+))",
        text,
        re.IGNORECASE
    )

    if invoice_match:
        invoice_number = invoice_match.group(3)
    date = re.search(r"Date[:\s]*([0-9/\-]+)", text)
    total = re.search(r"Total[:\s\$]*([\d,]+\.\d{2})", text)

    return {
        "invoice_number": invoice_number.group(1) if invoice_number else None,
        "date": date.group(1) if date else None,
        "total_amount": total.group(1) if total else None
    }


def parse_invoice(path):
    with pdfplumber.open(path) as pdf:
        text = ""
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"

    structured = extract_fields(text)
    structured["file_name"] = os.path.basename(path)

    return structured

def extract_text_from_image(path):
    results = reader.readtext(path, detail=0)
    return "\n".join(results)








def main():
    results = []

    for file in os.listdir(RAW_DIR):
        if file.endswith(".pdf"):
            path = os.path.join(RAW_DIR, file)
            parsed = parse_invoice(path)
            results.append(parsed)
            print(f"Parsed: {file}")

    with open(f"{PROCESSED_DIR}/invoices_structured.json", "w") as f:
        json.dump(results, f, indent=4)

    print("Structured extraction complete.")


if __name__ == "__main__":
    main()



def extract_invoice_data(text):

    import re
    import pandas as pd

    invoice_number = None
    vendor_name = None
    date = None
    total_amount = None
    address = None

    # -------- Invoice Number --------
    invoice_match = re.search(r"\b\d{5,}\b", text)
    if invoice_match:
        invoice_number = invoice_match.group(0)

    # -------- Date --------
    date_match = re.search(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", text)
    if date_match:
        date = date_match.group(0)

    # -------- Total --------
    total_match = re.search(r"(?i)total.*?([\d,]+\.\d{2})", text)
    if total_match:
        total_amount = total_match.group(1)

    # -------- Vendor --------
    lines = text.split("\n")
    if len(lines) > 0:
        vendor_name = lines[0].strip()

    # -------- Address --------
    address_match = re.search(r"\d{3,}.*?(?:VA|Virginia|Tripura).*?\d{5,6}", text)
    if address_match:
        address = address_match.group(0)

    # -------- Items --------
    items = []

    lines = text.split("\n")

    for line in lines:

        # Pattern: Item name + quantity + price
        match = re.search(r"([A-Za-z0-9\s\-\']+)\s+(\d+)\s+(\d+\.\d{2})", line)

        if match:

           item_name = match.group(1).strip()
           quantity = int(match.group(2))
           price = float(match.group(3))

           if not re.search(r"total|tax|invoice|amount", item_name.lower()):

                items.append({
                    "item_name": item_name,
                    "quantity": quantity,
                    "item_price": price
                })
    # -------- Combine --------

    structured_data = []

    for item in items:

        structured_data.append({
            "invoice_number": invoice_number,
            "vendor_name": vendor_name,
            "date": date,
            "total_amount": total_amount,
            "address": address,
            "item_name": item["item_name"],
            "quantity": item["quantity"],
            "item_price": item["item_price"]
        })

    return pd.DataFrame(structured_data)

   


def process_all_invoices():
    # Download new invoices from Google Drive
    # google_drive_etl.download_invoices()

    folder = "data/raw"
    all_data = []

    for file in os.listdir(folder):
        path = os.path.join(folder, file)

        if file.lower().endswith(".pdf"):
            text = extract_text_from_file(path)

        elif file.lower().endswith(".png"):
            text = extract_text_from_image(path)

        else:
            continue

        # Temporary debug print
        print(f"Processing: {file}")
        print("Extracted text preview:")
        print(text[:200])  # show first 200 characters

        # You probably already have extract_invoice_data()
        df = extract_invoice_data(text)

        if not df.empty:
            all_data.append(df)

    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)
        print("Invoices parsed successfully.")
        print(final_df.head())
    else:
        print("No structured data extracted.")
    final_df = pd.concat(all_data, ignore_index=True)
    print("Invoices parsed successfully.")
    print(final_df)

    from sqlalchemy import create_engine

    engine = create_engine("postgresql://postgres:postgres123@localhost:5432/inventory_ai")

    final_df.drop_duplicates(subset=["invoice_number"], inplace=True)

    final_df.to_sql(
         "invoice_data",
         engine,
         if_exists="append",
         index=False,
         method="multi"
    ) 



    print("Inserted into PostgreSQL successfully.")
