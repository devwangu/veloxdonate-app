import json
import os
import webbrowser
import time

CONFIG_PATH = "config.json"
token = ""

# Wait up to 5 seconds for app.py to generate config.json
for _ in range(10):
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
                token = config.get("admin_token", "")
                if token:
                    break
        except Exception:
            pass
    time.sleep(0.5)

if token:
    port = config.get("backend_port", 5000)
    url = f"http://127.0.0.1:{port}/controller?token={token}"
    print(f"Opening Controller: {url}")
    webbrowser.open(url)
else:
    print("Error: Could not retrieve admin_token from config.json")
