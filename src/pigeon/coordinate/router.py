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

# Strength/cost tier per configured runner (the full roster). The "cheap" tier is the
# free arm (opencode Zen / openrouter / nvidia connectors + standalone MiMo): near-free and
# effectively unbeatable on tokens-per-dollar, so it is the default worker tier, not a
# last resort. Rate limits are handled by SPREADING load across it (route() round-robins
# within a tier), not by avoiding it. Any unlisted oc-*/nv-* runner also falls to "cheap".
# Override the whole map via the config's coordinate.router_tiers.
DEFAULT_TIERS: dict[str, str] = {
    # strong: authority / hardest reasoning / final verdict
    "opus": "strong",
    # mid: reliable, metered
    "sonnet": "mid", "codex": "mid", "agy": "mid",
    # cheap: the free arm (abundant tokens; round-robined to spread provider rate limits)
    "mimo": "cheap",
    "oc-mimo": "cheap", "oc-north": "cheap", "oc-nemotron": "cheap", "oc-nex": "cheap",
    "nv-nano": "cheap", "nv-minimax": "cheap", "nv-mixtral": "cheap", "nv-mistral-large": "cheap",
}

# Which tier each role prefers, per policy. `static` keeps the declared runner.
#   cost-aware   : minimize $ without losing success — reasoning stays at reliable *mid*
#                  (sonnet), only the mechanical worker tasks go to the free arm. This is
#                  the arm most likely to beat a static all-sonnet DAG *net of cost*.
#   quality-first: maximize success, cost secondary — strong on planner + verifier.
#   strong-verify: middle ground — only the verifier is upgraded to strong.
POLICIES: dict[str, dict[str, str] | None] = {
    "static": None,
    "cost-aware": {"planner": "mid", "worker": "cheap", "verifier": "mid", "other": "cheap"},
    "quality-first": {"planner": "strong", "worker": "mid", "verifier": "strong", "other": "mid"},
    "strong-verify": {"planner": "mid", "worker": "mid", "verifier": "strong", "other": "mid"},
}

_DEGRADE = {
    "strong": ("strong", "mid", "cheap"),
    "mid": ("mid", "strong", "cheap"),
    "cheap": ("cheap", "mid", "strong"),
}

# Within-tier preference (lower index = preferred). Keeps mid-reasoning on the reliable
# sonnet (not agy, which is pure-edit-only under coordinate) and rotates the free arm.
# Runners not listed here sort after, by name.
_PREFER = ["opus", "sonnet", "codex", "mimo",
           "oc-mimo", "oc-north", "oc-nemotron", "oc-nex",
           "nv-nano", "nv-minimax", "nv-mixtral", "nv-mistral-large", "agy"]


def _rank(runner: str) -> tuple[int, str]:
    return (_PREFER.index(runner) if runner in _PREFER else len(_PREFER), runner)


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
        lst.sort(key=_rank)
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
    rr: dict[str, int] = {}  # per-tier round-robin cursor: spread the free arm across tasks
    out: dict[str, str] = {}
    for t in tasks:
        want = pref.get(classify_role(t), pref.get("other", "mid"))
        chosen = t.get("runner")
        for candidate_tier in _DEGRADE[want]:
            pool = by_tier.get(candidate_tier)
            if pool:
                i = rr.get(candidate_tier, 0)
                chosen = pool[i % len(pool)]
                rr[candidate_tier] = i + 1
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


def describe_runners(available: Iterable[str], tiers: dict[str, str] | None = None) -> str:
    lines = []
    for r in sorted(available, key=_rank):
        t = tier_of(r, tiers)
        note = {"strong": "most capable, most expensive",
                "mid": "reliable, metered",
                "cheap": "free arm, abundant/near-zero cost, capable for MECHANICAL work "
                         "but may fail hard reasoning"}[t]
        lines.append(f"- {r} [{t}]: {note}")
    return "\n".join(lines)


def prompted_prompt(tasks: list[dict[str, Any]], available: Iterable[str],
                    tiers: dict[str, str] | None = None,
                    history_summary: str | None = None) -> str:
    """Build the routing prompt for the B3 prompted coordinator.

    The LLM is asked to assign a runner to each task to maximize held-out success while
    minimizing cost, given the runner roster and (optionally) B1's logged history of what
    each runner did on each role. This is the 'learned' signal without training: the model
    reasons over the routing log rather than a fitted policy.
    """
    task_lines = "\n".join(
        f"- {t['id']} (role={classify_role(t)}): {str(t.get('doing',''))[:200]}"
        for t in tasks)
    hist = f"\n\nObserved routing history (runner -> outcomes on prior runs):\n{history_summary}" \
        if history_summary else ""
    return (
        "You are the COORDINATOR. Assign exactly one runner to each task below to maximize "
        "held-out success while minimizing cost. Send mechanical/boilerplate work to the "
        "cheap free arm, but keep genuinely hard reasoning on a reliable mid/strong runner "
        "(the free arm fails hard tasks). Return ONLY a JSON object mapping task id to runner "
        "name, nothing else.\n\n"
        f"RUNNERS:\n{describe_runners(available, tiers)}\n\n"
        f"TASKS:\n{task_lines}{hist}\n\n"
        'JSON (e.g. {"architect": "sonnet", "impl": "oc-mimo"}):'
    )


def parse_routing(text: str, task_ids: Iterable[str],
                  available: Iterable[str]) -> dict[str, str]:
    """Extract + validate {task: runner} from the coordinator's reply.

    Only assignments to a known runner and a known task are kept; anything else is dropped
    (the caller keeps the task's declared runner for a dropped id).
    """
    import json
    import re
    ids, avail = set(task_ids), set(available)
    obj: dict[str, Any] = {}
    for m in re.finditer(r"\{[^{}]*\}", text, re.DOTALL):
        try:
            cand = json.loads(m.group(0))
        except json.JSONDecodeError:
            continue
        if isinstance(cand, dict):
            obj.update(cand)
    return {k: v for k, v in obj.items()
            if k in ids and isinstance(v, str) and v in avail}


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
