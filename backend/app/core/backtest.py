"""
勝率計算モジュール。
- Bモード: 固定ルックアップテーブル（get_lookup_stats）
- Aモード: 過去データのバックテスト（run_backtest）
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from typing import Callable

import pandas as pd

from app.config import settings

JST = timezone(timedelta(hours=9))
STATS_CACHE = settings.cache_dir / "condition_stats.json"
CACHE_TTL_HOURS = 24 * 7  # 1週間

# ---------- B: 固定ルックアップテーブル ----------
# 翌週に期待方向へ動く歴史的確率（日本株市場の一般的なTA文献・経験則ベース）

LOOKUP_WIN_RATES: dict[str, float] = {
    "ppp_pullback":          0.67,
    "weekly_ma20_bounce":    0.65,
    "jump_dai":              0.63,
    "n_shape":               0.63,
    "dead_cross":            0.63,
    "reverse_jump_dai":      0.63,
    "kahanshin":             0.62,
    "reverse_kahanshin":     0.62,
    "golden_cross_imminent": 0.62,
    "dow_long_reversal":     0.61,
    "try_todokazu":          0.60,
}


def get_lookup_stats() -> dict[str, dict]:
    """固定テーブルから勝率情報を返す（Bモード）。"""
    return {
        key: {"win_rate": rate, "n": None, "source": "lookup"}
        for key, rate in LOOKUP_WIN_RATES.items()
    }


# ---------- A: バックテスト ----------

def load_backtest_cache() -> dict[str, dict] | None:
    """キャッシュファイルからバックテスト結果を読む。TTL切れまたは存在しなければNoneを返す。"""
    if not STATS_CACHE.exists():
        return None
    try:
        mtime = datetime.fromtimestamp(STATS_CACHE.stat().st_mtime, tz=JST)
        age_hours = (datetime.now(JST) - mtime).total_seconds() / 3600
        if age_hours > CACHE_TTL_HOURS:
            return None
        with STATS_CACHE.open(encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_backtest_cache(stats: dict[str, dict]) -> None:
    """バックテスト結果をJSONキャッシュに書き込む。"""
    with STATS_CACHE.open("w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False)


def run_backtest(
    daily_all: pd.DataFrame,
    weekly_all: pd.DataFrame,
    progress_cb: Callable[[int, int], None] | None = None,
) -> dict[str, dict]:
    """
    全銘柄×全週のデータでバックテストを実行し、条件ごとの勝率を返す。

    各週末時点でシグナルが発火した場合、翌週の終値が期待方向に動いたかを記録する。
    - Long条件: 翌週終値 > 当週終値 → win
    - Short条件: 翌週終値 < 当週終値 → win

    progress_cb(done, total) は任意のコールバック（スレッドから呼ばれる）。
    """
    from app.core.screener import CONDITION_FUNCS, LONG_CONDITIONS

    wins: dict[str, int] = {key: 0 for key in CONDITION_FUNCS}
    totals: dict[str, int] = {key: 0 for key in CONDITION_FUNCS}

    codes = list(set(daily_all["Code"].unique()) & set(weekly_all["Code"].unique()))
    n_total = len(codes)

    for i, code in enumerate(codes):
        d = daily_all[daily_all["Code"] == code].sort_values("Date").reset_index(drop=True)
        w = weekly_all[weekly_all["Code"] == code].sort_values("Date").reset_index(drop=True)

        # MA60が安定するため最低65週必要。翌週参照のため最後の1本は評価対象外
        if len(w) < 66 or len(d) < 65:
            continue

        d_dates = d["Date"].values

        for wi in range(64, len(w) - 1):
            w_slice = w.iloc[: wi + 1]
            week_date = w.iloc[wi]["Date"]
            cur_close = float(w.iloc[wi]["Close"])
            next_close = float(w.iloc[wi + 1]["Close"])
            if cur_close <= 0 or next_close <= 0:
                continue

            # 日足スライス: week_date 以前のデータのみ使用（look-ahead bias 防止）
            di = int(pd.searchsorted(d_dates, week_date.to_datetime64(), side="right"))
            if di < 65:
                continue
            d_slice = d.iloc[:di]

            for key, fn in CONDITION_FUNCS.items():
                try:
                    fired = fn(d_slice, w_slice)
                except Exception:
                    fired = False
                if not fired:
                    continue

                totals[key] += 1
                is_long = key in LONG_CONDITIONS
                if is_long and next_close > cur_close:
                    wins[key] += 1
                elif not is_long and next_close < cur_close:
                    wins[key] += 1

        if progress_cb and ((i + 1) % 20 == 0 or i + 1 == n_total):
            progress_cb(i + 1, n_total)

    result: dict[str, dict] = {}
    for key in CONDITION_FUNCS:
        t = totals[key]
        w_count = wins[key]
        result[key] = {
            "win_rate": round(w_count / t, 4) if t >= 30 else None,
            "n": t,
            "source": "backtest",
        }
    return result
