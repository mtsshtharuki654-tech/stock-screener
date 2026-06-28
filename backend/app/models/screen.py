from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime


ConditionKey = Literal[
    "jump_dai", "kahanshin", "ppp_pullback", "weekly_ma20_bounce",
    "n_shape", "dow_long_reversal",
    "reverse_jump_dai", "reverse_kahanshin", "try_todokazu",
    "dead_cross", "golden_cross_imminent",
]

LONG_CONDITIONS: set[str] = {
    "jump_dai", "kahanshin", "ppp_pullback", "weekly_ma20_bounce",
    "n_shape", "dow_long_reversal", "golden_cross_imminent",
}

SHORT_CONDITIONS: set[str] = {
    "reverse_jump_dai", "reverse_kahanshin", "try_todokazu", "dead_cross",
}


class ScreenRequest(BaseModel):
    conditions: list[ConditionKey] = Field(default_factory=lambda: [
        "jump_dai", "kahanshin", "ppp_pullback", "weekly_ma20_bounce",
        "n_shape", "dow_long_reversal",
        "reverse_jump_dai", "reverse_kahanshin", "try_todokazu",
        "dead_cross", "golden_cross_imminent",
    ])
    min_volume: int = 100_000
    max_price: float = 5_000.0
    segments: list[Literal["Prime", "Growth"]] = ["Prime", "Growth"]


class MASnapshot(BaseModel):
    ma5: float
    ma20: float
    ma60: float


class CorporateEvents(BaseModel):
    earnings_near: bool = False
    earnings_days_until: Optional[int] = None
    earnings_revision_up: bool = False   # 業績上方修正
    earnings_revision_down: bool = False # 業績下方修正
    warrant: bool = False                # 新株予約権（希薄化）
    secondary_offer: bool = False        # 公募増資（希薄化）
    buyback: bool = False                # 自社株買い


class IndexCorrelation(BaseModel):
    index_name: str
    beta: float
    correlation: float
    label: Literal["指数連動型", "独自動き型", "逆相関型"]
    beta_label: Optional[str] = None


class ScreenHit(BaseModel):
    code: str
    name: str
    segment: str
    last_price: float
    last_volume: int
    avg_weekly_volume: int
    conditions_matched: list[str]
    signal_type: Literal["long", "short", "mixed"]
    weekly_ma: MASnapshot
    daily_ma: MASnapshot
    corporate_events: CorporateEvents = Field(default_factory=CorporateEvents)
    index_correlation: Optional[IndexCorrelation] = None


class ScreenResponse(BaseModel):
    screened_at: datetime
    total_universe: int
    hits: list[ScreenHit]
    duration_ms: int
