import os
import shutil
import subprocess
import zipfile

VERSION = "0.1.1"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, "dist")
BUILD_DIR = os.path.join(BASE_DIR, "build")
RELEASE_ZIP_DIR = os.path.join(BASE_DIR, "dist_zip")

def build():
    print(f"=== [1/3] Compiling VeloxDonate.exe with PyInstaller (v{VERSION}) ===")

    # Clean old build dirs safely
    if os.path.exists(DIST_DIR):
        shutil.rmtree(DIST_DIR, ignore_errors=True)
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR, ignore_errors=True)
    if os.path.exists(RELEASE_ZIP_DIR):
        shutil.rmtree(RELEASE_ZIP_DIR, ignore_errors=True)

    os.makedirs(RELEASE_ZIP_DIR, exist_ok=True)

    # PyInstaller Add-Data separators: ';' on Windows
    sep = ";"

    datas = [
        ("controller.html", "."),
        ("index.html", "."),
        ("overlay.html", "."),
        ("widget_goal.html", "."),
        ("widget_recent.html", "."),
        ("widget_top.html", "."),
        ("style.css", "."),
        ("bin", "bin"),
        ("static", "static"),
    ]

    pyinstaller_cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onedir",
        "--name=VeloxDonate",
        "--console",
    ]

    for src, target in datas:
        full_src = os.path.join(BASE_DIR, src)
        if os.path.exists(full_src):
            pyinstaller_cmd.append(f"--add-data={full_src}{sep}{target}")

    pyinstaller_cmd.append("app.py")

    print(f"Executing: {' '.join(pyinstaller_cmd)}")
    res = subprocess.run(pyinstaller_cmd, cwd=BASE_DIR)
    if res.returncode != 0:
        print("[ERROR] PyInstaller compilation failed!")
        return False

    exe_folder = os.path.join(DIST_DIR, "VeloxDonate")
    exe_file = os.path.join(exe_folder, "VeloxDonate.exe")
    if not os.path.exists(exe_file):
        print(f"[ERROR] Compiled executable not found at: {exe_file}")
        return False

    # Do NOT copy local config.json so every user gets a fresh randomized token on first launch

    # Generate Start_VeloxDonate.bat in exe_folder
    bat_content = """@echo off
title VeloxDonate - Portable Server Launcher
cd /d "%~dp0"
echo ==================================================
echo   VeloxDonate Realtime Donation System Launcher
echo ==================================================
echo.
if exist "VeloxDonate.exe" (
    echo Starting VeloxDonate...
    start "" "VeloxDonate.exe"
) else (
    echo [ERROR] VeloxDonate.exe not found!
    pause
)
"""
    with open(os.path.join(exe_folder, "Start_VeloxDonate.bat"), "w", encoding="cp874") as f:
        f.write(bat_content)

    print(f"\n=== [2/3] Successfully built Portable Executable Folder: {exe_folder} ===")

    # Create Zip containing VeloxDonate folder
    zip_path = os.path.join(RELEASE_ZIP_DIR, f"VeloxDonate_v{VERSION}.zip")
    print(f"\n=== [3/3] Zipping into {zip_path} ===")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(exe_folder):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, DIST_DIR)
                zipf.write(file_path, rel_path)

    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"\n[SUCCESS] Portable Release Zip Created!")
    print(f"   --> Executable: {exe_file}")
    print(f"   --> Zip Package: {zip_path}")
    print(f"   --> Package Size: {size_mb:.2f} MB")
    return True

if __name__ == "__main__":
    build()
