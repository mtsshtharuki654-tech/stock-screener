import asyncio
import httpx
import pandas as pd
from datetime import datetime, timedelta, timezone, date
from bs4 import BeautifulSoup
from app.core import jquants_client as jq
from app.models.screen import (
    CorporateEvents, EarningsEvent, SplitEvent, TdnetEvent
)

JST = timezone(timedelta(hours=9))

TDNET_BASE = "https://www.release.tdnet.info"
TDNET_SEARCH = f"{TDNET_BASE}/inbs/I_main_00.html"

# キーワード分類
TDNET_KEYWORDS: dict[str, list[str]] = {
    "warrant":          ["新株予約権", "ワラント", "MSワラント"],
    "secondary_offer":  ["公募", "売出し", "第三者割当"],
    "earnings_revision": ["業績予想の修正"],
    "buyback":          ["自己株式の取得"],
    "tob":              ["公開買付"],
    "large_holder":     ["大量保有報告書"],
    "supervision":      ["監理銘柄", "整理銘柄"],
}

UP_KEYWORDS = ["増額", "上方", "引き上げ", "増収", "増益"]
DOWN_KEYWORDS = ["減額", "下方", "引き下げ", "減収", "減益"]

# キャッシュ（プロセス内メモリ、TTL付き）
_earnings_cache: tuple[datetime, pd.DataFrame] | None = None
_margin_cache: tuple[datetime, set[str]] | None = None
_tdnet_cache: dict[str, tuple[datetime, list[dict]]] = {}  # code → (expires_at, events)

TSE_MARGIN_URL = "https://www.jpx.co.jp/markets/credit/kisei/index.html"


async def _fetch_text(url: str, params: dict | None = None) -> str:
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        return r.text


def _now_jst() -> datetime:
    return datetime.now(JST)


async def get_earnings_schedule() -> pd.DataFrame:
    global _earnings_cache
    now = _now_jst()
    if _earnings_cache and (now - _earnings_cache[0]).total_seconds() < 86400:
        return _earnings_cache[1]
    df = jq.get_earnings_announcements()
    _earnings_cache = (now, df)
    return df


async def get_margin_restricted_codes() -> set[str]:
    global _margin_cache
    now = _now_jst()
    if _margin_cache and (now - _margin_cache[0]).total_seconds() < 10800:
        return _margin_cache[1]
    try:
        html = await _fetch_text(TSE_MARGIN_URL)
        soup = BeautifulSoup(html, "html.parser")
        codes: set[str] = set()
        for td in soup.find_all("td"):
            text = td.get_text(strip=True)
            if len(text) == 4 and text.isdigit():
                codes.add(text)
        _margin_cache = (now, codes)
        return codes
    except Exception:
        return set()


async def fetch_tdnet_events(code: str, lookback_days: int = 30) -> list[dict]:
    """
    TDnetから指定銘柄の直近開示を取得してキーワード分類する。
    """
    now = _now_jst()
    if code in _tdnet_cache:
        expires_at, events = _tdnet_cache[code]
        if now < expires_at:
            return events

    events: list[dict] = []
    cutoff = (now - timedelta(days=lookback_days)).date()

    try:
        # TDnet はページベース検索。簡易的に最初のページのみ取得。
        html = await _fetch_text(TDNET_SEARCH, params={"keyword": code, "type": "02"})
        soup = BeautifulSoup(html, "html.parser")
        rows = soup.select("table tr")
        for row in rows[1:]:  # ヘッダーをスキップ
            cells = row.find_all("td")
            if len(cells) < 3:
                continue
            date_str = cells[0].get_text(strip=True)
            title = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            link_tag = cells[1].find("a") if len(cells) > 1 else None
            href = link_tag["href"] if link_tag and link_tag.get("href") else ""
            url = f"{TDNET_BASE}{href}" if href.startswith("/") else href

            try:
                event_date = datetime.strptime(date_str[:10], "%Y/%m/%d").date()
            except ValueError:
                continue
            if event_date < cutoff:
                break

            # キーワード分類
            for category, keywords in TDNET_KEYWORDS.items():
                if any(kw in title for kw in keywords):
                    direction = None
                    if category == "earnings_revision":
                        if any(kw in title for kw in UP_KEYWORDS):
                            direction = "up"
                        elif any(kw in title for kw in DOWN_KEYWORDS):
                            direction = "down"
                    events.append({
                        "category": category,
                        "title": title,
                        "date": str(event_date),
                        "url": url,
                        "direction": direction,
                    })
                    break

    except Exception:
        pass

    # 6時間キャッシュ
    _tdnet_cache[code] = (now + timedelta(hours=6), events)
    return events


async def get_corporate_events(
    code: str,
    segment: str,
    daily_df: pd.DataFrame,
) -> CorporateEvents:
    """
    Gather all corporate event info for a single stock.
    """
    events = CorporateEvents()

    # 並行実行
    earnings_df, margin_codes, tdnet_events = await asyncio.gather(
        get_earnings_schedule(),
        get_margin_restricted_codes(),
        fetch_tdnet_events(code),
    )

    # 決算発表日
    if not earnings_df.empty:
        col_code = "Code" if "Code" in earnings_df.columns else earnings_df.columns[0]
        col_date = next((c for c in earnings_df.columns if "Date" in c or "date" in c), None)
        if col_date:
            row = earnings_df[earnings_df[col_code].astype(str) == code]
            if not row.empty:
                ann_date_str = str(row[col_date].iloc[0])[:10]
                try:
                    ann_date = date.fromisoformat(ann_date_str)
                    days_until = (ann_date - _now_jst().date()).days
                    if days_until >= 0:
                        events.earnings = EarningsEvent(
                            next_date=ann_date_str,
                            days_until=days_until,
                            is_near=days_until <= 14,
                        )
                except ValueError:
                    pass

    # 株式分割（AdjFactor変化 - V2 column name）
    if not daily_df.empty and "AdjFactor" in daily_df.columns:
        cutoff = (_now_jst() - timedelta(days=60)).date()
        recent = daily_df[daily_df["Date"].dt.date >= cutoff]
        if not recent.empty:
            factors = recent["AdjFactor"].dropna()
            if factors.nunique() > 1:
                first_f = factors.iloc[0]
                last_f = factors.iloc[-1]
                ratio_val = last_f / first_f if first_f != 0 else 1
                split_date = str(recent.loc[factors.diff().abs() > 0, "Date"].iloc[0].date()) if (factors.diff().abs() > 0).any() else None
                events.split = SplitEvent(
                    recent=True,
                    date=split_date,
                    ratio=f"{ratio_val:.2f}:1" if ratio_val != 1 else None,
                )

    # 信用規制
    events.margin_restriction = code in margin_codes

    # TDnetイベント
    for ev in tdnet_events:
        cat = ev["category"]
        tdnet_obj = TdnetEvent(detected=True, date=ev["date"], tdnet_url=ev["url"], title=ev["title"])
        if cat == "warrant":
            events.warrant = tdnet_obj
        elif cat == "secondary_offer":
            events.secondary_offer = tdnet_obj
        elif cat == "earnings_revision":
            if ev.get("direction") == "up":
                events.earnings_revision_up = tdnet_obj
            elif ev.get("direction") == "down":
                events.earnings_revision_down = tdnet_obj
            else:
                events.earnings_revision_down = tdnet_obj  # 方向不明は要注意扱い
        elif cat == "buyback":
            events.buyback = tdnet_obj
        elif cat == "tob":
            events.tob = tdnet_obj
        elif cat == "large_holder":
            events.large_holder = tdnet_obj
        elif cat == "supervision":
            events.under_supervision = True

    return events
