from etl.google_drive_etl import download_all_files
import parse_invoices
import parse_receipts

def run_pipeline():

    print("Starting pipeline")

    download_all_files("1mLUXpBHo6ki0kICoPLHpaYYKqGDGEW_u", "data/invoices")
    download_all_files("10OsCAFFowvrSENlYIfOTWtBZZ4GxLncE", "data/receipts")

    print("Parsing invoices...")
    parse_invoices.process_all_invoices()

    print("Parsing receipts...")
    parse_receipts.process_receipts()

    print("Pipeline finished")
if __name__ == "__main__":
    run_pipeline()
