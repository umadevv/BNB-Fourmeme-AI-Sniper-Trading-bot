from __future__ import annotations

import asyncio
import logging
from functools import partial
from typing import TYPE_CHECKING

from .models import CopySignal, ExecutionResult

if TYPE_CHECKING:
    from .settings import Settings

log = logging.getLogger(__name__)


class Executor:
    async def execute(self, signal: CopySignal) -> ExecutionResult:  # pragma: no cover
        raise NotImplementedError


# ── Paper ─────────────────────────────────────────────────────────────────────

class PaperExecutor(Executor):
    async def execute(self, signal: CopySignal) -> ExecutionResult:
        log.info(
            "PAPER FOK: %s %s/%s  usd=%.2f  price=%s",
            signal.side.value.upper(),
            signal.market_slug or signal.market_id,
            signal.outcome_name or signal.outcome_id,
            signal.usd_notional,
            signal.price,
        )
        return ExecutionResult(ok=True, mode="paper", details="paper FOK executed")


# ── Live (FOK with retry) ─────────────────────────────────────────────────────

class LiveExecutor(Executor):
    """
    Places a Fill-Or-Kill market order via the Polymarket CLOB.

    FOK semantics: the order must fill *completely and immediately* or it is
    rejected by the exchange.  When rejected we wait an exponentially growing
    delay and retry up to `fok_max_retries` times before giving up.

    Retry schedule (default): 0.5 s → 1 s → 2 s → 4 s → 8 s  (5 attempts)
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = None   # lazy-initialised; shared across orders

    # ── CLOB client ───────────────────────────────────────────────────────────

    def _get_client(self):
        if self._client is not None:
            return self._client

        try:
            from py_clob_client_v2.client import ClobClient
        except ImportError as exc:
            raise RuntimeError(
                "py-clob-client-v2 is not installed. Run: pip install py-clob-client-v2"
            ) from exc

        s = self._settings
        if not s.polygon_key:
            raise ValueError("POLYGON_KEY is not set in .env — required for live trading.")

        # funder is only needed for SIG_TYPE 1 (proxy) or 2 (Gnosis Safe)
        funder = s.proxy_address if s.sig_type in (1, 2) else None

        kwargs: dict = dict(
            key=s.polygon_key,
            chain_id=137,
            signature_type=s.sig_type,
        )
        if funder:
            kwargs["funder"] = funder

        client = ClobClient("https://clob.polymarket.com", **kwargs)
        client.set_api_creds(client.create_or_derive_api_key())
        self._client = client
        log.info("ClobClient V2 initialised (sig_type=%d, funder=%s)", s.sig_type, funder or "n/a")
        return self._client

    # ── Single FOK attempt ────────────────────────────────────────────────────

    def _place_fok_sync(self, signal: CopySignal) -> ExecutionResult:
        """
        Blocking call — run inside a thread executor.

        BUY  → amount = pUSD to spend           (usd_notional)
        SELL → amount = number of shares         (usd_notional / price)
        """
        from py_clob_client_v2.clob_types import MarketOrderArgs, OrderType

        client = self._get_client()
        side = "BUY" if signal.side.value.lower() == "buy" else "SELL"

        if side == "SELL":
            if signal.price and signal.price > 0:
                amount = signal.usd_notional / signal.price
            else:
                return ExecutionResult(
                    ok=False,
                    mode="live",
                    details="SELL order skipped: price is 0 or missing — cannot compute share amount",
                )
        else:
            amount = signal.usd_notional

        mo = MarketOrderArgs(
            token_id=signal.outcome_id,
            amount=amount,
            side=side,
            order_type=OrderType.FOK,
        )
        resp = client.create_and_post_market_order(mo, order_type=OrderType.FOK)

        # py-clob-client-v2 returns a dict; detect FOK rejection / API error
        if isinstance(resp, dict):
            error_msg = resp.get("errorMsg") or resp.get("error") or ""
            status    = str(resp.get("status", "")).lower()
            order_id  = resp.get("orderID") or resp.get("id") or ""

            if error_msg or status in ("failed", "rejected", "cancelled"):
                return ExecutionResult(
                    ok=False,
                    mode="live",
                    details=f"FOK rejected: {error_msg or status}",
                )
            if order_id:
                log.info(
                    "FOK order placed  orderID=%s  side=%s  pusd=%.4f  shares=%.4f",
                    order_id, side, signal.usd_notional, amount,
                )
                return ExecutionResult(ok=True, mode="live", details=f"orderID={order_id}")

        # Unexpected response shape — treat as success if no error key present
        log.info("FOK placed (unrecognised response shape): %s", resp)
        return ExecutionResult(ok=True, mode="live", details=str(resp))

    # ── Async entry point with retry ──────────────────────────────────────────

    async def execute(self, signal: CopySignal) -> ExecutionResult:
        s = self._settings
        max_retries = max(1, int(s.fok_max_retries))
        base_delay  = float(s.fok_retry_delay_s)
        # FIX: use get_running_loop() — get_event_loop() is deprecated in Python 3.10+
        loop = asyncio.get_running_loop()

        last_result = ExecutionResult(ok=False, mode="live", details="not attempted")

        for attempt in range(1, max_retries + 1):
            try:
                result = await loop.run_in_executor(
                    None, partial(self._place_fok_sync, signal)
                )
            except Exception as exc:
                result = ExecutionResult(ok=False, mode="live", details=repr(exc))

            if result.ok:
                return result

            last_result = result
            if attempt < max_retries:
                delay = base_delay * (2 ** (attempt - 1))   # 0.5 → 1 → 2 → 4 → 8
                log.warning(
                    "FOK attempt %d/%d failed (%s) — retrying in %.1fs",
                    attempt, max_retries, result.details, delay,
                )
                await asyncio.sleep(delay)

        log.error(
            "FOK order gave up after %d attempt(s): %s",
            max_retries, last_result.details,
        )
        return ExecutionResult(
            ok=False,
            mode="live",
            details=f"gave up after {max_retries} FOK attempt(s): {last_result.details}",
        )
