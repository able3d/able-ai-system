import time
from etl.google_drive_etl import list_files_in_folder, download_file
from etl.parse_invoices import process_invoice_file

processed_files = set()

FOLDER_NAME = "Invoices"

def check_for_new_invoices():
    files = list_files_in_folder(FOLDER_NAME)

    for file in files:
        file_id = file['id']
        file_name = file['name']

        if file_id not in processed_files:

            print(f"Processing new invoice: {file_name}")

            local_path = download_file(file_id, file_name)

            process_invoice_file(local_path)

            processed_files.add(file_id)


while True:

    check_for_new_invoices()

    print("Waiting for new invoices...")

    time.sleep(60)
