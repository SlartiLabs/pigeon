from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Account:
    """A ledger account."""

    name: str
    balance_cents: int
    created: datetime
    note: str | None = None
