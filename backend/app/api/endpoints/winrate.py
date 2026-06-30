"""
バックテスト勝率計算エンドポイント。
GET  /winrate/status   — キャッシュ存在確認と結果返却
POST /winrate/compute  — SSEでバックテスト計算実行（重い処理）
"""
from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timedelta, timezone

import anyio
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.core import data_pipeline as dp
from app.core import backtest as bt

router = APIRouter()
JST = timezone(timedelta(hours=9))

_computing = False  # 重複実行防止フラグ（単一プロセス前提）


@router.get("/winrate/status")
async def winrate_status():
    """バックテストキャッシュの有無と結果を返す。"""
    cached = bt.load_backtest_cache()
    if cached is None:
        return {"has_cache": False, "cached_at": None, "stats": None}

    mtime = bt.STATS_CACHE.stat().st_mtime
    return {
        "has_cache": True,
        "cached_at": datetime.fromtimestamp(mtime, tz=JST).isoformat(),
        "stats": cached,
    }


@router.post("/winrate/compute")
async def compute_winrate():
    """
    バックテストを実行してSSEで進捗を流す。
    計算完了後にキャッシュへ保存し、result イベントで結果を返す。
    """
    global _computing

    async def generate():
        global _computing
        if _computing:
            yield {"data": json.dumps({"type": "error", "message": "すでに計算中です。しばらくお待ちください。"}, ensure_ascii=False)}
            return

        _computing = True
        t0 = time.monotonic()
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        try:
            yield {"data": json.dumps({"type": "progress", "pct": 0, "message": "日足データを読み込み中...", "elapsed": 0, "eta": None}, ensure_ascii=False)}

            daily_all = await anyio.to_thread.run_sync(
                lambda: dp.load_daily_ohlcv([]), abandon_on_cancel=True
            )
            if daily_all.empty:
                yield {"data": json.dumps({"type": "error", "message": "日足データがありません。先にスクリーナーを実行してデータを取得してください。"}, ensure_ascii=False)}
                return

            yield {"data": json.dumps({"type": "progress", "pct": 3, "message": "移動平均を計算中...", "elapsed": int(time.monotonic() - t0), "eta": None}, ensure_ascii=False)}

            daily_ma, weekly_ma = await anyio.to_thread.run_sync(
                lambda: dp.compute_all_mas(daily_all), abandon_on_cancel=True
            )

            n_codes = len(set(daily_ma["Code"].unique()) & set(weekly_ma["Code"].unique()))
            yield {"data": json.dumps({"type": "progress", "pct": 8, "message": f"バックテスト開始（{n_codes} 銘柄）...", "elapsed": int(time.monotonic() - t0), "eta": None}, ensure_ascii=False)}

            def on_progress(done: int, total: int):
                ratio = done / total if total > 0 else 0
                pct = 8 + 90 * ratio
                elapsed = time.monotonic() - t0
                eta = int(elapsed / ratio * (1 - ratio)) if ratio > 0 else None
                payload = {
                    "type": "progress",
                    "pct": round(pct, 1),
                    "message": f"バックテスト計算中... ({done}/{total} 銘柄)",
                    "elapsed": int(elapsed),
                    "eta": eta,
                }
                loop.call_soon_threadsafe(queue.put_nowait, payload)

            compute_task = asyncio.create_task(
                anyio.to_thread.run_sync(
                    lambda: bt.run_backtest(daily_ma, weekly_ma, on_progress),
                    abandon_on_cancel=True,
                )
            )

            while not compute_task.done():
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=2.0)
                    yield {"data": json.dumps(payload, ensure_ascii=False)}
                except asyncio.TimeoutError:
                    pass

            while not queue.empty():
                yield {"data": json.dumps(queue.get_nowait(), ensure_ascii=False)}

            stats = compute_task.result()
            bt.save_backtest_cache(stats)

            elapsed_sec = int(time.monotonic() - t0)
            yield {"data": json.dumps({
                "type": "result",
                "pct": 100,
                "message": f"バックテスト完了（{elapsed_sec}秒）",
                "stats": stats,
            }, ensure_ascii=False)}

        except Exception as e:
            yield {"data": json.dumps({"type": "error", "message": f"計算エラー: {e}"}, ensure_ascii=False)}
        finally:
            _computing = False

    return EventSourceResponse(generate())
