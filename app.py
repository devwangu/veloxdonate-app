import os
import sys

# Ensure current directory is in sys.path for Embedded Python & custom environments
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import time
import uuid
import queue
import base64
import io
import re
import asyncio
import hashlib
import secrets
import edge_tts
import urllib.request
from flask import Flask, request, jsonify, Response, send_from_directory
import shutil
import zipfile
import qrcode
import db

# Helper functions for PyInstaller executable paths
def get_bundle_dir():
    if getattr(sys, 'frozen', False):
        return getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.dirname(os.path.abspath(__file__))

def get_exe_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))

BUNDLE_DIR = get_bundle_dir()
EXE_DIR = get_exe_dir()
CONFIG_PATH = os.path.join(EXE_DIR, "config.json")

# Initialize Flask app
app = Flask(__name__)

# Serve static files from root directory
@app.route('/')
@app.route('/donate')
def serve_index():
    return send_from_directory(BUNDLE_DIR, 'index.html')

@app.route('/overlay')
@app.route('/widget/alert')
def serve_overlay():
    token = request.args.get('token')
    if not token or token != ADMIN_TOKEN:
        return "401 Unauthorized: Invalid or missing token for Overlay", 401
    return send_from_directory(BUNDLE_DIR, 'overlay.html')

@app.route('/widget/top')
def serve_widget_top():
    token = request.args.get('token')
    if not token or token != ADMIN_TOKEN:
        return "401 Unauthorized: Invalid or missing token for Widget", 401
    return send_from_directory(BUNDLE_DIR, 'widget_top.html')

@app.route('/widget/recent')
def serve_widget_recent():
    token = request.args.get('token')
    if not token or token != ADMIN_TOKEN:
        return "401 Unauthorized: Invalid or missing token for Widget", 401
    return send_from_directory(BUNDLE_DIR, 'widget_recent.html')

@app.route('/widget/goal')
def serve_widget_goal():
    token = request.args.get('token')
    if not token or token != ADMIN_TOKEN:
        return "401 Unauthorized: Invalid or missing token for Widget", 401
    return send_from_directory(BUNDLE_DIR, 'widget_goal.html')

@app.route('/style.css')
def serve_style():
    return send_from_directory(BUNDLE_DIR, 'style.css')

@app.route('/static/<path:filename>')
def serve_static(filename):
    exe_static_dir = os.path.join(EXE_DIR, 'static')
    exe_file_path = os.path.join(exe_static_dir, filename)
    if os.path.exists(exe_file_path):
        return send_from_directory(exe_static_dir, filename)
    static_dir = os.path.join(BUNDLE_DIR, 'static')
    return send_from_directory(static_dir, filename)

@app.route('/controller')
def serve_controller():
    # Require token
    token = request.args.get('token')
    if not token or token != ADMIN_TOKEN:
        return "401 Unauthorized: Invalid or missing admin token", 401
    return send_from_directory(BUNDLE_DIR, 'controller.html')

import secrets

# Global Config Defaults
APP_VERSION = "0.1.1"
PROMPTPAY_ID = "0812345678"
BACKEND_PORT = 5000
TIMEOUT_SECONDS = 300  # 5 Minutes for UI Timer
BACKEND_BUFFER_SECONDS = 60 # 1 Minute extra grace period buffer for backend matching (Total 6 mins)
ADMIN_TOKEN = ""
VELOX_DONATE_TOKEN = ""
PORTAL_URL = "https://donate.veloxgg.com"
NETWORK_MODE = 2
MINIMUM_DONATION = 10.0
LINE_WINDOW_TITLE = ""
REGEX_FORMATS = [
    {"name": "Krungthai", "pattern": "เงินเข้า\\+?([\\d,]+\\.\\d{2})", "type": "in"},
    {"name": "SCB", "pattern": "การเงินเข้า\\+?([\\d,]+\\.\\d{2})", "type": "in"},
    {"name": "KBank", "pattern": "จํานวนเงิน([\\d,]+\\.\\d{2})", "type": "in"}
]
ALERT_CONFIG = {
    "template_text": "{name} สนับสนุน {amount} บาท!",
    "color_name": "#fbbf24",
    "color_amount": "#34d399",
    "color_message": "#ffffff",
    "image_url": "https://media.giphy.com/media/3o7TKSjRrfIPjeiVyM/giphy.gif",
    "image_position": "top",
    "font_family": "Prompt",
    "font_size": 32,
    "word_wrap": True,
    "duration": 6,
    "anim_in": "slideInDown",
    "anim_out": "slideOutUp",
    "anim_speed": 0.8,
    "sound_effect": "chime",
    "sound_volume": 80,
    "enable_tts": True,
    "tts_voice": "th-TH-PremwadeeNeural",
    "min_display": 0.0,
    "filter_badwords": True,
    "badwords_custom": ""
}

TOP_DONATOR_CONFIG = {
    "start_date": "",
    "color_name": "#ffffff",
    "color_amount": "#fbbf24",
    "font_family_name": "Prompt",
    "font_family_amount": "Prompt",
    "font_size_name": 28,
    "font_size_amount": 28,
    "item_gap": 15,
    "layout_mode": "name_first",
    "limit": 5,
    "filter_badwords": True,
    "custom_badwords": ""
}

RECENT_DONATOR_CONFIG = {
    "color_name": "#ffffff",
    "color_amount": "#34d399",
    "font_family_name": "Prompt",
    "font_family_amount": "Prompt",
    "font_size_name": 28,
    "font_size_amount": 28,
    "item_gap": 15,
    "layout_mode": "name_first",
    "limit": 5,
    "filter_badwords": True,
    "custom_badwords": ""
}

