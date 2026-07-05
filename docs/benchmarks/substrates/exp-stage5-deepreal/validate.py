#!/usr/bin/env python3
"""Mechanical validation of the Stage 5 deep-real substrate (no agents, no spend).

Asserts the five properties Stage 5 needs before any pilot trial is worth its
budget:

  [1] REAL     — a correct reference impl (with the external exponents) passes
                 the held-out grader.
  [2] SILENT   — the idiomatic pristine `x100` impl passes the *visible* tests
                 (so the break is invisible where the agent can see).
  [3] BREAKS   — that same idiomatic impl FAILS the grader on JPY/BHD (the
                 constraint genuinely bites).
  [4] EXTERNAL — the deciding fact (each currency's minor-unit exponent) appears
                 in NO visible file: not money.py, not TASK.md, not tests/. A
                 reader cannot lift the answer from the repo; it must come from
                 outside knowledge — which is exactly why Stage 5 adds the
                 no-code guessing baseline.
  [5] NO-TRACE — pristine money.py carries no JPY/BHD branch at all, so
                 pointers-only has no in-code residue to recover.

Run:  python3 docs/benchmarks/substrates/exp-stage5-deepreal/validate.py
"""
from __future__ import annotations

import subprocess
import sys
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent

# The external fact the substrate hides. ISO 4217 minor-unit exponents:
#   USD/EUR = 2 (hundredths), JPY = 0 (whole yen), BHD = 3 (fils).
CORRECT_EXPONENTS = {"USD": 2, "EUR": 2, "JPY": 0, "BHD": 3}

# Tokens that would betray the exponent fact if present in any visible file.
FORBIDDEN_IN_VISIBLE = [
    "fils", "yen", "iso 4217", "iso4217", "exponent", "10 **", "10**",
    "decimal place", "three decimal", "zero decimal", "no decimal",
    '"jpy": 0', '"bhd": 3', "'jpy': 0", "'bhd': 3",
]


def _run_grader(money_src: str) -> tuple[int, str]:
    """Grade a candidate money.py in an isolated temp package."""
    import tempfile
    import textwrap
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "ledger").mkdir()
        (root / "ledger" / "__init__.py").write_text("", encoding="utf-8")
        (root / "ledger" / "money.py").write_text(money_src, encoding="utf-8")
        (root / "accept.py").write_text(
            (HERE / "accept.py").read_text(encoding="utf-8"), encoding="utf-8")
        proc = subprocess.run([sys.executable, "accept.py"], cwd=root,
                              capture_output=True, text=True)
        return proc.returncode, proc.stdout + proc.stderr


def _run_visible_tests(money_src: str) -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "ledger").mkdir()
        (root / "ledger" / "__init__.py").write_text("", encoding="utf-8")
        (root / "ledger" / "money.py").write_text(money_src, encoding="utf-8")
        (root / "tests").mkdir()
        (root / "tests" / "test_money.py").write_text(
            (HERE / "tests" / "test_money.py").read_text(encoding="utf-8"), encoding="utf-8")
        proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests"],
                              cwd=root, capture_output=True, text=True)
        return proc.returncode


PRISTINE = (HERE / "ledger" / "money.py").read_text(encoding="utf-8")

REFERENCE = '''\
from __future__ import annotations
from decimal import Decimal
_EXP = {"USD": 2, "EUR": 2, "JPY": 0, "BHD": 3}
def to_minor_units(amount_major: Decimal, currency: str) -> int:
    return int(amount_major * (10 ** _EXP[currency]))
'''


def check() -> int:
    # [1] REAL
    rc, out = _run_grader(REFERENCE)
    assert rc == 0, f"reference impl should PASS grader, got:\n{out}"
    print("[1] REAL     ok — correct reference impl passes the held-out grader")

    # [2] SILENT
    assert _run_visible_tests(PRISTINE) == 0, "pristine x100 must pass visible tests"
    print("[2] SILENT   ok — idiomatic x100 passes the visible USD/EUR tests")

    # [3] BREAKS
    rc, out = _run_grader(PRISTINE)
    assert rc != 0, "pristine x100 must FAIL the grader (else constraint is vacuous)"
    assert "JPY" in out and "BHD" in out, f"grader should flag JPY/BHD, got:\n{out}"
    print("[3] BREAKS   ok — idiomatic x100 fails the grader on JPY and BHD")

    # [4] EXTERNAL
    visible = "\n".join([
        PRISTINE.lower(),
        (HERE / "TASK.md").read_text(encoding="utf-8").lower(),
        (HERE / "tests" / "test_money.py").read_text(encoding="utf-8").lower(),
    ])
    leaks = sorted({t for t in FORBIDDEN_IN_VISIBLE if t in visible})
    assert not leaks, f"exponent fact leaks into visible files: {leaks}"
    # and the correct per-currency exponents are not tabulated anywhere visible
    assert "0" not in _currency_exponent_hits(visible), "JPY exponent leaked"
    print("[4] EXTERNAL ok — the minor-unit exponents appear in no visible file")

    # [5] NO-TRACE
    assert "JPY" not in PRISTINE and "BHD" not in PRISTINE, \
        "pristine money.py must carry no JPY/BHD branch (pointers-only has no residue)"
    print("[5] NO-TRACE ok — pristine money.py has no JPY/BHD handling to recover")

    print("\nVALID: deep-real substrate is real, silent, and externally-fixed. "
          "Next: run the NO-CODE baseline to measure the guessing floor BEFORE "
          "spending confirm-tier budget (plan Stage 5, step 3).")
    return 0


def _currency_exponent_hits(text: str) -> set[str]:
    """Return exponent digits that co-occur with JPY/BHD in visible text (a
    cheap betrayal check). Empty in a well-formed substrate."""
    hits: set[str] = set()
    for cur, exp in (("jpy", "0"), ("bhd", "3")):
        i = text.find(cur)
        while i != -1:
            window = text[max(0, i - 40): i + 40]
            if exp in window and ("decimal" in window or "unit" in window or "exp" in window):
                hits.add(exp)
            i = text.find(cur, i + 1)
    return hits


if __name__ == "__main__":
    raise SystemExit(check())
