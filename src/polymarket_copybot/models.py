from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Side(str, Enum):
    buy = "buy"
    sell = "sell"


@dataclass(frozen=True)
class LeaderTradeEvent:
    ts: datetime
    market_id: str
    outcome_id: str
    side: Side
    usd_notional: float
    market_slug: str | None = None
    outcome_name: str | None = None
    price: float | None = None
    leader_tx: str | None = None
    market_image_url: str | None = None


@dataclass(frozen=True)
class CopySignal:
    ts: datetime
    market_id: str
    outcome_id: str
    side: Side
    usd_notional: float
    market_slug: str | None = None
    outcome_name: str | None = None
    price: float | None = None
    source_leader_tx: str | None = None


@dataclass(frozen=True)
class ExecutionResult:
    ok: bool
    mode: str
    details: str