GOAL_CONFIG = {
    "title": "เป้าหมายสนับสนุนสตรีมเมอร์",
    "start_date": "",
    "end_date": "",
    "target_amount": 5000.0,
    "initial_amount": 0.0,
    "color_bar": "#22c55e",
    "color_bg": "#1e293b",
    "color_text": "#ffffff",
    "font_family_title": "Prompt",
    "font_family_number": "Prompt",
    "font_size": 24
}

NETWORK_CONFIG = {
    "active_mode": "cloudflare",
    "modes": {
        "cloudflare": {"name": "Cloudflare Quick Tunnel", "status": "active", "type": "free"},
        "branded": {"name": "VeloxGG Branded Hub", "status": "locked", "badge": "🔒 เฉพาะสมาชิก VeloxGG เท่านั้น (เปิดบริการเร็วๆ นี้)"},
        "custom_domain": {"name": "Streamer Custom Domain", "status": "locked", "badge": "🔒 เฉพาะสมาชิก VeloxGG PRO เท่านั้น (เปิดบริการเร็วๆ นี้)"}
    }
}

STREAMER_NAME = "Streamer"

def load_config():
    global PROMPTPAY_ID, BACKEND_PORT, TIMEOUT_SECONDS, ADMIN_TOKEN, VELOX_DONATE_TOKEN, PORTAL_URL, NETWORK_MODE, MINIMUM_DONATION, LINE_WINDOW_TITLE, REGEX_FORMATS, ALERT_CONFIG, TOP_DONATOR_CONFIG, RECENT_DONATOR_CONFIG, GOAL_CONFIG, NETWORK_CONFIG, STREAMER_NAME
    config = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            
    # Generate secure random unique token for every streamer
    placeholder_tokens = ["velox_secret_token", "token_velox_default_key", "token_default_secret", ""]
    if "admin_token" not in config or not config["admin_token"] or config["admin_token"] in placeholder_tokens:
        config["admin_token"] = f"token_{secrets.token_urlsafe(16)}"
        
    if "minimum_donation" not in config:
        config["minimum_donation"] = 10.0
        
    if "streamer_name" not in config:
        config["streamer_name"] = "Streamer"

    if "velox_donate_token" not in config:
        config["velox_donate_token"] = ""
    if "portal_url" not in config:
        config["portal_url"] = "https://donate.veloxgg.com"
    if "network_mode" not in config:
        config["network_mode"] = 2 if config.get("velox_donate_token") else 1

    if "line_window_title" not in config:
        config["line_window_title"] = ""
    if "regex_formats" not in config:
        config["regex_formats"] = REGEX_FORMATS
    if "alert_config" not in config:
        config["alert_config"] = ALERT_CONFIG
    else:
        for k, v in ALERT_CONFIG.items():
            if k not in config["alert_config"]:
                config["alert_config"][k] = v

    if "top_donator_config" not in config:
        config["top_donator_config"] = TOP_DONATOR_CONFIG
    else:
        for k, v in TOP_DONATOR_CONFIG.items():
            if k not in config["top_donator_config"]:
                config["top_donator_config"][k] = v
        TOP_DONATOR_CONFIG = config["top_donator_config"]
        
    # Save back if we added defaults
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving config: {e}")

    STREAMER_NAME = config.get("streamer_name", STREAMER_NAME)
    PROMPTPAY_ID = config.get("promptpay_id", PROMPTPAY_ID)
    BACKEND_PORT = config.get("backend_port", BACKEND_PORT)
    TIMEOUT_SECONDS = config.get("timeout_seconds", TIMEOUT_SECONDS)
    ADMIN_TOKEN = config.get("admin_token", ADMIN_TOKEN)
    VELOX_DONATE_TOKEN = config.get("velox_donate_token", VELOX_DONATE_TOKEN)
    PORTAL_URL = config.get("portal_url", PORTAL_URL)
    NETWORK_MODE = int(config.get("network_mode", NETWORK_MODE))
    MINIMUM_DONATION = config.get("minimum_donation", MINIMUM_DONATION)
    LINE_WINDOW_TITLE = config.get("line_window_title", LINE_WINDOW_TITLE)
    REGEX_FORMATS = config.get("regex_formats", REGEX_FORMATS)
    ALERT_CONFIG = config.get("alert_config", ALERT_CONFIG)
    
    print(f"Config loaded: StreamerName={STREAMER_NAME}, PromptPay={PROMPTPAY_ID}, Mode={NETWORK_MODE}, MinDonation={MINIMUM_DONATION}")
    
    # Initialize SQLite Database
    db.init_db()

# In-Memory State
pending_donations = {} # donation_id -> donation_dict
completed_donations = []
listeners = [] # Queue list for OBS SSE streams

