import asyncio
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta, timezone
from app.core.yfinance_client import _to_yf_ticker
from app.models.screen import CorporateEvents

JST = timezone(timedelta(hours=9))


def _now_jst() -> datetime:
    return datetime.now(JST)


def _get_next_earnings(code: str) -> tuple[int | None, bool]:
    """
    yfinanceで次の決算予定日を取得。
    Returns (days_until, is_near) or (None, False) if not found.
    """
    today = _now_jst().date()
    ticker_str = _to_yf_ticker(code)
    try:
        t = yf.Ticker(ticker_str)
        ed = t.earnings_dates
        if ed is None or ed.empty:
            return None, False

        # インデックスをタイムゾーンなしに変換
        idx = ed.index
        if idx.tz is not None:
            idx = idx.tz_convert(None)

        # 今日以降の最初の決算日を探す
        for ts in idx:
            d = ts.date()
            if d >= today:
                days = (d - today).days
                return days, days <= 45
    except Exception:
        pass
    return None, False


def build_corporate_events(code: str) -> CorporateEvents:
    """yfinanceで決算接近フラグを生成。"""
    events = CorporateEvents()
    days_until, is_near = _get_next_earnings(code)
    if is_near and days_until is not None:
        events.earnings_near = True
        events.earnings_days_until = days_until
    return events


async def get_corporate_events(code: str) -> CorporateEvents:
    """非同期で注意情報を取得するエントリポイント。"""
    return await asyncio.to_thread(build_corporate_events, code)
