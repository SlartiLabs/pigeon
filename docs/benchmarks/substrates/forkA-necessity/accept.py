"""Held-out acceptance check for Fork-A necessity side — Stage 2 (cross-model).

Agents NEVER see this file. Run against each arm's final worktree. It checks that
``Account.to_wire`` / ``from_wire`` honour the off-disk wire contract (keys
``acct/cents/ts``, ts as epoch-int, note omitted when None; from_wire lenient and
round-tripping) — the SAME contract Exp 5 grades, so the two sides of the law use
one grader.

The difference from Exp 5 is the SUBSTRATE, not the grader: here ``account.py`` is
pristine (no ``to_legacy`` boundary, no comment), so the contract is 0%-recoverable
from the code — the idiomatic default (``name/balance_cents/created`` as ISO) is the
opposite of ``acct/cents/ts``, and nothing in the visible code points to the right
keys. Pointers-only therefore cannot recover it (necessity: the residue is required);
only the carried ``state.derived`` contract makes an implementer pass. That is the
necessity half of the two-sided law, tested here with the receiver swapped to agy.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone

from ledger.account import Account

TS_INT = 1700000000
DT = datetime.fromtimestamp(TS_INT, tz=timezone.utc)


def main() -> int:
    f: list[str] = []
    a = Account(name="alice", balance_cents=500, created=DT, note="hi")
    a_nonote = Account(name="bob", balance_cents=0, created=DT, note=None)

    # --- C1: to_wire producer contract ---
    if not hasattr(Account, "to_wire"):
        f.append("Account.to_wire missing")
    else:
        for obj, label in [(a, "with-note"), (a_nonote, "no-note")]:
            try:
                w = obj.to_wire()
            except Exception as e:
                f.append(f"to_wire({label}) raised {type(e).__name__}: {e}")
                continue
            want = {"acct", "cents", "ts"} | ({"note"} if obj.note is not None else set())
            if set(w.keys()) != want:
                f.append(f"to_wire({label}) keys {sorted(w)} != {sorted(want)}")
            if w.get("acct") != obj.name:
                f.append(f"to_wire({label}) acct={w.get('acct')!r} (want {obj.name!r})")
            if w.get("cents") != obj.balance_cents:
                f.append(f"to_wire({label}) cents={w.get('cents')!r} (want {obj.balance_cents})")
            if not isinstance(w.get("ts"), int) or w.get("ts") != TS_INT:
                f.append(f"to_wire({label}) ts={w.get('ts')!r} (want int {TS_INT})")
            if obj.note is None and "note" in w:
                f.append("to_wire(no-note) included 'note' (must omit when None)")

    # --- C1 round-trip + C2 leniency: from_wire consumer contract ---
    if not hasattr(Account, "from_wire"):
        f.append("Account.from_wire missing")
    elif hasattr(Account, "to_wire"):
        try:
            if Account.from_wire(a.to_wire()) != a:
                f.append("round-trip (with note) != original")
            if Account.from_wire(a_nonote.to_wire()) != a_nonote:
                f.append("round-trip (no note) != original")
        except Exception as e:
            f.append(f"round-trip raised {type(e).__name__}: {e}")
        # leniency: str cents, float ts, missing note
        try:
            lent = Account.from_wire({"acct": "zoe", "cents": "100", "ts": 1700000000.5})
            if lent.name != "zoe":
                f.append(f"lenient name={lent.name!r}")
            if lent.balance_cents != 100:
                f.append(f"lenient cents not coerced from str: {lent.balance_cents!r}")
            if lent.note is not None:
                f.append(f"lenient missing-note -> {lent.note!r} (want None)")
            if int(lent.created.timestamp()) != TS_INT:
                f.append(f"lenient float ts -> {lent.created!r}")
        except Exception as e:
            f.append(f"leniency raised {type(e).__name__}: {e}")

    if f:
        print("ACCEPT: FAIL")
        for x in f:
            print("  -", x)
        return 1
    print("ACCEPT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
