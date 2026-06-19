"""Parallel agent coordination: fan a tasks file out to AI agent CLIs.

``pigeon coordinate tasks.yaml`` reads a tasks definition (YAML or JSON),
writes one validated handoff per task, then spawns each task's runner CLI
(``claude`` / ``agy`` / ``opencode`` — argv templates live in config)
concurrently, prefixing live output with the task id and saving a per-task
log under ``.pigeon/coordinate/logs/``.

Tasks file shape::

    sid: sprint-42
    tasks:
      - id: api
        runner: claude            # key into coordinate.runners (default: claude)
        doing: implement the /users endpoint
        done: [design]            # optional, like every field below
        needs: [schema]           # run only after these tasks exit 0
        artifacts: ["repo://src/api.py"]
        decisions: {auth: oauth2_pkce}
        rag: {query: "users endpoint", top_k: 3}
        constraints: {fail_fast: true}
        pack: true                # attach a packed context bundle to the handoff
        mutates_packages: false   # true => requires an isolated environment
        telemetry: true           # append JSON-output flags; record measured tokens
        readonly: true            # no writes: hard read-only constraint +
                                  #   worktree containment (unless isolation set)
        isolation: worktree       # run in a throwaway git worktree + task branch
        crew:                     # deterministic staffing, carried in the handoff
          skills: [advanced-python-backend]
          subagents:
            - role: adversarial-reviewer
              skill: security-audit
              verdict: must approve before hand-back
        prompt: "..."             # override the default prompt template

Tasks without dependency edges run fully parallel (bounded by the limit);
``needs`` forms an acyclic graph — a task launches when everything it needs
has exited 0, and everything downstream of a failure is skipped, not run.

Safety strategy — checked as a *preflight* before anything spawns, and
embedded into every handoff's ``constraints`` object so the receiving agent
sees the same policy it must honor:

* agents may modify the folder only when the repository is set up: a
  ``.git`` checkout with pigeon initialized, so every change is
  revertible and contract-validated;
* coordination runs on Linux only;
* package mutations (``pip install`` / ``pip uninstall`` / library or
  dependency changes) are allowed only inside a conda env, virtualenv, or
  container — never against the system interpreter;
* runners get their unattended flag (e.g. ``--dangerously-skip-permissions``)
  only when the operator explicitly passes ``--skip-permissions``.

Each rule can be relaxed in ``.pigeon/config.yaml`` under
``coordinate.safety`` — policy lives in config, not code.

This module is a package: the scheduler, tasks-file loading, safety preflight,
planning, and the run loop live here; the read-side rendering lives in
:mod:`~pigeon.coordinate.reporting`, git worktree isolation in
:mod:`~pigeon.coordinate.worktree`, and the per-vendor telemetry usage parsers
in :mod:`~pigeon.coordinate.telemetry`. Every public name those submodules own
is re-exported below, so ``coordinate.<name>`` is unchanged for callers.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import select as _select
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from .. import SCHEMA_VERSION, tokens
from .. import handoff as ho
from ..config import Config

COORDINATOR = "Coordinator"
DEPTH_ENV = "PIGEON_DEPTH"
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

# Injected into every generated handoff; task-level constraints override keys.
SAFETY_CONSTRAINTS: dict[str, str] = {
    "fs_scope": "create or modify files only inside this repository checkout",
    "package_policy": (
        "pip install/uninstall and any library or dependency change only inside "
        "a conda env, virtualenv, or container — never the system interpreter"
    ),
    "escalation": (
        "if a step would violate a constraint, stop and hand back to "
        f"'{COORDINATOR}' instead of proceeding"
    ),
}

# Overrides fs_scope for readonly tasks. Soft (prompt-level); the constraint is
# matched to the task's effective isolation by `_readonly_fs` below.
#
# SHARED tree: the task does not touch repo source but MAY persist its hand-back
# and any artifact its `doing` names under the .pigeon/ contract dir — this is the
# reviewer/auditor pattern (findings written to a JSON/markdown artifact).
READONLY_CONSTRAINTS_SHARED: dict[str, str] = {
    "fs_scope": (
        "READ-ONLY TASK: do not create, modify, move, or delete any file in the "
        "repository working tree (source, configs, docs), and instruct every "
        "subagent you dispatch to do the same. You MAY write your hand-back and "
        "any artifact your 'doing' step names, but ONLY under the .pigeon/ "
        "contract directory. If a step would require editing a repository file, "
        f"stop and hand back to '{COORDINATOR}'."
    ),
}
# Throwaway WORKTREE: any file the task writes is discarded on teardown, so it
# must produce findings in the hand-back only — writing an artifact would be lost.
READONLY_CONSTRAINTS_WORKTREE: dict[str, str] = {
    "fs_scope": (
        "READ-ONLY TASK: do not create, modify, move, or delete any file, and "
        "instruct every subagent you dispatch to do the same — produce findings "
        "and a hand-back only (you run in a throwaway worktree; any file you "
        "write is discarded). If a step seems to require a write, stop and hand "
        f"back to '{COORDINATOR}'."
    ),
}


def _readonly_fs(task: dict[str, Any]) -> dict[str, str]:
    """Pick the readonly fs constraint matching the task's effective isolation.

    A shared-tree readonly task may persist artifacts under ``.pigeon/``; a
    worktree-isolated one cannot (its writes vanish on teardown) so it is told to
    hand findings back only. Isolation has already been resolved (a bare readonly
    task defaults to ``worktree``) by the time handoffs are built.
    """
    return (READONLY_CONSTRAINTS_SHARED if task.get("isolation") == "shared"
            else READONLY_CONSTRAINTS_WORKTREE)

DEFAULT_PROMPT = (
    "You are sub-agent '{task_id}' in pigeon session '{sid}'. "
    "Read your handoff at {handoff} and follow the protocol in AGENTS.md. "
    "Treat every entry in the handoff 'constraints' object as a hard rule. "
    "Do only the 'doing' step, then record your result with `pigeon handoff` "
    "(from '{task_id}' to '" + COORDINATOR + "')."
)

def crew_instructions(crew: dict[str, Any],
                      playbooks_rel: str = "the memory playbooks dir") -> str:
    """Render a crew block as marching orders for the receiving agent.

    The roster is part of the contract: the agent spawns the subagents via
    its own native mechanism (Claude Code Task tool, etc.), but *which*
    specialists run is decided here, deterministically, not improvised.
    """
    lines: list[str] = []
    if crew.get("skills"):
        lines.append("Load these skills before starting: "
                     + ", ".join(crew["skills"]) + ".")
    for member in crew.get("subagents", []):
        part = f"Dispatch a subagent for the role '{member['role']}'"
        if member.get("skill"):
            part += f", loading skill '{member['skill']}'"
        if member.get("doing"):
            part += f", to: {member['doing']}"
        part += "."
        if member.get("verdict"):
            part += f" Gate: {member['verdict']}."
        lines.append(part)
    lines.append("This crew is part of the contract — staff it exactly as "
                 f"specified; skill names resolve in {playbooks_rel}/.")
    return " ".join(lines)


_print_lock = threading.Lock()


# ----------------------------------------------------------------- tasks file
def _pool_models(pool: Any) -> list[str]:
    """The model list of a pool in either accepted form.

    A bare list ``[m1, m2]`` *is* the models; the object form
    ``{models: [...], max_concurrency, ...}`` carries throttle knobs consumed in
    a later phase. Returns ``[]`` for an unknown (``None``) pool; raises on a
    malformed one (so a referenced-but-broken pool fails loud, not silently).
    """
    if pool is None:
        return []
    if isinstance(pool, list):
        models = pool
    elif isinstance(pool, dict):
        models = pool.get("models") or []
    else:
        raise ValueError(
            f"model_pool must be a list or a mapping, got {type(pool).__name__}"
        )
    if not isinstance(models, list) or not all(
            isinstance(m, str) and m for m in models):
        raise ValueError("model_pool models must be a list of non-empty strings")
    return list(models)


def _pool_throttle(pool: Any) -> dict[str, Any]:
    """The spawn-side throttle knobs of a pool (object form only; a bare list
    carries none). Clock-only, coordinator-enforceable (DESIGN §2e):
      * max_concurrency      — cap concurrent in-flight tasks drawing on the pool
      * min_spawn_interval_s — minimum wall-clock gap between spawns on the pool
      * max_retries          — re-queue a rate-limited exit this many times
    Defaults mean 'no throttle', so a bare list / absent knobs behave as today."""
    d = pool if isinstance(pool, dict) else {}
    mc = d.get("max_concurrency")
    return {
        "max_concurrency": int(mc) if mc is not None else None,
        "min_spawn_interval_s": float(d.get("min_spawn_interval_s", 0) or 0),
        "max_retries": int(d.get("max_retries", 0) or 0),
    }


# Coarse rate-limit / contention signal in a child's output — the only thing the
# coordinator can react to (telemetry arrives only post-exit; DESIGN Fact #4).
_RATE_LIMIT_RE = re.compile(
    r"\b(429|503|rate[ -]?limit|too many requests|quota exceeded|overloaded|"
    r"database is locked|resource exhausted)\b", re.IGNORECASE)


def _looks_rate_limited(log_path: Path) -> bool:
    """True when a task's log tail carries a rate-limit/contention signal."""
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return bool(_RATE_LIMIT_RE.search(text[-4000:]))


def _min_opt(current: float | None, candidate: float) -> float:
    """min() that treats None as 'unset' — for accumulating the soonest wait."""
    return candidate if current is None else min(current, candidate)


