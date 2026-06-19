"""Gate G0: bench_join reproduces the published marshmallow result from raw.

The committed ``benchmarks/results/raw/marshmallow`` artifacts and the published
``benchmarks/results/marshmallow.json`` are two views of the same run. If
``bench_join`` (aggregating through the same code as ``pigeon metrics``) does not
reproduce the published totals and the recorded success tie, the instrument is
not trustworthy and no later phase may build on it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pigeon import bench_join, tokens

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "benchmarks" / "results" / "raw" / "marshmallow"
PUBLISHED = REPO_ROOT / "benchmarks" / "results" / "marshmallow.json"

pytestmark = pytest.mark.skipif(
    not RAW_DIR.is_dir() or not PUBLISHED.is_file(),
    reason="marshmallow benchmark artifacts not present",
)


def _published_accounting() -> dict:
    data = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    return data["task"]["arms"]["with-pigeon-3wave"]["pigeon_internal_accounting"]


def test_join_reproduces_published_with_arm_accounting():
    joined = bench_join.join_repo(RAW_DIR)
    published = _published_accounting()
    with_arm = joined["arms"]["with"]

    assert with_arm["events"] == published["events"] == 16
    assert with_arm["reduction_pct"] == published["overall_reduction_pct_vs_retransmission"]

    # Per-kind saved percentages come straight from the shared aggregation.
    summary = tokens.aggregate_metrics(RAW_DIR / "with.metrics.jsonl")
    by_kind = summary["by_kind"]

    def saved_pct(kind: str) -> float:
        b = by_kind[kind]
        return round(100.0 * b["saved_tokens"] / b["baseline_tokens"], 1)

    assert saved_pct("handoff") == published["handoff_saved_pct"] == 97.5
    assert saved_pct("pack") == published["pack_saved_pct"] == 92.1


def test_join_reproduces_recorded_success_tie():
    data = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    assert data["task"]["delta_pigeon_vs_naive"]["success"].startswith("tie")

    joined = bench_join.join_repo(RAW_DIR)
    assert joined["success"] == "tie"
    assert joined["all_pass"] is True
    assert all(arm["accept_pass"] is True for arm in joined["arms"].values())


def test_channel_and_derived_meters():
    """channel_tokens is the handoff total; derived is 0 until the polymath lands."""
    with_arm = bench_join.join_repo(RAW_DIR)["arms"]["with"]
    assert with_arm["channel_tokens"] == 3142   # carrier-to-carrier channel (Lever 1 target)
    assert with_arm["pack_tokens"] == 5985
    assert with_arm["derived_tokens"] == 0       # residue-bloat meter, pre-Lever-2
    assert with_arm["regression_count"] == 0


def test_naive_arm_has_no_ledger_but_keeps_its_verdict():
    naive = bench_join.join_repo(RAW_DIR)["arms"]["naive"]
    assert naive["has_ledger"] is False
    assert naive["accept_pass"] is True
    assert naive["channel_tokens"] == 0


def test_summarize_delegates_to_aggregate_metrics(repo):
    """The Config-taking wrapper and the path-taking engine return the same thing."""
    from pigeon import handoff as ho

    h = ho.build_handoff(sid="s1", frm="A", to="B", done=[], doing="x",
                         artifacts=["repo://AGENTS.md"])
    tokens.account_handoff(repo, h)
    assert tokens.summarize(repo) == tokens.aggregate_metrics(repo.metrics)
