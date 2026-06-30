from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from app.config import settings
from app.core import jquants_client as jq
from app.core import yfinance_client as yfc

JST = timezone(timedelta(hours=9))
LOOKBACK_DAYS = 450  # 60週MA計算に必要な期間 + バッファ
DAILY_CACHE = settings.cache_dir / "daily_ohlcv.parquet"
UNIVERSE_CACHE = settings.cache_dir / "universe.parquet"
INDEX_CACHE_TPL = settings.cache_dir / "index_{code}.parquet"

# 途中保存の間隔（日数）
_SAVE_EVERY = 10
# 並列バッチ取得サイズ
_BATCH_SIZE = 3


def _today_jst() -> datetime:
    return datetime.now(JST).replace(hour=0, minute=0, second=0, microsecond=0)


def _load_cache() -> pd.DataFrame:
    """キャッシュを読み込む。空・破損の場合は削除して空DFを返す。"""
    if not DAILY_CACHE.exists():
        return pd.DataFrame()
    try:
        df = pd.read_parquet(DAILY_CACHE)
        if df.empty or "Date" not in df.columns:
            DAILY_CACHE.unlink(missing_ok=True)
            return pd.DataFrame()
        df["Date"] = pd.to_datetime(df["Date"])
        return df
    except Exception:
        DAILY_CACHE.unlink(missing_ok=True)
        return pd.DataFrame()


def _save_cache(df: pd.DataFrame) -> None:
    if not df.empty:
        df.to_parquet(DAILY_CACHE)


def load_universe(segments: list[str]) -> pd.DataFrame:
    """Load equity master with caching (7日TTL、API失敗時はキャッシュで続行)。"""
    now = _today_jst()
    if UNIVERSE_CACHE.exists():
        mtime = datetime.fromtimestamp(UNIVERSE_CACHE.stat().st_mtime, tz=JST)
        if (now - mtime).total_seconds() < 604800:  # 7 days
            return pd.read_parquet(UNIVERSE_CACHE)
    try:
        df = jq.get_universe(segments)
        df.to_parquet(UNIVERSE_CACHE)
        return df
    except Exception:
        if UNIVERSE_CACHE.exists():
            return pd.read_parquet(UNIVERSE_CACHE)
        raise


def _naive(dt: datetime) -> datetime:
    """タイムゾーンを除去してnaiveなdatetimeに変換。"""
    return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt


def load_daily_ohlcv(
    segments: list[str],
    progress_cb: "Callable[[int, int], None] | None" = None,
) -> pd.DataFrame:
    """
    日足OHLCVをyfinanceで取得。キャッシュが当日のものなら再取得しない。
    """
    end = _today_jst()
    start = end - timedelta(days=LOOKBACK_DAYS)

    # キャッシュが今日のものであれば再取得しない
    cached = _load_cache()
    if not cached.empty:
        last_date = _naive(pd.Timestamp(cached["Date"].max()).to_pydatetime())
        today_naive = _naive(end)
        if (today_naive - last_date).days <= 1:
            if progress_cb:
                progress_cb(1, 1)
            return cached

    # ユニバースからコード一覧を取得
    universe_df = load_universe(segments)
    codes = universe_df["Code"].astype(str).tolist()

    fresh = yfc.fetch_batch(codes, start, end, progress_cb=progress_cb, batch_size=50)

    if fresh.empty:
        return cached if not cached.empty else pd.DataFrame()

    _save_cache(fresh)
    return fresh


def _merge(base: pd.DataFrame, new_frames: list[pd.DataFrame]) -> pd.DataFrame:
    """既存データと新規データをマージして重複除去・ソート。"""
    parts = ([base] if not base.empty else []) + new_frames
    result = pd.concat(parts).drop_duplicates(subset=["Code", "Date"])
    result = result.sort_values(["Code", "Date"]).reset_index(drop=True)
    return result


