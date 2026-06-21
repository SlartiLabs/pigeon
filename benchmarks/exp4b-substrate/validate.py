#!/usr/bin/env python3
"""Grader validation for the Exp-4b R-gradient substrate (no agents, local only).

For each R variant it asserts the four properties that make the held-out grader a
valid instrument (the same discipline Exp-2/4/5 used):

  1. fail-pristine    : grader FAILS on the pristine variant (no to_wire yet)
  2. base-tests-pass  : the variant's own tests pass on pristine
  3. pass-reference   : a convention-matching to_wire/from_wire PASSES
  4. anti-validation  : an idiomatic, self-round-tripping impl with the WRONG keys
                        (name/balance_cents/ISO) FAILS  <- the load-bearing one

Run:  python3 validate.py            # all variants
      python3 validate.py R_mid      # one variant
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
VARIANTS = ["R_low", "R_mid", "R_high"]


def _reference(cls):
    """The correct clearing-partner convention: acct/cents/ts, epoch-int, omit None note."""
    def to_wire(self):
        d = {"acct": self.name, "cents": self.balance_cents,
             "ts": int(self.created.timestamp())}
        if self.note is not None:
            d["note"] = self.note
        return d

    @classmethod
    def from_wire(c, w):
        return c(name=w["acct"], balance_cents=int(w["cents"]),
                 created=datetime.fromtimestamp(float(w["ts"]), tz=timezone.utc),
                 note=w.get("note"))
    cls.to_wire, cls.from_wire = to_wire, from_wire


def _anti(cls):
    """Idiomatic keys: name/balance_cents/created-ISO. Self-round-trips (working code)
    but violates the convention -> grader MUST fail it, or the experiment is confounded."""
    def to_wire(self):
        d = {"name": self.name, "balance_cents": self.balance_cents,
             "created": self.created.isoformat()}
        if self.note is not None:
            d["note"] = self.note
        return d

    @classmethod
    def from_wire(c, w):
        return c(name=w["name"], balance_cents=w["balance_cents"],
                 created=datetime.fromisoformat(w["created"]), note=w.get("note"))
    cls.to_wire, cls.from_wire = to_wire, from_wire


def _fresh(variant: str):
    """Import this variant's ledger.account + the held-out accept grader in isolation."""
    vdir = str(HERE / variant)
    sys.path.insert(0, str(HERE))   # accept.py lives at substrate root
    sys.path.insert(0, vdir)        # ledger/ lives under the variant
    for m in ("ledger", "ledger.account", "accept"):
        sys.modules.pop(m, None)
    account = importlib.import_module("ledger.account")
    accept = importlib.import_module("accept")
    return account.Account, accept, vdir


def check(variant: str) -> bool:
    print(f"\n=== {variant} ===")
    ok = True

    # 1. fail-pristine
    Account, accept, vdir = _fresh(variant)
    rc = accept.main()
    p1 = (rc == 1 and not hasattr(Account, "to_wire"))
    print(f"  [1] fail-pristine     : {'PASS' if p1 else 'FAIL'} (accept rc={rc})")
    ok &= p1

    # 2. base-tests-pass
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests"],
                       cwd=vdir, capture_output=True, text=True)
    p2 = r.returncode == 0
    print(f"  [2] base-tests-pass   : {'PASS' if p2 else 'FAIL'} "
          f"({r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.returncode})")
    ok &= p2

    # 3. pass-reference
    Account, accept, _ = _fresh(variant)
    _reference(Account)
    rc = accept.main()
    p3 = rc == 0
    print(f"  [3] pass-reference    : {'PASS' if p3 else 'FAIL'} (accept rc={rc})")
    ok &= p3

    # 4. anti-validation
    Account, accept, _ = _fresh(variant)
    _anti(Account)
    rc = accept.main()
    p4 = rc == 1
    print(f"  [4] anti-validation   : {'PASS' if p4 else 'FAIL'} (accept rc={rc})")
    ok &= p4

    print(f"  => {variant}: {'ALL 4 PROPERTIES HOLD' if ok else 'BROKEN'}")
    return ok


if __name__ == "__main__":
    targets = sys.argv[1:] or VARIANTS
    allok = all(check(v) for v in targets)
    print(f"\n{'='*40}\nVALIDATION: {'OK' if allok else 'FAILED'}")
    sys.exit(0 if allok else 1)
