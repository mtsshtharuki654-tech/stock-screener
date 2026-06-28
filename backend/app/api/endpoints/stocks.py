import calendar
from datetime import datetime, timedelta, timezone

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.core import jquants_client as jq
from app.core.data_pipeline import add_ma_columns, resample_to_weekly, DAILY_CACHE
from app.models.stock import ChartData, OHLCV, MASet, MAPoint

router = APIRouter()
JST = timezone(timedelta(hours=9))


def _to_unix(dt) -> int:
    if isinstance(dt, pd.Timestamp):
        return int(dt.timestamp())
    return int(datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc).timestamp())


def _load_from_cache(code: str) -> pd.DataFrame:
    """全銘柄キャッシュから1銘柄分を取り出す。キャッシュがなければ空DFを返す。"""
    if not DAILY_CACHE.exists():
        return pd.DataFrame()
    try:
        df = pd.read_parquet(DAILY_CACHE, filters=[("Code", "==", code)])
        df["Date"] = pd.to_datetime(df["Date"])
        return df.sort_values("Date").reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


@router.get("/stocks/{code}/chart", response_model=ChartData)
async def get_chart(
    code: str,
    timeframe: str = Query("weekly", pattern="^(weekly|daily)$"),
    periods: int = Query(200, ge=20, le=500),
) -> ChartData:
    # まずキャッシュから取得し、なければAPIにフォールバック
    daily_df = _load_from_cache(code)
    if daily_df.empty:
        end = datetime.now(JST)
        start = end - timedelta(days=periods * 7 + 90)
        daily_df = jq.get_daily_ohlcv_single(code, start, end)
    if daily_df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {code}")

    daily_df = daily_df.sort_values("Date").reset_index(drop=True)

    # V2 uses AdjC/AdjVo; resample_to_weekly renames them to Close/Volume
    if timeframe == "weekly":
        df = resample_to_weekly(daily_df)
        df = add_ma_columns(df, price_col="Close")
        price_col = "Close"
        open_col = "Open"
        high_col = "High"
        low_col = "Low"
        vol_col = "Volume"
    else:
        df = add_ma_columns(daily_df, price_col="AdjC")
        price_col = "AdjC"
        open_col = "O"
        high_col = "H"
        low_col = "L"
        vol_col = "AdjVo"

    df = df.tail(periods).reset_index(drop=True)

    candles = [
        OHLCV(
            time=_to_unix(row["Date"]),
            open=round(float(row[open_col]), 2),
            high=round(float(row[high_col]), 2),
            low=round(float(row[low_col]), 2),
            close=round(float(row[price_col]), 2),
            volume=int(row[vol_col]) if not pd.isna(row[vol_col]) else 0,
        )
        for _, row in df.iterrows()
        if not pd.isna(row[price_col])
    ]

    def _ma_series(col: str) -> list[MAPoint]:
        return [
            MAPoint(time=_to_unix(row["Date"]), value=round(float(row[col]), 2))
            for _, row in df.iterrows()
            if col in df.columns and not pd.isna(row[col])
        ]

    # 銘柄名を取得（ユニバースから）
    try:
        universe = jq.get_universe(["Prime", "Growth"])
        name_row = universe[universe["Code"].astype(str) == code]
        name = str(name_row["CoName"].iloc[0]) if not name_row.empty else code
    except Exception:
        name = code

    return ChartData(
        code=code,
        name=name,
        timeframe=timeframe,
        candles=candles,
        ma=MASet(
            ma5=_ma_series("MA5"),
            ma20=_ma_series("MA20"),
            ma60=_ma_series("MA60"),
        ),
    )
