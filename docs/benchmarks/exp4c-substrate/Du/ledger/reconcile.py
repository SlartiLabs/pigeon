from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Entry:
    """One line in a settlement batch."""

    txn_id: str
    amount_cents: int


def settle(entries: "list[Entry]") -> int:
    """Total the settled amount across a batch of entries."""
    latest: dict[str, int] = {}
    for e in entries:
        latest[e.txn_id] = e.amount_cents
    return sum(latest.values())
