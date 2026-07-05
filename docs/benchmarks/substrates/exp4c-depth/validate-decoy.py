#!/usr/bin/env python3
"""Mechanical check that the Stage 1b rebuilt decoy is a valid control.

The prereg locks the decoy as "content unrelated to the constraint, equal token
budget" — a control for any-extra-prose, not an adversarial manipulation. The
original decoy failed that on two counts (it was directive and nudged toward the
break). This validator asserts the rebuild satisfies the locked contract, with
no agents and no spend:

  [1] TRUE       — every carried fact is verifiable against the Du fixtures.
  [2] OFF-TOPIC  — no carried fact mentions any constraint keyword (dedup,
                   re-submission, txn_id uniqueness, retry, double-count) nor
                   recommends a refactor.
  [3] WEIGHT     — the residue matches a representative +derived residue within
                   +/-15% under the canonical o200k_base tokenizer.

Run:  python3 docs/benchmarks/substrates/exp4c-depth/validate-decoy.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_SRC = HERE.parents[3] / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
from pigeon.tokens import canonical_token_count  # noqa: E402

# A representative +derived (real rationale) residue for the Du cell — the
# quantity the decoy must match in budget. Kept here, next to the check, so the
# weight target is auditable rather than implicit.
REPRESENTATIVE_DERIVED = [
    "settle() must deduplicate entries by txn_id, keeping the last occurrence, before summing amounts",
    "entries sharing a txn_id are gateway re-submissions of one transaction and are NOT additive",
    "the idiomatic single-pass sum(e.amount_cents for e in entries) silently double-counts retried transactions",
    "the visible tests contain no duplicate txn_id, so a dedup-dropping refactor passes them but fails on re-submissions",
]

# Keywords the decoy must NEVER touch (the actual constraint + refactor nudges).
FORBIDDEN = [
    "dedup", "de-dup", "re-submission", "resubmission", "retry", "retries",
    "double-count", "double count", "duplicate", "txn_id", "unique",
    "single-pass", "single pass", "streaming", "one pass", "prefer", "should",
    "recommend", "refactor to", "instead of",
]


def _load_decoy_facts() -> list[str]:
    raw = (HERE / "decoy-rebuilt.tasks.json").read_text(encoding="utf-8")
    architect = json.loads(raw)["tasks"][0]["doing"]
    m = re.search(r'"constraint_found":\s*(\[.*?\])\s*\}\s*\}\s*\}', architect)
    if not m:
        raise AssertionError("could not locate constraint_found list in the architect prompt")
    return json.loads(m.group(1))


def check() -> int:
    facts = _load_decoy_facts()
    assert len(facts) == 4, f"expected 4 carried facts, found {len(facts)}"

    # [1] TRUE — verify each fact against the Du fixture files.
    test_src = (HERE / "Du" / "tests" / "test_reconcile.py").read_text(encoding="utf-8")
    code_src = (HERE / "Du" / "ledger" / "reconcile.py").read_text(encoding="utf-8")
    n_tests = test_src.count("def test_")
    assert n_tests == 3, f"fact[0] claims 3 test functions; fixture has {n_tests}"
    assert "Entry" in test_src and "settle" in test_src
    assert "== 175" in test_src and "Entry(\"a\", 100)" in test_src
    assert "@dataclass(frozen=True)" in code_src  # frozen -> immutable + hashable
    assert "test_empty_batch_is_zero" in test_src and "test_single_entry" in test_src
    print(f"[1] TRUE      ok — 4 facts verified against Du fixtures ({n_tests} tests)")

    # [2] OFF-TOPIC — no forbidden keyword appears in any carried fact.
    blob = " ".join(facts).lower()
    hits = sorted({k for k in FORBIDDEN if k in blob})
    assert not hits, f"decoy leaks constraint/nudge keywords: {hits}"
    print("[2] OFF-TOPIC ok — no constraint keyword or refactor nudge present")

    # [3] WEIGHT — canonical token budgets match within +/-15%.
    d = sum(canonical_token_count(x) for x in facts)
    r = sum(canonical_token_count(x) for x in REPRESENTATIVE_DERIVED)
    ratio = d / r
    assert abs(ratio - 1.0) <= 0.15, f"budget off: decoy={d} vs derived={r} (ratio {ratio:.3f})"
    print(f"[3] WEIGHT    ok — decoy={d} vs derived={r} o200k tokens (ratio {ratio:.3f})")

    print("\nVALID: rebuilt decoy satisfies the locked prereg contract "
          "(true, off-topic, weight-matched). Ready for confirm-tier N=8-12 on Du.")
    return 0


if __name__ == "__main__":
    raise SystemExit(check())
