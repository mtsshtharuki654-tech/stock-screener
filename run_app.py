#!/usr/bin/env python
"""
Production entry point for the PPP Stock Screener application.
This script starts the FastAPI backend and serves the built frontend from one process.

Usage:
    python run_app.py
    or double-click start_production.bat on Windows
"""

import os
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
STATIC_DIR = BACKEND_DIR / "static"

# Add backend to path for imports
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Set environment
os.environ.setdefault("PYTHONUNBUFFERED", "1")


def run_command(cmd, cwd: Path | None = None) -> None:
    """Run a shell command and raise if it fails."""
    print(f"\n▶ {cmd}")
    result = subprocess.run(cmd, cwd=cwd, shell=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {result.returncode}: {cmd}")


def ensure_frontend_build() -> None:
    """Build the frontend automatically if the static assets are missing or stale."""
    if not FRONTEND_DIR.exists():
        raise FileNotFoundError(f"Frontend directory not found: {FRONTEND_DIR}")

    static_index = STATIC_DIR / "index.html"
    frontend_sources = [
        FRONTEND_DIR / "package.json",
        FRONTEND_DIR / "index.html",
        FRONTEND_DIR / "src",
    ]

    should_build = False
    if not static_index.exists():
        should_build = True
    else:
        static_mtime = static_index.stat().st_mtime
        for src in frontend_sources:
            if src.exists() and src.stat().st_mtime > static_mtime:
                should_build = True
                break

    if not should_build:
        print("Frontend static assets are already up to date.")
        return

    print("Building frontend assets for production...")
    node_modules = FRONTEND_DIR / "node_modules"
    if not node_modules.exists():
        run_command("npm install", cwd=FRONTEND_DIR)

    run_command("npm run build", cwd=FRONTEND_DIR)


def is_server_available(url: str = "http://127.0.0.1:8000/api/health") -> bool:
    """Return True when the app is already reachable on the expected port."""
    try:
        with urllib.request.urlopen(url, timeout=1.0) as response:
            return response.status == 200
    except Exception:
        return False


def open_browser_when_ready(url: str = "http://127.0.0.1:8000") -> None:
    """Wait briefly for the app to come up, then open the browser automatically."""
    for _ in range(20):
        if is_server_available():
            try:
                webbrowser.open(url)
                print(f"Opened browser at {url}")
            except Exception as exc:
                print(f"Could not open browser automatically: {exc}")
            return
        time.sleep(0.5)


def main() -> None:
    if is_server_available():
        print("PPP Stock Screener is already running. Opening the app...")
        open_browser_when_ready()
        return

    ensure_frontend_build()

    print("\nStarting PPP Stock Screener production server...")
    browser_thread = threading.Thread(target=open_browser_when_ready, daemon=True)
    browser_thread.start()

    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            log_level="info",
            access_log=True,
        )
    except OSError as exc:
        if "address already in use" in str(exc).lower() or "10048" in str(exc):
            print("Port 8000 is already in use. Opening the app if it is reachable...")
            open_browser_when_ready()
            return
        raise


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    except Exception as exc:
        print(f"\nFailed to start production server: {exc}")
        sys.exit(1)