def _latest_handback(config: Config, sid: str, task_id: str) -> dict[str, Any] | None:
    """The newest hand-back this task wrote to the Coordinator (``from==task_id``,
    ``to==COORDINATOR``), by claim sequence. The re-entry signal lives in its
    ``state.decisions.verdict``; ``None`` when the task handed nothing back."""
    d = config.handoffs_dir
    if not d.is_dir():
        return None

    def _seq(path: Path) -> int:
        m = re.match(rf"{re.escape(sid)}-(\d+)", path.stem)
        return int(m.group(1)) if m else -1

    # Newest claim-sequence first, returning the first hand-back from this task —
    # an early exit that parses only the tail, not every handoff in the session
    # (U4: this is called once per re-entry; the old scan was O(all handoffs)).
    for path in sorted(d.glob(f"{sid}-*.json"), key=_seq, reverse=True):
        try:
            h = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if h.get("from") == task_id and h.get("to") == COORDINATOR:
            return h
    return None


def load_tasks(path: Path,
               default_runner: str | list[str] | None = None,
               model_pools: dict[str, Any] | None = None) -> dict[str, Any]:
    """Load and structurally validate a tasks definition (JSON or YAML).

    Tasks without a ``runner`` are resolved via ``default_runner``: a name
    assigns that runner, a list round-robins across it (task order), and
    ``None`` raises — pigeon never silently routes work to a runner you
    didn't choose (that is how Pro plans evaporate in ten minutes).

    A task's ``model_pool`` is resolved against ``model_pools`` into a concrete
    ``model`` by sid-seeded round-robin (see :func:`_pool_models`), mirroring the
    ``default_runner`` round-robin above it.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"tasks file not found: {path}")
    text = path.read_text(encoding="utf-8")
    spec = json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)
    if not isinstance(spec, dict):
        raise ValueError("tasks file must be a mapping with 'sid' and 'tasks'")
    sid = spec.get("sid")
    if not isinstance(sid, str) or not sid:
        raise ValueError("tasks file: 'sid' (non-empty string) is required")
    if not _SAFE_ID_RE.match(sid):
        raise ValueError(f"tasks file: unsafe sid {sid!r} — ids become filenames, "
                         "branch names, and CLI args; use [A-Za-z0-9._-]")
    tasks = spec.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("tasks file: 'tasks' must be a non-empty list")
    seen: set[str] = set()
    for i, task in enumerate(tasks):
        if not isinstance(task, dict):
            raise ValueError(f"task #{i}: must be a mapping")
        tid = task.get("id")
        if not isinstance(tid, str) or not tid:
            raise ValueError(f"task #{i}: 'id' (non-empty string) is required")
        if not _SAFE_ID_RE.match(tid):
            raise ValueError(f"task id {tid!r} is unsafe — ids become filenames, "
                             "branch names, and CLI args; use [A-Za-z0-9._-]")
        if tid in seen:
            raise ValueError(f"duplicate task id {tid!r}")
        seen.add(tid)
        if not task.get("doing"):
            raise ValueError(f"task {tid!r}: 'doing' is required")
        if task.get("isolation") not in (None, "shared", "worktree"):
            raise ValueError(
                f"task {tid!r}: 'isolation' must be 'shared' or 'worktree'"
            )
        if "readonly" in task and not isinstance(task["readonly"], bool):
            raise ValueError(f"task {tid!r}: 'readonly' must be true or false")
        # A read-only task gets hard containment by default: a prompt-level
        # "don't write" is soft (an agent or its subagent can ignore it), so
        # unless isolation is set explicitly, run it in a throwaway worktree —
        # a contract violation lands on a disposable branch, not the tree.
        if task.get("readonly") and task.get("isolation") is None:
            task["isolation"] = "worktree"
        model = task.get("model")
        if model is not None and (not isinstance(model, str) or not model):
            raise ValueError(f"task {tid!r}: 'model' must be a non-empty string")
        model_pool = task.get("model_pool")
        if model_pool is not None and (not isinstance(model_pool, str) or not model_pool):
            raise ValueError(f"task {tid!r}: 'model_pool' must be a non-empty string")
        if model and model_pool:
            raise ValueError(
                f"task {tid!r}: set 'model' or 'model_pool', not both"
            )
        receives = task.get("receives")
        if receives is not None and (
                not isinstance(receives, list)
                or not all(isinstance(x, str) and x for x in receives)):
            raise ValueError(
                f"task {tid!r}: 'receives' must be a list of pointer/glob strings"
            )
        mcp = task.get("mcp")
        if mcp is not None and (
                not isinstance(mcp, list)
                or not all(isinstance(x, str) and x for x in mcp)):
            raise ValueError(
                f"task {tid!r}: 'mcp' must be a list of MCP server-name strings"
            )
        if "reentry" in task and not isinstance(task["reentry"], bool):
            raise ValueError(f"task {tid!r}: 'reentry' must be true or false")
        max_reentry = task.get("max_reentry")
        if max_reentry is not None and (
                not isinstance(max_reentry, int) or isinstance(max_reentry, bool)
                or max_reentry < 1):
            raise ValueError(
                f"task {tid!r}: 'max_reentry' must be a positive integer")
        if max_reentry is not None and not task.get("reentry"):
            raise ValueError(
                f"task {tid!r}: 'max_reentry' set without 'reentry: true'")
        crew = task.get("crew")
        if crew is not None:
            if not isinstance(crew, dict):
                raise ValueError(f"task {tid!r}: 'crew' must be a mapping")
            skills = crew.get("skills", [])
            if not isinstance(skills, list) or not all(
                    isinstance(x, str) and x for x in skills):
                raise ValueError(f"task {tid!r}: crew.skills must be a list of names")
            members = crew.get("subagents", [])
            if not isinstance(members, list):
                raise ValueError(f"task {tid!r}: crew.subagents must be a list")
            for i, member in enumerate(members):
                if not isinstance(member, dict) or not member.get("role"):
                    raise ValueError(
                        f"task {tid!r}: crew.subagents[{i}] needs a 'role'"
                    )
            if not skills and not members:
                raise ValueError(f"task {tid!r}: 'crew' is empty")
        # runner resolution happens after the whole structural pass

    # Dependency graph: `needs` must reference known tasks and stay acyclic.
    ids = {t["id"] for t in tasks}
    for task in tasks:
        needs = task.get("needs") or []
        if not isinstance(needs, list) or not all(isinstance(n, str) for n in needs):
            raise ValueError(f"task {task['id']!r}: 'needs' must be a list of task ids")
        for need in needs:
            if need == task["id"]:
                raise ValueError(f"task {task['id']!r}: cannot depend on itself")
            if need not in ids:
                raise ValueError(f"task {task['id']!r}: unknown dependency {need!r}")
    indegree = {t["id"]: len(set(t.get("needs") or [])) for t in tasks}
    dependents: dict[str, list[str]] = {tid: [] for tid in ids}
    for task in tasks:
        for need in set(task.get("needs") or []):
            dependents[need].append(task["id"])
    ready = [tid for tid, deg in indegree.items() if deg == 0]
    resolved = 0
    while ready:
        for dep in dependents[ready.pop()]:
            indegree[dep] -= 1
            if indegree[dep] == 0:
                ready.append(dep)
        resolved += 1
    if resolved != len(ids):
        cyclic = sorted(tid for tid, deg in indegree.items() if deg > 0)
        raise ValueError(f"dependency cycle among tasks: {', '.join(cyclic)}")

    unassigned = [t for t in tasks if not t.get("runner")]
    if unassigned:
        if default_runner is None:
            ids = ", ".join(t["id"] for t in unassigned)
            raise ValueError(
                f"task(s) {ids} name no runner and coordinate.default_runner "
                "is not set — name a runner per task, or set "
                "coordinate.default_runner to a runner name (or a list of "
                "names for round-robin)"
            )
        pool = ([default_runner] if isinstance(default_runner, str)
                else list(default_runner))
        if not pool or not all(isinstance(r, str) and r for r in pool):
            raise ValueError("coordinate.default_runner must be a runner "
                             "name or a non-empty list of names")
        for i, task in enumerate(unassigned):
            task["runner"] = pool[i % len(pool)]

    # Model pools: round-robin a pool's models across the tasks that name it,
    # seeded by sid so the assignment is reproducible per session yet rotated
    # across sessions (so concurrent sessions don't all start at models[0]).
    # `i` counts only the tasks using *that* pool, in task-definition order.
    pools = model_pools or {}
    pool_index: dict[str, int] = {}
    for task in tasks:
        pname = task.get("model_pool")
        if not pname:
            continue
        models = _pool_models(pools.get(pname))
        if not models:
            raise ValueError(
                f"task {task['id']!r}: model_pool {pname!r} is undefined or empty "
                f"(configured pools: {', '.join(sorted(pools)) or 'none'})"
            )
        offset = int(hashlib.sha1(sid.encode("utf-8")).hexdigest(), 16) % len(models)
        i = pool_index.get(pname, 0)
        task["model"] = models[(offset + i) % len(models)]
        pool_index[pname] = i + 1
    return spec


# --------------------------------------------------------------------- safety
def repo_is_setup(config: Config) -> bool:
    """True when agents may modify this folder: git checkout + pigeon init."""
    return (config.root / ".git").exists() and config.handoff_schema.is_file()


def isolated_env() -> str | None:
    """Describe the isolated environment children will inherit, or ``None``.

    Only signals that propagate to subprocesses count: conda/virtualenv
    activation env vars and container markers. The coordinator's own
    ``sys.prefix`` is deliberately ignored — it proves nothing about what
    ``pip`` resolves to in a spawned agent.
    """
    conda = os.environ.get("CONDA_DEFAULT_ENV") or os.environ.get("CONDA_PREFIX")
    if conda:
        return f"conda env: {conda}"
    venv = os.environ.get("VIRTUAL_ENV")
    if venv:
        return f"virtualenv: {venv}"
    for marker in ("/.dockerenv", "/run/.containerenv"):
        if Path(marker).exists():
            return f"container: {marker}"
    try:
        cgroup = Path("/proc/1/cgroup").read_text(encoding="utf-8")
        if any(k in cgroup for k in ("docker", "containerd", "kubepods", "podman", "lxc")):
            return "container: cgroup"
    except OSError:
        pass
    return None


def current_depth() -> int:
    try:
        return max(0, int(os.environ.get(DEPTH_ENV, "0")))
    except ValueError:
        return 0


def preflight(
    config: Config,
    spec: dict[str, Any],
    *,
    check_binaries: bool = True,
) -> list[str]:
    """Return every safety violation; an empty list means cleared to spawn."""
    ccfg = config.coordinate_cfg
    safety = ccfg.get("safety", {})
    errors: list[str] = []

    depth = current_depth()
    max_depth = int(safety.get("max_depth", 1))
    if depth >= max_depth:
        errors.append(
            f"nested coordination depth {depth} reached the limit of {max_depth} "
            f"({DEPTH_ENV} is set by a parent run); raise "
            "coordinate.safety.max_depth only if you really want agents "
            "spawning agents"
        )

    if safety.get("require_linux", True) and not sys.platform.startswith("linux"):
        errors.append(
            f"coordinate is supported on Linux only (this is {sys.platform!r}); "
            "override with coordinate.safety.require_linux: false"
        )
    if safety.get("require_repo_setup", True) and not repo_is_setup(config):
        errors.append(
            "repository is not set up — agents may modify this folder only in a "
            ".git checkout with pigeon initialized (run `git init` and `pigeon init`)"
        )
    if safety.get("require_isolated_env_for_packages", True):
        mutating = [t["id"] for t in spec["tasks"] if t.get("mutates_packages")]
        if mutating and isolated_env() is None:
            errors.append(
                f"task(s) {', '.join(mutating)} declare mutates_packages, but no conda env, "
                "virtualenv, or container was detected — package changes never run against "
                "the system interpreter"
            )

    runners = ccfg["runners"]
    for task in spec["tasks"]:
        name = task["runner"]
        template = runners.get(name)
        if not template:
            errors.append(
                f"task {task['id']!r}: unknown runner {name!r} "
                f"(configured: {', '.join(sorted(runners))})"
            )
            continue
        if check_binaries and shutil.which(template[0]) is None:
            errors.append(f"task {task['id']!r}: runner binary not found on PATH: {template[0]!r}")
        # A {model} placeholder MUST resolve, or _fill leaves it literal and the
        # child CLI receives a bogus '{model}' argument (the unmatched-placeholder
        # trap that motivates this whole feature).
        if any("{model}" in arg for arg in template) and not task.get("model"):
            errors.append(
                f"task {task['id']!r}: runner {name!r} template contains '{{model}}' "
                "but no model resolved — set 'model:' or 'model_pool:' on the task"
            )

    isolated = [t["id"] for t in spec["tasks"] if t.get("isolation") == "worktree"]
    if isolated:
        if shutil.which("git") is None:
            errors.append("worktree isolation needs git on PATH "
                          f"(tasks: {', '.join(isolated)})")
        elif _git(config.root, "rev-parse", "HEAD", check=False).returncode != 0:
            errors.append(
                "worktree isolation needs a git repository with at least one "
                f"commit (tasks: {', '.join(isolated)})"
            )
    return errors


def model_warnings(config: Config, spec: dict[str, Any]) -> list[str]:
    """Non-blocking advisories about model wiring (the inverse of the preflight
    error): a task resolved a model but its runner template has no ``{model}``
    placeholder to receive it, so the model is silently ignored."""
    runners = config.coordinate_cfg["runners"]
    warnings: list[str] = []
    for task in spec["tasks"]:
        template = runners.get(task["runner"]) or []
        if task.get("model") and not any("{model}" in arg for arg in template):
            warnings.append(
                f"task {task['id']!r} resolved model {task['model']!r} but runner "
                f"{task['runner']!r} has no '{{model}}' placeholder — model ignored"
            )
    return warnings


def receives_warnings(config: Config, spec: dict[str, Any]) -> list[str]:
    """The worktree paradox (DESIGN §2d): a task that ``receives:`` from a
    worktree-isolated upstream. Only that upstream's *materialized diff* and
    *harvested handoffs* land on the shared tree; any other file artifact it
    produced lives on a throwaway branch and will not resolve. Non-blocking."""
    by_id = {t["id"]: t for t in spec["tasks"]}
    warnings: list[str] = []
    for task in spec["tasks"]:
        if not task.get("receives"):
            continue
        wt = [n for n in (task.get("needs") or [])
              if (by_id.get(n) or {}).get("isolation") == "worktree"]
        if wt:
            warnings.append(
                f"task {task['id']!r} receives from worktree-isolated upstream(s) "
                f"{', '.join(wt)} — only their materialized diff and harvested "
                "handoffs live on the shared tree; other file artifacts won't resolve"
            )
    return warnings


def crew_skill_warnings(config: Config, spec: dict[str, Any]) -> list[str]:
    """Non-blocking advisories for crew skill names that are neither a
    canonical playbook nor an allow-listed adopted asset.  The run proceeds;
    the runner may still find the skill via its own search path, but pigeon
    cannot verify it.  Use `pigeon adopt --allow <name>` to clear the warning.

    Deduplicates per unique skill name (one advisory regardless of how many
    tasks reference it).  Names in ``coordinate.assume_known_skills`` are
    treated as runner-native and suppressed without adoption.
    """
    from .. import adopt as adopt_mod
    from .. import skills as skills_mod

    assume_known = set(config.coordinate_cfg.get("assume_known_skills") or [])
    warnings: list[str] = []
    seen_unknown: set[str] = set()

    for task in spec.get("tasks", []):
        crew = task.get("crew") or {}
        skill_names = list(crew.get("skills", []))
        for member in crew.get("subagents", []):
            if member.get("skill"):
                skill_names.append(member["skill"])
        for sname in skill_names:
            if sname in assume_known:
                continue
            if skills_mod.resolve_skill(config, sname) is not None:
                continue
            if adopt_mod.check_allow(sname, config):
                continue
            if sname in seen_unknown:
                continue
            seen_unknown.add(sname)
            warnings.append(
                f"crew skill {sname!r} is neither a playbook "
                "nor an allow-listed adopted asset — run `pigeon adopt --allow` "
                "to reference it in a crew"
            )

    return warnings


def mcp_warnings(config: Config, spec: dict[str, Any]) -> list[str]:
    """Thin MCP pass-through validation: a task may declare ``mcp: [names]`` it
    expects; warn (non-blocking, deduped) when a declared server is not in the
    discovered MCP inventory. Validation ONLY — pigeon never connects to, proxies,
    or orchestrates MCP; it just confirms the server is configured somewhere it
    can see (the adopt ``mcp`` sources)."""
    from .. import adopt as adopt_mod

    available: set[str] | None = None
    warnings: list[str] = []
    seen: set[str] = set()
    for task in spec.get("tasks", []):
        for name in (task.get("mcp") or []):
            if available is None:                     # parse configs once, lazily
                available = adopt_mod.discovered_mcp_names(config)
            if name in available or name in seen:
                continue
            seen.add(name)
            warnings.append(
                f"task {task['id']!r}: MCP server {name!r} is declared but not "
                "configured (not in the adopt mcp sources) — coordinate cannot "
                "pass it through"
            )
    return warnings


def telemetry_warnings(config: Config, spec: dict[str, Any],
                       run_telemetry: bool = False) -> list[str]:
    """Telemetry was requested (run-level ``--telemetry`` or a task's
    ``telemetry: true``) for a runner with no ``telemetry_flags`` — so its CLI
    emits no usage report and the child's tokens/cost are recorded as zero.
    Surface that instead of silently measuring nothing (a known gap beats a
    confident zero): the operator must add the runner's real usage flag, or
    accept it is unmeasured. One advisory per distinct runner."""
    tflags = config.coordinate_cfg.get("telemetry_flags", {})
    warnings: list[str] = []
    seen: set[str] = set()
    for task in spec["tasks"]:
        runner = task["runner"]
        if runner in seen:
            continue
        if task.get("telemetry", run_telemetry) and not tflags.get(runner):
            seen.add(runner)
            warnings.append(
                f"runner {runner!r}: telemetry requested but no 'telemetry_flags' "
                "configured — its child tokens/cost are recorded as zero"
            )
    return warnings


def _resolve_receives(config: Config, task: dict[str, Any],
                      *, quiet: bool = False) -> list[str]:
    """Expand a task's ``receives:`` globs into ``repo://`` pointers for files
    that exist *now*, dropping (with a warning) any pattern that matches none.

    The whole point of deferring this to spawn time: a glob like
    ``repo://.pigeon/coordinate/diffs/<run>/*.diff`` is empty up-front and
    populated only once the upstream tasks have run. ``quiet`` suppresses the
    no-match warning for the up-front *speculative* pass (which runs before any
    upstream has produced anything, so a miss there is expected, not a failure)
    — only the real spawn-time resolution should warn."""
    out: list[str] = []
    for pat in (task.get("receives") or []):
        rel = pat[len("repo://"):] if pat.startswith("repo://") else pat
        files = sorted(m for m in config.root.glob(rel) if m.is_file())
        if not files:
            if not quiet:
                with _print_lock:
                    print(f"[{task['id']}] receives: nothing matched {pat!r} — skipped",
                          file=sys.stderr)
            continue
        out += [f"repo://{m.relative_to(config.root)}" for m in files]
    return out


# ----------------------------------------------------------------------- plan
def compute_waves(tasks: list[dict[str, Any]]) -> list[list[str]]:
    """Topological waves: wave N holds tasks whose needs are met by waves < N.

    This is the run's *shape* — what executes together, what gates what —
    independent of parallel_limit (which only throttles within a wave).
    """
    deps = {t["id"]: set(t.get("needs") or []) for t in tasks}
    waves: list[list[str]] = []
    placed: set[str] = set()
    remaining = dict(deps)
    while remaining:
        ready = sorted(tid for tid, need in remaining.items() if need <= placed)
        if not ready:  # load_tasks rejects cycles; defensive flush
            ready = sorted(remaining)
        waves.append(ready)
        placed.update(ready)
        for tid in ready:
            remaining.pop(tid)
    return waves


def longest_chain(tasks: list[dict[str, Any]]) -> list[str]:
    """The longest dependency chain — the run's critical path by hops."""
    deps = {t["id"]: set(t.get("needs") or []) for t in tasks}
    best: dict[str, tuple[int, list[str]]] = {}
    for wave in compute_waves(tasks):
        for tid in wave:
            prev: tuple[int, list[str]] = (0, [])
            for need in deps[tid]:
                if need in best and best[need][0] > prev[0]:
                    prev = best[need]
            best[tid] = (prev[0] + 1, prev[1] + [tid])
    return max(best.values(), key=lambda v: v[0])[1] if best else []


