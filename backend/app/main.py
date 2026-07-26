from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from app.api.router import router
from app.config import settings
from app.startup import open_browser_on_startup, IS_STANDALONE

app = FastAPI(title="PPP Stock Screener", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    """Open browser when app starts (standalone mode only)."""
    if IS_STANDALONE:
        open_browser_on_startup()


# Serve static files from frontend build
static_dir = os.path.join(os.path.dirname(__file__), "../static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
else:
    # Fallback for development
    @app.get("/{full_path:path}")
    async def catch_all(full_path: str):
        # In development, redirect to frontend dev server
        return {"error": "Frontend build not found. Run: npm run build in frontend directory"}
