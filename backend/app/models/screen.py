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


class EarningsEvent(BaseModel):
    next_date: Optional[str] = None
    days_until: Optional[int] = None
    is_near: bool = False


class SplitEvent(BaseModel):
    recent: bool = False
    date: Optional[str] = None
    ratio: Optional[str] = None


class TdnetEvent(BaseModel):
    detected: bool = False
    date: Optional[str] = None
    tdnet_url: Optional[str] = None
    title: Optional[str] = None


class CorporateEvents(BaseModel):
    earnings: EarningsEvent = Field(default_factory=EarningsEvent)
    split: SplitEvent = Field(default_factory=SplitEvent)
    warrant: TdnetEvent = Field(default_factory=TdnetEvent)
    secondary_offer: TdnetEvent = Field(default_factory=TdnetEvent)
    earnings_revision_up: TdnetEvent = Field(default_factory=TdnetEvent)
    earnings_revision_down: TdnetEvent = Field(default_factory=TdnetEvent)
    margin_restriction: bool = False
    under_supervision: bool = False
    buyback: TdnetEvent = Field(default_factory=TdnetEvent)
    tob: TdnetEvent = Field(default_factory=TdnetEvent)
    large_holder: TdnetEvent = Field(default_factory=TdnetEvent)


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