def _task_badges(task: dict[str, Any]) -> str:
    badges = [task["runner"]]
    if task.get("model"):
        badges.append(f"model={task['model']}")
    if task.get("model_pool"):
        badges.append(f"pool={task['model_pool']}")
    if task.get("receives"):
        badges.append(f"receives×{len(task['receives'])}")
    if task.get("reentry"):
        badges.append(f"reentry≤{int(task.get('max_reentry', 2))}")
    crew = task.get("crew") or {}
    n_crew = len(crew.get("subagents", [])) + len(crew.get("skills", []))
    if n_crew:
        badges.append(f"crew×{n_crew}")
    if task.get("readonly"):
        badges.append("readonly")
    # Effective isolation: a readonly task with no explicit isolation defaults
    # to a throwaway worktree (see _norm_task); badge "worktree" only when the
    # task will actually run in one — an explicit `isolation: shared` must not.
    eff_isolation = task.get("isolation") or ("worktree" if task.get("readonly") else "shared")
    if eff_isolation == "worktree":
        badges.append("worktree")
    for flag in ("pack", "telemetry", "mutates_packages"):
        if task.get(flag):
            badges.append(flag)
    if task.get("needs"):
        badges.append("← " + ",".join(task["needs"]))
    return " · ".join(badges)


def plan(config: Config, spec: dict[str, Any]) -> dict[str, Any]:
    """A read-only preview of a run: shape, badges, preflight verdict.

    Nothing is written — no handoffs, no run manifest. This is the
    look-before-you-dispatch view (think /workflows, before the fan-out).
    """
    tasks = spec["tasks"]
    ccfg = config.coordinate_cfg
    return {
        "sid": spec["sid"],
        "tasks": {
            t["id"]: {
                "runner": t["runner"],
                **({"model": t["model"]} if t.get("model") else {}),
                "needs": list(t.get("needs") or []),
                "isolation": t.get("isolation") or "shared",
                "pack": bool(t.get("pack")),
                "telemetry": bool(t.get("telemetry")),
                "mutates_packages": bool(t.get("mutates_packages")),
                "readonly": bool(t.get("readonly")),
                **({"crew": t["crew"]} if t.get("crew") else {}),
            }
            for t in tasks
        },
        "waves": compute_waves(tasks),
        "longest_chain": longest_chain(tasks),
        "parallel_limit": int(ccfg["parallel_limit"]),
        "depth": current_depth(),
        "isolated_env": isolated_env(),
        "budget": ccfg.get("budget", {}),
        "preflight_errors": preflight(config, spec),
        "crew_skill_warnings": crew_skill_warnings(config, spec),
        "mcp_warnings": mcp_warnings(config, spec),
    }


