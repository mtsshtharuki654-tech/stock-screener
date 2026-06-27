import time
import jquantsapi
import pandas as pd
from datetime import datetime, timedelta, timezone
from app.config import settings

_client: jquantsapi.ClientV2 | None = None

JST = timezone(timedelta(hours=9))

# V2 subscription end date (update if plan is renewed)
SUBSCRIPTION_END = datetime(2026, 4, 5, tzinfo=JST)

# V2 column name mappings (short abbreviations)
# EQ master: MktNm=市場名(JP), MktNmEn=市場名(EN), CoName=会社名
# EQ bars daily: O/H/L/C=OHLC, Vo=Volume, AdjC=AdjClose, AdjVo=AdjVolume, AdjFactor


def get_client() -> jquantsapi.ClientV2:
    global _client
    if _client is None:
        _client = jquantsapi.ClientV2(api_key=settings.jquants_api_key)
    return _client


def _cap_end(end_dt: datetime) -> datetime:
    """Cap end date to subscription coverage."""
    return min(end_dt, SUBSCRIPTION_END)


def get_universe(segments: list[str]) -> pd.DataFrame:
    """
    Return listed stocks filtered to requested market segments.
    V2 columns: Code, CoName, CoNameEn, MktNm, MktNmEn, Mkt, ...
    """
    client = get_client()
    df = client.get_list()
    mask = df["MktNmEn"].isin(segments)
    return df[mask].copy().reset_index(drop=True)


def get_daily_ohlcv(
    start_dt: datetime,
    end_dt: datetime,
) -> pd.DataFrame:
    """
    Fetch adjusted daily OHLCV for all stocks over the date range.
    V2 columns: Code, Date, O, H, L, C, Vo, AdjFactor, AdjO, AdjH, AdjL, AdjC, AdjVo
    """
    client = get_client()
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            df = client.get_eq_bars_daily_range(start_dt=start_dt, end_dt=_cap_end(end_dt))
            df["Date"] = pd.to_datetime(df["Date"])
            return df
        except Exception as e:
            last_exc = e
            if attempt < 2:
                wait = 30 * (attempt + 1)  # 30s, 60s
                time.sleep(wait)
    raise last_exc


def get_daily_ohlcv_single(
    code: str,
    start_dt: datetime,
    end_dt: datetime,
) -> pd.DataFrame:
    """Fetch daily OHLCV for a single stock."""
    client = get_client()
    df = client.get_eq_bars_daily(
        code=code,
        from_yyyymmdd=start_dt.strftime("%Y%m%d"),
        to_yyyymmdd=_cap_end(end_dt).strftime("%Y%m%d"),
    )
    df["Date"] = pd.to_datetime(df["Date"])
    return df


def get_earnings_announcements() -> pd.DataFrame:
    """
    Return scheduled earnings announcement dates.
    V2 columns: Date, Code, CoName, FY, SectorNm, FQ, Section
    """
    client = get_client()
    try:
        df = client.get_eq_earnings_cal()
        return df
    except Exception:
        return pd.DataFrame()


def get_index_ohlcv(index_code: str, start_dt: datetime, end_dt: datetime) -> pd.DataFrame:
    """
    Fetch daily OHLCV for a market index.
    V2 columns: Date, Code, O, H, L, C
    Use index_code='topix' to get TOPIX via the dedicated endpoint.
    """
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
