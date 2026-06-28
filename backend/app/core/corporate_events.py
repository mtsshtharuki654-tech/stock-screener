import asyncio
import pandas as pd
from datetime import datetime, timedelta, timezone, date
from app.core import jquants_client as jq
from app.models.screen import CorporateEvents

JST = timezone(timedelta(hours=9))

_earnings_cache: tuple[datetime, pd.DataFrame] | None = None


def _now_jst() -> datetime:
    return datetime.now(JST)


async def _get_earnings_schedule() -> pd.DataFrame:
    global _earnings_cache
    now = _now_jst()
    if _earnings_cache and (now - _earnings_cache[0]).total_seconds() < 86400:
        return _earnings_cache[1]
    df = await asyncio.to_thread(jq.get_earnings_announcements)
    _earnings_cache = (now, df)
    return df


async def get_corporate_events(
    code: str,
    segment: str,
    daily_df: pd.DataFrame,
) -> CorporateEvents:
    """決算接近チェックのみ（J-Quants、24hキャッシュ）。"""
    events = CorporateEvents()
    try:
        earnings_df = await asyncio.wait_for(_get_earnings_schedule(), timeout=10.0)
        if not earnings_df.empty:
            col_code = "Code" if "Code" in earnings_df.columns else earnings_df.columns[0]
            col_date = next((c for c in earnings_df.columns if "Date" in c or "date" in c), None)
            if col_date:
                row = earnings_df[earnings_df[col_code].astype(str) == code]
                if not row.empty:
                    ann_date = date.fromisoformat(str(row[col_date].iloc[0])[:10])
                    days_until = (ann_date - _now_jst().date()).days
                    if 0 <= days_until <= 14:
                        events.earnings_near = True
                        events.earnings_days_until = days_until
    except Exception:
        pass
    return events
