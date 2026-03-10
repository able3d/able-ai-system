import time
from run_pipeline import run_pipeline

while True:

    print("Starting auto inventory pipeline...")

    run_pipeline()

    print("Waiting 60 seconds before next check...")

    time.sleep(60)
