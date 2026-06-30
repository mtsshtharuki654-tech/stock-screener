import asyncio
import json
import math
import time
from datetime import datetime, timezone, timedelta

import anyio
import pandas as pd
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.models.screen import ScreenRequest, ScreenResponse, ScreenHit, MASnapshot, CorporateEvents, ConditionStat
from app.core import data_pipeline as dp, screener as sc
from app.core.corporate_events import get_corporate_events
from app.core.index_correlation import get_correlation_for_stock
from app.core import backtest as bt

router = APIRouter()
JST = timezone(timedelta(hours=9))

_WEIGHT_UNIVERSE  = 2
_WEIGHT_OHLCV     = 85
_WEIGHT_MA        = 8
_WEIGHT_SCREEN    = 5
_WEIGHT_CORP      = 5


def _safe_float(val, default: float = 0.0) -> float:
    """float変換後に NaN/Inf なら default を返す。"""
    try:
        v = float(val)
        return default if (math.isnan(v) or math.isinf(v)) else v
    except Exception:
        return default


def _clean_nans(obj):
    """dict/list を再帰的に走査し、NaN/Inf を None に置換してJSON安全にする。"""
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: _clean_nans(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean_nans(v) for v in obj]
    return obj


def _ma_snap(df: pd.DataFrame) -> MASnapshot:
    return MASnapshot(
        ma5=round(_safe_float(df["MA5"].iloc[-1]), 2) if "MA5" in df.columns else 0,
        ma20=round(_safe_float(df["MA20"].iloc[-1]), 2) if "MA20" in df.columns else 0,
        ma60=round(_safe_float(df["MA60"].iloc[-1]), 2) if "MA60" in df.columns else 0,
    )


def _make_progress(t0: float, pct: float, msg: str) -> dict:
    elapsed = time.monotonic() - t0
    eta = int(elapsed / pct * (100 - pct)) if pct > 0 else None
    return {
        "type": "progress",
        "pct": round(pct, 1),
        "message": msg,
        "elapsed": int(elapsed),
        "eta": eta,
    }


