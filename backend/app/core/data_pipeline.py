import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from pathlib import Path
from app.config import settings
from app.core import jquants_client as jq

JST = timezone(timedelta(hours=9))
LOOKBACK_DAYS = 450  # 60週MA計算に必要な期間 + バッファ
DAILY_CACHE = settings.cache_dir / "daily_ohlcv.parquet"
UNIVERSE_CACHE = settings.cache_dir / "universe.parquet"
INDEX_CACHE_TPL = settings.cache_dir / "index_{code}.parquet"


def _today_jst() -> datetime:
    return datetime.now(JST).replace(hour=0, minute=0, second=0, microsecond=0)


def load_universe(segments: list[str]) -> pd.DataFrame:
    """Load equity master with caching (24h TTL)."""
    now = _today_jst()
    if UNIVERSE_CACHE.exists():
        mtime = datetime.fromtimestamp(UNIVERSE_CACHE.stat().st_mtime, tz=JST)
        if (now - mtime).total_seconds() < 86400:
            return pd.read_parquet(UNIVERSE_CACHE)

    df = jq.get_universe(segments)
    df.to_parquet(UNIVERSE_CACHE)
    return df


def load_daily_ohlcv(segments: list[str]) -> pd.DataFrame:
    """
    Load daily OHLCV for all Prime+Growth stocks with parquet cache and incremental update.
    """
    end = _today_jst()
    start = end - timedelta(days=LOOKBACK_DAYS)

    if DAILY_CACHE.exists():
        cached = pd.read_parquet(DAILY_CACHE)
        cached["Date"] = pd.to_datetime(cached["Date"])
        last_date = cached["Date"].max()
        delta_start = last_date + timedelta(days=1)

        if delta_start.date() >= end.date():
            return cached

        delta = jq.get_daily_ohlcv(delta_start, end)
        if not delta.empty:
            merged = pd.concat([cached, delta]).drop_duplicates(subset=["Code", "Date"])
            merged = merged.sort_values(["Code", "Date"]).reset_index(drop=True)
            merged.to_parquet(DAILY_CACHE)
            return merged
        return cached

    df = jq.get_daily_ohlcv(start, end)
    df.to_parquet(DAILY_CACHE)
    return df


def load_index_ohlcv(index_code: str) -> pd.DataFrame:
    """Load index daily data with daily cache."""
    cache_path = Path(str(INDEX_CACHE_TPL).replace("{code}", index_code))
    end = _today_jst()
    start = end - timedelta(days=LOOKBACK_DAYS)

    if cache_path.exists():
        cached = pd.read_parquet(cache_path)
        cached["Date"] = pd.to_datetime(cached["Date"])
        last_date = cached["Date"].max()
        delta_start = last_date + timedelta(days=1)
        if delta_start.date() >= end.date():
            return cached
        delta = jq.get_index_ohlcv(index_code, delta_start, end)
        if not delta.empty:
            merged = pd.concat([cached, delta]).drop_duplicates(subset=["Date"])
            merged = merged.sort_values("Date").reset_index(drop=True)
            merged.to_parquet(cache_path)
            return merged
        return cached

    df = jq.get_index_ohlcv(index_code, start, end)
    if not df.empty:
        df.to_parquet(cache_path)
    return df


def resample_to_weekly(daily_df: pd.DataFrame) -> pd.DataFrame:
    """Resample daily OHLCV to weekly (Friday close). Uses V2 column names."""
    df = daily_df.copy()
    df = df.set_index("Date")
    weekly = df.resample("W-FRI").agg({
        "O": "first",
        "H": "max",
        "L": "min",
        "AdjC": "last",
        "AdjVo": "sum",
    }).dropna(subset=["AdjC"])
    weekly = weekly.rename(columns={
        "O": "Open", "H": "High", "L": "Low",
        "AdjC": "Close", "AdjVo": "Volume",
    })
    weekly.index.name = "Date"
    return weekly.reset_index()


def add_ma_columns(df: pd.DataFrame, price_col: str = "Close") -> pd.DataFrame:
    """Add MA5, MA20, MA60 and their slopes in-place."""
    df = df.copy()
    for p in [5, 20, 60]:
        col = f"MA{p}"
        df[col] = df[price_col].rolling(p, min_periods=p).mean()
        df[f"{col}_slope"] = df[col].pct_change()
    return df


def compute_all_mas(daily_all: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Compute daily and weekly MAs for all codes in one vectorized pass.
    Returns (daily_with_ma, weekly_with_ma).
    """
    # Use AdjC (V2 adjusted close) for all MA calculations
    daily = daily_all.sort_values(["Code", "Date"]).copy()

    for p in [5, 20, 60]:
        daily[f"MA{p}"] = daily.groupby("Code")["AdjC"].transform(
            lambda x: x.rolling(p, min_periods=p).mean()
        )
        daily[f"MA{p}_slope"] = daily.groupby("Code")[f"MA{p}"].transform(
            lambda x: x.pct_change()
        )

    # Add standard column aliases so screener can use Open/High/Low/Close/Volume
    daily["Open"] = daily["O"]
    daily["High"] = daily["H"]
    daily["Low"] = daily["L"]
    daily["Close"] = daily["AdjC"]
    daily["Volume"] = daily["AdjVo"]

    # Weekly resample per code
    weekly_frames = []
    for code, grp in daily.groupby("Code"):
        wk = resample_to_weekly(grp[["Date", "O", "H", "L", "AdjC", "AdjVo"]])
        wk["Code"] = code
        wk = add_ma_columns(wk, price_col="Close")
        weekly_frames.append(wk)

    weekly_all = pd.concat(weekly_frames, ignore_index=True) if weekly_frames else pd.DataFrame()
    return daily, weekly_all


def filter_by_volume(weekly_all: pd.DataFrame, min_daily_volume: int, weeks: int = 4) -> set[str]:
    """Return set of codes passing the average daily volume filter."""
    passing = set()
    for code, grp in weekly_all.groupby("Code"):
        if len(grp) < weeks:
            continue
        avg_weekly = grp["Volume"].iloc[-weeks:].mean()
        avg_daily = avg_weekly / 5
        if avg_daily >= min_daily_volume:
            passing.add(code)
    return passing


def filter_by_price(daily_all: pd.DataFrame, max_price: float) -> set[str]:
    """Return set of codes where the most recent AdjC <= max_price."""
    latest = daily_all.sort_values("Date").groupby("Code")["AdjC"].last()
    return set(latest[latest <= max_price].index)


def build_stock_frames(
    daily_all: pd.DataFrame,
    weekly_all: pd.DataFrame,
    codes: set[str],
) -> dict[str, dict[str, pd.DataFrame]]:
    """Return {code: {"daily": df, "weekly": df}} for the given codes."""
    result = {}
    for code in codes:
        d = daily_all[daily_all["Code"] == code].sort_values("Date").reset_index(drop=True)
        w = weekly_all[weekly_all["Code"] == code].sort_values("Date").reset_index(drop=True)
        if len(d) >= 62 and len(w) >= 62:
            result[code] = {"daily": d, "weekly": w}
    return result
