"""
Startup helper for standalone executable.
Automatically opens browser when the app starts.
"""

import webbrowser
import threading
import time
import os


def open_browser_on_startup(url="http://localhost:8000", delay=2):
    """Open browser after a short delay to ensure server is ready."""
    def _open():
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"Could not open browser: {e}")
    
    thread = threading.Thread(target=_open, daemon=True)
    thread.start()


# Only open browser when running as standalone EXE
IS_STANDALONE = getattr(os, "_MEIPASS", None) is not None

if IS_STANDALONE:
    # This will be executed when the FastAPI app starts
    import atexit
    
    def on_app_start():
        open_browser_on_startup()
    
    # Schedule browser opening for after app starts
    atexit.register(lambda: None)  # Placeholder for compatibility
