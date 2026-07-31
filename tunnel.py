import os
import sys
import re
import time
import json
import subprocess
import threading
import urllib.request

if getattr(sys, 'frozen', False):
    BUNDLE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    EXE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    EXE_DIR = os.path.dirname(os.path.abspath(__file__))

CLOUDFLARED_DOWNLOAD_URL = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
BIN_DIR = os.path.join(BUNDLE_DIR, "bin")
EXE_PATH = os.path.join(BIN_DIR, "cloudflared.exe")

class TunnelManager:
    def __init__(self):
        self.process = None
        self.url = None
        self.status = "disconnected" # disconnected, connecting, connected, error
        self.error_message = None
        self.thread = None
        self._stop_event = threading.Event()

    def ensure_binary(self):
        """Ensure cloudflared.exe is available locally or in PATH."""
        if os.path.exists(EXE_PATH):
            return EXE_PATH

        # Check system PATH
        try:
            res = subprocess.run(["where", "cloudflared"], capture_output=True, text=True)
            if res.returncode == 0 and res.stdout.strip():
                return "cloudflared"
        except Exception:
            pass

        # Create bin directory and download cloudflared.exe
        print(f"[Tunnel] cloudflared.exe not found. Downloading from official Cloudflare releases...")
        os.makedirs(BIN_DIR, exist_ok=True)
        try:
            def report_progress(block_num, block_size, total_size):
                percent = int(block_num * block_size * 100 / total_size) if total_size > 0 else 0
                if block_num % 50 == 0 or percent == 100:
                    sys.stdout.write(f"\r[Tunnel] Downloading cloudflared.exe: {percent}%")
                    sys.stdout.flush()

            urllib.request.urlretrieve(CLOUDFLARED_DOWNLOAD_URL, EXE_PATH, reporthook=report_progress)
            print("\n[Tunnel] Download completed successfully!")
            return EXE_PATH
        except Exception as e:
            print(f"\n[Tunnel] Failed to download cloudflared.exe: {e}")
            self.error_message = f"Download failed: {e}"
            return None

    def start_tunnel(self, port=5000):
        if self.status in ["connecting", "connected"] and self.process and self.process.poll() is None:
            print("[Tunnel] Tunnel is already running.")
            return self.url

        cmd_path = self.ensure_binary()
        if not cmd_path:
            self.status = "error"
            return None

        self.status = "connecting"
        self.url = None
        self.error_message = None
        self._stop_event.clear()

        cmd = [cmd_path, "tunnel", "--url", f"http://localhost:{port}"]
        print(f"[Tunnel] Starting Cloudflare Quick Tunnel on port {port}...")

        try:
            # Hide console window on Windows
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                startupinfo=startupinfo
            )

            self.thread = threading.Thread(target=self._monitor_output, daemon=True)
            self.thread.start()
            return True
        except Exception as e:
            print(f"[Tunnel] Failed to start tunnel process: {e}")
            self.status = "error"
            self.error_message = str(e)
            return False

    def _monitor_output(self):
        url_regex = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
        
        while not self._stop_event.is_set() and self.process and self.process.poll() is None:
            line = self.process.stdout.readline()
            if not line:
                break
            
            line_str = line.strip()
            # print(f"[Cloudflared] {line_str}")

            match = url_regex.search(line_str)
            if match:
                found_url = match.group(0)
                self.url = found_url
                self.status = "connected"
                print(f"\n[Tunnel] SUCCESS! Public Cloudflare Tunnel URL: {self.url}")
                print(f"[Tunnel] Public Streamer Donate Link: {self.url}/donate\n")
                self.sync_portal(found_url)

        if self.status != "connected":
            self.status = "error"
            if not self.error_message:
                self.error_message = "Tunnel process terminated unexpectedly."
            print(f"[Tunnel] Process stopped. Status: {self.status}")

    def sync_portal(self, tunnel_url=None, token=None, portal_url=None):
        target_url = tunnel_url or self.url
        if not target_url:
            return False

        try:
            streamer_name = ""
            config_path = os.path.join(EXE_DIR, "config.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                streamer_name = cfg.get("streamer_name", "")
                if not token or not portal_url:
                    token = token or cfg.get("velox_donate_token", "")
                    portal_url = portal_url or cfg.get("portal_url", "https://donate.veloxgg.com")

            token = (token or "").strip()
            portal_url = (portal_url or "https://donate.veloxgg.com").rstrip("/")

            if not token:
                self.sync_error = "ยังไม่ได้กรอก Velox Donate Token"
                print("[Tunnel] Velox Donate Token not configured. Skipping Portal sync.")
                return False

            api_endpoint = f"{portal_url}/api/tunnel/update"
            payload = json.dumps({"token": token, "tunnelUrl": target_url, "streamerName": streamer_name}).encode("utf-8")

            req = urllib.request.Request(
                api_endpoint,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 VeloxDonateClient/1.0"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                if res_data.get("success"):
                    slug = res_data.get("customSlug")
                    self.synced_slug = slug
                    self.sync_error = None
                    custom_link = f"{portal_url}/{slug}" if slug else portal_url
                    print(f"[Tunnel] [SYNC OK] Synced with Velox Portal! Custom URL: {custom_link}")
                    return True
                else:
                    self.synced_slug = None
                    self.sync_error = res_data.get("error") or "Token ไม่ถูกต้อง"
                    print(f"[Tunnel] [SYNC WARN] Portal sync warning: {self.sync_error}")
                    return False
        except urllib.error.HTTPError as e:
            self.synced_slug = None
            if e.code == 401:
                self.sync_error = "Token ไม่ถูกต้อง (Invalid Velox Donate Token)"
            elif e.code == 403:
                self.sync_error = "Cloudflare WAF ปฏิเสธการเชื่อมต่อ (HTTP 403 Forbidden)"
            else:
                self.sync_error = f"HTTP Error {e.code}"
            print(f"[Tunnel] [SYNC FAIL] HTTP Error: {self.sync_error}")
            return False
        except Exception as e:
            self.synced_slug = None
            self.sync_error = f"ไม่สามารถเชื่อมต่อ Portal ได้ ({e})"
            print(f"[Tunnel] [SYNC FAIL] Failed to sync with Velox Portal: {e}")
            return False

    def clear_portal(self):
        try:
            config_path = os.path.join(EXE_DIR, "config.json")
            if not os.path.exists(config_path):
                return False

            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)

            token = cfg.get("velox_donate_token", "").strip()
            portal_url = cfg.get("portal_url", "https://donate.veloxgg.com").rstrip("/")

            if not token:
                return False

            api_endpoint = f"{portal_url}/api/tunnel/update"
            payload = json.dumps({"token": token, "active": False}).encode("utf-8")

            req = urllib.request.Request(
                api_endpoint,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 VeloxDonateClient/1.0"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                self.synced_slug = None
                self.sync_error = None
                print("[Tunnel] [CLEAR OK] Deactivated Velox Portal sync.")
                return True
        except Exception as e:
            self.synced_slug = None
            print(f"[Tunnel] [CLEAR FAIL] Failed to clear Velox Portal sync: {e}")
            return False

    def stop_tunnel(self):
        print("[Tunnel] Stopping Cloudflare Tunnel...")
        self._stop_event.set()
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None

        self.status = "disconnected"
        self.url = None
        print("[Tunnel] Tunnel stopped cleanly.")

    def get_info(self):
        return {
            "status": self.status,
            "url": self.url,
            "donate_url": f"{self.url}/donate" if self.url else None,
            "error_message": self.error_message
        }

# Global Instance
tunnel_manager = TunnelManager()
