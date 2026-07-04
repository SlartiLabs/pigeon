"""Held-out acceptance check for Experiment 4c — deep constraint (dedup-before-aggregate).

Agents NEVER see this file. It is the FIXED instrument, identical across the Dr
(deep-recoverable) and Du (deep-unrecoverable) cells, so reasoning-recoverability is the
single manipulated variable and the grader can never be the thing that differs.

Constraint: entries sharing a ``txn_id`` are RE-SUBMISSIONS of one transaction (gateway
retries), not distinct debits. ``settle`` must dedup by txn_id (keep last) before summing;
a direct sum double-counts every retried transaction. On pristine the code already dedups
— the deep question is whether a carrier who REFACTORS settle preserves the dedup, which
is load-bearing, not defensive. The idiomatic single-pass ``sum(e.amount_cents for e in
entries)`` drops it, passes the visible tests (no duplicate txn_ids), and fails here.
"""

from __future__ import annotations

import sys

from ledger import reconcile


def main() -> int:
    settle, Entry = reconcile.settle, reconcile.Entry
    f: list[str] = []

    # C1: plain batch, no re-submissions — correct and broken both pass (sanity floor).
    if settle([Entry("a", 100), Entry("b", 50), Entry("c", 25)]) != 175:
        f.append("plain batch total wrong (base arithmetic broken)")

    # C2: a re-submitted txn (one gateway retry) must not be double-counted.
    got = settle([Entry("t1", 100), Entry("t2", 50), Entry("t1", 100)])
    if got != 150:
        f.append(f"re-submission double-counted: settle={got} (want 150; dedup by txn_id)")

    # C3: keep-last — a corrected re-submission overrides the earlier amount.
    got = settle([Entry("t1", 100), Entry("t1", 120)])
    if got != 120:
        f.append(f"keep-last violated: settle={got} (want 120; last submission wins)")

    # C4: several retries of one txn collapse to a single debit.
    got = settle([Entry("x", 10), Entry("x", 10), Entry("x", 10), Entry("y", 5)])
    if got != 15:
        f.append(f"multi-retry not collapsed: settle={got} (want 15)")

    if f:
        print("ACCEPT: FAIL")
        for x in f:
            print("  -", x)
        return 1
    print("ACCEPT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
