from pydantic import BaseModel
from typing import Literal


class OHLCV(BaseModel):
    time: int
    open: float
    high: float
    low: float
    close: float
    volume: int


class MAPoint(BaseModel):
    time: int
    value: float


class MASet(BaseModel):
    ma5: list[MAPoint]
    ma20: list[MAPoint]
    ma60: list[MAPoint]


class ChartData(BaseModel):
    code: str
    name: str
    timeframe: Literal["weekly", "daily"]
    candles: list[OHLCV]
    ma: MASet
