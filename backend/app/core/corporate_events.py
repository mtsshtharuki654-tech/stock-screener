import asyncio
import httpx
import pandas as pd
from datetime import datetime, timedelta, timezone, date
from bs4 import BeautifulSoup
from app.core import jquants_client as jq
from app.models.screen import CorporateEvents

JST = timezone(timedelta(hours=9))

TDNET_BASE = "https://www.release.tdnet.info"
TDNET_SEARCH = f"{TDNET_BASE}/inbs/I_main_00.html"

TDNET_KEYWORDS: dict[str, list[str]] = {
    "warrant":            ["新株予約権", "ワラント", "MSワラント"],
    "secondary_offer":    ["公募", "売出し", "第三者割当"],
    "earnings_revision":  ["業績予想の修正"],
    "buyback":            ["自己株式の取得"],
}

UP_KEYWORDS   = ["増額", "上方", "引き上げ", "増収", "増益"]
DOWN_KEYWORDS = ["減額", "下方", "引き下げ", "減収", "減益"]

_earnings_cache: tuple[datetime, pd.DataFrame] | None = None
_tdnet_cache: dict[str, tuple[datetime, list[dict]]] = {}


def _now_jst() -> datetime:
    return datetime.now(JST)


async def _fetch_text(url: str, params: dict | None = None) -> str:
    async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        return r.text


async def _get_earnings_schedule() -> pd.DataFrame:
    global _earnings_cache
    now = _now_jst()
    if _earnings_cache and (now - _earnings_cache[0]).total_seconds() < 86400:
        return _earnings_cache[1]
    df = await asyncio.to_thread(jq.get_earnings_announcements)
    _earnings_cache = (now, df)
    return df


async def _fetch_tdnet(code: str, lookback_days: int = 30) -> list[dict]:
    now = _now_jst()
    if code in _tdnet_cache:
        expires_at, events = _tdnet_cache[code]
        if now < expires_at:
            return events

    events: list[dict] = []
    cutoff = (now - timedelta(days=lookback_days)).date()

    try:
        html = await _fetch_text(TDNET_SEARCH, params={"keyword": code, "type": "02"})
        soup = BeautifulSoup(html, "html.parser")
        for row in soup.select("table tr")[1:]:
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            date_str = cells[0].get_text(strip=True)
            title = cells[1].get_text(strip=True)
            try:
                event_date = datetime.strptime(date_str[:10], "%Y/%m/%d").date()
            except ValueError:
                continue
            if event_date < cutoff:
                break
            for category, keywords in TDNET_KEYWORDS.items():
                if any(kw in title for kw in keywords):
                    direction = None
                    if category == "earnings_revision":
                        if any(kw in title for kw in UP_KEYWORDS):
                            direction = "up"
                        elif any(kw in title for kw in DOWN_KEYWORDS):
                            direction = "down"
                    events.append({"category": category, "direction": direction})
                    break
    except Exception:
        pass

    _tdnet_cache[code] = (now + timedelta(hours=6), events)
    return events


async def get_corporate_events(
    code: str,
    segment: str,
    daily_df: pd.DataFrame,
) -> CorporateEvents:
    events = CorporateEvents()

    earnings_df, tdnet_events = await asyncio.gather(
        _get_earnings_schedule(),
        _fetch_tdnet(code),
    )

    # 決算接近チェック（14日以内）
    if not earnings_df.empty:
        col_code = "Code" if "Code" in earnings_df.columns else earnings_df.columns[0]
        col_date = next((c for c in earnings_df.columns if "Date" in c or "date" in c), None)
        if col_date:
            row = earnings_df[earnings_df[col_code].astype(str) == code]
            if not row.empty:
                try:
                    ann_date = date.fromisoformat(str(row[col_date].iloc[0])[:10])
                    days_until = (ann_date - _now_jst().date()).days
                    if 0 <= days_until <= 14:
                        events.earnings_near = True
                        events.earnings_days_until = days_until
                except ValueError:
                    pass

    # TDnetイベント分類
    for ev in tdnet_events:
        cat = ev["category"]
        if cat == "warrant":
            events.warrant = True
        elif cat == "secondary_offer":
            events.secondary_offer = True
        elif cat == "earnings_revision":
            if ev.get("direction") == "up":
                events.earnings_revision_up = True
            else:
                events.earnings_revision_down = True
        elif cat == "buyback":
            events.buyback = True

    return events
