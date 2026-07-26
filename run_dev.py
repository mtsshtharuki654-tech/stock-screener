#!/usr/bin/env python
"""
Local development server launcher.
Starts both frontend (Vite dev server) and backend (FastAPI) with one command.
Automatically opens browser to http://localhost:5173 (frontend dev server).

Usage: python run_dev.py
"""

import subprocess
import sys
import os
import webbrowser
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
BACKEND_DIR = PROJECT_ROOT / "backend"

def open_browser(url="http://localhost:5173", delay=3):
    """Open browser after a delay to ensure servers are ready."""
    def _open():
        time.sleep(delay)
        try:
            print(f"\n🌐 Opening browser at {url}...")
            webbrowser.open(url)
        except Exception as e:
            print(f"❌ Could not open browser: {e}")
    
    thread = threading.Thread(target=_open, daemon=True)
    thread.start()

def run_backend():
    """Run FastAPI backend server."""
    print("\n" + "="*60)
    print("🚀 Starting Backend (FastAPI) on http://localhost:8000")
    print("="*60)
    
    os.chdir(BACKEND_DIR)
    subprocess.run(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
        env={**os.environ, "PYTHONUNBUFFERED": "1"}
    )

def run_frontend():
    """Run Vite frontend dev server."""
    print("\n" + "="*60)
    print("📦 Starting Frontend (Vite) on http://localhost:5173")
    print("="*60)
    
    os.chdir(FRONTEND_DIR)
    # Use shell=True to ensure npm is found on Windows
    subprocess.run(["npm", "run", "dev"], shell=True)

def main():
    """Main launcher."""
    print("\n" + "="*60)
    print("🎯 PPP Stock Screener - Development Server")
    print("="*60)
    print("\n📝 Starting both frontend and backend servers...")
    print("   Frontend: http://localhost:5173")
    print("   Backend:  http://localhost:8000")
    print("   API:      http://localhost:5173/api")
    print("\n💡 Press Ctrl+C to stop both servers")
    print("="*60 + "\n")
    
    # Open browser after a delay
    open_browser()
    
    # Start backend and frontend in separate processes
    backend_proc = threading.Thread(target=run_backend, daemon=True)
    frontend_proc = threading.Thread(target=run_frontend, daemon=True)
    
    backend_proc.start()
    time.sleep(2)  # Give backend time to start
    frontend_proc.start()
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Shutting down servers...")
        sys.exit(0)

if __name__ == "__main__":
    main()
