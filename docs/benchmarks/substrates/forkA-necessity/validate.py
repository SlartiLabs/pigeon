#!/usr/bin/env python3
"""Mechanical validation of the Fork-A necessity substrate (no agents, no spend).

Asserts the three properties the necessity side needs:

  [1] REAL          — an implementation that follows the off-disk contract
                      (keys acct/cents/ts, lenient from_wire) passes the grader.
  [2] UNRECOVERABLE — pristine account.py carries NO wire boundary and the
                      contract keys (acct/cents/ts) appear in NO visible file
                      (account.py, tests). The contract is 0%-recoverable from
                      the code by construction — pointers-only cannot find it.
  [3] IDIOMATIC-FAILS — the idiomatic Python default (name/balance_cents/created
                      as ISO) FAILS the grader, so a pointers-only implementer
                      that guesses the default does not accidentally pass.

Run:  python3 docs/benchmarks/substrates/forkA-necessity/validate.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

CONTRACT_KEYS = ('"acct"', '"cents"', '"ts"')
WIRE_MARKERS = ("to_legacy", "from_legacy")

PRISTINE = (HERE / "ledger" / "account.py").read_text(encoding="utf-8")

# A correct implementation, per the off-disk contract.
REFERENCE = '''\
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
@dataclass
class Account:
    name: str
    balance_cents: int
    created: datetime
    note: "str | None" = None
    def to_wire(self) -> dict:
        d = {"acct": self.name, "cents": self.balance_cents,
             "ts": int(self.created.timestamp())}
        if self.note is not None:
            d["note"] = self.note
        return d
    @classmethod
    def from_wire(cls, w: dict) -> "Account":
        return cls(name=w["acct"], balance_cents=int(w["cents"]),
                   created=datetime.fromtimestamp(float(w["ts"]), tz=timezone.utc),
                   note=w.get("note"))
'''

# The idiomatic default a pointers-only implementer would reach for: Python field
# names as keys, ISO datetime. Opposite of the contract -> must FAIL the grader.
IDIOMATIC = '''\
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
@dataclass
class Account:
    name: str
    balance_cents: int
    created: datetime
    note: "str | None" = None
    def to_wire(self) -> dict:
        return {"name": self.name, "balance_cents": self.balance_cents,
                "created": self.created.isoformat(), "note": self.note}
    @classmethod
    def from_wire(cls, w: dict) -> "Account":
        return cls(name=w["name"], balance_cents=w["balance_cents"],
                   created=datetime.fromisoformat(w["created"]), note=w.get("note"))
'''


def _grade(account_src: str) -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "ledger").mkdir()
        (root / "ledger" / "__init__.py").write_text("", encoding="utf-8")
        (root / "ledger" / "account.py").write_text(account_src, encoding="utf-8")
        (root / "accept.py").write_text(
            (HERE / "accept.py").read_text(encoding="utf-8"), encoding="utf-8")
        return subprocess.run([sys.executable, "accept.py"], cwd=root,
                              capture_output=True, text=True).returncode


def check() -> int:
    # [1] REAL
    assert _grade(REFERENCE) == 0, "contract-following reference impl must PASS the grader"
    print("[1] REAL          ok — contract-following impl passes the grader")

    # [2] UNRECOVERABLE
    assert "def to_wire" not in PRISTINE and "def from_wire" not in PRISTINE, \
        "pristine account.py must ship no wire methods"
    visible = PRISTINE.lower() + "\n" + \
        (HERE / "tests" / "test_account.py").read_text(encoding="utf-8").lower()
    leaks = sorted({k for k in CONTRACT_KEYS if k in visible}) + \
        sorted({m for m in WIRE_MARKERS if m in visible})
    assert not leaks, f"contract leaks into visible files: {leaks}"
    print("[2] UNRECOVERABLE ok — no wire boundary, contract keys in no visible file")

    # [3] IDIOMATIC-FAILS
    assert _grade(IDIOMATIC) != 0, "idiomatic default must FAIL the grader (contract is non-idiomatic)"
    print("[3] IDIOMATIC-FAILS ok — idiomatic name/ISO default fails the grader")

    print("\nVALID: necessity substrate is real, 0%-recoverable, and non-idiomatic. "
          "Expected live: pointers-only ~0/8, with-derived ~8/8 (GATE A). "
          "Run with run-stage2-forkA-agy.sh (receiver=agy).")
    return 0


if __name__ == "__main__":
    raise SystemExit(check())
