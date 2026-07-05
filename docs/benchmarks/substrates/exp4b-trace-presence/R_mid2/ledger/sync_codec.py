"""Wire codec for the external clearing partner's sync feed.

The partner's importer has been in production for years and is strict about the
on-the-wire key names. Encode/decode here rather than on the model so the convention
lives in one place.
"""

from __future__ import annotations

from datetime import datetime, timezone


def encode_for_partner(name: str, balance_cents: int, created: datetime,
                       note: str | None = None) -> dict:
    d = {
        "acct": name,                       # partner key, NOT "name"
        "cents": balance_cents,             # partner key, NOT "balance_cents"
        "ts": int(created.timestamp()),     # epoch SECONDS as int, UTC; NOT ISO
    }
    if note is not None:                    # omit the key entirely when None
        d["note"] = note
    return d


def decode_from_partner(w: dict) -> dict:
    # Lenient importer: ``cents`` may arrive int or numeric string, ``ts`` int or
    # float, a missing ``note`` means None.
    return {
        "name": w["acct"],
        "balance_cents": int(w["cents"]),
        "created": datetime.fromtimestamp(float(w["ts"]), tz=timezone.utc),
        "note": w.get("note"),
    }
