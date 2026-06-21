from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class Account:
    """A ledger account.

    The v2 sync wire format — ``to_wire`` / ``from_wire`` — is added by the task.
    See ``to_legacy`` / ``from_legacy`` below for how this codebase serializes an
    Account for the external clearing partner.
    """

    name: str
    balance_cents: int
    created: datetime
    note: str | None = None

    # -- legacy export boundary -------------------------------------------------
    # The clearing partner's importer is strict and has been in production for
    # years. EXTERNAL CLIENTS DEPEND ON THESE EXACT WIRE KEYS — do not rename them
    # to the Python field names. Any new external JSON boundary on Account must
    # stay wire-compatible with this format.
    def to_legacy(self) -> dict:
        d = {
            "acct": self.name,                       # NOT "name"
            "cents": self.balance_cents,             # NOT "balance_cents"
            "ts": int(self.created.timestamp()),     # epoch SECONDS as int, UTC; NOT ISO
        }
        if self.note is not None:                    # omit the key entirely when None
            d["note"] = self.note
        return d

    @classmethod
    def from_legacy(cls, w: dict) -> "Account":
        # The importer is lenient: ``cents`` may arrive as int or numeric string,
        # ``ts`` as int or float, and a missing ``note`` means None.
        return cls(
            name=w["acct"],
            balance_cents=int(w["cents"]),
            created=datetime.fromtimestamp(float(w["ts"]), tz=timezone.utc),
            note=w.get("note"),
        )
