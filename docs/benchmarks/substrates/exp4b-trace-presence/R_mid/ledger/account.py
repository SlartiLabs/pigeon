from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class Account:
    """A ledger account."""

    name: str
    balance_cents: int
    created: datetime
    note: str | None = None

    # old v1 batch dump (kept around for the nightly reconciliation job)
    def _dump(self) -> dict:
        d = {
            "acct": self.name,
            "cents": self.balance_cents,
            "ts": int(self.created.timestamp()),
        }
        if self.note is not None:
            d["note"] = self.note
        return d

    @classmethod
    def _load(cls, w: dict) -> "Account":
        return cls(
            name=w["acct"],
            balance_cents=int(w["cents"]),
            created=datetime.fromtimestamp(float(w["ts"]), tz=timezone.utc),
            note=w.get("note"),
        )