def format_plan(p: dict[str, Any], tasks: list[dict[str, Any]]) -> str:
    by_id = {t["id"]: t for t in tasks}
    lines = [
        f"plan: {p['sid']} — {len(by_id)} task(s), "
        f"{len(p['waves'])} wave(s), parallel_limit {p['parallel_limit']}, "
        f"depth {p['depth']}",
    ]
    for i, wave in enumerate(p["waves"], 1):
        for j, tid in enumerate(wave):
            prefix = f"  wave {i}  " if j == 0 else "          "
            lines.append(f"{prefix}{tid}  [{_task_badges(by_id[tid])}]")
    if len(p["longest_chain"]) > 1:
        lines.append("  longest chain: " + " → ".join(p["longest_chain"]))
    budget = {k: v for k, v in (p.get("budget") or {}).items() if v}
    if budget:
        lines.append("  budget: " + ", ".join(f"{k}={v}" for k, v in budget.items()))
    if p["preflight_errors"]:
        lines.append("  preflight: REFUSED")
        lines += [f"    ✗ {e}" for e in p["preflight_errors"]]
    else:
        lines.append("  preflight: ok")
    for w in p.get("crew_skill_warnings", []):
        lines.append(f"  warning: {w}")
    for w in p.get("mcp_warnings", []):
        lines.append(f"  warning: {w}")
    return "\n".join(lines)


# --------------------------------------------------------------- run manifest
def _utcnow() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


# Scalar fields worth carrying into the event stream (events are the
# primary object; logs and the full manifest are the drill-down).
_EVENT_FIELDS = ("exit_code", "duration_s", "output_lines", "skipped_because",
                 "return_handoff", "branch", "model")


