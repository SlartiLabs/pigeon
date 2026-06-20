"""Join pigeon's token ledger with held-out acceptance + regression outcomes.

A benchmark arm records two *independent* signals, written by the operator and
never shown to the agents:

* **tokens** — pigeon's own ledger (``<arm>.metrics.jsonl``), aggregated through
  :func:`pigeon.tokens.aggregate_metrics` — the exact code that powers
  ``pigeon metrics``, so a join *reproduces* a published result rather than
  re-deriving it.
* **success** — the held-out acceptance test (``<arm>.accept`` → ``ACCEPT: PASS``)
  and the full-suite regression gate (``<arm>.meta`` ``pytest_rc`` / ``<arm>.pytest``).

``bench_join`` puts both on one row per arm, exposing the triple later phases
sweep over — ``(channel_tokens, accept_pass, regression_count)`` — where
``channel_tokens`` is the carrier-to-carrier handoff total (Lever 1's target)
and ``derived_tokens`` is the residue-bloat meter (Lever 2; 0 until the polymath
schema is populated). It only *reads* artifacts; it never re-runs a benchmark.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .tokens import aggregate_metrics


@dataclass
class ArmJoin:
    """One arm's tokens joined to its pass/fail signals."""

    arm: str
    accept_pass: bool | None          # held-out acceptance test
    regression_count: int | None      # failed tests in the full-suite gate (0 = green)
    channel_tokens: int               # handoff actual — the carrier-to-carrier channel (Lever 1)
    pack_tokens: int                  # curated-context scaffolding actual
    derived_tokens: int               # polymath residue-bloat meter (Lever 2; 0 until populated)
    actual_tokens: int                # ledger overall
    baseline_tokens: int
    reduction_pct: float
    events: int
    has_ledger: bool                  # False for arms with no pigeon ledger (e.g. naive)
    # Panel-correction axes (from the run manifest): the multi-turn tool tax and
    # the ground-truth USD cost. A compression "win" that raises turns or USD is
    # not a win — cost_usd is the real measured spend, so the USD-win rule reads
    # it directly rather than re-weighting output tokens.
    num_turns: int | None = None
    cost_usd: float | None = None


def _read_accept(path: Path) -> bool | None:
    """Parse an ``<arm>.accept`` file (``ACCEPT: PASS`` / ``ACCEPT: FAIL``)."""
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8").strip().upper()
    if "PASS" in text:
        return True
    if "FAIL" in text:
        return False
    return None


def _read_meta(path: Path) -> dict[str, str]:
    """Parse a ``key=value``-per-line ``<arm>.meta`` file."""
    meta: dict[str, str] = {}
    if not path.is_file():
        return meta
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if "=" in line:
            key, _, value = line.partition("=")
            meta[key.strip()] = value.strip()
    return meta


def _regression_count(meta: dict[str, str], pytest_path: Path) -> int | None:
    """Number of failing tests in the regression gate.

    ``pytest_rc=0`` means green → 0 regressions. On a non-zero rc, try to read a
    ``N failed`` count from the captured pytest output; fall back to ``None`` when
    the count can't be recovered (rc says red, magnitude unknown).
    """
    rc = meta.get("pytest_rc")
    if rc is not None:
        try:
            if int(rc) == 0:
                return 0
        except ValueError:
            pass
    if pytest_path.is_file():
        for line in reversed(pytest_path.read_text(encoding="utf-8").splitlines()):
            if "failed" in line:
                for token in line.replace("=", " ").split():
                    if token.isdigit():
                        return int(token)
                break
    return None if rc is None or rc == "0" else -1


def _component(summary: dict[str, Any], kind: str, field: str = "actual_tokens") -> int:
    return int(summary["by_kind"].get(kind, {}).get(field, 0))


