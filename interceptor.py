import uiautomation as auto
import time
import os
import re
import ctypes
from ctypes import wintypes
from PIL import Image
import pytesseract
import json
import requests

# Load config
import sys

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
BACKEND_PORT = 5000

if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
            BACKEND_PORT = config.get("backend_port", 5000)
    except Exception as e:
        print(f"Error loading config: {e}")

WEBHOOK_URL = f"http://localhost:{BACKEND_PORT}/api/webhook/payment"

def parse_ocr_text(text, regex_formats):
    # Remove any newlines or spaces to make matching easier
    flat_text = text.replace("\n", "").replace(" ", "")
    
    for fmt in regex_formats:
        pattern = fmt.get("pattern", "")
        if not pattern:
            continue
            
        try:
            match = re.search(pattern, flat_text)
            if match and match.group(1):
                amount_str = match.group(1).replace(",", "")
                return {"type": fmt.get("type", "in"), "amount": float(amount_str)}
        except:
            pass
            
    return None

import ocr_engine

import sys

def run_interceptor_loop():
    # Initialize COM in background thread to prevent CoInitialize warning
    try:
        import pythoncom
        pythoncom.CoInitialize()
    except Exception:
        pass
    try:
        auto.InitializeUIAutomationInThread()
    except Exception:
        pass

    # Reconfigure stdout to use UTF-8 to prevent UnicodeEncodeError in Windows Console
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
        
    print("==================================================")
    print(" LINE PC Interceptor (Background Worker Started)")
    print("==================================================")
    
    def get_target_window():
        global BACKEND_PORT
        target_title = ""
        regex_formats = []
        # Reload config
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    BACKEND_PORT = cfg.get("backend_port", 5000)
                    target_title = cfg.get("line_window_title", "")
                    regex_formats = cfg.get("regex_formats", [])
            except Exception as e:
                pass
                
        if target_title:
            win = auto.WindowControl(searchDepth=1, Name=target_title)
            return win, target_title, regex_formats
        else:
            # Fallback to ChatWindow class
            win = auto.WindowControl(searchDepth=1, ClassName="ChatWindow")
            if not win.Exists(0):
                win = auto.WindowControl(searchDepth=1, Name="LINE")
            return win, "LINE Chat", regex_formats

    last_item_id = None
    known_count = 0
    has_warned_missing = False
    
    with auto.UIAutomationInitializerInThread():
        while True:
            try:
                line_window, window_name, regex_formats = get_target_window()
                
                if not line_window or not line_window.Exists(0):
                    if not has_warned_missing:
                        print(f"[Interceptor Worker] Waiting for target window ({window_name})...")
                        has_warned_missing = True
                    time.sleep(3)
                    continue
                    
                if has_warned_missing:
                    print(f"[Interceptor Worker] Target window ({window_name}) connected!")
                    has_warned_missing = False

                hwnd = line_window.NativeWindowHandle
                list_view = line_window.ListControl(ClassName="LcListView")
                
                if not list_view.Exists(0):
                    time.sleep(2)
                    continue

                current_items = list_view.GetChildren()
                valid_items = []
                for item in current_items:
                    try:
                        if 100 < item.BoundingRectangle.height() < 600:
                            valid_items.append(item)
                    except:
                        pass
                
                current_count = len(valid_items)
                current_last_id = None
                current_last_rect = None
                
                if current_count > 0:
                    try:
                        current_last_item = valid_items[-1]
                        current_last_id = current_last_item.GetRuntimeId()
                        current_last_rect = current_last_item.BoundingRectangle
                    except Exception as e:
                        pass

                # Trigger detection if the last message RuntimeId has changed
                is_new_message = False
                if current_last_id is not None and last_item_id is not None and current_last_id != last_item_id:
                    is_new_message = True
                elif current_last_id is not None and last_item_id is None:
                    # Initial state tracking
                    last_item_id = current_last_id

                if is_new_message:
                    print(f"\n[!] New message detected in LINE chat! (RuntimeID changed)")
                    win_rect = line_window.BoundingRectangle
                    item_rect = current_last_rect
                    
                    raw_text = ocr_engine.do_ocr_on_item(hwnd, win_rect, item_rect)
                    tx = parse_ocr_text(raw_text, regex_formats)
                    
                    if tx:
                        print(f"[Interceptor Worker] MATCH FOUND! Type: {tx['type'].upper()} | Amount: {tx['amount']} THB")
                        try:
                            webhook_url = f"http://localhost:{BACKEND_PORT}/api/webhook/payment"
                            resp = requests.post(webhook_url, json=tx, timeout=5)
                            print(f"[Interceptor Worker] Webhook notification sent! ({resp.status_code})")
                        except Exception as e:
                            print(f"[Interceptor Worker] Webhook error: {e}")
                    else:
                        print("[Interceptor Worker] OCR finished, but text did not match any regex pattern.")
                    
                    last_item_id = current_last_id
                    known_count = current_count
                else:
                    known_count = current_count

            except Exception as e:
                # Catch non-fatal errors to keep background thread running
                pass
                
            time.sleep(2)

def main():
    run_interceptor_loop()

if __name__ == "__main__":
    main()
