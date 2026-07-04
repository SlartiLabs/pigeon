"""Routing-decision log (Track B, rung B1) — the cheap probe before any learned router.

For every task in every coordination run, record the routing DECISION (which runner/model
took which role, at what DAG depth, whether it carried reasoning residue) joined to the
OUTCOME (status, turns, cost, tokens, duration). Records accumulate across runs in a single
appendable log (``.pigeon/routing_log.jsonl``) so the go/no-go question for the whole ASIA
track, "do routings vary in ways that change outcomes?", can be answered from real traffic
BEFORE a heuristic (B2) or learned (B3) router is built.

The log is a passive observation surface: writing it never changes routing and must never
break a run (the recorder calls it best-effort). The summary is deliberately conservative,
on an expert operator's own hand-written DAGs it will usually report "no variation", which
is itself the finding: a learned coordinator has little to capture where the DAG is already
near-optimal (see the roadmap's non-you-user caveat).
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

_OK_STATUS = ("exited", "completed", "ok", "succeeded")


def build_records(run_id: str | None, sid: str | None, tasks_data: dict[str, Any],
                  depth: dict[str, int], carried: dict[str, bool]) -> list[dict[str, Any]]:
    """One decision->outcome record per task. ``tasks_data`` is a manifest ``tasks`` map."""
    out: list[dict[str, Any]] = []
    for tid, t in tasks_data.items():
        tel = t.get("telemetry") or {}
        out.append({
            "run_id": run_id,
            "sid": sid,
            "task": tid,
            "runner": t.get("runner"),
            "model": t.get("model") or t.get("runner"),
            "num_deps": len(t.get("needs") or []),
            "depth": int(depth.get(tid, 0)),
            "carried_residue": bool(carried.get(tid, False)),
            "status": t.get("status"),
            "num_turns": tel.get("num_turns"),
            "cost_usd": tel.get("total_cost_usd"),
            "total_tokens": tel.get("total_tokens"),
            "duration_ms": tel.get("duration_ms"),
        })
    return out


def append_log(path: Path, records: list[dict[str, Any]]) -> None:
    if not records:
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


def load_log(path: Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def records_from_manifest(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Backfill records from an existing run manifest (depth from its own ``needs``)."""
    tasks = manifest.get("tasks", {})
    direct = {tid: set(t.get("needs") or []) for tid, t in tasks.items()}

    def _depth(tid: str) -> int:
        seen: set[str] = set()
        stack = list(direct.get(tid, ()))
        while stack:
            up = stack.pop()
            if up not in seen:
                seen.add(up)
                stack.extend(direct.get(up, ()))
        return len(seen)

    depth = {tid: _depth(tid) for tid in tasks}
    carried = {tid: bool(direct.get(tid)) for tid in tasks}  # coarse: had upstreams
    return build_records(manifest.get("run_id"), manifest.get("sid"), tasks, depth, carried)


def _mean(xs: list[Any]) -> float | None:
    vals = [x for x in xs if isinstance(x, (int, float))]
    return round(sum(vals) / len(vals), 4) if vals else None


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    """The free probe: do routings vary, and do outcomes vary with the routing?"""
    by_role: dict[str, dict[Any, list]] = defaultdict(lambda: defaultdict(list))
    for r in records:
        by_role[r["task"]][r.get("runner")].append(r)

    roles: dict[str, Any] = {}
    varied_roles = 0
    signal_roles = 0
    for role, runners in by_role.items():
        entry = {"n_runners": len(runners), "runners": {}}
        for runner, recs in runners.items():
            entry["runners"][runner] = {
                "n": len(recs),
                "pass_rate": _mean([1.0 if x.get("status") in _OK_STATUS else 0.0 for x in recs]),
                "mean_turns": _mean([x.get("num_turns") for x in recs]),
                "mean_cost_usd": _mean([x.get("cost_usd") for x in recs]),
            }
        roles[role] = entry
        if len(runners) > 1:
            varied_roles += 1
            costs = [o["mean_cost_usd"] for o in entry["runners"].values() if o["mean_cost_usd"] is not None]
            turns = [o["mean_turns"] for o in entry["runners"].values() if o["mean_turns"] is not None]
            passes = [o["pass_rate"] for o in entry["runners"].values() if o["pass_rate"] is not None]
            cost_gap = (max(costs) - min(costs)) > 0.05 * (min(costs) or 1) if len(costs) > 1 else False
            turn_gap = (max(turns) - min(turns)) >= 2 if len(turns) > 1 else False
            pass_gap = (max(passes) - min(passes)) >= 0.2 if len(passes) > 1 else False
            if cost_gap or turn_gap or pass_gap:
                signal_roles += 1

    if not records:
        verdict = "empty log: run some coordination (or `pigeon routing-log --backfill`) first."
    elif varied_roles == 0:
        verdict = ("NO routing variation: every role was always routed to the same runner. A "
                   "learned router has nothing to capture on this traffic. To get a signal, "
                   "vary routing deliberately (rung B2, a heuristic baseline) and compare.")
    elif signal_roles == 0:
        verdict = (f"{varied_roles} role(s) saw more than one runner, but outcomes did not "
                   "differ materially: the routing choice did not change the result here. Weak "
                   "case for a learned router on this traffic.")
    else:
        verdict = (f"{signal_roles}/{varied_roles} varied role(s) show outcome differences "
                   "across runners: dynamic routing changes outcomes here. A heuristic router "
                   "(rung B2) is worth testing against the static DAG before any learned policy.")

    return {
        "runs": len({r.get("run_id") for r in records}),
        "task_records": len(records),
        "roles": roles,
        "varied_roles": varied_roles,
        "signal_roles": signal_roles,
        "verdict": verdict,
    }


def format_summary(s: dict[str, Any]) -> str:
    lines = [f"routing-log: {s['task_records']} task record(s) across {s['runs']} run(s)"]
    for role, e in sorted(s["roles"].items()):
        lines.append(f"  role {role!r}  ({e['n_runners']} runner(s))")
        for runner, o in sorted(e["runners"].items(), key=lambda kv: str(kv[0])):
            lines.append(f"    {str(runner):16s} n={o['n']:<3} pass={o['pass_rate']} "
                         f"turns={o['mean_turns']} cost=${o['mean_cost_usd']}")
    lines.append("")
    lines.append(f"PROBE: {s['verdict']}")
    return "\n".join(lines)
