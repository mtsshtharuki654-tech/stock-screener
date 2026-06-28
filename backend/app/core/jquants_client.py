import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import jquantsapi
import pandas as pd
from datetime import datetime, timedelta, timezone
from app.config import settings

_client: jquantsapi.ClientV2 | None = None

JST = timezone(timedelta(hours=9))

# V2 subscription end date (update if plan is renewed)
def get_client() -> jquantsapi.ClientV2:
    global _client
    if _client is None:
        _client = jquantsapi.ClientV2(api_key=settings.jquants_api_key)
    return _client


SUBSCRIPTION_END = datetime(2026, 4, 6, tzinfo=JST)


def _cap_end(end_dt: datetime) -> datetime:
    return min(end_dt, SUBSCRIPTION_END)


def fetch_date(date_str: str) -> pd.DataFrame:
    """全銘柄の1日分OHLCVを取得。15秒タイムアウト付き。"""
    client = get_client()
    with ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(client.get_eq_bars_daily, date_yyyymmdd=date_str)
        try:
            return fut.result(timeout=15)
        except Exception:
            return pd.DataFrame()


def get_universe(segments: list[str]) -> pd.DataFrame:
    client = get_client()
    df = client.get_list()
    mask = df["MktNmEn"].isin(segments)
    return df[mask].copy().reset_index(drop=True)


def get_daily_ohlcv(
    start_dt: datetime,
    end_dt: datetime,
    progress_cb: "Callable[[int, int], None] | None" = None,
) -> pd.DataFrame:
    """
    全銘柄の日足OHLCVを日付範囲で取得。
    progress_cb(done, total) を各バッチ後に呼び出す。
    """
    end_capped = _cap_end(end_dt)
    dates = pd.date_range(start_dt, end_capped, freq="B")

    frames: list[pd.DataFrame] = []
    batch_size = 3
    batches = [dates[i:i + batch_size] for i in range(0, len(dates), batch_size)]
    total_batches = len(batches)

    for idx, batch_dates in enumerate(batches):
        batch = [d.strftime("%Y-%m-%d") for d in batch_dates]
        with ThreadPoolExecutor(max_workers=batch_size) as ex:
            futs = [ex.submit(fetch_date, d) for d in batch]
            for f in as_completed(futs):
                df = f.result()
                if not df.empty:
                    frames.append(df)
        if progress_cb:
            progress_cb(idx + 1, total_batches)
        time.sleep(2.0)

    if not frames:
        return pd.DataFrame()
    result = pd.concat(frames).sort_values(["Code", "Date"]).reset_index(drop=True)
    result["Date"] = pd.to_datetime(result["Date"])
    return result


def get_daily_ohlcv_single(
    code: str,
    start_dt: datetime,
    end_dt: datetime,
) -> pd.DataFrame:
    """1銘柄の日足OHLCVを取得。"""
    client = get_client()
    df = client.get_eq_bars_daily(
        code=code,
        from_yyyymmdd=start_dt.strftime("%Y%m%d"),
        to_yyyymmdd=_cap_end(end_dt).strftime("%Y%m%d"),
    )
    df["Date"] = pd.to_datetime(df["Date"])
    return df


def get_earnings_announcements() -> pd.DataFrame:
    client = get_client()
    try:
        return client.get_eq_earnings_cal()
    except Exception:
        return pd.DataFrame()


def get_index_ohlcv(index_code: str, start_dt: datetime, end_dt: datetime) -> pd.DataFrame:
    client = get_client()
    try:
        end_capped = _cap_end(end_dt)
        if index_code == "topix":
            df = client.get_idx_bars_daily_topix(
                from_yyyymmdd=start_dt.strftime("%Y%m%d"),
                to_yyyymmdd=end_capped.strftime("%Y%m%d"),
            )
        else:
            df = client.get_idx_bars_daily(
                code=index_code,
                from_yyyymmdd=start_dt.strftime("%Y%m%d"),
                to_yyyymmdd=end_capped.strftime("%Y%m%d"),
            )
        df["Date"] = pd.to_datetime(df["Date"])
        return df
    except Exception:
        return pd.DataFrame()
