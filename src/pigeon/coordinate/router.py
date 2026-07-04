"""Heuristic router (Track B, rung B2): a deterministic model-per-role policy.

This is the BASELINE a learned coordinator (rung B3) must beat. It assigns each task a
runner from the available pool by its ROLE (planner / worker / verifier), so *dynamic*
routing can be ablated against the static single-model DAG on a graded task. If this simple
role-aware policy already captures most of the gain over a fixed DAG, the learned "20%" is
mostly an 80%-shaped problem, which is exactly what B2 exists to find out BEFORE any policy
is trained.

The router is a pure spec transform: `apply(spec, policy, available)` returns a spec with
each task's `runner` reassigned. It never executes anything and never mutates unknown
runners in. Use `pigeon route <spec> --policy cost-aware` to produce the routed arm.
"""

from __future__ import annotations

from typing import Any, Iterable

# Role inference from a task's id + `doing` text. Order matters: a "review the plan" task
# is a verifier, not a planner, so verifier keywords win first.
ROLE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "verifier": ("review", "verif", "gate", "judge", "critic", "audit", "assess", "grade"),
    "planner": ("architect", "plan", "design", "scope", "spec", "decompos", "coordinat", "triage"),
    "worker": ("implement", "build", "write", "refactor", "code", "fix", "edit",
               "draft", "generat", "migrat", "port"),
}
_ROLE_ORDER = ("verifier", "planner", "worker")

# Default reliability/strength tier per known runner. oc-*/nv-* (opencode-routed free
# models) default to "cheap". Override via the config's coordinate.router_tiers.
DEFAULT_TIERS: dict[str, str] = {
    "opus": "strong", "sonnet": "mid", "codex": "mid", "agy": "mid", "mimo": "cheap",
}

# Which tier each role prefers, per policy. `static` keeps the declared runner.
POLICIES: dict[str, dict[str, str] | None] = {
    "static": None,
    "cost-aware": {"planner": "strong", "worker": "cheap", "verifier": "strong", "other": "mid"},
    "strong-verify": {"planner": "mid", "worker": "mid", "verifier": "strong", "other": "mid"},
}

_DEGRADE = {
    "strong": ("strong", "mid", "cheap"),
    "mid": ("mid", "strong", "cheap"),
    "cheap": ("cheap", "mid", "strong"),
}


def classify_role(task: dict[str, Any]) -> str:
    text = (str(task.get("id", "")) + " " + str(task.get("doing", ""))).lower()
    for role in _ROLE_ORDER:
        if any(k in text for k in ROLE_KEYWORDS[role]):
            return role
    return "worker"  # a task with a `doing` step is work by default


def tier_of(runner: str, tiers: dict[str, str] | None = None) -> str:
    tiers = tiers or DEFAULT_TIERS
    if runner in tiers:
        return tiers[runner]
    if runner.startswith(("oc-", "nv-")):
        return "cheap"
    return "mid"


def _by_tier(available: Iterable[str], tiers: dict[str, str] | None) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for r in available:
        out.setdefault(tier_of(r, tiers), []).append(r)
    for lst in out.values():
        lst.sort()
    return out


def route(tasks: list[dict[str, Any]], policy: str, available: Iterable[str],
          tiers: dict[str, str] | None = None) -> dict[str, str]:
    """Return {task_id: runner} for `policy` over the `available` runner names.

    Unknown policy raises. `static` keeps each task's declared runner. When no runner of
    any tier is available, a task keeps its declared runner (best-effort, never invents).
    """
    if policy not in POLICIES:
        raise ValueError(f"unknown routing policy {policy!r} "
                         f"(known: {', '.join(sorted(POLICIES))})")
    pref = POLICIES[policy]
    if pref is None:
        return {t["id"]: t.get("runner") for t in tasks}
    by_tier = _by_tier(available, tiers)
    out: dict[str, str] = {}
    for t in tasks:
        want = pref.get(classify_role(t), pref.get("other", "mid"))
        chosen = t.get("runner")
        for candidate_tier in _DEGRADE[want]:
            if by_tier.get(candidate_tier):
                chosen = by_tier[candidate_tier][0]
                break
        out[t["id"]] = chosen
    return out


def apply(spec: dict[str, Any], policy: str, available: Iterable[str],
          tiers: dict[str, str] | None = None) -> dict[str, Any]:
    """Reassign `runner` on each task in `spec` per `policy`. Mutates and returns `spec`."""
    tasks = spec.get("tasks", [])
    assign = route(tasks, policy, available, tiers)
    for t in tasks:
        r = assign.get(t["id"])
        if r:
            t["runner"] = r
    return spec


def explain(tasks: list[dict[str, Any]], policy: str, available: Iterable[str],
            tiers: dict[str, str] | None = None) -> list[dict[str, str]]:
    """Human/JSON view: per task, the inferred role and the (from -> to) runner change."""
    assign = route(tasks, policy, available, tiers)
    rows = []
    for t in tasks:
        rows.append({
            "task": t["id"],
            "role": classify_role(t),
            "from": t.get("runner") or "(unassigned)",
            "to": assign.get(t["id"]) or "(unassigned)",
        })
    return rows
