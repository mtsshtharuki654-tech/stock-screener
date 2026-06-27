import pandas as pd
import numpy as np
from typing import Callable

# ---------- helpers ----------

def _latest(df: pd.DataFrame, col: str, offset: int = 0) -> float:
    return float(df[col].iloc[-(1 + offset)])


def _slope(df: pd.DataFrame, col: str, offset: int = 0) -> float:
    return float(df[f"{col}_slope"].iloc[-(1 + offset)])


def _find_local_lows(series: pd.Series, window: int = 3) -> list[int]:
    """Return indices of local minima."""
    lows = []
    arr = series.values
    for i in range(window, len(arr) - window):
        if arr[i] == min(arr[i - window:i + window + 1]):
            lows.append(i)
    return lows


def _find_local_highs(series: pd.Series, window: int = 3) -> list[int]:
    """Return indices of local maxima."""
    highs = []
    arr = series.values
    for i in range(window, len(arr) - window):
        if arr[i] == max(arr[i - window:i + window + 1]):
            highs.append(i)
    return highs


# ---------- Long conditions ----------

def check_jump_dai(daily: pd.DataFrame, weekly: pd.DataFrame) -> bool:
    """
    ジャンプ台: MA5 > MA20, MA5がMA20に接近してから陽線で反発。
    日足または週足で判定。
    """
    def _check(df: pd.DataFrame) -> bool:
        if len(df) < 10:
            return False
        latest = df.iloc[-1]
        if latest["MA5"] <= latest["MA20"]:
            return False

        # 直近5本でMA5とMA20の距離が最小になったバーを探す
        window = df.iloc[-6:-1]
        gaps = ((window["MA5"] - window["MA20"]) / window["MA20"]).abs()
        min_gap = gaps.min()
        if min_gap > 0.03:
            return False

        # 現在は距離が広がり始め（MA5スロープ上向き）かつ陽線
        current_gap = abs(latest["MA5"] - latest["MA20"]) / latest["MA20"]
        if current_gap <= min_gap:
            return False
        if _slope(df, "MA5") <= 0:
            return False
        return latest["Close"] > latest["Open"]  # 陽線

    return _check(daily) or _check(weekly)


def check_kahanshin(daily: pd.DataFrame, weekly: pd.DataFrame) -> bool:
    """
    下半身: 前バーの終値がMA5以下 → 現バーの陽線でMA5を上抜け、実体の50%以上がMA5より上。
    """
    def _check(df: pd.DataFrame) -> bool:
        if len(df) < 10:
            return False
        cur = df.iloc[-1]
        prev = df.iloc[-2]
        ma5 = cur["MA5"]
        if pd.isna(ma5):
            return False
        if prev["Close"] > ma5:
            return False
        if cur["Close"] <= ma5:
            return False
        if cur["Open"] >= cur["Close"]:  # 陰線は除外
            return False
        body = cur["Close"] - cur["Open"]
        if body <= 0:
            return False
        above_ratio = (cur["Close"] - ma5) / body
        return above_ratio >= 0.5

    return _check(daily) or _check(weekly)


def check_ppp_pullback(weekly: pd.DataFrame, _daily: pd.DataFrame = None) -> bool:
    """
    PPP押し目: 週足でパーフェクトオーダー維持 + 直近3週に押し目。
    """
    if len(weekly) < 62:
        return False
    latest = weekly.iloc[-1]

    # パーフェクトオーダー
    if not (latest["MA5"] > latest["MA20"] > latest["MA60"]):
        return False
    # 全線上向き
    for ma in ["MA5", "MA20", "MA60"]:
        if _slope(weekly, ma) <= 0:
            return False

    # 直近3週に押し目（終値がMA20の103%以内）
    pullback_window = weekly.iloc[-4:-1]
    touched = any(
        row["Close"] <= row["MA20"] * 1.03
        for _, row in pullback_window.iterrows()
        if not pd.isna(row["MA20"])
    )
    if not touched:
        return False

    # 直近安値がMA60の95%以上（暴落でない）
    return latest["Low"] >= latest["MA60"] * 0.95


def check_weekly_ma20_bounce(weekly: pd.DataFrame, _daily: pd.DataFrame = None) -> bool:
    """
    週足20線反発: MA60上向き、前週安値がMA20付近、今週陽線でMA20より上。
    """
    if len(weekly) < 62:
        return False
    cur = weekly.iloc[-1]
    prev = weekly.iloc[-2]

    if _slope(weekly, "MA60") <= 0:
        return False
    if pd.isna(prev["MA20"]) or pd.isna(cur["MA20"]):
        return False
    # 前週安値がMA20の103%以内
    if prev["Low"] > prev["MA20"] * 1.03:
        return False
    # 今週陽線かつMA20より上
    if cur["Close"] <= cur["Open"]:
        return False
    if cur["Close"] <= cur["MA20"]:
        return False
    # 直近安値がMA60の95%以上
    return cur["Low"] >= cur["MA60"] * 0.95


