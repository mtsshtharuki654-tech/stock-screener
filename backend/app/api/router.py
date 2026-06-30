from fastapi import APIRouter
from app.api.endpoints import health, screen, stocks, winrate

router = APIRouter()
router.include_router(health.router, tags=["health"])
router.include_router(screen.router, tags=["screen"])
router.include_router(stocks.router, tags=["stocks"])
router.include_router(winrate.router, tags=["winrate"])
