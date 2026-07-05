from __future__ import annotations

from decimal import Decimal


def to_minor_units(amount_major: Decimal, currency: str) -> int:
    """Convert a major-unit amount to the integer minor unit the clearing
    partner settles in.

    The partner's ledger settles in whole minor units (no fractional minor
    unit ever crosses the wire). Amounts are held as :class:`Decimal` major
    units and converted at this export boundary.

    Only the USD and euro-zone desks are live today; both settle in hundredths.
    """
    return int(amount_major * 100)
