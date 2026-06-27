import asyncio
import time
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter

from app.models.screen import ScreenRequest, ScreenResponse, ScreenHit, MASnapshot
from app.core import data_pipeline as dp, screener as sc
from app.core.corporate_events import get_corporate_events
from app.core.index_correlation import get_correlation_for_stock

router = APIRouter()
JST = timezone(timedelta(hours=9))


@router.post("/screen", response_model=ScreenResponse)
async def run_screen(req: ScreenRequest) -> ScreenResponse:
    t0 = time.monotonic()

    # --- 1. データ取得 & MA計算 ---
    universe_df = dp.load_universe(req.segments)
    daily_all = dp.load_daily_ohlcv(req.segments)

    daily_ma, weekly_ma = dp.compute_all_mas(daily_all)

    # --- 2. 基本フィルター ---
    price_pass = dp.filter_by_price(daily_ma, req.max_price)
    volume_pass = dp.filter_by_volume(weekly_ma, req.min_volume)
    candidate_codes = price_pass & volume_pass

    # 市場区分フィルター適用済みのコードセット
    universe_codes = set(universe_df["Code"].astype(str))
    candidate_codes &= universe_codes

    total_universe = len(universe_codes)

    # --- 3. MA付きフレームを構築 ---
    stock_frames = dp.build_stock_frames(daily_ma, weekly_ma, candidate_codes)

    # --- 4. スクリーニング ---
    hits: list[ScreenHit] = []
    corp_tasks = []

    for code, frames in stock_frames.items():
        matched = sc.run_conditions(frames["daily"], frames["weekly"], req.conditions)
        if not matched:
            continue

        daily_df = frames["daily"]
        weekly_df = frames["weekly"]
        row = universe_df[universe_df["Code"].astype(str) == code]
        name = str(row["CoName"].iloc[0]) if not row.empty else code
        segment_en = str(row["MktNmEn"].iloc[0]) if not row.empty else "Prime"

        last_price = float(daily_df["AdjC"].iloc[-1])
        last_volume = int(daily_df["AdjVo"].iloc[-1])
        avg_weekly_volume = int(weekly_df["Volume"].iloc[-4:].mean() / 5) if len(weekly_df) >= 4 else 0

        def _ma_snap(df, col_suffix=""):
            return MASnapshot(
                ma5=round(float(df["MA5"].iloc[-1]), 2) if "MA5" in df.columns else 0,
                ma20=round(float(df["MA20"].iloc[-1]), 2) if "MA20" in df.columns else 0,
                ma60=round(float(df["MA60"].iloc[-1]), 2) if "MA60" in df.columns else 0,
            )

        corr = get_correlation_for_stock(daily_df, segment_en)

        hit = ScreenHit(
            code=code,
            name=name,
            segment=segment_en,
            last_price=last_price,
            last_volume=last_volume,
            avg_weekly_volume=avg_weekly_volume,
            conditions_matched=matched,
            signal_type=sc.determine_signal_type(matched),
            weekly_ma=_ma_snap(weekly_df),
            daily_ma=_ma_snap(daily_df),
            index_correlation=corr,
        )
        corp_tasks.append((hit, code, segment_en, daily_df))
        hits.append(hit)

    # --- 5. コーポレートアクション（ヒット銘柄のみ） ---
    if corp_tasks:
        events_results = await asyncio.gather(*[
            get_corporate_events(code, seg, df)
            for (hit, code, seg, df) in corp_tasks
        ])
        for (hit, _, _, _), events in zip(corp_tasks, events_results):
            hit.corporate_events = events

    duration_ms = int((time.monotonic() - t0) * 1000)

    return ScreenResponse(
        screened_at=datetime.now(JST),
        total_universe=total_universe,
        hits=hits,
        duration_ms=duration_ms,
    )
