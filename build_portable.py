import os
import sys
import shutil
import zipfile
import urllib.request
import subprocess

VERSION = "0.1.3"
EMBED_PYTHON_URL = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-embed-amd64.zip"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "build_cache")
BUILD_DIR = os.path.join(BASE_DIR, "dist_portable")
RELEASE_FOLDER = f"VeloxDonate_v{VERSION}_Portable"
TARGET_DIR = os.path.join(BUILD_DIR, RELEASE_FOLDER)
PYTHON_RUNTIME_DIR = os.path.join(TARGET_DIR, "python_runtime")
SITE_PACKAGES_DIR = os.path.join(PYTHON_RUNTIME_DIR, "Lib", "site-packages")

FILES_TO_COPY = [
    "app.py",
    "tunnel.py",
    "interceptor.py",
    "ocr_engine.py",
    "db.py",
    "open_controller.py",
    "config.example.json",
    "controller.html",
    "index.html",
    "overlay.html",
    "widget_goal.html",
    "widget_recent.html",
    "widget_top.html",
    "style.css",
    "requirements.txt",
]

DIRS_TO_COPY = [
    "bin",
    "static",
]

def download_file(url, target_path):
    print(f"Downloading {url}...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp, open(target_path, "wb") as out_file:
        shutil.copyfileobj(resp, out_file)
    print("Download completed.")

def setup_embedded_python():
    os.makedirs(CACHE_DIR, exist_ok=True)
    zip_cache_path = os.path.join(CACHE_DIR, "python-3.12.8-embed-amd64.zip")

    if not os.path.exists(zip_cache_path):
        download_file(EMBED_PYTHON_URL, zip_cache_path)

    print("Extracting Python Embedded Runtime...")
    os.makedirs(PYTHON_RUNTIME_DIR, exist_ok=True)
    with zipfile.ZipFile(zip_cache_path, "r") as z:
        z.extractall(PYTHON_RUNTIME_DIR)

    # Enable site-packages in ._pth file
    for file in os.listdir(PYTHON_RUNTIME_DIR):
        if file.endswith("._pth"):
            pth_path = os.path.join(PYTHON_RUNTIME_DIR, file)
            with open(pth_path, "r", encoding="utf-8") as f:
                content = f.read()

            content = content.replace("#import site", "import site")
            if "Lib/site-packages" not in content:
                content += "\nLib/site-packages\n.\n"

            with open(pth_path, "w", encoding="utf-8") as f:
                f.write(content)

    os.makedirs(SITE_PACKAGES_DIR, exist_ok=True)

def install_dependencies():
    print("Installing dependencies into Embedded Python runtime...")
    req_file = os.path.join(BASE_DIR, "requirements.txt")
    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "-r",
        req_file,
        "--target",
        SITE_PACKAGES_DIR,
        "--quiet",
        "--disable-pip-version-check"
    ]
    res = subprocess.run(cmd)
    if res.returncode != 0:
        print("[WARNING] Dependency installation finished with non-zero exit code.")
    else:
        print("[+] Dependencies successfully installed into Embedded Python.")

def build_portable():
    print(f"=== Building VeloxDonate Embedded Portable Release v{VERSION} ===")

    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR, ignore_errors=True)
    os.makedirs(TARGET_DIR, exist_ok=True)

    # 1. Download & extract Python Embedded Runtime
    setup_embedded_python()

    # 2. Install requirements into site-packages
    install_dependencies()

    # 3. Copy Project Files
    for file in FILES_TO_COPY:
        src = os.path.join(BASE_DIR, file)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(TARGET_DIR, file))
            print(f"  [+] Copied file: {file}")

    # Do NOT copy local config.json so every user gets a fresh randomized token on first launch

    # 4. Copy Directories
    for d in DIRS_TO_COPY:
        src = os.path.join(BASE_DIR, d)
        if os.path.exists(src):
            shutil.copytree(src, os.path.join(TARGET_DIR, d))
            print(f"  [+] Copied folder: {d}")

    # 5. Create 1-Click Launcher (Start_VeloxDonate.bat)
    launcher_content = """@echo off
title VeloxDonate v0.1.1 - Streamer Launcher
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================================
echo   VeloxDonate Realtime Donation System Launcher
echo   Automated PromptPay Donation System for Streamers
echo ============================================================
echo.

if exist "python_runtime\\python.exe" (
    echo [!] Starting VeloxDonate Server...
    python_runtime\\python.exe app.py
) else (
    echo [ERROR] Embedded Python runtime not found!
    echo Please re-download the VeloxDonate Portable package.
)
echo.
echo ============================================================
echo Server stopped. Press any key to exit...
pause >nul
"""
    launcher_path = os.path.join(TARGET_DIR, "Start_VeloxDonate.bat")
    with open(launcher_path, "w", encoding="cp874") as f:
        f.write(launcher_content)
    print("  [+] Created Start_VeloxDonate.bat launcher")

    # 6. Zip the Package
    zip_filename = os.path.join(BUILD_DIR, f"{RELEASE_FOLDER}.zip")
    print(f"\nCompressing into {zip_filename}...")

    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(TARGET_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, BUILD_DIR)
                zipf.write(file_path, arcname)

    size_mb = os.path.getsize(zip_filename) / (1024 * 1024)
    print(f"\n[SUCCESS] Embedded Portable Release Package Created!")
    print(f"   --> Zip File: {zip_filename}")
    print(f"   --> Package Size: {size_mb:.2f} MB")

if __name__ == "__main__":
    build_portable()