class RunRecorder:
    """Live run manifest under ``coordinate/runs/<sid>-<n>.json``.

    The manifest is rewritten atomically (tmp + rename) on every state change,
    so ``pigeon status`` — or an MCP ``coordinate_status`` call — can poll it
    while agents are still executing. Like handoffs, run files are append-only:
    a new coordination run never rewrites a previous run's manifest.

    Every state change is also appended to ``coordinate/events/<run_id>.jsonl``
    — the chronological record the manifest's last-write-wins shape cannot
    hold. ``pigeon runs --timeline`` reads it back.
    """

    def __init__(self, config: Config, sid: str, tasks: list[dict[str, Any]],
                 **meta: Any) -> None:
        runs_dir = config.coordinate_runs_dir
        runs_dir.mkdir(parents=True, exist_ok=True)
        highest = 0
        for child in runs_dir.glob("*.json"):
            stem = child.stem
            if stem.startswith(sid + "-") and stem[len(sid) + 1:].isdigit():
                highest = max(highest, int(stem[len(sid) + 1:]))
        # atomic claim: concurrent coordinators can never share a run id
        self.path = ho.claim_path(
            runs_dir, lambda n, b=highest: f"{sid}-{b + n}.json")
        self.events_path = config.coordinate_events_dir / f"{sid}-{highest + 1}.jsonl"
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.data: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "run_id": self.path.stem,
            "sid": sid,
            "status": "running",
            "started_at": _utcnow(),
            "finished_at": None,
            **meta,
            "tasks": {
                t["id"]: {
                    "runner": t["runner"],
                    "status": "queued",
                    "doing": t.get("doing", ""),
                    **({"model": t["model"]} if t.get("model") else {}),
                    **({"needs": list(t["needs"])} if t.get("needs") else {}),
                    **({"crew": t["crew"]} if t.get("crew") else {}),
                }
                for t in tasks
            },
        }
        self._flush()
        self._emit("run.started", tasks=[t["id"] for t in tasks])

    def _emit(self, event: str, **fields: Any) -> None:
        rec = {"ts": _utcnow(), "run_id": self.data["run_id"],
               "sid": self.data["sid"], "event": event, **fields}
        with self.events_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")

    def event(self, name: str, **fields: Any) -> None:
        """Append a free-form event (e.g. handoff.dispatched) to the stream."""
        self._emit(name, **fields)

    def _flush(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(self.data, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(tmp, self.path)

    def task(self, task_id: str, **fields: Any) -> None:
        with self._lock:
            self.data["tasks"][task_id].update(fields)
            self._flush()
        if "status" in fields:
            extras = {k: fields[k] for k in _EVENT_FIELDS if k in fields}
            telemetry = fields.get("telemetry")
            if telemetry:
                extras["tokens"] = telemetry.get("total_tokens")
                if "total_cost_usd" in telemetry:
                    extras["cost_usd"] = telemetry["total_cost_usd"]
            self._emit(f"task.{fields['status']}", task=task_id,
                       runner=self.data["tasks"][task_id].get("runner"), **extras)

    def finish(self, status: str, **fields: Any) -> None:
        with self._lock:
            self.data.update(fields)
            self.data["status"] = status
            self.data["finished_at"] = _utcnow()
            self._flush()
        self._emit(f"run.{status}", summary=fields.get("summary"))


# ------------------------------------------------------------------ execution
def _fill(template: str, subs: dict[str, str]) -> str:
    """Substitute ``{key}`` placeholders without choking on stray braces."""
    out = template
    for key, val in subs.items():
        out = out.replace("{" + key + "}", val)
    return out


def _build_command(
    task: dict[str, Any],
    config: Config,
    handoff_rel: str,
    sid: str,
    *,
    skip_permissions: bool,
    telemetry: bool = False,
) -> list[str]:
    ccfg = config.coordinate_cfg
    subs = {
        "handoff": handoff_rel,
        "root": str(config.root),
        "task_id": task["id"],
        "sid": sid,
    }
    prompt = _fill(task.get("prompt") or DEFAULT_PROMPT, subs)
    if task.get("crew"):
        playbooks_rel = str(config.memory_dir.relative_to(config.root) / "playbooks")
        prompt += " " + crew_instructions(task["crew"], playbooks_rel)
    subs["prompt"] = prompt
    # {model} is substituted ONLY when a model resolved (direct `model:` or a
    # `model_pool:`). Absent that, it is never added to subs, so a template with
    # no {model} is byte-identical to today and a stray {model} is caught by
    # preflight rather than silently reaching the CLI as a literal arg.
    if task.get("model"):
        subs["model"] = task["model"]
    cmd = [_fill(arg, subs) for arg in ccfg["runners"][task["runner"]]]
    if skip_permissions:
        cmd += ccfg.get("skip_permissions_flags", {}).get(task["runner"], [])
    if task.get("telemetry", telemetry):
        cmd += ccfg.get("telemetry_flags", {}).get(task["runner"], [])
    return cmd


# ------------------------------------------------------------------ worktrees
def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed (exit {proc.returncode}): "
            + (proc.stderr.strip() or proc.stdout.strip())
        )
    return proc


# git mutates shared lock files (index.lock, refs); concurrent worktree
# add/remove from worker threads must be serialized within this process.
# Worktree teardown and `cleanup` live in `worktree.py`; they reach this lock
# and `_git` back through the package so the `coordinate._git` patch point keeps
# governing every git call.
_GIT_LOCK = threading.Lock()


# --------------------------------------------------------------------- budget
class BudgetTracker:
    """Thread-safe spend ledger fed by child telemetry.

    Ceilings are *hard*: once a measured total crosses a limit, the scheduler
    launches nothing new (tasks already running finish). Without telemetry a
    task contributes nothing — budgets only bind what can be measured.
    """

    def __init__(self, max_tokens: int | None = None, max_usd: float | None = None):
        self.max_tokens = max_tokens
        self.max_usd = max_usd
        self.tokens = 0
        self.usd = 0.0
        self._lock = threading.Lock()

    def add(self, tokens: int = 0, usd: float = 0.0) -> None:
        with self._lock:
            self.tokens += int(tokens)
            self.usd += float(usd)

    def exhausted(self) -> str | None:
        with self._lock:
            if self.max_tokens is not None and self.tokens >= self.max_tokens:
                return f"token budget exhausted ({self.tokens}/{self.max_tokens})"
            if self.max_usd is not None and self.usd >= self.max_usd:
                return f"cost budget exhausted (${round(self.usd, 4)}/${self.max_usd})"
        return None

    def as_dict(self) -> dict[str, Any]:
        with self._lock:
            out: dict[str, Any] = {"spent_tokens": self.tokens,
                                   "spent_usd": round(self.usd, 6)}
            if self.max_tokens is not None:
                out["max_tokens"] = self.max_tokens
            if self.max_usd is not None:
                out["max_usd"] = self.max_usd
            return out


# Always forwarded even under an allowlist: the child cannot function
# without a sane base environment.
_ENV_BASELINE = ("PATH", "HOME", "LANG", "LC_ALL", "TERM", "USER", "SHELL",
                 "TMPDIR", "VIRTUAL_ENV", "CONDA_PREFIX", "CONDA_DEFAULT_ENV")


def _child_env(config: Config) -> dict[str, str]:
    """Child environment: full inherit by default, allowlist when configured.

    ``coordinate.env_allowlist`` (a list of names) turns on strict mode: only
    those variables plus a functional baseline reach the agents — secrets in
    the operator's shell (cloud keys, tokens) stay out of reach of spawned
    agents. Default None = inherit everything (agents usually need their own
    API keys; opt in deliberately).
    """
    allowlist = config.coordinate_cfg.get("env_allowlist")
    if allowlist is None:
        env = dict(os.environ)
    else:
        keep = set(allowlist) | set(_ENV_BASELINE)
        env = {k: v for k, v in os.environ.items() if k in keep}
    env[DEPTH_ENV] = str(current_depth() + 1)
    return env


def _seed_opencode_creds(cmd: list[str]) -> None:
    """Best-effort: seed opencode credentials into a runner's per-runner
    ``XDG_DATA_HOME`` so a fresh isolated data dir is authenticated.

    The opencode-routed runners embed ``env XDG_DATA_HOME=/tmp/pigeon-oc/<runner>``
    in their argv so each gets its own opencode SQLite DB (avoiding the shared-DB
    lock that stalled the army). But opencode reads credentials from
    ``$XDG_DATA_HOME/opencode/auth.json``; a fresh per-runner dir would be
    unauthenticated. Copy ``auth.json`` + ``account.json`` from the user's real
    opencode data dir into it. NEVER raises — seeding must not fail a run, so the
    whole body is guarded (a malformed XDG path or odd ``cmd`` shape is ignored).
    """
    try:
        if "opencode" not in cmd:
            return
        target_root = next(
            (a.split("=", 1)[1] for a in cmd if a.startswith("XDG_DATA_HOME=")),
            None,
        )
        if not target_root:
            return
        src = Path(os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))) / "opencode"
        dst = Path(target_root) / "opencode"
        dst.mkdir(parents=True, exist_ok=True)
        for name in ("auth.json", "account.json"):
            s = src / name
            if s.is_file():
                shutil.copy2(s, dst / name)
    except Exception:
        pass


def _opencode_permission_env(cmd: list[str], config: Config) -> dict[str, str]:
    """Grant an opencode runner read access to the main repo tree.

    opencode (non-interactive ``run``) auto-rejects reads outside its cwd. A
    worktree-isolated task's cwd is the throwaway worktree, but its handoff and
    any ``receives:`` artifacts live on the MAIN tree (``.pigeon/`` is gitignored,
    so a fresh worktree does not contain them) — so an opencode runner can't read
    them and dies before starting. ``OPENCODE_PERMISSION`` (deep-merged last by
    opencode) flips the ``external_directory`` permission to ``allow`` for the
    repo root, scoped to reads only. Empty for non-opencode runners — claude/agy
    reach external paths via ``--dangerously-skip-permissions`` instead.
    """
    if "opencode" not in cmd:
        return {}
    return {
        "OPENCODE_PERMISSION": json.dumps(
            {"external_directory": {f"{config.root}/**": "allow"}}
        )
    }


def _resolve_timeouts(
    ccfg: dict[str, Any], runner: str
) -> tuple[float | None, float | None, float]:
    """Resolve (idle_s, hard_s, grace_s) for a runner.

    Resolution order: per-runner override → global → (None, None, 30).
    A per-runner ``null`` value explicitly masks a global setting.
    """
    global_idle: float | None = ccfg.get("idle_timeout_s")
    global_hard: float | None = ccfg.get("hard_cap_s")
    global_grace: float = ccfg.get("grace_kill_s", 30)
    per: dict[str, Any] = (ccfg.get("timeouts") or {}).get(runner, {})
    # ``in`` check distinguishes "key absent" (inherit global) from "key=null" (mask it)
    idle = per["idle_timeout_s"] if "idle_timeout_s" in per else global_idle
    hard = per["hard_cap_s"]     if "hard_cap_s"     in per else global_hard
    grace = per["grace_kill_s"]  if "grace_kill_s"   in per else global_grace
    return idle, hard, float(grace)


def _classify_status(rc: int, kill_reason: str | None) -> str:
    """Map (rc, kill_reason) → task status string.

    NEVER branches on rc == 124 (Ground-truth #2: pigeon kills yield -9/-15).
    """
    if rc == 0:
        return "exited"
    if kill_reason == "idle":
        return "timed_out_idle"
    if kill_reason == "hard":
        return "timed_out"
    return "failed"


def _kill(proc: subprocess.Popen, pgid: int, grace_s: float) -> None:
    """SIGTERM the process group, wait up to grace_s for the leader, then SIGKILL
    the whole group — reaping grandchildren even if the leader already exited.

    ``pgid`` is the child's process-group id, cached by the caller. With
    ``start_new_session=True`` it equals ``proc.pid``, so we never call
    ``os.getpgid`` on a pid that may already be reaped (which would raise and
    leak orphaned grandchildren).
    """
    try:
        os.killpg(pgid, signal.SIGTERM)
    except (ProcessLookupError, OSError):
        pass
    deadline = time.monotonic() + grace_s
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            break
        time.sleep(0.05)
    try:
        # SIGKILL the group unconditionally — even if the leader exited, a
        # grandchild that ignored SIGTERM is still in the group and must be reaped.
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, OSError):
        pass


