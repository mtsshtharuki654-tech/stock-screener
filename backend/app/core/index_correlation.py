import pandas as pd
import numpy as np
from app.models.screen import IndexCorrelation
from app.core import jquants_client as jq
from app.core.data_pipeline import load_index_ohlcv

INDEX_CODES = {
    "Prime": ("topix", "TOPIX"),
    "Growth": ("0049", "グロース250"),
}
LOOKBACK = 60  # 営業日


def calc_index_correlation(
    stock_daily: pd.DataFrame,
    index_code: str,
    index_name: str,
) -> IndexCorrelation | None:
    """
    Compute beta and correlation for a stock vs an index over the last 60 trading days.
    """
    try:
        index_df = load_index_ohlcv(index_code)
        if index_df.empty:
            return None

        # V2 index column is "C" (Close); TOPIX endpoint has no "Code" column
        close_col = "C" if "C" in index_df.columns else "Close"
        index_df = index_df[["Date", close_col]].rename(columns={close_col: "IndexClose"})
        index_df["Date"] = pd.to_datetime(index_df["Date"])

        # V2 equity bars use "AdjC" for adjusted close
        adj_col = "AdjC" if "AdjC" in stock_daily.columns else "AdjClose"
        stock = stock_daily[["Date", adj_col]].copy().rename(columns={adj_col: "AdjClose"})
        stock["Date"] = pd.to_datetime(stock["Date"])

        merged = pd.merge(stock, index_df, on="Date", how="inner").sort_values("Date")
        if len(merged) < LOOKBACK // 2:
            return None

        merged = merged.tail(LOOKBACK)

        s_ret = np.log(merged["AdjClose"] / merged["AdjClose"].shift(1)).dropna()
        m_ret = np.log(merged["IndexClose"] / merged["IndexClose"].shift(1)).dropna()

        common_idx = s_ret.index.intersection(m_ret.index)
        if len(common_idx) < 20:
            return None

        s = s_ret.loc[common_idx].values
        m = m_ret.loc[common_idx].values

        corr = float(np.corrcoef(s, m)[0, 1])
        cov_mat = np.cov(s, m)
        beta = float(cov_mat[0, 1] / cov_mat[1, 1]) if cov_mat[1, 1] != 0 else 0.0

        if corr >= 0.6:
            label = "指数連動型"
        elif corr <= -0.3:
            label = "逆相関型"
        else:
            label = "独自動き型"

        beta_label = None
        if beta > 1.5:
            beta_label = f"高ベータ（指数の{beta:.1f}倍動く）"
        elif beta < 0.5:
            beta_label = "低ベータ（指数の動きに鈍感）"

        return IndexCorrelation(
            index_name=index_name,
            beta=round(beta, 2),
            correlation=round(corr, 2),
            label=label,
            beta_label=beta_label,
        )

    except Exception:
        return None


def get_correlation_for_stock(
    stock_daily: pd.DataFrame,
    segment: str,
) -> IndexCorrelation | None:
    code_info = INDEX_CODES.get(segment)
    if not code_info:
        return None
    index_code, index_name = code_info
    return calc_index_correlation(stock_daily, index_code, index_name)
