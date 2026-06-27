from fastapi import APIRouter
from datetime import datetime, timezone, timedelta

router = APIRouter()
JST = timezone(timedelta(hours=9))


@router.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.now(JST).isoformat()}
