#!/usr/bin/env python
"""
Build script to compile frontend and backend into a standalone app.
Usage: python build.py
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
BACKEND_DIR = PROJECT_ROOT / "backend"
STATIC_DIR = BACKEND_DIR / "static"

def run_command(cmd, cwd=None, shell=False):
    """Run a shell command and return exit code."""
    print(f"\n{'='*60}")
    print(f"Running: {cmd}")
    print(f"{'='*60}\n")
    result = subprocess.run(cmd, cwd=cwd, shell=shell)
    if result.returncode != 0:
        print(f"\n❌ Command failed with exit code {result.returncode}")
        sys.exit(result.returncode)
    return result.returncode

def build_frontend():
    """Build React frontend using Vite."""
    print("\n📦 Building frontend...")
    
    # Clean old build
    if STATIC_DIR.exists():
        shutil.rmtree(STATIC_DIR)
        print(f"Cleaned: {STATIC_DIR}")
    
    # Install dependencies if needed
    node_modules = FRONTEND_DIR / "node_modules"
    if not node_modules.exists():
        print("Installing npm dependencies...")
        run_command("npm install", cwd=FRONTEND_DIR, shell=True)
    
    # Build
    run_command("npm run build", cwd=FRONTEND_DIR, shell=True)
    print("✅ Frontend build complete")

def build_backend():
    """Prepare backend for PyInstaller."""
    print("\n🐍 Preparing backend...")
    
    # Check if venv exists
    venv_dir = BACKEND_DIR / "venv"
    if not venv_dir.exists():
        print("Creating virtual environment...")
        run_command(f'"{sys.executable}" -m venv venv', cwd=BACKEND_DIR, shell=True)
    
    # Use python -m pip to avoid path issues with Japanese characters
    python_exe = venv_dir / "Scripts" / "python.exe" if sys.platform == "win32" else "python"
    print("Installing Python dependencies...")
    run_command(f'"{python_exe}" -m pip install -r requirements.txt', cwd=BACKEND_DIR, shell=True)
    run_command(f'"{python_exe}" -m pip install pyinstaller', cwd=BACKEND_DIR, shell=True)
    
    print("✅ Backend prepared")

def build_exe():
    """Create standalone EXE using PyInstaller."""
    print("\n🔨 Building standalone executable...")
    
    spec_file = PROJECT_ROOT / "stock_screener.spec"
    venv_dir = BACKEND_DIR / "venv"
    python_exe = venv_dir / "Scripts" / "python.exe" if sys.platform == "win32" else "python"
    
    run_command(f'"{python_exe}" -m PyInstaller "{spec_file}"', cwd=PROJECT_ROOT, shell=True)
    
    print("✅ Executable build complete")
    print(f"\n📍 Output: {PROJECT_ROOT / 'dist' / 'PPPStockScreener.exe'}")

def main():
    """Main build process."""
    print("\n" + "="*60)
    print("🚀 PPP Stock Screener - Build Process")
    print("="*60)
    
    try:
        build_frontend()
        build_backend()
        build_exe()
        
        print("\n" + "="*60)
        print("✅ Build successful!")
        print("="*60)
        print(f"\nExecutable ready at: dist/PPPStockScreener.exe")
        print("Run it directly without command line arguments.")
        
    except Exception as e:
        print(f"\n❌ Build failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