def load_index_ohlcv(index_code: str) -> pd.DataFrame:
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
    df = daily_df.copy()
    df = df.set_index("Date")
    weekly = df.resample("W-FRI").agg({
        "O": "first", "H": "max", "L": "min",
        "AdjC": "last", "AdjVo": "sum",
    }).dropna(subset=["AdjC"])
    weekly = weekly.rename(columns={
        "O": "Open", "H": "High", "L": "Low",
        "AdjC": "Close", "AdjVo": "Volume",
    })
    weekly.index.name = "Date"
    return weekly.reset_index()


def add_ma_columns(df: pd.DataFrame, price_col: str = "Close") -> pd.DataFrame:
    df = df.copy()
    for p in [5, 20, 60]:
        col = f"MA{p}"
        min_p = max(p // 2, 1)
        df[col] = df[price_col].rolling(p, min_periods=min_p).mean()
        df[f"{col}_slope"] = df[col].pct_change(fill_method=None)
    return df


def compute_all_mas(daily_all: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    daily = daily_all.sort_values(["Code", "Date"]).copy()

    for p in [5, 20, 60]:
        min_p = max(p // 2, 1)
        daily[f"MA{p}"] = daily.groupby("Code")["AdjC"].transform(
            lambda x, _p=p, _m=min_p: x.rolling(_p, min_periods=_m).mean()
        )
        daily[f"MA{p}_slope"] = daily.groupby("Code")[f"MA{p}"].transform(
            lambda x: x.pct_change(fill_method=None)
        )

    daily["Open"] = daily["O"]
    daily["High"] = daily["H"]
    daily["Low"] = daily["L"]
    daily["Close"] = daily["AdjC"]
    daily["Volume"] = daily["AdjVo"]

    # 週足リサンプリング（銘柄ごと）→ MA は一括計算で高速化
    weekly_frames = []
    for code, grp in daily.groupby("Code"):
        wk = resample_to_weekly(grp[["Date", "O", "H", "L", "AdjC", "AdjVo"]])
        wk["Code"] = code
        weekly_frames.append(wk)

    if not weekly_frames:
        return daily, pd.DataFrame()

    weekly_all = pd.concat(weekly_frames, ignore_index=True).sort_values(["Code", "Date"])
    for p in [5, 20, 60]:
        min_p = max(p // 2, 1)
        weekly_all[f"MA{p}"] = weekly_all.groupby("Code")["Close"].transform(
            lambda x, _p=p, _m=min_p: x.rolling(_p, min_periods=_m).mean()
        )
        weekly_all[f"MA{p}_slope"] = weekly_all.groupby("Code")[f"MA{p}"].transform(
            lambda x: x.pct_change(fill_method=None)
        )

    return daily, weekly_all


def filter_by_volume(weekly_all: pd.DataFrame, min_daily_volume: int, weeks: int = 4) -> set[str]:
    passing = set()
    for code, grp in weekly_all.groupby("Code"):
        if len(grp) < 2:
            continue
        n = min(weeks, len(grp))
        avg_daily = grp["Volume"].iloc[-n:].mean() / 5
        if avg_daily >= min_daily_volume:
            passing.add(code)
    return passing


def filter_by_price(daily_all: pd.DataFrame, max_price: float) -> set[str]:
    latest = daily_all.sort_values("Date").groupby("Code")["AdjC"].last()
    return set(latest[latest <= max_price].index)


def build_stock_frames(
    daily_all: pd.DataFrame,
    weekly_all: pd.DataFrame,
    codes: set[str],
) -> dict[str, dict[str, pd.DataFrame]]:
    result = {}
    for code in codes:
        d = daily_all[daily_all["Code"] == code].sort_values("Date").reset_index(drop=True)
        w = weekly_all[weekly_all["Code"] == code].sort_values("Date").reset_index(drop=True)
        # 日足10本・週足3本あれば評価対象（データが溜まるにつれて条件精度が上がる）
        if len(d) >= 10 and len(w) >= 3:
            result[code] = {"daily": d, "weekly": w}
    return result
