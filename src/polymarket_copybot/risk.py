from __future__ import annotations

from dataclasses import dataclass

from .models import CopySignal


@dataclass
class RiskState:
    total_usd_exposure: float = 0.0


class RiskManager:
    def __init__(self, *, min_usd_per_trade: float, max_usd_per_trade: float, max_total_usd_exposure: float) -> None:
        self.min_usd_per_trade = float(min_usd_per_trade)
        self.max_usd_per_trade = float(max_usd_per_trade)
        self.max_total_usd_exposure = float(max_total_usd_exposure)
        self.state = RiskState()

    def validate(self, signal: CopySignal) -> tuple[bool, str]:
        if signal.usd_notional <= 0:
            return False, "usd_notional must be > 0"
        if signal.usd_notional < self.min_usd_per_trade:
            return False, f"trade size {signal.usd_notional} below MIN_USD_PER_TRADE={self.min_usd_per_trade}"
        if self.state.total_usd_exposure + signal.usd_notional > self.max_total_usd_exposure:
            return False, "total exposure limit would be exceeded"
        return True, "ok"

    def on_executed(self, signal: CopySignal) -> None:
        self.state.total_usd_exposure += signal.usd_notional

