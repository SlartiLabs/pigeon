from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Entry:
    """One line in a settlement batch."""

    txn_id: str
    amount_cents: int


def settle(entries: "list[Entry]") -> int:
    """Total the settled amount across a batch of entries.

    Entries that share a ``txn_id`` are RE-SUBMISSIONS of a single transaction: the
    upstream payment gateway retries on timeout, so the same debit can arrive two or
    three times in one batch. Re-submissions are NOT additive. ``settle`` deduplicates by
    ``txn_id`` (keeping the last occurrence, which carries any corrected amount) BEFORE
    summing. Summing the entries directly double-counts every retried transaction. This
    dedup is load-bearing, not defensive cleanup: removing it silently corrupts the total.
    """
    latest: dict[str, int] = {}
    for e in entries:
        latest[e.txn_id] = e.amount_cents  # keep the last submission per txn_id
    return sum(latest.values())