def _run_task(
    task_id: str,
    cmd: list[str],
    config: Config,
    log_path: Path,
    recorder: RunRecorder | None = None,
    *,
    sid: str = "",
    runner: str = "",
    model: str = "",
    cwd: Path | None = None,
    budget: BudgetTracker | None = None,
    procs: dict[str, subprocess.Popen] | None = None,
) -> tuple[int, str | None]:
    """Spawn one runner; prefix-stream merged stdout/stderr and tee to a log.

    Returns ``(rc, kill_reason)`` where ``kill_reason`` is ``"idle"`` or
    ``"hard"`` when pigeon killed the process, ``None`` otherwise.

    The tail of the output is mined for a usage report; when found, the
    child's *measured* token consumption is written to the run manifest and
    appended to metrics.jsonl as an ``agent_run`` event (baseline/saved are 0:
    these tokens were consumed by the agent, not transmitted by pigeon —
    ``by_kind`` in the metrics report keeps the two ledgers separate).
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    last_output = started
    kill_reason: str | None = None
    if recorder:
        recorder.task(task_id, status="running", started_at=_utcnow())
    lines = 0
    tail: deque[str] = deque(maxlen=200)
    idle_s, hard_s, grace_s = _resolve_timeouts(config.coordinate_cfg, runner)
    with log_path.open("w", encoding="utf-8") as log:
        log.write("$ " + " ".join(shlex.quote(c) for c in cmd) + "\n")
        try:
            _seed_opencode_creds(cmd)
            env = _child_env(config)
            env.update(_opencode_permission_env(cmd, config))
            proc = subprocess.Popen(
                cmd, cwd=cwd or config.root,
                stdin=subprocess.DEVNULL,  # headless batch: never inherit pigeon's
                                           # stdin. Some agent CLIs (e.g. agy) block
                                           # reading stdin for a "next message" and
                                           # never exit; DEVNULL gives immediate EOF.
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                bufsize=0,          # unbuffered BINARY: select() and readline()
                env=env,            # see the same bytes (a buffered text wrapper
                start_new_session=True,   # can hide data select never reports)
            )
        except OSError as exc:
            line = f"failed to spawn: {exc}"
            log.write(line + "\n")
            with _print_lock:
                print(f"[{task_id}] {line}")
            if recorder:
                recorder.task(task_id, status="spawn-failed", exit_code=127,
                              finished_at=_utcnow())
            return 127, None
        if procs is not None:
            procs[task_id] = proc
        assert proc.stdout is not None
        # Read raw OS-level chunks, not readline(): select() only guarantees ≥1
        # byte is ready, not a whole line, so readline() would BLOCK on a
        # partial-line-then-hang and defeat both timers. Chunked os.read() also
        # avoids the byte-by-byte syscall overhead of a bufsize=0 readline().
        fd_int = proc.stdout.fileno()
        pgid = proc.pid                 # == process-group id (start_new_session)
        buf = b""

        def _emit(text: str) -> None:
            nonlocal lines
            lines += 1
            tail.append(text)
            log.write(text + "\n")
            with _print_lock:
                print(f"[{task_id}] {text}")

        timed = bool(idle_s or hard_s)
        while True:
            if timed:
                now = time.monotonic()
                budget_idle = (idle_s - (now - last_output)) if idle_s else None
                budget_hard = (hard_s - (now - started))     if hard_s else None
                wait_s = min(w for w in (budget_idle, budget_hard, 1.0)
                             if w is not None)
                ready, _, _ = _select.select([fd_int], [], [], max(0.05, wait_s))
                now = time.monotonic()
                if idle_s and (now - last_output) >= idle_s:
                    kill_reason = "idle"
                    _kill(proc, pgid, grace_s)
                    break
                if hard_s and (now - started) >= hard_s:
                    kill_reason = "hard"
                    _kill(proc, pgid, grace_s)
                    break
                if not ready:
                    continue
            try:
                chunk = os.read(fd_int, 65536)   # ready ⇒ returns now (≥1 byte or b"" at EOF)
            except OSError:
                break
            if not chunk:               # EOF — child closed its stream
                break
            last_output = time.monotonic()
            buf += chunk
            while b"\n" in buf:
                rawline, buf = buf.split(b"\n", 1)
                _emit(rawline.decode("utf-8", errors="replace").rstrip("\r"))
        if buf:                         # flush a trailing partial line at EOF
            _emit(buf.decode("utf-8", errors="replace").rstrip("\r"))
        # The caps must bound TOTAL subprocess lifetime, not just time spent in
        # the read loop: a child that closes stdout+stderr then keeps running
        # breaks the loop on EOF with no kill, leaving a bare proc.wait() to
        # block forever. Re-apply the same idle/hard budget to the final wait.
        while timed and kill_reason is None and proc.poll() is None:
            now = time.monotonic()
            if idle_s and (now - last_output) >= idle_s:
                kill_reason = "idle"
                _kill(proc, pgid, grace_s)
            elif hard_s and (now - started) >= hard_s:
                kill_reason = "hard"
                _kill(proc, pgid, grace_s)
            else:
                try:
                    proc.wait(timeout=0.1)
                except subprocess.TimeoutExpired:
                    pass
        rc = proc.wait()
        if procs is not None:
            procs.pop(task_id, None)
        log.write(f"# exit {rc}\n")
    telemetry = _extract_telemetry("\n".join(tail))
    if telemetry and budget:
        budget.add(telemetry["total_tokens"], telemetry.get("total_cost_usd", 0.0))
    if telemetry:
        event: dict[str, Any] = {
            "kind": "agent_run", "sid": sid, "task": task_id, "runner": runner,
            "actual_tokens": telemetry["total_tokens"],
            "baseline_tokens": 0, "saved_tokens": 0,
            "usage": telemetry["usage"],
        }
        if model:
            event["model"] = model
        if "total_cost_usd" in telemetry:
            event["cost_usd"] = telemetry["total_cost_usd"]
        tokens.record(config, event)
        cost = f" cost=${telemetry['total_cost_usd']}" if "total_cost_usd" in telemetry else ""
        with _print_lock:
            print(f"[{task_id}] telemetry: {telemetry['total_tokens']} tokens (measured){cost}")
    if recorder:
        fields: dict[str, Any] = dict(
            status=_classify_status(rc, kill_reason),
            exit_code=rc,
            finished_at=_utcnow(),
            duration_s=round(time.monotonic() - started, 3),
            output_lines=lines,
        )
        if kill_reason:
            fields["kill_reason"] = kill_reason
        if telemetry:
            fields["telemetry"] = telemetry
        recorder.task(task_id, **fields)
    return rc, kill_reason


def run_coordinate(
    tasks_path: Path,
    config: Config,
    parallel_limit: int | None = None,
    log_dir: Path | None = None,
    *,
    skip_permissions: bool = False,
    dry_run: bool = False,
    telemetry: bool = False,
    budget_tokens: int | None = None,
    budget_usd: float | None = None,
) -> int:
    """Coordinate a tasks file end to end. 0 = all green, 1 = failures, 2 = refused."""
    spec = load_tasks(Path(tasks_path),
                      default_runner=config.coordinate_cfg.get("default_runner"),
                      model_pools=config.coordinate_cfg.get("model_pools"))
    sid: str = spec["sid"]
    tasks: list[dict[str, Any]] = spec["tasks"]

    ccfg = config.coordinate_cfg
    limit = max(1, parallel_limit or int(ccfg["parallel_limit"]))
    log_root = Path(log_dir).resolve() if log_dir else config.coordinate_log_dir
    iso = isolated_env()
    budget_cfg = ccfg.get("budget", {})
    budget = BudgetTracker(
        max_tokens=budget_tokens if budget_tokens is not None else budget_cfg.get("tokens"),
        max_usd=budget_usd if budget_usd is not None else budget_cfg.get("usd"),
    )
    recorder = RunRecorder(
        config, sid, tasks,
        tasks_file=str(tasks_path),
        parallel_limit=limit,
        skip_permissions=skip_permissions,
        dry_run=dry_run,
        telemetry=telemetry,
        isolated_env=iso,
        depth=current_depth(),
    )

    errors = preflight(config, spec, check_binaries=not dry_run)
    if errors:
        for err in errors:
            print(f"preflight: {err}", file=sys.stderr)
        print("coordinate: refusing to spawn agents (see preflight errors)", file=sys.stderr)
        recorder.finish("refused", preflight_errors=errors)
        return 2

    # U5 hygiene: clear git's stale worktree bookkeeping left by prior crashed
    # runs (a SIGKILL'd coordinator never tears its worktrees down) before we
    # register new ones. Idempotent and safe under concurrent runs — prune only
    # drops entries whose working dir is already gone, never a live one.
    if not dry_run and any(t.get("isolation") == "worktree" for t in tasks):
        with _GIT_LOCK:
            # --expire=now: prune even *recently* orphaned entries; plain prune
            # honors gc.worktreePruneExpire (~3 months) and would skip a run
            # that crashed minutes ago — exactly the case we want cleared.
            _git(config.root, "worktree", "prune", "--expire=now", check=False)

    for warning in (model_warnings(config, spec) + receives_warnings(config, spec)
                    + telemetry_warnings(config, spec, run_telemetry=telemetry)
                    + crew_skill_warnings(config, spec)
                    + mcp_warnings(config, spec)):
        print(f"coordinate: warning: {warning}", file=sys.stderr)

    print(
        f"coordinate: run={recorder.data['run_id']} tasks={len(tasks)} "
        f"parallel_limit={limit} isolated_env={iso or 'none'} "
        f"skip_permissions={skip_permissions}"
    )
    waves = compute_waves(tasks)
    if len(tasks) > 1:
        print("plan: " + "  →  ".join("[" + " ".join(w) + "]" for w in waves))

    before = {p.name for p in config.handoffs_dir.glob("*.json")} \
        if config.handoffs_dir.is_dir() else set()

    # One handoff per task: validated on write, token-accounted, pointers only.
    # A `receives:` task DEFERS its single (append-only) write to spawn, when
    # its cross-wave pointers actually exist on disk (see _spawn_prepare).
    def _make_handoff(task: dict[str, Any], injected: list[str], *,
                      do_pack: bool,
                      salvaged_upstream: list[str] | None = None) -> Any:
        artifacts = list(task.get("artifacts") or [])
        if do_pack and task.get("pack"):
            from .. import pack as pack_mod  # lazy: avoids a module cycle
            bundle = pack_mod.pack(config, task["doing"],
                                   max_tokens=int(task.get("pack_max_tokens", 4000)))
            artifacts.append(f"repo://{bundle['path']}")
            print(f"[{task['id']}] packed context: {bundle['path']} "
                  f"({bundle['tokens']['actual_tokens']} tokens)")
        artifacts += injected
        return ho.build_handoff(
            sid=sid,
            frm=COORDINATOR,
            to=task["id"],
            done=list(task.get("done") or []),
            doing=task["doing"],
            artifacts=artifacts or None,
            decisions=task.get("decisions") or None,
            rag=task.get("rag") or None,
            constraints={**SAFETY_CONSTRAINTS,
                         **(_readonly_fs(task) if task.get("readonly") else {}),
                         **(task.get("constraints") or {})},
            crew=task.get("crew") or None,
            context_ref=task.get("context_ref", "manifest@HEAD"),
            salvaged_upstream=salvaged_upstream or None,
        )

    def _write_handoff_cmd(task: dict[str, Any],
                           injected: list[str],
                           salvaged_upstream: list[str] | None = None,
                           ) -> tuple[list[str], str]:
        handoff = _make_handoff(task, injected, do_pack=True,
                                salvaged_upstream=salvaged_upstream)
        path = ho.write_handoff(handoff, config)
        rel = str(path.relative_to(config.root))
        ev = tokens.account_handoff(config, handoff, path=rel)
        print(f"[{task['id']}] handoff {rel} "
              f"(tokens actual={ev['actual_tokens']} saved={ev['saved_tokens']})")
        # Isolated tasks read the handoff from the *main* checkout: handoffs
        # are gitignored, so a fresh worktree does not contain them.
        handoff_ref = str(path) if task.get("isolation") == "worktree" else rel
        cmd = _build_command(task, config, handoff_ref, sid,
                             skip_permissions=skip_permissions, telemetry=telemetry)
        return cmd, rel

    def _log_paths(task: dict[str, Any]) -> tuple[Path, str]:
        lp = log_root / f"{sid}-{task['id']}.log"
        lr = (str(lp.relative_to(config.root))
              if lp.is_relative_to(config.root) else str(lp))
        return lp, lr

    # Phase 3: tasks that need a worktree-isolated upstream are deferred at spawn
    # so salvage_diff pointers can be injected once we know which upstreams were salvaged.
    worktree_task_ids: set[str] = {t["id"] for t in tasks
                                   if t.get("isolation") == "worktree"}
    commands: list[tuple[dict[str, Any], list[str], Path]] = []
    deferred: set[str] = set()
    for task in tasks:
        log_path, log_rel = _log_paths(task)
        # A `receives:` task defers to resolve cross-wave pointers at spawn; a
        # `reentry:` task defers so every attempt writes a fresh handoff (its
        # prior verdict's fix list injected). Both write once per spawn.
        # Phase 3 widening: also defer tasks whose `needs` include a worktree
        # task (so salvage_diff pointers can be injected at spawn time).
        needs_worktree = bool(
            not task.get("block_on_salvage")
            and set(task.get("needs") or []) & worktree_task_ids
        )
        if task.get("receives") or task.get("reentry") or needs_worktree:
            injected = _resolve_receives(config, task, quiet=True)  # speculative
            tokens.account_handoff(
                config, _make_handoff(task, injected, do_pack=False),
                path="(speculative)")
            disp_cmd = _build_command(
                task, config, "<handoff resolved at spawn>", sid,
                skip_permissions=skip_permissions, telemetry=telemetry)
            recorder.task(task["id"], command=disp_cmd, log=log_rel)
            deferred.add(task["id"])
            commands.append((task, disp_cmd, log_path))
            if task.get("reentry") and not task.get("receives"):
                why = "reentry — handoff written per attempt"
            elif task.get("receives"):
                why = (f"receives (resolved at spawn) — matching now: "
                       f"{', '.join(injected) or 'none yet'}")
            else:
                why = "salvage-aware — handoff written at spawn"
            print(f"[{task['id']}] {why}")
        else:
            cmd, rel = _write_handoff_cmd(task, [])
            recorder.task(task["id"], command=cmd, handoff=rel, log=log_rel)
            recorder.event("handoff.dispatched", task=task["id"], handoff=rel)
            commands.append((task, cmd, log_path))

    if dry_run:
        for task, cmd, _ in commands:
            tail = ("  (speculative — resolved at spawn)"
                    if task["id"] in deferred else "")
            print(f"[{task['id']}] would run: "
                  + " ".join(shlex.quote(c) for c in cmd) + tail)
            recorder.task(task["id"], status="dry-run")
        print("coordinate: dry run — no agents spawned")
        recorder.finish("dry-run")
        return 0

    run_id = recorder.data["run_id"]
    running_procs: dict[str, subprocess.Popen] = {}

    # Pool throttle (DESIGN §2e) and Phase F re-entry state.
    pools_cfg = ccfg.get("model_pools") or {}
    pool_of = {t["id"]: t.get("model_pool") for t in tasks}
    throttle_of = {name: _pool_throttle(p) for name, p in pools_cfg.items()}
    inflight_pool: dict[str, int] = {}
    pool_last_spawn: dict[str, float] = {}
    task_retries: dict[str, int] = {}
    not_before: dict[str, float] = {}            # monotonic floor for (re)spawn
    reentry_max = {t["id"]: int(t.get("max_reentry", 2))
                   for t in tasks if t.get("reentry")}
    reentry_count: dict[str, int] = {}
    reentry_inject: dict[str, list[str]] = {}    # fix-list pointers for next attempt

    def _execute(task: dict[str, Any], cmd: list[str], log_path: Path) -> int:
        tid = task["id"]
        if task.get("isolation") != "worktree":
            rc, _kill_reason = _run_task(tid, cmd, config, log_path, recorder,
                                         sid=sid, runner=task["runner"],
                                         model=task.get("model") or "", budget=budget,
                                         procs=running_procs)
            return rc
        try:
            wt_dir, branch, base = _worktree_setup(config, run_id, tid)
        except RuntimeError as exc:
            with _print_lock:
                print(f"[{tid}] worktree setup failed: {exc}")
            recorder.task(tid, status="failed", exit_code=125,
                          isolation_error=str(exc), finished_at=_utcnow())
            return 125
        recorder.task(tid, worktree=str(wt_dir), branch=branch)
        rc, _kill_reason = _run_task(tid, cmd, config, log_path, recorder,
                                     sid=sid, runner=task["runner"],
                                     model=task.get("model") or "", cwd=wt_dir,
                                     budget=budget, procs=running_procs)
        try:
            info, harvested = _worktree_finish(config, tid, wt_dir, branch, run_id, base)
        except RuntimeError as exc:
            with _print_lock:
                print(f"[{tid}] worktree teardown failed: {exc}")
            recorder.task(tid, isolation_error=str(exc))
            return rc or 125
        fields: dict[str, Any] = {"isolation": info}
        if harvested:
            fields["harvested_handoffs"] = harvested
        recorder.task(tid, **fields)
        if info.get("branch"):
            with _print_lock:
                print(f"[{tid}] work committed to branch {info['branch']} "
                      f"({info.get('commit', '?')})")
        # Phase 2 — salvage detection: rc!=0 + worktree + materialized diff → salvaged
        if rc != 0 and not task.get("block_on_salvage") and info.get("diff"):
            recorder.task(tid, status="salvaged", salvage_diff=info["diff"])
            recorder.event("salvage.detected", task=tid, diff=info["diff"])
            with _print_lock:
                print(f"\n[{tid}] *** SALVAGED *** diff materialized at {info['diff']}\n")
        return rc

    def _spawn_prepare(task: dict[str, Any]) -> list[str]:
        """Deferred write-at-spawn for a `receives:`/`reentry:`/salvage-aware task:
        resolve cross-wave pointers, inject salvage_diff pointers from salvaged
        upstreams, write the handoff, return the cmd."""
        injected = _resolve_receives(config, task) + reentry_inject.get(task["id"], [])
        # Phase 3: advisory salvage-diff injection for salvaged upstreams
        salvaged_upstreams: list[str] = []
        for dep_tid in (task.get("needs") or []):
            if dep_tid in salvaged:
                dep_data = recorder.data.get("tasks", {}).get(dep_tid, {})
                diff = dep_data.get("salvage_diff")
                if diff:
                    injected.append(f"repo://{diff}")
                    salvaged_upstreams.append(dep_tid)
        cmd, rel = _write_handoff_cmd(task, injected,
                                      salvaged_upstream=salvaged_upstreams or None)
        recorder.task(task["id"], handoff=rel)
        recorder.event("handoff.dispatched", task=task["id"], handoff=rel)
        return cmd

    # Dependency-aware scheduler: a task launches once everything it `needs`
    # has exited 0; tasks downstream of a failure are skipped (cascading).
    by_id = {task["id"]: (task, cmd, log_path) for task, cmd, log_path in commands}
    deps = {tid: set(by_id[tid][0].get("needs") or []) for tid in by_id}
    results: dict[str, int | None] = {}  # exit code; None = skipped
    succeeded: set[str] = set()
    salvaged: set[str] = set()           # rc!=0 but diff materialized — advisory proceed
    blocked: set[str] = set()            # failed or skipped
    pending = set(by_id)
    futures: dict[Any, str] = {}
    aborted = False
    with ThreadPoolExecutor(max_workers=limit) as pool:
      try:
        while pending or futures:
            over = budget.exhausted()
            if over and pending:         # hard ceiling: nothing new launches
                for tid in sorted(pending):
                    results[tid] = None
                    blocked.add(tid)
                    recorder.task(tid, status="skipped", skipped_because=[over])
                    with _print_lock:
                        print(f"[{tid}] skipped ({over})")
                pending.clear()
            changed = True
            while changed:               # cascade skips to a fixpoint
                changed = False
                for tid in sorted(pending):
                    task_obj = by_id[tid][0]
                    # block_on_salvage: a salvaged dep is a blocker too, so a hard
                    # gate cascade-skips instead of orphaning in `pending`.
                    if task_obj.get("block_on_salvage"):
                        bad = deps[tid] & (blocked | salvaged)
                    else:
                        bad = deps[tid] & (blocked - salvaged)
                    if bad:
                        pending.discard(tid)
                        results[tid] = None
                        blocked.add(tid)
                        changed = True
                        recorder.task(tid, status="skipped",
                                      skipped_because=sorted(bad))
                        with _print_lock:
                            print(f"[{tid}] skipped "
                                  f"(dependency failed: {', '.join(sorted(bad))})")
            spawn_wait: float | None = None   # soonest a timing-deferred task runs
            for tid in sorted(pending):
                task_obj = by_id[tid][0]
                # block_on_salvage: only succeeded deps satisfy (old conservative behavior)
                if task_obj.get("block_on_salvage"):
                    if not (deps[tid] <= succeeded):
                        continue
                elif not (deps[tid] <= (succeeded | salvaged)):
                    continue
                now = time.monotonic()
                floor = not_before.get(tid, 0.0)
                if now < floor:               # backoff / retry cooldown
                    spawn_wait = _min_opt(spawn_wait, floor - now)
                    continue
                pname: str | None = pool_of.get(tid)
                thr = throttle_of.get(pname) if pname else None
                if thr and pname:           # pname is a real pool name here
                    cap = thr["max_concurrency"]
                    if cap is not None and inflight_pool.get(pname, 0) >= cap:
                        continue              # pool saturated; frees on a completion
                    interval = thr["min_spawn_interval_s"]
                    last = pool_last_spawn.get(pname)
                    if interval and last is not None and (now - last) < interval:
                        spawn_wait = _min_opt(spawn_wait, interval - (now - last))
                        continue
                task, cmd, log_path = by_id[tid]
                if tid in deferred:           # write its handoff now (resolved)
                    cmd = _spawn_prepare(task)
                fut = pool.submit(_execute, task, cmd, log_path)
                futures[fut] = tid
                pending.discard(tid)
                if pname:
                    inflight_pool[pname] = inflight_pool.get(pname, 0) + 1
                    pool_last_spawn[pname] = time.monotonic()
            if not futures:
                if spawn_wait and spawn_wait > 0:   # only a throttle window holds us
                    time.sleep(min(spawn_wait, 5.0))
                    continue
                break  # nothing running, nothing ready => done
            # Wake on the first completion, or sooner if a throttle window opens.
            timeout = min(spawn_wait, 5.0) if (spawn_wait and spawn_wait > 0) else None
            done_set, _ = wait(set(futures), return_when=FIRST_COMPLETED, timeout=timeout)
            for fut in done_set:
                tid = futures.pop(fut)
                rc = fut.result()
                pname = pool_of.get(tid)
                if pname and inflight_pool.get(pname):
                    inflight_pool[pname] -= 1
                log_path = by_id[tid][2]
                thr = throttle_of.get(pname) if pname else None
                max_r = thr["max_retries"] if thr else 0
                # Reactive rate-limit safety net (DESIGN §2e): re-queue with backoff.
                if (rc != 0 and max_r and task_retries.get(tid, 0) < max_r
                        and _looks_rate_limited(log_path)):
                    task_retries[tid] = task_retries.get(tid, 0) + 1
                    backoff = min(60.0, 0.5 * 2 ** (task_retries[tid] - 1))
                    not_before[tid] = time.monotonic() + backoff
                    pending.add(tid)
                    recorder.task(tid, status="queued", retry=task_retries[tid])
                    with _print_lock:
                        print(f"[{tid}] rate-limited — retry "
                              f"{task_retries[tid]}/{max_r} in {backoff:.1f}s")
                    continue
                # Phase F: a re-entry task that ruled "rework" re-runs with the
                # fix list injected, until it approves or hits max_reentry.
                if (rc == 0 and tid in reentry_max
                        and reentry_count.get(tid, 0) < reentry_max[tid]):
                    hb = _latest_handback(config, sid, tid)
                    state = (hb or {}).get("state") or {}
                    if (state.get("decisions") or {}).get("verdict") == "rework":
                        reentry_count[tid] = reentry_count.get(tid, 0) + 1
                        reentry_inject[tid] = list(state.get("artifacts") or [])
                        pending.add(tid)      # re-queue; NOT marked succeeded
                        recorder.task(tid, status="queued",
                                      reentry=reentry_count[tid])
                        with _print_lock:
                            print(f"[{tid}] verdict=rework — re-entry "
                                  f"{reentry_count[tid]}/{reentry_max[tid]}")
                        continue
                results[tid] = rc
                if rc == 0:
                    succeeded.add(tid)
                elif (recorder.data.get("tasks", {})
                      .get(tid, {}).get("status") == "salvaged"):
                    salvaged.add(tid)
                else:
                    blocked.add(tid)
      except KeyboardInterrupt:
        # Terminate children NOW (their streams close -> workers drain ->
        # the executor can shut down instead of deadlocking on readers).
        aborted = True
        with _print_lock:
            print("\ninterrupted — terminating spawned agents…", file=sys.stderr)
        for proc in list(running_procs.values()):
            try:
                proc.terminate()
            except OSError:
                pass
        time.sleep(2)
        for proc in list(running_procs.values()):
            try:
                proc.kill()
            except OSError:
                pass

    if aborted:
        for fut, tid in list(futures.items()):
            try:
                results[tid] = fut.result(timeout=10)
            except Exception:
                results[tid] = None
        for tid in sorted(pending):
            results[tid] = None
            recorder.task(tid, status="skipped",
                          skipped_because=["run aborted (interrupt)"])
        recorder.finish("aborted", budget=budget.as_dict())
        print(f"coordinate: run aborted — manifest "
              f"{recorder.path.relative_to(config.root)}", file=sys.stderr)
        return 130

    # Validate everything appended during the run — ours and any handoffs the
    # agents themselves recorded (validate on receipt, same as load_handoff).
    # A valid handoff back to the Coordinator is the completion contract: it
    # upgrades a task from merely "exited" to "completed".
    invalid: list[str] = []
    returns: dict[str, str] = {}
    for path in sorted(config.handoffs_dir.glob("*.json")):
        if path.name in before:
            continue
        try:
            obj = ho.load_handoff(path, config)
        except ho.HandoffValidationError as exc:
            invalid.append(f"{path.relative_to(config.root)}: {exc}")
            continue
        if obj.get("sid") == sid and obj.get("to") == COORDINATOR and obj.get("from") in results:
            returns[obj["from"]] = str(path.relative_to(config.root))

    # Salvaged tasks are NOT genuine failures; exclude them from the failed list.
    # A salvaged task with no consumer (or with block_on_salvage) counts as failure.
    salvaged_no_consumer = {
        tid for tid in salvaged
        if not any(tid in set(by_id[dtid][0].get("needs") or [])
                   for dtid in succeeded)
    }
    failed = [tid for tid, rc in results.items()
              if rc not in (0, None) and tid not in salvaged]
    failed += sorted(salvaged_no_consumer)
    skipped = [tid for tid, rc in results.items() if rc is None]
    print("\n" + "=" * 60)
    for task, _, log_path in commands:
        tid = task["id"]
        rc = results[tid]
        if rc is None:
            status = "SKIPPED (dependency failed)"
        elif rc == 0 and tid in returns:
            recorder.task(tid, status="completed", return_handoff=returns[tid])
            status = "ok (completed, handed back)"
        elif rc == 0:
            status = "ok (exited; no handoff back to Coordinator)"
        elif tid in salvaged:
            task_data = recorder.data.get("tasks", {}).get(tid, {})
            diff_ref = task_data.get("salvage_diff", "?")
            status = f"SALVAGED (exit {rc}; diff at {diff_ref})"
        else:
            status = f"FAILED (exit {rc})"
        log_disp = log_path.relative_to(config.root) \
            if log_path.is_relative_to(config.root) else log_path
        print(f"  [{tid}] {status}  log: {log_disp}")
    if invalid:
        print("  invalid handoffs recorded during run:")
        for msg in invalid:
            print(f"    - {msg}")
    ok = len(tasks) - len(failed) - len(skipped)
    run_status = "completed" if not failed and not skipped and not invalid else "failed"
    recorder.finish(
        run_status, invalid_handoffs=invalid,
        summary={"ok": ok, "failed": len(failed), "skipped": len(skipped),
                 "salvaged": len(salvaged), "total": len(tasks)},
        budget=budget.as_dict(),
    )
    print(f"coordinate: {ok}/{len(tasks)} tasks ok"
          + (f"  ({len(salvaged)} salvaged)" if salvaged else ""))
    print(f"run manifest: {recorder.path.relative_to(config.root)}")
    if ccfg.get("auto_distill"):
        from .. import distill as distill_mod  # lazy: avoids a module cycle
        try:
            res = distill_mod.distill_session(config, sid)
            print(f"distilled: {res['session']}")
        except ValueError:
            pass  # nothing to consolidate (should not happen post-run)
    print("=" * 60)
    return 0 if run_status == "completed" else 1


# ----------------------------------------------------- public surface re-export
# The split lifted three concerns into submodules; re-export their names here so
# `coordinate.<name>` stays byte-identical for every caller (other modules, the
# CLI, the MCP server, and the tests) and the run loop above keeps calling them
# by their bare names. Imports sit at the foot of the module because the submodules
# reach back into this package (e.g. `worktree` uses `coordinate._git`).
from .reporting import (
    _STATUS_GLYPHS,
    _agg_lines,
    _aggregate_tasks,
    _elapsed,
    by_agent_report,
    critical_path_report,
    list_runs,
    model_report,
    model_stats,
    render_status,
    run_events,
    timeline_report,
)
from .telemetry import USAGE_PARSERS, UsageParser, _extract_telemetry, _opencode_usage
from .worktree import (
    _worktree_commit_and_remove,
    _worktree_finish,
    _worktree_setup,
    cleanup,
)
