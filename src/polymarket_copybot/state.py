from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LeaderCursor:
    """
    Persisted cursor to avoid replaying history on restart.

    last_ts is a unix timestamp (seconds). last_ids tracks trade IDs observed
    at exactly last_ts so we can safely query start=last_ts (inclusive).
    """

    last_ts: int | None = None
    last_ids: set[str] | None = None


def load_leader_cursor(path: str, leader_wallet: str) -> LeaderCursor:
    p = Path(path)
    if not p.exists():
        return LeaderCursor()

    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        key = leader_wallet.lower()
        obj = raw.get("leaders", {}).get(key, {})
        last_ts = obj.get("last_ts")
        last_ids = obj.get("last_ids")
        return LeaderCursor(
            last_ts=int(last_ts) if last_ts is not None else None,
            last_ids=set(last_ids) if isinstance(last_ids, list) else None,
        )
    except Exception:
        return LeaderCursor()


def save_leader_cursor(path: str, leader_wallet: str, cursor: LeaderCursor) -> None:
    p = Path(path)
    try:
        raw: dict = {}
        if p.exists():
            raw = json.loads(p.read_text(encoding="utf-8"))
        raw.setdefault("leaders", {})

        raw["leaders"][leader_wallet.lower()] = {
            "last_ts": cursor.last_ts,
            "last_ids": sorted(list(cursor.last_ids or set())),
        }

        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(json.dumps(raw, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(p)
    except Exception:
        # State is a best-effort optimization; bot should still run without it.
        return