def check_n_shape(daily: pd.DataFrame, _weekly: pd.DataFrame = None) -> bool:
    """
    N大: 直近20本以内にGC、その後MA20に接近するが割れず、現在再上昇。
    """
    if len(daily) < 25:
        return False

    window = daily.iloc[-21:]
    ma5 = window["MA5"].values
    ma20 = window["MA20"].values

    # GC（MA5がMA20を下から上に抜いた）を検索
    gc_idx = None
    for i in range(1, len(window) - 2):
        if ma5[i - 1] < ma20[i - 1] and ma5[i] >= ma20[i]:
            gc_idx = i
            break
    if gc_idx is None:
        return False

    # GC後に接近（ギャップ≤3%）したが割り込まず
    post = window.iloc[gc_idx:]
    for _, row in post.iterrows():
        if pd.isna(row["MA5"]) or pd.isna(row["MA20"]):
            continue
        if row["MA5"] < row["MA20"]:
            return False  # MA20を割り込んだ

    gaps = ((post["MA5"] - post["MA20"]) / post["MA20"]).abs()
    if gaps.min() > 0.03:
        return False  # 十分に接近しなかった

    # 現在MA5スロープ上向き
    if _slope(daily, "MA5") <= 0:
        return False
    return _slope(daily, "MA60") > 0


def check_dow_long_reversal(daily: pd.DataFrame, _weekly: pd.DataFrame = None) -> bool:
    """
    ダウ理論転換（買い）: 直近15本以内に安値の切り上げ + 直近が陽線。
    """
    if len(daily) < 20:
        return False

    window = daily.iloc[-16:]
    lows = _find_local_lows(window["Low"])
    if len(lows) < 2:
        return False

    # 安値が切り上がっているか
    last_two_lows = [window["Low"].iloc[i] for i in lows[-2:]]
    if last_two_lows[1] <= last_two_lows[0]:
        return False

    latest = daily.iloc[-1]
    if latest["Close"] <= latest["Open"]:
        return False

    ma60_slope = _slope(daily, "MA60")
    return ma60_slope >= -0.001  # 長期下落でなければOK


# ---------- Short conditions ----------

def check_reverse_jump_dai(daily: pd.DataFrame, weekly: pd.DataFrame) -> bool:
    """
    逆ジャンプ台: MA5 < MA20、MA5がMA20に接近してから陰線で反落。
    """
    def _check(df: pd.DataFrame) -> bool:
        if len(df) < 10:
            return False
        latest = df.iloc[-1]
        if latest["MA5"] >= latest["MA20"]:
            return False

        window = df.iloc[-6:-1]
        gaps = ((window["MA5"] - window["MA20"]) / window["MA20"]).abs()
        min_gap = gaps.min()
        if min_gap > 0.03:
            return False

        current_gap = abs(latest["MA5"] - latest["MA20"]) / latest["MA20"]
        if current_gap <= min_gap:
            return False
        if _slope(df, "MA5") >= 0:
            return False
        return latest["Close"] < latest["Open"]  # 陰線

    return _check(daily) or _check(weekly)


def check_reverse_kahanshin(daily: pd.DataFrame, weekly: pd.DataFrame) -> bool:
    """
    逆下半身: 前バーの終値がMA5以上 → 現バーの陰線でMA5を下抜け、実体の50%以上がMA5より下。
    """
    def _check(df: pd.DataFrame) -> bool:
        if len(df) < 10:
            return False
        cur = df.iloc[-1]
        prev = df.iloc[-2]
        ma5 = cur["MA5"]
        if pd.isna(ma5):
            return False
        if prev["Close"] < ma5:
            return False
        if cur["Close"] >= ma5:
            return False
        if cur["Open"] <= cur["Close"]:  # 陽線は除外
            return False
        body = cur["Open"] - cur["Close"]
        if body <= 0:
            return False
        below_ratio = (ma5 - cur["Close"]) / body
        return below_ratio >= 0.5

    return _check(daily) or _check(weekly)


