import asyncio
import pandas as pd
from datetime import datetime, timedelta, timezone, date
import yfinance as yf
from app.core.yfinance_client import _to_yf_ticker
from app.models.screen import CorporateEvents

JST = timezone(timedelta(hours=9))


def _now_jst() -> datetime:
    return datetime.now(JST)


def _get_next_earnings_yfinance(code: str) -> date | None:
    """yfinanceで直近の決算予定日を取得。取得できなければNoneを返す。"""
    try:
        ticker = yf.Ticker(_to_yf_ticker(code))
        cal = ticker.calendar
        if cal is None:
            return None
        # calはdict形式 {"Earnings Date": [Timestamp, ...], ...}
        if isinstance(cal, dict):
            dates = cal.get("Earnings Date", [])
            if dates:
                d = pd.Timestamp(dates[0]).date() if not isinstance(dates[0], date) else dates[0]
                return d
        # DataFrame形式の場合
        if isinstance(cal, pd.DataFrame) and not cal.empty:
            for col in cal.columns:
                if "Earnings" in col or "earnings" in col:
                    val = cal[col].dropna()
                    if not val.empty:
                        return pd.Timestamp(val.iloc[0]).date()
    except Exception:
        pass
    return None


def build_corporate_events(code: str, earnings_date: date | None = None) -> CorporateEvents:
    """決算接近フラグを生成。earnings_dateがなければyfinanceで取得を試みる。"""
    events = CorporateEvents()
    today = _now_jst().date()

    # 決算日が渡されていなければyfinanceで取得
    ann_date = earnings_date
    if ann_date is None:
        ann_date = _get_next_earnings_yfinance(code)

    if ann_date is not None:
        days_until = (ann_date - today).days
        if 0 <= days_until <= 30:
            events.earnings_near = True
            events.earnings_days_until = days_until

    return events


async def get_corporate_events(code: str) -> CorporateEvents:
    """非同期で注意情報を取得するエントリポイント（エンドポイントから呼ばれる）。"""
    return await asyncio.to_thread(build_corporate_events, code)
