from __future__ import annotations

from .models import CopySignal, LeaderTradeEvent


def leader_event_to_copy_signal(event: LeaderTradeEvent, *, copy_ratio: float) -> CopySignal:
    usd = float(event.usd_notional) * float(copy_ratio)
    return CopySignal(
        ts=event.ts,
        market_id=event.market_id,
        outcome_id=event.outcome_id,
        market_slug=event.market_slug,
        outcome_name=event.outcome_name,
        side=event.side,
        usd_notional=usd,
        price=event.price,
        source_leader_tx=event.leader_tx,
    )

