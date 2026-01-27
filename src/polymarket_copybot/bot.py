from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timezone

from .execution import Executor, LiveExecutor, PaperExecutor
from .leader import LeaderFeed
from .mapping import leader_event_to_copy_signal
from .models import CopySignal, LeaderTradeEvent
from .risk import RiskManager
from .settings import Settings

log = logging.getLogger(__name__)


def build_executor(mode: str, settings: Settings) -> Executor:
    mode = (mode or "paper").lower()
    if mode == "live":
        return LiveExecutor(settings)
    return PaperExecutor()


async def run_bot(
    settings: Settings,
    *,
    stop_event: asyncio.Event | None = None,
    on_target_activity: Callable[[LeaderTradeEvent], None] | None = None,
    on_trade: Callable[[CopySignal, float, int], None] | None = None,
    on_skip: Callable[[CopySignal, str], None] | None = None,
    on_fail: Callable[[CopySignal, str], None] | None = None,
) -> None:
    """
    Main bot loop.

    Properly cancellable: when stop_event is set the current asyncio.sleep
    inside LeaderFeed is cancelled immediately — no need to wait for the next
    poll tick.
    """
    if not settings.leader_wallet:
        raise ValueError("Leader wallet is not set. Set LEADER_WALLET in .env")

    if settings.mode == "live" and not settings.polygon_key:
        raise ValueError(
            "POLYGON_KEY is empty — live mode requires your wallet private key in .env"
        )

    leader = LeaderFeed(
        leader_wallet=settings.leader_wallet,
        poll_interval_seconds=settings.poll_interval_seconds,
        data_api_base=settings.data_api_base,
        state_path=settings.leader_state_path,
        start_from_now=settings.leader_start_from_now,
    )
    risk = RiskManager(
        min_usd_per_trade=settings.min_usd_per_trade,
        max_usd_per_trade=settings.max_usd_per_trade,
        max_total_usd_exposure=settings.max_total_usd_exposure,
    )
    executor = build_executor(settings.mode, settings)
    stop_event = stop_event or asyncio.Event()

    log.info(
        "Starting copybot  mode=%s  leader=%s  poll=%ss",
        settings.mode,
        settings.leader_wallet,
        settings.poll_interval_seconds,
    )

    trade_count = 0
    gen = leader.events()

    while not stop_event.is_set():
        # Race: get the next leader event OR a stop signal — whichever fires first.
        # This ensures Stop is instant even while the leader feed is sleeping.
        next_task = asyncio.ensure_future(gen.__anext__())
        stop_task = asyncio.ensure_future(stop_event.wait())

        done, pending = await asyncio.wait(
            [next_task, stop_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Cancel whichever branch didn't win
        for p in pending:
            p.cancel()
            try:
                await p
            except (asyncio.CancelledError, StopAsyncIteration):
                pass

        # Stop requested
        if stop_task in done:
            next_task.cancel()
            break

        # Generator exhausted
        try:
            event = next_task.result()
        except StopAsyncIteration:
            log.info("Leader feed exhausted.")
            break

        if on_target_activity is not None:
            try:
                on_target_activity(event)
            except Exception:
                pass

        signal = leader_event_to_copy_signal(event, copy_ratio=settings.copy_ratio)

        # If the leader's (scaled) trade size is bigger than our allowed max,
        # cap it to max and still execute.
        if signal.usd_notional > settings.max_usd_per_trade:
            original = signal.usd_notional
            signal = replace(signal, usd_notional=float(settings.max_usd_per_trade))
            log.info("Capped trade size from %.4f -> %.4f (MAX_USD_PER_TRADE)", original, signal.usd_notional)

        ok, reason = risk.validate(signal)
        if not ok:
            log.warning("Risk rejected signal: %s", reason)
            if on_skip is not None:
                try:
                    on_skip(signal, reason)
                except Exception:
                    pass
            continue

        res = await executor.execute(signal)
        if res.ok:
            risk.on_executed(signal)
            trade_count += 1
            if on_trade is not None:
                try:
                    on_trade(signal, risk.state.total_usd_exposure, trade_count)
                except Exception:
                    pass
        else:
            log.error("Execution failed: %s", res.details)
            if on_fail is not None:
                try:
                    on_fail(signal, res.details)
                except Exception:
                    pass

    log.info("Copybot stopped.")
