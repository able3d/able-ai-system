import time
import parse_invoices
import parse_receipts


def run_pipeline():

    print("Checking for new files...")

    parse_invoices.process_invoices()

    parse_receipts.process_receipts()

    print("Pipeline finished\n")


while True:

    run_pipeline()

    # check every 60 seconds
    time.sleep(60)
