import subprocess
import webbrowser
import time

print("Starting Inventory AI App...")

# start auto pipeline
subprocess.Popen(["python", "auto_pipeline.py"])

# wait for backend to start
time.sleep(3)

# start streamlit dashboard
subprocess.Popen([
    "streamlit",
    "run",
    "dashboard.py"
])

# open browser automatically
time.sleep(5)

webbrowser.open("http://localhost:8501")