# PromptPay QR Code Generation Functions
def crc16(data: str) -> str:
    crc = 0xFFFF
    for char in data.encode('ascii'):
        crc ^= (char << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return f"{crc:04X}"

def generate_promptpay_payload(promptpay_id, amount):
    # Clean the PromptPay ID (remove dashes, spaces)
    target = promptpay_id.replace("-", "").replace(" ", "").strip()
    
    pfi = "000201"
    poi = "010212" # Dynamic QR (with amount)
    
    # Merchant Account Info (Tag 29)
    if len(target) == 10:  # Phone number starting with 0
        formatted_id = "0066" + target[1:]
        account_info = f"0016A0000006770101110113{formatted_id}"
    else:  # National ID or Tax ID (13 digits)
        account_info = f"0016A0000006770101110213{target}"
        
    merchant_info = f"29{len(account_info):02d}{account_info}"
    country_code = "5802TH"
    currency_code = "5303764"
    
    # Amount (Tag 54)
    formatted_amount = f"{amount:.2f}"
    amount_field = f"54{len(formatted_amount):02d}{formatted_amount}"
    
    # CRC Calculation
    payload_to_crc = f"{pfi}{poi}{merchant_info}{country_code}{currency_code}{amount_field}6304"
    checksum = crc16(payload_to_crc)
    return f"{payload_to_crc}{checksum}"

# Endpoints
@app.route('/api/config', methods=['GET'])
def get_config():
    return jsonify({
        "streamer_name": STREAMER_NAME,
        "promptpay_id": PROMPTPAY_ID,
        "minimum_donation": MINIMUM_DONATION,
        "timeout_seconds": TIMEOUT_SECONDS
    })

@app.route('/api/donate', methods=['POST'])
def donate():
    """
    Submits a new pending donation, calculates Decimal Confirmation,
    and returns PromptPay QR Code payload.
    """
    data = request.json or {}
    name = data.get("name", "Anonymous").strip()
    message = data.get("message", "").strip()
    
    try:
        amount = float(data.get("amount", 0))
    except ValueError:
        return jsonify({"error": "Invalid amount"}), 400
        
    if amount < 1.0:
        return jsonify({"error": "จำนวนเงินขั้นต่ำสำหรับการทำรายการคือ 1.00 บาท"}), 400
        
    current_time = time.time()
    
    # Clean up expired pending donations (after 5 mins + 1 min buffer = 6 mins total)
    expired_ids = []
    for d_id, d in pending_donations.items():
        if d["status"] == "pending" and (current_time - d["timestamp"]) > (TIMEOUT_SECONDS + BACKEND_BUFFER_SECONDS):
            expired_ids.append(d_id)
    for d_id in expired_ids:
        db.mark_donation_abandoned(d_id)
        del pending_donations[d_id]
        print(f"Cleaned expired & abandoned pending donation: {d_id}")

    # Decimal Confirmation Logic
    # Find active decimal amounts in pending donations for the same base amount
    active_decimals = set()
    for d in pending_donations.values():
        if d["status"] == "pending" and int(d["amount"]) == int(amount):
            active_decimals.add(d["decimal_amount"])
            
    # Successively decrease by 0.01 until we find a free slot
    target_amount = amount
    while round(target_amount, 2) in active_decimals:
        target_amount -= 0.01
        
    target_amount = round(target_amount, 2)
    if target_amount <= 0:
        # Fallback if too many pending (unlikely for MVP)
        target_amount = amount
        
    # Create Donation Record
    donation_id = str(uuid.uuid4())
    pending_donations[donation_id] = {
        "id": donation_id,
        "name": name,
        "message": message,
        "amount": amount,
        "decimal_amount": target_amount,
        "timestamp": current_time,
        "status": "pending"
    }
    
    # Save to SQLite Database
    db.save_donation(donation_id, name, message, amount, "pending")
    
    # Generate PromptPay QR Base64 Image
    payload = generate_promptpay_payload(PROMPTPAY_ID, target_amount)
    
    qr = qrcode.QRCode(version=1, box_size=8, border=4)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1e293b", back_color="white") # Premium slate color
    
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    qr_base64 = "data:image/png;base64," + base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    print(f"Created pending donation {donation_id} for {name} | Base: {amount} THB -> Dec: {target_amount} THB")
    
    return jsonify({
        "donation_id": donation_id,
        "name": name,
        "amount": amount,
        "decimal_amount": target_amount,
        "qr_code": qr_base64,
        "timeout": TIMEOUT_SECONDS,
        "minimum_donation": MINIMUM_DONATION
    })

@app.route('/api/donation/status/<donation_id>', methods=['GET'])
def get_donation_status(donation_id):
    """
    Checks if a pending donation is paid or expired.
    """
    donation = pending_donations.get(donation_id)
    if not donation:
        # Check in completed list
        for d in completed_donations:
            if d["id"] == donation_id:
                return jsonify({"status": "success", "donation": d})
        return jsonify({"status": "expired_or_not_found"}), 404
        
    current_time = time.time()
    if (current_time - donation["timestamp"]) > TIMEOUT_SECONDS:
        # Return expired to UI, but keep in memory for backend buffer until 6 mins
        return jsonify({"status": "expired"}), 200
        
    return jsonify({"status": donation["status"]})

@app.route('/api/webhook/payment', methods=['POST'])
def webhook_payment():
    """
    Receives parsed payments from the LINE Interceptor and matches them to pending donations.
    """
    data = request.json or {}
    tx_type = data.get("type", "").lower()
    amount = data.get("amount", 0.0)
    
    print(f"[Webhook] Received: Type: {tx_type.upper()} | Amount: {amount} THB")
    
    if tx_type != "in":
        # Ignore withdrawals/money out
        return jsonify({"status": "ignored", "reason": "Not a deposit transaction"}), 200
        
    current_time = time.time()
    matched_donation = None
    
    # Try to match the exact decimal amount with active pending donations
    for d_id, d in list(pending_donations.items()):
        # Check if expired beyond 6 mins (300s + 60s buffer)
        if (current_time - d["timestamp"]) > (TIMEOUT_SECONDS + BACKEND_BUFFER_SECONDS):
            db.mark_donation_abandoned(d_id)
            del pending_donations[d_id]
            print(f"Cleaned abandoned pending donation in webhook: {d_id}")
            continue
            
        if d["status"] == "pending" and abs(d["decimal_amount"] - amount) < 0.001:
            matched_donation = d
            break
            
    if matched_donation:
        # Mark as success
        matched_donation["status"] = "success"
        matched_donation["payment_timestamp"] = current_time
        
        # Move to completed
        completed_donations.append(matched_donation)
        del pending_donations[matched_donation["id"]]
        
        # Mark as paid in SQLite Database
        db.mark_donation_paid(matched_donation["id"])
        
        print(f"[Webhook] MATCHED & SUCCESS: Donation ID {matched_donation['id']} from {matched_donation['name']} for {amount} THB!")
        
        # Notify SSE listeners (Only if amount >= MINIMUM_DONATION)
        notification = {
            "id": matched_donation["id"],
            "name": matched_donation["name"],
            "message": matched_donation["message"],
            "amount": matched_donation["amount"],
            "decimal_amount": matched_donation["decimal_amount"]
        }
        
        if matched_donation["amount"] >= MINIMUM_DONATION:
            for q in list(listeners):
                try:
                    q.put_nowait(json.dumps(notification))
                except Exception as e:
                    print(f"Error putting in queue: {e}")
        else:
            print(f"[Webhook] Payment matched ({matched_donation['amount']} THB), but skipped OBS overlay alert (Minimum is {MINIMUM_DONATION} THB).")
                
        return jsonify({
            "status": "success", 
            "message": f"Payment of {amount} matched with donation from {matched_donation['name']}"
        }), 200
        
    print(f"[Webhook] UNMATCHED: No pending donation found for amount {amount} THB")
    return jsonify({
        "status": "unmatched", 
        "message": f"No pending donation found for amount {amount}"
    }), 404

# Database Analytics APIs
@app.route('/api/donations/top', methods=['GET'])
def get_top_donations():
    try:
        limit = int(request.args.get('limit', TOP_DONATOR_CONFIG.get('limit', 10)))
    except ValueError:
        limit = TOP_DONATOR_CONFIG.get('limit', 10)
        
    start_date = request.args.get('start_date', TOP_DONATOR_CONFIG.get('start_date', ''))
    top_list = db.get_top_donators(limit=limit, start_date=start_date)
    return jsonify(top_list)

@app.route('/api/donations/recent', methods=['GET'])
def get_recent_donations():
    try:
        limit = int(request.args.get('limit', 10))
    except ValueError:
        limit = 10
    recent_list = db.get_recent_donations(limit=limit)
    return jsonify(recent_list)

@app.route('/api/donations/goal', methods=['GET'])
def get_donation_goal():
    start_date = GOAL_CONFIG.get("start_date", "")
    end_date = GOAL_CONFIG.get("end_date", "")
    raised = db.get_goal_total(start_date=start_date, end_date=end_date)
    initial = float(GOAL_CONFIG.get("initial_amount", 0.0))
    current_amount = raised + initial
    target_amount = max(1.0, float(GOAL_CONFIG.get("target_amount", 5000.0)))
    percentage = min(100.0, max(0.0, (current_amount / target_amount) * 100.0))
    
    return jsonify({
        "title": GOAL_CONFIG.get("title", ""),
        "current_amount": current_amount,
        "target_amount": target_amount,
        "percentage": round(percentage, 1),
        "start_date": start_date,
        "end_date": end_date,
        "goal_config": GOAL_CONFIG
    })

@app.route('/api/donations/stats', methods=['GET'])
def get_donation_stats():
    stats = db.get_donation_stats()
    return jsonify(stats)

@app.route('/api/stream')
def sse_stream():
    """
    SSE stream for OBS Studio overlay to receive real-time donation alerts.
    """
    token = request.args.get('token')
    if not token or token != ADMIN_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401
    def event_stream():
        q = queue.Queue()
        listeners.append(q)
        print(f"[SSE] Client connected. Total listeners: {len(listeners)}")
        try:
            # Yield a welcome message
            yield f"data: {json.dumps({'status': 'connected'})}\n\n"
            while True:
                # Block until we have a message
                data = q.get()
                yield f"data: {data}\n\n"
        except GeneratorExit:
            pass
        finally:
            if q in listeners:
                listeners.remove(q)
            print(f"[SSE] Client disconnected. Total listeners: {len(listeners)}")
            
    return Response(event_stream(), mimetype="text/event-stream")

# --- ADMIN CONTROLLER APIs ---
def check_admin_token():
    token = request.args.get("token") or (request.json and request.json.get("token"))
    if not token or token != ADMIN_TOKEN:
        return False
    return True

@app.route('/api/admin/windows', methods=['GET'])
def admin_get_windows():
    if not check_admin_token():
        return jsonify({"error": "Unauthorized"}), 401
    
    windows_set = set()
    
    # 1. Try pygetwindow
    try:
        import pygetwindow as gw
        for w in gw.getAllWindows():
            if w.title and w.title.strip():
                windows_set.add(w.title.strip())
    except Exception as e:
        print(f"[Windows Enumeration] pygetwindow error: {e}")

    # 2. Try ctypes Win32 EnumWindows
    try:
        import ctypes
        user32 = ctypes.windll.user32
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
        def enum_cb(hwnd, lparam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    title = buf.value.strip()
                    if title:
                        windows_set.add(title)
            return True
        user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    except Exception as e:
        print(f"[Windows Enumeration] ctypes error: {e}")

    # 3. Try uiautomation fallback
    try:
        import uiautomation as auto
        root = auto.GetRootControl()
        for child in root.GetChildren():
            name = child.Name.strip() if child.Name else ""
            if name:
                windows_set.add(name)
    except Exception as e:
        print(f"[Windows Enumeration] uiautomation error: {e}")

    return jsonify({"windows": sorted(list(windows_set))})

@app.route('/api/admin/config', methods=['GET', 'POST'])
def admin_config():
    global PROMPTPAY_ID, MINIMUM_DONATION, LINE_WINDOW_TITLE, REGEX_FORMATS, ALERT_CONFIG, TOP_DONATOR_CONFIG, RECENT_DONATOR_CONFIG, GOAL_CONFIG, STREAMER_NAME, VELOX_DONATE_TOKEN, PORTAL_URL, NETWORK_MODE
    if not check_admin_token():
        return jsonify({"error": "Unauthorized"}), 401
        
    if request.method == 'GET':
        from tunnel import tunnel_manager
        synced_slug = getattr(tunnel_manager, "synced_slug", None)
        sync_error = getattr(tunnel_manager, "sync_error", None)
        return jsonify({
            "streamer_name": STREAMER_NAME,
            "promptpay_id": PROMPTPAY_ID,
            "minimum_donation": MINIMUM_DONATION,
            "line_window_title": LINE_WINDOW_TITLE,
            "regex_formats": REGEX_FORMATS,
            "alert_config": ALERT_CONFIG,
            "top_donator_config": TOP_DONATOR_CONFIG,
            "recent_donator_config": RECENT_DONATOR_CONFIG,
            "goal_config": GOAL_CONFIG,
            "token": ADMIN_TOKEN,
            "velox_donate_token": VELOX_DONATE_TOKEN,
            "portal_url": PORTAL_URL,
            "network_mode": NETWORK_MODE,
            "synced_slug": synced_slug,
            "sync_error": sync_error,
            "tunnel_url": tunnel_manager.url
        })
        
    elif request.method == 'POST':
        data = request.json or {}
        
        if "streamer_name" in data:
            STREAMER_NAME = str(data["streamer_name"]).strip()
        if "promptpay_id" in data:
            PROMPTPAY_ID = data["promptpay_id"]
        if "minimum_donation" in data:
            try:
                MINIMUM_DONATION = float(data["minimum_donation"])
            except ValueError:
                pass
        if "line_window_title" in data:
            LINE_WINDOW_TITLE = data["line_window_title"]
        if "streamer_name" in data:
            STREAMER_NAME = str(data["streamer_name"]).strip()
        if "promptpay_id" in data:
            PROMPTPAY_ID = data["promptpay_id"]
        if "minimum_donation" in data:
            try:
                MINIMUM_DONATION = float(data["minimum_donation"])
            except ValueError:
                pass
        if "line_window_title" in data:
            LINE_WINDOW_TITLE = data["line_window_title"]
        if "velox_donate_token" in data:
            VELOX_DONATE_TOKEN = str(data["velox_donate_token"]).strip()
        if "portal_url" in data:
            PORTAL_URL = str(data["portal_url"]).strip()

        if "regex_formats" in data:
            REGEX_FORMATS = data["regex_formats"]
        if "alert_config" in data:
            ALERT_CONFIG = data["alert_config"]
        if "top_donator_config" in data:
            TOP_DONATOR_CONFIG = data["top_donator_config"]
        if "recent_donator_config" in data:
            RECENT_DONATOR_CONFIG = data["recent_donator_config"]
        if "goal_config" in data:
            GOAL_CONFIG = data["goal_config"]

        # Validate Token if user wants Network Mode 2
        requested_mode = int(data.get("network_mode", NETWORK_MODE))
        from tunnel import tunnel_manager
        sync_result = None

        if requested_mode == 2:
            test_url = tunnel_manager.url or f"http://localhost:{BACKEND_PORT}"
            valid = tunnel_manager.sync_portal(test_url, VELOX_DONATE_TOKEN, PORTAL_URL)
            if not valid:
                NETWORK_MODE = 1
                err_msg = getattr(tunnel_manager, "sync_error", None) or "Token ไม่ถูกต้อง (Invalid Velox Donate Token)"
                return jsonify({"error": f"ไม่สามารถเปิดใช้งานโหมด 2 ได้: {err_msg}"}), 400
            else:
                NETWORK_MODE = 2
        else:
            NETWORK_MODE = 1
            tunnel_manager.clear_portal()

        # Save to file
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
        except:
            config = {}
            
        config["streamer_name"] = STREAMER_NAME
        config["promptpay_id"] = PROMPTPAY_ID
        config["minimum_donation"] = MINIMUM_DONATION
        config["line_window_title"] = LINE_WINDOW_TITLE
        config["velox_donate_token"] = VELOX_DONATE_TOKEN
        config["portal_url"] = PORTAL_URL
        config["network_mode"] = NETWORK_MODE
        config["regex_formats"] = REGEX_FORMATS
        config["alert_config"] = ALERT_CONFIG
        config["top_donator_config"] = TOP_DONATOR_CONFIG
        config["recent_donator_config"] = RECENT_DONATOR_CONFIG
        config["goal_config"] = GOAL_CONFIG
        
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            return jsonify({"error": f"Failed to save config: {e}"}), 500
            
        return jsonify({
            "success": True,
            "message": "Config updated successfully",
            "sync_result": sync_result,
            "synced_slug": getattr(tunnel_manager, "synced_slug", None),
            "sync_error": getattr(tunnel_manager, "sync_error", None)
        })

def parse_version_tuple(ver_str):
    try:
        return tuple(int(x) for x in str(ver_str).strip().lstrip("v").split("."))
    except Exception:
        return (1, 0, 0)

@app.route('/api/admin/check_update', methods=['GET'])
def admin_check_update():
    if not check_admin_token():
        return jsonify({"error": "Unauthorized"}), 401

    try:
        version_api = f"{PORTAL_URL.rstrip('/')}/api/version"
        req = urllib.request.Request(
            version_api,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 VeloxDonateClient/1.0"
            }
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            latest = data.get("latestVersion", APP_VERSION)
            has_update = parse_version_tuple(latest) > parse_version_tuple(APP_VERSION)
            return jsonify({
                "current_version": APP_VERSION,
                "latest_version": latest,
                "has_update": has_update,
                "release_notes": data.get("releaseNotes", ""),
                "download_url": data.get("downloadUrl", ""),
                "published_at": data.get("publishedAt", "")
            })
    except Exception as e:
        print(f"[Update Check Exception] {e}")
        return jsonify({
            "current_version": APP_VERSION,
            "latest_version": APP_VERSION,
            "has_update": False,
            "release_notes": "",
            "download_url": "",
            "error": str(e)
        })

@app.route('/api/admin/test_download_zip', methods=['GET'])
def test_download_zip():
    zip_dir = os.path.join(EXE_DIR, "dist_zip")
    zip_path = os.path.join(zip_dir, "VeloxDonate_v1.0.0.zip")
    if not os.path.exists(zip_path):
        import zipfile
        os.makedirs(zip_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr("test_update.txt", "VeloxDonate Auto-Update Test File")
    return send_from_directory(zip_dir, "VeloxDonate_v1.0.0.zip", as_attachment=True)

UPDATE_STATE = {
    "status": "idle",
    "progress": 0,
    "message": "",
    "error": None
}

@app.route('/api/admin/update_progress', methods=['GET'])
def admin_update_progress():
    if not check_admin_token():
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify(UPDATE_STATE)

def run_background_update(download_url):
    global UPDATE_STATE
    try:
        UPDATE_STATE["status"] = "downloading"
        UPDATE_STATE["progress"] = 5
        UPDATE_STATE["message"] = "กำลังเตรียมดาวน์โหลดไฟล์อัปเดต..."
        UPDATE_STATE["error"] = None

        tmp_dir = os.path.join(EXE_DIR, "update_tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        zip_path = os.path.join(tmp_dir, "update.zip")

        # Download file with progress tracking
        req = urllib.request.Request(
            download_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 VeloxDonateClient/1.0"
            }
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            total_size = int(resp.headers.get('content-length', 0))
            downloaded = 0
            chunk_size = 65536
            with open(zip_path, 'wb') as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = int((downloaded / total_size) * 70) + 5
                        UPDATE_STATE["progress"] = min(percent, 75)
                        UPDATE_STATE["message"] = f"กำลังดาวน์โหลด ({int(downloaded/(1024*1024))}MB / {int(total_size/(1024*1024))}MB)..."
                    else:
                        UPDATE_STATE["progress"] = 50
                        UPDATE_STATE["message"] = f"กำลังดาวน์โหลด ({int(downloaded/(1024*1024))}MB)..."

        UPDATE_STATE["status"] = "extracting"
        UPDATE_STATE["progress"] = 80
        UPDATE_STATE["message"] = "กำลังแตกไฟล์อัปเดต..."

        extract_dir = os.path.join(tmp_dir, "extracted")
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        os.makedirs(extract_dir, exist_ok=True)

        import zipfile
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        # Locate root directory inside zip
        source_dir = extract_dir
        subdirs = [os.path.join(extract_dir, d) for d in os.listdir(extract_dir) if os.path.isdir(os.path.join(extract_dir, d))]
        if len(subdirs) == 1 and (os.path.exists(os.path.join(subdirs[0], "VeloxDonate.exe")) or os.path.exists(os.path.join(subdirs[0], "app.py"))):
            source_dir = subdirs[0]

        UPDATE_STATE["status"] = "applying"
        UPDATE_STATE["progress"] = 90
        UPDATE_STATE["message"] = "กำลังเตรียมรีสตาร์ตระบบเพื่อติดตั้งเวอร์ชันใหม่..."

        # Create auto-update batch script
        bat_script = os.path.join(tmp_dir, "apply_update.bat")
        
        bat_content = f"""@echo off
chcp 65001 >nul
echo VeloxDonate Auto-Updater
cd /d "{EXE_DIR}"
echo Waiting for application to exit...
timeout /t 2 /nobreak >nul

taskkill /f /im cloudflared.exe >nul 2>&1
taskkill /f /im VeloxDonate.exe >nul 2>&1
timeout /t 1 /nobreak >nul

echo Overwriting files with new update...
xcopy /s /e /y /h /r /q "{source_dir}\\*" "{EXE_DIR}\\"

echo Cleaning temporary update files...
rd /s /q "{tmp_dir}"

echo Restarting VeloxDonate...
cd /d "{EXE_DIR}"
if exist "{EXE_DIR}\\Start_VeloxDonate.bat" (
    start "" cmd /c "{EXE_DIR}\\Start_VeloxDonate.bat"
) else if exist "{EXE_DIR}\\VeloxDonate.exe" (
    start "" "{EXE_DIR}\\VeloxDonate.exe"
) else (
    start "" python app.py
)

del "%~f0"
"""
        with open(bat_script, "w", encoding="cp874") as f:
            f.write(bat_content)

        UPDATE_STATE["status"] = "completed"
        UPDATE_STATE["progress"] = 100
        UPDATE_STATE["message"] = "อัปเดตสำเร็จ! กำลังรีสตาร์ตแอปพลิเคชัน..."

        time.sleep(1)

        # Launch updater script via Windows ShellExecute (independent of Python process tree)
        if hasattr(os, 'startfile'):
            os.startfile(bat_script)
        else:
            subprocess.Popen(["cmd.exe", "/c", bat_script])

        os._exit(0)

    except Exception as e:
        print(f"[Auto-Update Failed] {e}")
        UPDATE_STATE["status"] = "error"
        UPDATE_STATE["error"] = str(e)
        UPDATE_STATE["message"] = f"การอัปเดตผิดพลาด: {e}"

@app.route('/api/admin/perform_update', methods=['POST'])
def admin_perform_update():
    if not check_admin_token():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}
    download_url = data.get("download_url", "")
    if not download_url:
        return jsonify({"error": "Missing download URL"}), 400

    if UPDATE_STATE["status"] in ["downloading", "extracting", "applying"]:
        return jsonify({"success": True, "message": "Update already in progress"})

    threading.Thread(target=run_background_update, args=(download_url,), daemon=True).start()
    return jsonify({"success": True, "message": "Update started"})

@app.route('/api/admin/donations', methods=['GET'])
def admin_get_donations():
    if not check_admin_token():
        return jsonify({"error": "Unauthorized"}), 401
    all_donations = db.get_all_donations(limit=200)
    stats = db.get_donation_stats()
    return jsonify({
        "donations": all_donations,
        "stats": stats
    })

@app.route('/api/admin/donations/<donation_id>', methods=['DELETE'])
def admin_delete_donation(donation_id):
    if not check_admin_token():
        return jsonify({"error": "Unauthorized"}), 401
    success = db.delete_donation(donation_id)
    return jsonify({"success": success})

@app.route('/api/admin/donations/clear', methods=['POST'])
def admin_clear_donations():
    if not check_admin_token():
        return jsonify({"error": "Unauthorized"}), 401
    success = db.clear_all_donations()
    return jsonify({"success": success})

@app.route('/api/admin/tunnel/status', methods=['GET'])
def admin_tunnel_status():
    if not check_admin_token():
        return jsonify({"error": "Unauthorized"}), 401
    import tunnel
    return jsonify(tunnel.tunnel_manager.get_info())

@app.route('/api/admin/tunnel/toggle', methods=['POST'])
def admin_tunnel_toggle():
    if not check_admin_token():
        return jsonify({"error": "Unauthorized"}), 401
    import tunnel
    info = tunnel.tunnel_manager.get_info()
    if info["status"] in ["connected", "connecting"]:
        tunnel.tunnel_manager.stop_tunnel()
    else:
        tunnel.tunnel_manager.start_tunnel(port=BACKEND_PORT)
    return jsonify(tunnel.tunnel_manager.get_info())

@app.route('/api/admin/network', methods=['GET'])
def admin_get_network():
    if not check_admin_token():
        return jsonify({"error": "Unauthorized"}), 401
    import tunnel
    tunnel_info = tunnel.tunnel_manager.get_info()
    return jsonify({
        "network_config": NETWORK_CONFIG,
        "tunnel_info": tunnel_info
    })

@app.route('/api/admin/test_ocr', methods=['POST'])
def admin_test_ocr():
    if not check_admin_token():
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.json or {}
    window_title = data.get("window_title", "")
    
    try:
        import ocr_engine
        result = ocr_engine.test_ocr_window(window_title)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/admin/test_alert', methods=['POST'])
def admin_test_alert():
    if not check_admin_token():
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.json or {}
    save_to_db = bool(data.get("save_to_db", False))

    test_data = {
        "id": "test-" + str(uuid.uuid4())[:8],
        "name": data.get("name", "Test User"),
        "message": data.get("message", "ขอให้สตรีมเมอร์มีความสุขกับการสตรีมครับ! 💖"),
        "amount": float(data.get("amount", 5000.0)),
        "is_test": True
    }
    
    # Broadcast to SSE listeners
    for q in list(listeners):
        try:
            q.put_nowait(json.dumps(test_data))
        except Exception as e:
            print(f"Error putting test alert in queue: {e}")
            
    # Save test donation to DB ONLY if save_to_db is True
    if save_to_db:
        try:
            db.save_donation(test_data["id"], test_data["name"], test_data["message"], test_data["amount"], status="success")
            db.mark_donation_paid(test_data["id"])
        except Exception as e:
            print(f"Failed to save test donation to DB: {e}")
            
    return jsonify({"success": True, "data": test_data, "saved_to_db": save_to_db})

TTS_CACHE_DIR = os.path.join(EXE_DIR, 'static', 'tts_cache')
os.makedirs(TTS_CACHE_DIR, exist_ok=True)

async def _generate_edge_tts_file(text, voice, filepath):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(filepath)

@app.route('/api/tts', methods=['GET', 'POST'])
def generate_tts():
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        text = data.get('text', '')
        voice = data.get('voice', 'th-TH-PremwadeeNeural')
    else:
        text = request.args.get('text', '')
        voice = request.args.get('voice', 'th-TH-PremwadeeNeural')

    if not text or not text.strip():
        return jsonify({'error': 'No text provided'}), 400

    text_clean = text.strip()
    if not voice or voice == 'default':
        voice = 'th-TH-PremwadeeNeural'

    cache_key = f"{voice}_{text_clean}".encode('utf-8')
    filename = hashlib.md5(cache_key).hexdigest() + ".mp3"
    filepath = os.path.join(TTS_CACHE_DIR, filename)

    if not os.path.exists(filepath):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_generate_edge_tts_file(text_clean, voice, filepath))
            loop.close()
        except Exception as e:
            print(f"Edge TTS Generation Error: {e}")
            return jsonify({'error': f'TTS generation failed: {str(e)}'}), 500

    return jsonify({
        'success': True,
        'audio_url': f'/static/tts_cache/{filename}',
        'voice': voice
    })

@app.route('/api/admin/media_list', methods=['GET'])
def admin_media_list():
    if not check_admin_token():
        return jsonify({"error": "Unauthorized"}), 401

    base_dir = BUNDLE_DIR
    
    preset_images = [
        {"name": "🎁 กล่องของขวัญ (Gift Box)", "url": "/static/presets/images/gift_box.svg"},
        {"name": "🪙 เหรียญทอง (Gold Coin)", "url": "/static/presets/images/coin.svg"},
        {"name": "🏆 ถ้วยรางวัล (Gold Trophy)", "url": "/static/presets/images/trophy.svg"},
        {"name": "🎉 พลุฉลอง (Party Popper)", "url": "/static/presets/images/party.svg"},
        {"name": "💖 หัวใจดวงโต (Red Heart)", "url": "/static/presets/images/heart.svg"},
        {"name": "⭐ ดาวส่องประกาย (Shiny Star)", "url": "/static/presets/images/star.svg"},
        {"name": "🚀 จรวดนำโชค (Rocket)", "url": "/static/presets/images/rocket.svg"},
        {"name": "🐱 แมวน้อยน่ารัก (Orange Cat)", "url": "/static/presets/images/cat.svg"}
    ]
    
    preset_sounds = [
        {"name": "🔔 Chime (เสียงกริ่งกระดิ่ง)", "url": "/static/presets/sounds/chime.wav"},
        {"name": "🪙 Coin (เสียงเหรียญ)", "url": "/static/presets/sounds/coin.wav"},
        {"name": "🎺 Victory (เสียงชัยชนะ)", "url": "/static/presets/sounds/victory.wav"},
        {"name": "✨ Success (เสียงสำเร็จ)", "url": "/static/presets/sounds/success.wav"},
        {"name": "🛎️ Desk Bell (เสียงกระดิ่งใส)", "url": "/static/presets/sounds/bell.wav"}
    ]

    upload_img_dir = os.path.join(base_dir, 'static', 'uploads', 'images')
    upload_snd_dir = os.path.join(base_dir, 'static', 'uploads', 'sounds')

    uploaded_images = []
    if os.path.exists(upload_img_dir):
        for f in sorted(os.listdir(upload_img_dir)):
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp')):
                uploaded_images.append({"name": f"📁 {f}", "url": f"/static/uploads/images/{f}"})

    uploaded_sounds = []
    if os.path.exists(upload_snd_dir):
        for f in sorted(os.listdir(upload_snd_dir)):
            if f.lower().endswith(('.mp3', '.wav', '.ogg', '.m4a')):
                uploaded_sounds.append({"name": f"📁 {f}", "url": f"/static/uploads/sounds/{f}"})

    return jsonify({
        "preset_images": preset_images,
        "preset_sounds": preset_sounds,
        "uploaded_images": uploaded_images,
        "uploaded_sounds": uploaded_sounds
    })

@app.route('/api/admin/upload_media', methods=['POST'])
def admin_upload_media():
    if not check_admin_token():
        return jsonify({"error": "Unauthorized"}), 401

    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    media_type = request.form.get('type', 'image')

    if not file or file.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    base_name = os.path.splitext(file.filename)[0]
    safe_base = re.sub(r'[^a-zA-Z0-9_\-]', '_', base_name)
    filename = f"{safe_base}_{int(time.time())}{ext}"

    base_dir = EXE_DIR
    if media_type == 'sound':
        folder = os.path.join(base_dir, 'static', 'uploads', 'sounds')
        url_path = f"/static/uploads/sounds/{filename}"
    else:
        folder = os.path.join(base_dir, 'static', 'uploads', 'images')
        url_path = f"/static/uploads/images/{filename}"

    os.makedirs(folder, exist_ok=True)
    save_path = os.path.join(folder, filename)
    file.save(save_path)

    return jsonify({
        "success": True,
        "filename": filename,
        "url": url_path
    })

if __name__ == '__main__':
    load_config()
    
    # 1. Start LINE Interceptor Daemon Thread
    import threading
    import time
    import webbrowser
    import interceptor
    
    interceptor_thread = threading.Thread(target=interceptor.run_interceptor_loop, daemon=True)
    interceptor_thread.start()
    print("LINE Interceptor worker thread started successfully!")
    
    # 2. Auto-Open Controller Dashboard in Default Browser
    def open_browser():
        time.sleep(1.5)
        url = f"http://127.0.0.1:{BACKEND_PORT}/controller?token={ADMIN_TOKEN}"
        print(f"Opening Controller Dashboard: {url}")
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"Failed to auto-open browser: {e}")

    threading.Thread(target=open_browser, daemon=True).start()
        
    # 3. Start Cloudflare Quick Tunnel Daemon Thread
    import tunnel
    threading.Thread(target=tunnel.tunnel_manager.start_tunnel, kwargs={'port': BACKEND_PORT}, daemon=True).start()

    # 4. Register Graceful Exit Cleanup Handler
    import atexit
    def on_app_exit():
        print("[App Cleanup] Shutting down VeloxDonate. Clearing Portal Tunnel...")
        try:
            tunnel.tunnel_manager.clear_portal()
            tunnel.tunnel_manager.stop_tunnel()
        except Exception as e:
            print(f"[App Cleanup] Exit cleanup error: {e}")

    atexit.register(on_app_exit)

    print(f"Starting VeloxDonate All-in-One Server on port {BACKEND_PORT}...")
    app.run(host='0.0.0.0', port=BACKEND_PORT, debug=False)