@router.post("/screen")
async def run_screen(req: ScreenRequest):
    async def generate():
        t0 = time.monotonic()
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        # ---- ステップ1: 銘柄マスター ----
        yield {"data": json.dumps(_make_progress(t0, 0, "銘柄マスターを取得中..."), ensure_ascii=False)}
        try:
            universe_df = await anyio.to_thread.run_sync(
                lambda: dp.load_universe(req.segments), abandon_on_cancel=True
            )
        except Exception as e:
            yield {"data": json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)}
            return
        yield {"data": json.dumps(_make_progress(t0, _WEIGHT_UNIVERSE, "銘柄マスター取得完了"), ensure_ascii=False)}

        # ---- ステップ2: 日足OHLCV（進捗はスレッドからキュー経由） ----
        yield {"data": json.dumps(_make_progress(t0, _WEIGHT_UNIVERSE, "日足データを取得中..."), ensure_ascii=False)}

        def on_ohlcv_progress(done: int, total: int):
            pct = _WEIGHT_UNIVERSE + _WEIGHT_OHLCV * done / total
            payload = _make_progress(t0, pct, f"日足データを取得中...（{done}/{total} バッチ）")
            loop.call_soon_threadsafe(queue.put_nowait, payload)

        async def _fetch_ohlcv():
            return await anyio.to_thread.run_sync(
                lambda: dp.load_daily_ohlcv(req.segments, on_ohlcv_progress),
                abandon_on_cancel=True,
            )

        async with anyio.create_task_group() as tg:
            fetch_result: list = []

            async def _run_fetch():
                try:
                    fetch_result.append(await _fetch_ohlcv())
                except Exception as exc:
                    fetch_result.append(exc)
                finally:
                    tg.cancel_scope.cancel()

            tg.start_soon(_run_fetch)

            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=2.0)
                    yield {"data": json.dumps(payload, ensure_ascii=False)}
                except asyncio.TimeoutError:
                    if fetch_result:
                        break

        # 残りのキューを全部流す
        while not queue.empty():
            yield {"data": json.dumps(queue.get_nowait(), ensure_ascii=False)}

        if not fetch_result:
            yield {"data": json.dumps({"type": "error", "message": "日足データ取得が完了しませんでした。"}, ensure_ascii=False)}
            return

        daily_all_or_exc = fetch_result[0]
        if isinstance(daily_all_or_exc, Exception):
            msg = str(daily_all_or_exc)
            detail = "J-Quants APIのレート制限です。少し待ってから再試行してください。" if "429" in msg else msg
            yield {"data": json.dumps({"type": "error", "message": detail}, ensure_ascii=False)}
            return
        daily_all = daily_all_or_exc

        if daily_all.empty or "Date" not in daily_all.columns:
            yield {"data": json.dumps({"type": "error", "message": "日足データが取得できませんでした。J-Quants APIのレート制限または契約期間を確認してください。"}, ensure_ascii=False)}
            return

        # ---- ステップ3: MA計算 ----
        yield {"data": json.dumps(_make_progress(t0, _WEIGHT_UNIVERSE + _WEIGHT_OHLCV, "移動平均を計算中..."), ensure_ascii=False)}
        daily_ma, weekly_ma = await anyio.to_thread.run_sync(
            lambda: dp.compute_all_mas(daily_all), abandon_on_cancel=True
        )

        price_pass = dp.filter_by_price(daily_ma, req.max_price)
        volume_pass = dp.filter_by_volume(weekly_ma, req.min_volume)
        candidate_codes = price_pass & volume_pass & set(universe_df["Code"].astype(str))
        total_universe = len(set(universe_df["Code"].astype(str)))
        stock_frames = dp.build_stock_frames(daily_ma, weekly_ma, candidate_codes)

        # ---- ステップ4: スクリーニング ----
        yield {"data": json.dumps(_make_progress(t0, _WEIGHT_UNIVERSE + _WEIGHT_OHLCV + _WEIGHT_MA, f"スクリーニング中（{len(stock_frames)} 銘柄）..."), ensure_ascii=False)}

        # 指数データを事前に非同期取得（タイムアウト付き）。スレッド内でのAPI呼び出しを防ぐ。
        async def _load_index_safe(code: str) -> pd.DataFrame:
            try:
                return await anyio.to_thread.run_sync(
                    lambda: dp.load_index_ohlcv(code), abandon_on_cancel=True
                )
            except Exception:
                return pd.DataFrame()

        index_cache: dict[str, pd.DataFrame] = {}
        for _idx_code in ("topix", "0049"):
            with anyio.move_on_after(10.0):
                index_cache[_idx_code] = await _load_index_safe(_idx_code)
            if _idx_code not in index_cache:
                index_cache[_idx_code] = pd.DataFrame()

        screen_queue: asyncio.Queue = asyncio.Queue()
        total_stocks = len(stock_frames)

        def _run_screening() -> list[ScreenHit]:
            result: list[ScreenHit] = []
            for i, (code, frames) in enumerate(stock_frames.items()):
                try:
                    matched = sc.run_conditions(frames["daily"], frames["weekly"], req.conditions)
                    if not matched:
                        continue
                    daily_df = frames["daily"]
                    weekly_df = frames["weekly"]
                    row = universe_df[universe_df["Code"].astype(str) == code]
                    name = str(row["CoName"].iloc[0]) if not row.empty else code
                    segment_en = str(row["MktNmEn"].iloc[0]) if not row.empty else "Prime"
                    last_vol = daily_df["AdjVo"].iloc[-1]
                    avg_vol = weekly_df["Volume"].iloc[-4:].mean() / 5 if len(weekly_df) >= 4 else 0.0
                    result.append(ScreenHit(
                        code=code,
                        name=name,
                        segment=segment_en,
                        last_price=_safe_float(daily_df["AdjC"].iloc[-1]),
                        last_volume=int(last_vol) if pd.notna(last_vol) else 0,
                        avg_weekly_volume=int(avg_vol) if pd.notna(avg_vol) else 0,
                        conditions_matched=matched,
                        signal_type=sc.determine_signal_type(matched),
                        weekly_ma=_ma_snap(weekly_df),
                        daily_ma=_ma_snap(daily_df),
                        index_correlation=get_correlation_for_stock(daily_df, segment_en, index_cache),
                    ))
                except Exception:
                    pass

                if total_stocks > 0 and ((i + 1) % 50 == 0 or (i + 1) == total_stocks):
                    pct = _WEIGHT_UNIVERSE + _WEIGHT_OHLCV + _WEIGHT_MA + _WEIGHT_SCREEN * (i + 1) / total_stocks
                    payload = _make_progress(t0, pct, f"スクリーニング中（{i + 1}/{total_stocks} 銘柄）...")
                    loop.call_soon_threadsafe(screen_queue.put_nowait, payload)

            return result

        screen_task = asyncio.create_task(
            anyio.to_thread.run_sync(_run_screening, abandon_on_cancel=True)
        )

        while not screen_task.done():
            try:
                payload = await asyncio.wait_for(screen_queue.get(), timeout=2.0)
                yield {"data": json.dumps(payload, ensure_ascii=False)}
            except asyncio.TimeoutError:
                pass

        while not screen_queue.empty():
            yield {"data": json.dumps(screen_queue.get_nowait(), ensure_ascii=False)}

        try:
            hits = screen_task.result()
        except Exception as e:
            yield {"data": json.dumps({"type": "error", "message": f"スクリーニングエラー: {str(e)}"}, ensure_ascii=False)}
            return

        duration_ms = int((time.monotonic() - t0) * 1000)

        lookup_raw = bt.get_lookup_stats()
        lookup_stats = {k: ConditionStat(**v) for k, v in lookup_raw.items()}

        backtest_raw = bt.load_backtest_cache()
        backtest_stats = {k: ConditionStat(**v) for k, v in backtest_raw.items()} if backtest_raw else None

        response = ScreenResponse(
            screened_at=datetime.now(JST),
            total_universe=total_universe,
            hits=hits,
            duration_ms=duration_ms,
            lookup_stats=lookup_stats,
            backtest_stats=backtest_stats,
        )
        yield {"data": json.dumps(
            _clean_nans({"type": "result", "pct": 100, "data": response.model_dump(mode="json")}),
            ensure_ascii=False,
        )}

    return EventSourceResponse(generate())


@router.get("/events/{code}", response_model=CorporateEvents)
async def get_stock_events(code: str):
    """銘柄コードの注意情報を返す（オンデマンド）。yfinanceで決算日を取得。"""
    return await get_corporate_events(code)