def _manifest_totals(path: Path) -> tuple[int | None, float | None]:
    """Sum ``num_turns`` and ``total_cost_usd`` over a coordinate run manifest.

    The manifest (``<arm>.manifest.json``, a copy of
    ``.pigeon/coordinate/runs/<run>.json``) carries per-task ``telemetry`` with
    the measured turn count and USD — the multi-turn tool tax and the
    ground-truth cost the panel flagged. Returns ``(None, None)`` when absent so a
    naive/un-instrumented arm degrades cleanly.
    """
    if not path.is_file():
        return (None, None)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return (None, None)
    tasks = data.get("tasks")
    if not isinstance(tasks, dict):
        return (None, None)
    turns = 0
    cost = 0.0
    saw_turns = saw_cost = False
    for task in tasks.values():
        tel = task.get("telemetry") or {}
        if tel.get("num_turns") is not None:
            turns += int(tel["num_turns"])
            saw_turns = True
        if tel.get("total_cost_usd") is not None:
            cost += float(tel["total_cost_usd"])
            saw_cost = True
    return (turns if saw_turns else None, round(cost, 6) if saw_cost else None)


def _sum_derived(jsonl_path: Path) -> int:
    """Sum ``components.derived`` across handoff events (the residue-bloat meter)."""
    if not jsonl_path.is_file():
        return 0
    total = 0
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        total += int((ev.get("components") or {}).get("derived", 0))
    return total


def join_arm(raw_dir: Path, arm: str, *, ledger_arm: str | None = None) -> ArmJoin:
    """Join one arm in ``raw_dir``.

    ``arm`` is the accept/meta prefix (e.g. ``"with"``, ``"naive"``). The pigeon
    ledger may live under a different prefix; pass ``ledger_arm`` to point at it
    (defaults to ``arm``). An arm with no ``<ledger_arm>.metrics.jsonl`` is a
    no-ledger arm (the naive baseline keeps its totals elsewhere).
    """
    raw_dir = Path(raw_dir)
    ledger = raw_dir / f"{ledger_arm or arm}.metrics.jsonl"
    summary = aggregate_metrics(ledger)
    meta = _read_meta(raw_dir / f"{arm}.meta")
    turns, cost = _manifest_totals(raw_dir / f"{arm}.manifest.json")
    return ArmJoin(
        arm=arm,
        accept_pass=_read_accept(raw_dir / f"{arm}.accept"),
        regression_count=_regression_count(meta, raw_dir / f"{arm}.pytest"),
        channel_tokens=_component(summary, "handoff"),
        pack_tokens=_component(summary, "pack"),
        derived_tokens=_sum_derived(ledger),
        actual_tokens=summary["overall"]["actual_tokens"],
        baseline_tokens=summary["overall"]["baseline_tokens"],
        reduction_pct=summary["overall"]["reduction_pct"],
        events=summary["overall"]["events"],
        has_ledger=ledger.is_file(),
        num_turns=turns,
        cost_usd=cost,
    )


def discover_arms(raw_dir: Path) -> list[str]:
    """Arm prefixes in ``raw_dir``, derived from ``*.accept`` files (sorted)."""
    return sorted(p.name[: -len(".accept")] for p in Path(raw_dir).glob("*.accept"))


def join_repo(raw_dir: Path) -> dict[str, Any]:
    """Join every arm found in ``raw_dir`` and label the success outcome.

    ``success`` is ``"tie"`` when all arms agree on the acceptance verdict and
    ``"split"`` when they disagree — the recorded marshmallow result is a tie
    (both pass).
    """
    raw_dir = Path(raw_dir)
    arms = {arm: join_arm(raw_dir, arm) for arm in discover_arms(raw_dir)}
    verdicts = {a.accept_pass for a in arms.values() if a.accept_pass is not None}
    success = "tie" if len(verdicts) <= 1 else "split"
    return {
        "raw_dir": str(raw_dir),
        "arms": {name: asdict(a) for name, a in arms.items()},
        "success": success,
        "all_pass": verdicts == {True},
    }


def main(argv: list[str] | None = None) -> int:
    """``python -m pigeon.bench_join <raw_dir>`` → print the join as JSON."""
    args = sys.argv[1:] if argv is None else argv
    if not args:
        print("usage: python -m pigeon.bench_join <raw_results_dir>", file=sys.stderr)
        return 2
    print(json.dumps(join_repo(Path(args[0])), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
