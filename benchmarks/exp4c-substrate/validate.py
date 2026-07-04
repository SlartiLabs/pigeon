#!/usr/bin/env python3
"""Grader validation for the Exp-4c deep-constraint substrate (no agents, local only).

Asserts the properties that make the held-out grader a valid instrument for BOTH deep
cells (Dr = deep-recoverable, Du = deep-unrecoverable):

  1. pass-pristine      : grader PASSES on the pristine (correct, deduping) settle
  2. base-tests-pass    : the visible tests pass on pristine
  3. break-fails-grader : the idiomatic single-pass sum (no dedup) FAILS the grader
                          <- the load-bearing property; the constraint is real
  4. break-is-silent    : that same broken impl still satisfies the visible-test inputs
                          <- why pointers-only can miss it; the break is invisible to the
                             tests the agent sees
  5. diff-clean         : Dr and Du reconcile.py are identical modulo docstrings/comments
                          <- difficulty is held constant BY CONSTRUCTION; only the
                             recoverable RATIONALE differs (the whole design)

Run:  python3 validate.py            # both cells + diff-clean
      python3 validate.py Dr         # one cell
"""

from __future__ import annotations

import ast
import importlib
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CELLS = ["Dr", "Du"]

# the idiomatic "streamline it" refactor: one pass, no intermediate dict -> drops dedup
_BROKEN = "def settle(entries):\n    return sum(e.amount_cents for e in entries)\n"

# visible-test inputs (mirror tests/test_reconcile.py; NO duplicate txn_ids by design)
_VISIBLE = [
    ([("a", 100), ("b", 50), ("c", 25)], 175),
    ([], 0),
    ([("solo", 42)], 42),
]


def _fresh(cell: str, broken: bool = False):
    vdir = str(HERE / cell)
    sys.path.insert(0, str(HERE))  # accept.py at substrate root
    sys.path.insert(0, vdir)       # ledger/ under the cell
    for m in ("ledger", "ledger.reconcile", "accept"):
        sys.modules.pop(m, None)
    reconcile = importlib.import_module("ledger.reconcile")
    if broken:
        ns: dict = {}
        exec(_BROKEN, ns)
        reconcile.settle = ns["settle"]  # patch on the module -> accept.main reads it live
    accept = importlib.import_module("accept")
    return reconcile, accept, vdir


def check(cell: str) -> bool:
    print(f"\n=== {cell} ===")
    ok = True

    # 1. pass-pristine
    reconcile, accept, vdir = _fresh(cell)
    rc = accept.main()
    p1 = rc == 0
    print(f"  [1] pass-pristine      : {'PASS' if p1 else 'FAIL'} (accept rc={rc})")
    ok &= p1

    # 2. base-tests-pass
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests"],
                       cwd=vdir, capture_output=True, text=True)
    p2 = r.returncode == 0
    last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.returncode
    print(f"  [2] base-tests-pass    : {'PASS' if p2 else 'FAIL'} ({last})")
    ok &= p2

    # 3. break-fails-grader
    reconcile, accept, _ = _fresh(cell, broken=True)
    rc = accept.main()
    p3 = rc == 1
    print(f"  [3] break-fails-grader : {'PASS' if p3 else 'FAIL'} (accept rc={rc})")
    ok &= p3

    # 4. break-is-silent (broken impl still satisfies the visible-test inputs)
    reconcile, _, _ = _fresh(cell, broken=True)
    Entry = reconcile.Entry
    p4 = all(reconcile.settle([Entry(t, a) for t, a in ins]) == want
             for ins, want in _VISIBLE)
    print(f"  [4] break-is-silent    : {'PASS' if p4 else 'FAIL'}")
    ok &= p4

    print(f"  => {cell}: {'ALL 4 PROPERTIES HOLD' if ok else 'BROKEN'}")
    return ok


def _skeleton(path: Path) -> str:
    """Source with every docstring and comment removed (comments dropped by unparse)."""
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if (isinstance(body, list) and body and isinstance(body[0], ast.Expr)
                and isinstance(getattr(body[0], "value", None), ast.Constant)
                and isinstance(body[0].value.value, str)):
            node.body = body[1:]
    return ast.unparse(tree)


def diff_clean() -> bool:
    a = _skeleton(HERE / "Dr" / "ledger" / "reconcile.py")
    b = _skeleton(HERE / "Du" / "ledger" / "reconcile.py")
    ok = a == b
    print("\n=== diff-clean (Dr vs Du) ===")
    print(f"  [5] identical modulo docstrings/comments : {'PASS' if ok else 'FAIL'}")
    if not ok:
        print("  Dr and Du differ in CODE, not just rationale — difficulty NOT held constant.")
    return ok


if __name__ == "__main__":
    targets = [c for c in sys.argv[1:] if c in CELLS] or CELLS
    allok = all(check(c) for c in targets)
    if set(targets) >= set(CELLS):
        allok &= diff_clean()
    print(f"\n{'=' * 44}\nVALIDATION: {'OK' if allok else 'FAILED'}")
    sys.exit(0 if allok else 1)