def check_try_todokazu(daily: pd.DataFrame, _weekly: pd.DataFrame = None) -> bool:
    """
    トライ届かず: 直近の局所高値が前の局所高値を下回り、現在下落中。
    """
    if len(daily) < 25:
        return False

    highs = _find_local_highs(daily["High"].iloc[-61:])
    if len(highs) < 2:
        return False

    h1 = float(daily["High"].iloc[-61:].iloc[highs[-2]])
    h2 = float(daily["High"].iloc[-61:].iloc[highs[-1]])

    if h2 >= h1:
        return False

    latest = daily.iloc[-1]
    if latest["Close"] >= float(daily["High"].iloc[-61:].iloc[highs[-1]]):
        return False
    return _slope(daily, "MA5") < 0


def check_dead_cross(daily: pd.DataFrame, weekly: pd.DataFrame) -> bool:
    """
    デッドクロス or 逆PPP: MA5がMA20を下抜けた（直近3本以内）or 逆パーフェクトオーダー。
    """
    def _check(df: pd.DataFrame) -> bool:
        if len(df) < 10:
            return False
        latest = df.iloc[-1]

        # 逆PPP
        if (latest["MA60"] > latest["MA20"] > latest["MA5"] and
                _slope(df, "MA60") <= 0):
            return True

        # 直近3本でDC発生
        for offset in range(3):
            if offset + 1 >= len(df):
                break
            cur_ma5 = float(df["MA5"].iloc[-(offset + 1)])
            cur_ma20 = float(df["MA20"].iloc[-(offset + 1)])
            prev_ma5 = float(df["MA5"].iloc[-(offset + 2)])
            prev_ma20 = float(df["MA20"].iloc[-(offset + 2)])
            if prev_ma5 >= prev_ma20 and cur_ma5 < cur_ma20:
                return True
        return False

    return _check(daily) or _check(weekly)


def check_golden_cross_imminent(daily: pd.DataFrame, weekly: pd.DataFrame) -> bool:
    """
    GC直前: MA5がMA20をまさに抜こうとしている（ギャップ≤2%＋上向き）、またはGC直後。
    """
    def _check(df: pd.DataFrame) -> bool:
        if len(df) < 10:
            return False
        latest = df.iloc[-1]
        if _slope(df, "MA60") <= 0:
            return False

        ma5 = latest["MA5"]
        ma20 = latest["MA20"]
        if pd.isna(ma5) or pd.isna(ma20):
            return False

        gap_pct = (ma20 - ma5) / ma20
        if 0 < gap_pct <= 0.02 and _slope(df, "MA5") > 0:
            return True

        # 直近3本でGC
        if len(df) >= 4:
            was_below = df["MA5"].iloc[-4] < df["MA20"].iloc[-4]
            now_above = df["MA5"].iloc[-1] > df["MA20"].iloc[-1]
            if was_below and now_above:
                return True
        return False

    return _check(daily) or _check(weekly)


# ---------- Orchestrator ----------

CONDITION_FUNCS: dict[str, Callable] = {
    "jump_dai":             check_jump_dai,
    "kahanshin":            check_kahanshin,
    "ppp_pullback":         lambda d, w: check_ppp_pullback(w, d),
    "weekly_ma20_bounce":   lambda d, w: check_weekly_ma20_bounce(w, d),
    "n_shape":              check_n_shape,
    "dow_long_reversal":    check_dow_long_reversal,
    "reverse_jump_dai":     check_reverse_jump_dai,
    "reverse_kahanshin":    check_reverse_kahanshin,
    "try_todokazu":         check_try_todokazu,
    "dead_cross":           check_dead_cross,
    "golden_cross_imminent": check_golden_cross_imminent,
}

LONG_CONDITIONS: set[str] = {
    "jump_dai", "kahanshin", "ppp_pullback", "weekly_ma20_bounce",
    "n_shape", "dow_long_reversal", "golden_cross_imminent",
}
SHORT_CONDITIONS: set[str] = {
    "reverse_jump_dai", "reverse_kahanshin", "try_todokazu", "dead_cross",
}


def run_conditions(
    daily: pd.DataFrame,
    weekly: pd.DataFrame,
    requested: list[str],
) -> list[str]:
    """Return list of condition keys that match for this stock."""
    matched = []
    for key in requested:
        fn = CONDITION_FUNCS.get(key)
        if fn is None:
            continue
        try:
            if fn(daily, weekly):
                matched.append(key)
        except Exception:
            pass
    return matched


def determine_signal_type(conditions_matched: list[str]) -> str:
    has_long = any(c in LONG_CONDITIONS for c in conditions_matched)
    has_short = any(c in SHORT_CONDITIONS for c in conditions_matched)
    if has_long and has_short:
        return "mixed"
    if has_long:
        return "long"
    if has_short:
        return "short"
    return "long"
