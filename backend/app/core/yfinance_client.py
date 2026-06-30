from datetime import datetime, timedelta
import time
import pandas as pd
import yfinance as yf

LOOKBACK_DAYS = 450


def _to_jquants_format(df: pd.DataFrame, code: str) -> pd.DataFrame:
    """yfinanceのDataFrameをJ-Quants互換形式（O/H/L/AdjC/AdjVo）に変換。"""
    df = df.copy()

    # MultiIndex列をフラット化
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.reset_index()
    df = df.rename(columns={
        "Open": "O",
        "High": "H",
        "Low": "L",
        "Close": "AdjC",
        "Volume": "AdjVo",
    })
    df["Code"] = code
    df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)

    cols = [c for c in ["Date", "Code", "O", "H", "L", "AdjC", "AdjVo"] if c in df.columns]
    return df[cols].dropna(subset=["AdjC"]).sort_values("Date").reset_index(drop=True)


def _to_yf_ticker(code: str) -> str:
    """J-Quants 5桁コード（例: 72030）をYahoo Finance用4桁コード（例: 7203.T）に変換。"""
    c = str(code)
    if len(c) == 5 and c.endswith("0"):
        c = c[:-1]
    return f"{c}.T"


def fetch_single(code: str, start: datetime, end: datetime) -> pd.DataFrame:
    """単一銘柄のOHLCVを取得。"""
    try:
        raw = yf.download(
            _to_yf_ticker(code),
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            auto_adjust=True,
            progress=False,
        )
        if raw.empty:
            return pd.DataFrame()
        return _to_jquants_format(raw, code)
    except Exception:
        return pd.DataFrame()


def fetch_batch(
    codes: list[str],
    start: datetime,
    end: datetime,
    progress_cb=None,
    batch_size: int = 50,
) -> pd.DataFrame:
    """複数銘柄のOHLCVを一括取得。"""
    all_frames: list[pd.DataFrame] = []
    total = len(codes)
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")

    for batch_start in range(0, total, batch_size):
        batch_codes = codes[batch_start:batch_start + batch_size]
        tickers = [_to_yf_ticker(c) for c in batch_codes]

        try:
            raw = yf.download(
                tickers,
                start=start_str,
                end=end_str,
                auto_adjust=True,
                progress=False,
                group_by="ticker",
            )
            if raw.empty:
                continue

            for code, ticker in zip(batch_codes, tickers):
                try:
                    stock_df = raw[ticker] if len(tickers) > 1 else raw
                    if stock_df.empty:
                        continue
                    df = _to_jquants_format(stock_df, code)
                    if not df.empty:
                        all_frames.append(df)
                except Exception:
                    continue

        except Exception:
            continue

        if progress_cb:
            progress_cb(min(batch_start + batch_size, total), total)

        time.sleep(0.5)

    if not all_frames:
        return pd.DataFrame()

    result = pd.concat(all_frames, ignore_index=True)
    return result.sort_values(["Code", "Date"]).reset_index(drop=True)
