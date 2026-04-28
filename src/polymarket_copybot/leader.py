from __future__ import annotations

import asyncio
import logging
import json
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

import httpx

from .models import LeaderTradeEvent, Side
from .state import LeaderCursor, load_leader_cursor, save_leader_cursor

log = logging.getLogger(__name__)


class LeaderFeed:
    """
    Replace this with a real leader wallet watcher.

    Options you can implement here:
    - indexer API (recommended)
    - onchain logs + decoding
    - Polymarket-provided endpoints (if available to you)
    """

    def __init__(
        self,
        *,
        leader_wallet: str,
        poll_interval_seconds: int = 5,
        data_api_base: str = "https://data-api.polymarket.com",
        state_path: str | None = None,
        start_from_now: bool = True,
    ) -> None:
        self.leader_wallet = leader_wallet
        self.poll_interval_seconds = poll_interval_seconds
        self.data_api_base = data_api_base
        self.state_path = state_path
        self.start_from_now = start_from_now
        self._market_cache: dict[str, tuple[str | None, dict[str, str], str | None]] = {}

    async def events(self) -> AsyncIterator[LeaderTradeEvent]:
        """
        Poll Polymarket Data API activity endpoint and yield new TRADE events.

        Docs: GET https://data-api.polymarket.com/activity?user={address}
        """
        user = self.leader_wallet.strip()
        if not user:
            raise ValueError("leader_wallet is empty")

        base = self.data_api_base
        seen: set[str] = set()

        cursor = LeaderCursor()
        if self.state_path:
            cursor = load_leader_cursor(self.state_path, user)

        # We keep a moving window by timestamp; Data API supports start/end.
        start_ts: int | None = cursor.last_ts
        last_ids_at_ts: set[str] = set(cursor.last_ids or set())

        # User expectation for copy-trading: when the bot starts, do NOT replay
        # history. If start_from_now=True, always reset cursor to "now",
        # regardless of any previously saved state.
        if self.start_from_now:
            start_ts = int(datetime.now(tz=timezone.utc).timestamp())
            last_ids_at_ts.clear()
            if self.state_path:
                save_leader_cursor(self.state_path, user, LeaderCursor(last_ts=start_ts, last_ids=set()))

        timeout = httpx.Timeout(connect=10.0, read=20.0, write=10.0, pool=10.0)
        async with httpx.AsyncClient(base_url=base, timeout=timeout) as client, httpx.AsyncClient(
            base_url="https://gamma-api.polymarket.com", timeout=timeout
        ) as gamma:
            while True:
                try:
                    params: dict[str, Any] = {
                        "user": user,
                        "type": "TRADE",
                        "limit": 100,
                        "offset": 0,
                        "sortBy": "TIMESTAMP",
                        "sortDirection": "ASC",
                    }
                    if start_ts is not None:
                        params["start"] = start_ts

                    data = await self._get_activity_page(client, params)
                    emitted = 0

                    for item in data:
                        # Prefer a stable ID if present, else derive one.
                        uid = str(item.get("id") or item.get("txHash") or "")
                        if not uid:
                            uid = "|".join(
                                str(item.get(k, "")) for k in ("timestamp", "conditionId", "asset", "side", "size", "price", "usdcSize")
                            )
                        ts_int = int(item.get("timestamp") or 0)

                        # Prevent duplicates when querying start=start_ts (inclusive)
                        if start_ts is not None and ts_int == start_ts and uid in last_ids_at_ts:
                            continue
                        if uid in seen:
                            continue
                        seen.add(uid)

                        ev = await self._parse_trade(item, gamma)
                        if ev is None:
                            continue

                        emitted += 1
                        # Move start_ts forward (inclusive) to keep a small replay window.
                        if ts_int > 0:
                            if start_ts != ts_int:
                                start_ts = ts_int
                                last_ids_at_ts.clear()
                            last_ids_at_ts.add(uid)

                            if self.state_path:
                                save_leader_cursor(
                                    self.state_path,
                                    user,
                                    LeaderCursor(last_ts=start_ts, last_ids=set(last_ids_at_ts)),
                                )
                        yield ev

                    # Keep seen bounded (avoid unbounded memory growth)
                    if len(seen) > 5000:
                        seen = set(list(seen)[-2500:])

                    # If nothing new, sleep. If we emitted a bunch, immediately loop again
                    # to catch up via paging (basic catch-up behaviour).
                    if emitted == 0:
                        await asyncio.sleep(self.poll_interval_seconds)
                    else:
                        await asyncio.sleep(0)
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    log.warning("LeaderFeed poll failed: %r", e)
                    await asyncio.sleep(max(1, self.poll_interval_seconds))

    async def _get_activity_page(self, client: httpx.AsyncClient, params: dict[str, Any]) -> list[dict[str, Any]]:
        r = await client.get("/activity", params=params)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        return []

    async def _parse_trade(self, item: dict[str, Any], gamma: httpx.AsyncClient) -> LeaderTradeEvent | None:
        """
        Data API Activity item fields vary. We defensively extract:
        - timestamp (unix seconds)
        - conditionId (market id)
        - asset (token id)
        - side (BUY/SELL)
        - usdcSize (notional in pUSD — 1:1 with USDC since the Apr-2026 migration)
        - price
        """
        try:
            ts_int = int(item.get("timestamp") or 0)
            if ts_int <= 0:
                return None
            ts = datetime.fromtimestamp(ts_int, tz=timezone.utc)

            market_id = str(item.get("conditionId") or item.get("market") or "")
            token_id = str(item.get("asset") or item.get("asset_id") or item.get("token_id") or "")
            if not market_id or not token_id:
                return None

            side_raw = str(item.get("side") or "").lower()
            side = Side.buy if side_raw == "buy" else Side.sell

            # Prefer explicit usdcSize (pUSD, 1:1 USDC since Apr-2026), else fall back to size*price
            usd = item.get("usdcSize")
            price = item.get("price")
            if usd is None:
                size = item.get("size")
                if size is not None and price is not None:
                    usd = float(size) * float(price)
            usd_notional = float(usd) if usd is not None else 0.0
            px = float(price) if price is not None else None

            leader_tx = str(item.get("txHash") or item.get("id") or "")

            market_slug, outcome_name, market_image_url = await self._resolve_market_meta(gamma, market_id, token_id)

            return LeaderTradeEvent(
                ts=ts,
                market_id=market_id,
                outcome_id=token_id,   # token id (YES/NO asset) used for execution
                market_slug=market_slug,
                outcome_name=outcome_name,
                side=side,
                usd_notional=usd_notional,
                price=px,
                leader_tx=leader_tx or None,
                market_image_url=market_image_url or None,
            )
        except Exception:
            return None

    async def _resolve_market_meta(
        self, gamma: httpx.AsyncClient, condition_id: str, token_id: str
    ) -> tuple[str | None, str | None, str | None]:
        """
        Resolve a conditionId + clob token_id into (market_slug, outcome_name, image_url).
        Uses Gamma API and caches per conditionId.
        """
        if condition_id in self._market_cache:
            slug, token_map, image_url = self._market_cache[condition_id]
            return slug, token_map.get(token_id), image_url

        try:
            r = await gamma.get("/markets", params={"condition_ids": condition_id, "limit": 1})
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, list) or not data:
                self._market_cache[condition_id] = (None, {}, None)
                return None, None, None

            m = data[0] if isinstance(data[0], dict) else {}
            slug = m.get("slug")
            # Polymarket stores the market icon in the "image" field as a direct S3 URL
            image_url: str | None = m.get("image") or m.get("icon") or None
            if image_url:
                image_url = str(image_url).strip()
            outcomes_raw = m.get("outcomes")
            tokens_raw = m.get("clobTokenIds") or m.get("clob_token_ids")

            outcomes = []
            tokens = []
            if isinstance(outcomes_raw, str):
                try:
                    outcomes = json.loads(outcomes_raw)
                except Exception:
                    outcomes = []
            if isinstance(tokens_raw, str):
                try:
                    tokens = json.loads(tokens_raw)
                except Exception:
                    tokens = []

            token_map: dict[str, str] = {}
            if isinstance(outcomes, list) and isinstance(tokens, list) and len(outcomes) == len(tokens):
                for o, t in zip(outcomes, tokens):
                    if o is None or t is None:
                        continue
                    token_map[str(t)] = str(o)

            self._market_cache[condition_id] = (str(slug) if slug else None, token_map, image_url)
            return self._market_cache[condition_id][0], token_map.get(token_id), image_url
        except Exception:
            self._market_cache[condition_id] = (None, {}, None)
            return None, None, None

