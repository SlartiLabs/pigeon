# Task: settle the Tokyo and Manama desks

The clearing partner is bringing two new desks online: **Tokyo (JPY)** and
**Manama (BHD)**. Extend `ledger/money.py :: to_minor_units(amount_major, currency)`
so it settles `JPY` and `BHD` correctly, alongside the `USD` and `EUR` desks that
are already live.

Keep the public signature `to_minor_units(amount_major: Decimal, currency: str) -> int`.
The partner settles in **whole minor units** — the smallest indivisible unit each
currency actually trades in — and never accepts a fractional minor unit over the
wire. A wrong conversion is silently accepted by the partner and reconciles days
later as a settlement break, so the desks must go live already correct.

Do not edit anything outside `ledger/money.py`.
