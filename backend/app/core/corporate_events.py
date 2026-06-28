import asyncio
import pandas as pd
from datetime import datetime, timedelta, timezone, date
from app.core import jquants_client as jq
from app.models.screen import CorporateEvents

JST = timezone(timedelta(hours=9))

_earnings_cache: tuple[datetime, pd.DataFrame] | None = None
_earnings_lock = asyncio.Lock()


def _now_jst() -> datetime:
    return datetime.now(JST)


async def fetch_earnings_schedule() -> pd.DataFrame:
    """決算カレンダーを1回だけ取得してキャッシュ（24h TTL）。"""
    global _earnings_cache
    now = _now_jst()
    if _earnings_cache and (now - _earnings_cache[0]).total_seconds() < 86400:
        return _earnings_cache[1]
    async with _earnings_lock:
        # ロック取得後に再チェック
        if _earnings_cache and (now - _earnings_cache[0]).total_seconds() < 86400:
            return _earnings_cache[1]
        try:
            df = await asyncio.wait_for(
                asyncio.to_thread(jq.get_earnings_announcements),
                timeout=10.0,
            )
        except Exception:
            df = pd.DataFrame()
        _earnings_cache = (now, df)
        return df


def build_corporate_events(code: str, earnings_df: pd.DataFrame) -> CorporateEvents:
    """決算カレンダーから銘柄の決算接近フラグを同期で生成（ネットワーク不使用）。"""
    events = CorporateEvents()
    if earnings_df.empty:
        return events
    col_code = "Code" if "Code" in earnings_df.columns else earnings_df.columns[0]
    col_date = next((c for c in earnings_df.columns if "Date" in c or "date" in c), None)
    if not col_date:
        return events
    row = earnings_df[earnings_df[col_code].astype(str) == code]
    if row.empty:
        return events
    try:
        ann_date = date.fromisoformat(str(row[col_date].iloc[0])[:10])
        days_until = (ann_date - _now_jst().date()).days
        if 0 <= days_until <= 14:
            events.earnings_near = True
            events.earnings_days_until = days_until
    except ValueError:
        pass
    return events
