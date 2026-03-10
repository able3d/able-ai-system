import threading
import subprocess
import webview
import time


def start_pipeline():
    subprocess.Popen(["python", "auto_pipeline.py"])


def start_streamlit():
    subprocess.Popen(["streamlit", "run", "dashboard.py"])


threading.Thread(target=start_pipeline).start()
threading.Thread(target=start_streamlit).start()

time.sleep(5)

webview.create_window(
    "Liquor Inventory AI",
    "http://localhost:8501",
    width=1200,
    height=800
)

webview.start()
