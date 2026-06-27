import asyncio
import json
import time
from datetime import datetime, timezone, timedelta

import pandas as pd
from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.models.screen import ScreenRequest, ScreenResponse, ScreenHit, MASnapshot
from app.core import data_pipeline as dp, screener as sc
from app.core.corporate_events import get_corporate_events
from app.core.index_correlation import get_correlation_for_stock

router = APIRouter()
JST = timezone(timedelta(hours=9))


def _ma_snap(df: pd.DataFrame) -> MASnapshot:
    return MASnapshot(
        ma5=round(float(df["MA5"].iloc[-1]), 2) if "MA5" in df.columns else 0,
        ma20=round(float(df["MA20"].iloc[-1]), 2) if "MA20" in df.columns else 0,
        ma60=round(float(df["MA60"].iloc[-1]), 2) if "MA60" in df.columns else 0,
    )


@router.post("/screen")
async def run_screen(req: ScreenRequest):
    """SSEで進捗を流しながらスクリーニング結果を返す。"""

    async def generate():
        t0 = time.monotonic()

        def progress(msg: str):
            return json.dumps({"type": "progress", "message": msg}, ensure_ascii=False)

        # --- 1. データ取得 ---
        yield {"data": progress("銘柄マスターを取得中...")}
        try:
            universe_df = await asyncio.to_thread(dp.load_universe, req.segments)
        except Exception as e:
            yield {"data": json.dumps({"type": "error", "message": f"銘柄マスター取得失敗: {e}"})}
            return

        yield {"data": progress("日足データを取得中（初回は数分かかります）...")}
        try:
            daily_all = await asyncio.to_thread(dp.load_daily_ohlcv, req.segments)
        except Exception as e:
            msg = str(e)
            detail = "J-Quants APIのレート制限です。1〜2分待って再試行してください。" if "429" in msg else str(e)
            yield {"data": json.dumps({"type": "error", "message": detail})}
            return

        # --- 2. MA計算 & フィルター ---
        yield {"data": progress("移動平均を計算中...")}
        daily_ma, weekly_ma = await asyncio.to_thread(dp.compute_all_mas, daily_all)

        price_pass = dp.filter_by_price(daily_ma, req.max_price)
        volume_pass = dp.filter_by_volume(weekly_ma, req.min_volume)
        candidate_codes = price_pass & volume_pass & set(universe_df["Code"].astype(str))
        total_universe = len(set(universe_df["Code"].astype(str)))

        stock_frames = dp.build_stock_frames(daily_ma, weekly_ma, candidate_codes)
        yield {"data": progress(f"スクリーニング中（対象 {len(stock_frames)} 銘柄）...")}

        # --- 3. スクリーニング ---
        def _run_screening() -> tuple[list[ScreenHit], list[tuple]]:
            result_hits: list[ScreenHit] = []
            result_tasks = []
            for code, frames in stock_frames.items():
                matched = sc.run_conditions(frames["daily"], frames["weekly"], req.conditions)
                if not matched:
                    continue
                daily_df = frames["daily"]
                weekly_df = frames["weekly"]
                row = universe_df[universe_df["Code"].astype(str) == code]
                name = str(row["CoName"].iloc[0]) if not row.empty else code
                segment_en = str(row["MktNmEn"].iloc[0]) if not row.empty else "Prime"
                hit = ScreenHit(
                    code=code,
                    name=name,
                    segment=segment_en,
                    last_price=float(daily_df["AdjC"].iloc[-1]),
                    last_volume=int(daily_df["AdjVo"].iloc[-1]),
                    avg_weekly_volume=int(weekly_df["Volume"].iloc[-4:].mean() / 5) if len(weekly_df) >= 4 else 0,
                    conditions_matched=matched,
                    signal_type=sc.determine_signal_type(matched),
                    weekly_ma=_ma_snap(weekly_df),
                    daily_ma=_ma_snap(daily_df),
                    index_correlation=get_correlation_for_stock(daily_df, segment_en),
                )
                result_tasks.append((hit, code, segment_en, daily_df))
                result_hits.append(hit)
            return result_hits, result_tasks

        hits, corp_tasks = await asyncio.to_thread(_run_screening)

        # --- 4. コーポレートアクション ---
        if corp_tasks:
            yield {"data": progress(f"コーポレート情報を取得中（{len(corp_tasks)} 銘柄）...")}
            events_results = await asyncio.gather(*[
                get_corporate_events(code, seg, df)
                for (hit, code, seg, df) in corp_tasks
            ])
            for (hit, _, _, _), events in zip(corp_tasks, events_results):
                hit.corporate_events = events

        duration_ms = int((time.monotonic() - t0) * 1000)
        response = ScreenResponse(
            screened_at=datetime.now(JST),
            total_universe=total_universe,
            hits=hits,
            duration_ms=duration_ms,
        )
        yield {"data": json.dumps({"type": "result", "data": response.model_dump(mode="json")}, ensure_ascii=False)}

    return EventSourceResponse(generate())
