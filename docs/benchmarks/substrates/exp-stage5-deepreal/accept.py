"""Held-out acceptance check for Stage 5 — deep-REAL substrate (minor units).

Agents NEVER see this file. Run against each arm's final `ledger/money.py`.

The constraint is fixed by an EXTERNAL fact — each currency's number of minor-unit
digits (ISO 4217 exponent): USD/EUR settle in hundredths (2), JPY settles in whole
yen (0), BHD settles in thousandths / fils (3). None of these exponents appears in
the visible code, comments, TASK.md, or tests (asserted by validate.py). So a
correct implementation cannot come from reading the repo alone: it must come from
external knowledge of the currencies. The idiomatic "multiply by 100" default that
the pristine code ships is correct for USD/EUR and WRONG for JPY (100x too big) and
BHD (100x too small) — and the visible tests use only USD/EUR, so the break is
silent there.

This grader is the arbiter of the black-box pass/fail. Interpret its rate against
the NO-CODE guessing baseline (`no-code-baseline.tasks.json`), never as a clean 0%
floor: a naturalistic currency rule is partly guessable from training priors, which
is exactly what the baseline arm measures.
"""
from __future__ import annotations

import sys
from decimal import Decimal

from ledger.money import to_minor_units

# (currency, major amount, expected integer minor units). USD/EUR are the live
# desks (idiomatic x100, also in the visible tests); JPY/BHD are the new desks
# whose correctness depends on the external exponent fact.
CASES = [
    ("USD", Decimal("12.34"), 1234),
    ("USD", Decimal("0.05"), 5),
    ("EUR", Decimal("5.00"), 500),
    ("JPY", Decimal("1000"), 1000),   # exponent 0 — whole yen, NOT 100000
    ("JPY", Decimal("1500"), 1500),
    ("BHD", Decimal("1.234"), 1234),  # exponent 3 — fils, NOT 123
    ("BHD", Decimal("0.500"), 500),
]


def main() -> int:
    failures: list[str] = []
    for currency, amount, want in CASES:
        try:
            got = to_minor_units(amount, currency)
        except Exception as e:  # noqa: BLE001
            failures.append(f"{currency} {amount}: raised {type(e).__name__}: {e}")
            continue
        if got != want:
            failures.append(f"{currency} {amount}: got {got}, want {want}")
    if failures:
        print("ACCEPT: FAIL")
        for x in failures:
            print("  -", x)
        return 1
    print("ACCEPT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
