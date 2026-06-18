"""Configuration loading and repo-root discovery.

Config lives at ``<contract-dir>/config.yaml``, where the contract directory
is ``.pigeon/`` in pigeon-native repositories and ``.agentctx/`` in
repositories scaffolded before the rename — the legacy name is honored
forever (deployed consumers never break). It is YAML because it is
human-edited (the one place YAML is appropriate). The cross-model *contract*
— handoffs — is strictly JSON; see the decision record in AGENTS.md.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

CONTRACT_DIR = ".pigeon"            # native name for new repositories
LEGACY_CONTRACT_DIR = ".agentctx"   # pre-rename repos: honored forever


def contract_dirname(root: Path) -> str:
    """The contract directory this repository actually uses."""
    if (root / CONTRACT_DIR).is_dir():
        return CONTRACT_DIR
    if (root / LEGACY_CONTRACT_DIR).is_dir():
        return LEGACY_CONTRACT_DIR
    return CONTRACT_DIR  # fresh repos are pigeon-native


CONFIG_RELPATH = f"{LEGACY_CONTRACT_DIR}/config.yaml"  # back-compat constant

# Defaults are deep-merged under the on-disk config, so a partial or absent
# config.yaml still yields a fully-populated, working configuration.
def default_config(contract_dir: str = LEGACY_CONTRACT_DIR) -> dict[str, Any]:
    d = contract_dir
    return {
        "schema_version": "1.0",
        "paths": {
            "canonical": "AGENTS.md",
            "generated": "auto",  # detect installed CLIs; or an explicit list
            "manifest": f"{d}/manifest.json",
            "handoffs_dir": f"{d}/handoffs",
            "metrics": f"{d}/metrics.jsonl",
            "handoff_schema": f"{d}/handoff.schema.json",
            "memory_dir": f"{d}/memory",
            "context_dir": f"{d}/context",
        },
        "manifest": {
            "include": ["src/**/*.py", "*.py"],
            "exclude": ["**/__pycache__/**"],
            "decisions": {},
            "owners": {},
        },
        "retrieval": {
            "include": ["**/*.py", "**/*.md", "**/*.json", "**/*.toml", "**/*.sh"],
            "exclude": [
                "**/__pycache__/**",
                ".git/**",
                ".venv/**",
                "venv/**",
                "**/*.egg-info/**",
                f"{d}/metrics.jsonl",
            ],
            "max_file_bytes": 200_000,
            "chunk_lines": 40,
            "chunk_overlap": 10,
            "default_top_k": 5,
            "ripgrep_path": None,
            "vector": {
                "enabled": False,
                "model": "all-MiniLM-L6-v2",
                "store_dir": f"{d}/vector",
            },
        },
        "resolve": {
            "allow_s3": False,
            # S1 fence: pointers resolve only INSIDE the repo root by default.
            # repo:// is always confined; set true to let file:// and bare/
            # absolute paths read outside the repo — a deliberate, auditable
            # opt-in, off by default so a handoff cannot exfiltrate /etc/passwd.
            "allow_outside_root": False,
        },
        "tokens": {
            "encoding": "cl100k_base",
        },
        # Skill projection: playbook pages -> each runtime's native subagent files.
        "skills": {
            "targets": {
                "claude": ".claude/agents",
            },
        },
        # Adopt: discover & catalogue existing subagents, skills, MCP servers.
        # Sources are relative to repo root; ~ paths expand to the real home.
        # Project-scope sources should be listed first so project wins on name
        # collision with user scope.  allow: [] means nothing is usable until
        # explicitly allow-listed via `pigeon adopt --allow <name>`.
        "adopt": {
            "enabled": True,
            "sources": {
                "subagents": [".claude/agents"],
                "skills": [".claude/skills"],
                "mcp": [".mcp.json", ".cursor/mcp.json"],
            },
            "allow": [],
            "import": False,
        },
        "coordinate": {
            "log_dir": f"{d}/coordinate/logs",
            "runs_dir": f"{d}/coordinate/runs",
            "events_dir": f"{d}/coordinate/events",
            "worktrees_dir": f"{d}/coordinate/worktrees",
            # Full diffs materialized from changed worktree commits, on the
            # SHARED tree so they survive `worktree remove` and can be handed
            # downstream as a pointer (a reviewer reads the diff, not the repo).
            "diffs_dir": f"{d}/coordinate/diffs",
            "parallel_limit": 4,
            # Runner for tasks that don't name one. A string assigns it to
            # every unassigned task; a LIST round-robins across them (spread
            # load off your metered CLI); null (default) REFUSES unassigned
            # tasks — after one too many surprise bills, implicit routing to
            # an expensive runner is not a default this tool will ever have.
            "default_runner": None,
            # Run `pigeon distill <sid>` automatically when a coordinate run ends.
            "auto_distill": False,
            # argv templates; placeholders: {prompt} {handoff} {root} {task_id} {sid}
            "runners": {
                "claude": ["claude", "-p", "{prompt}"],
                "agy": ["agy", "-p", "{prompt}"],
                "opencode": ["opencode", "run", "{prompt}"],
            },
            # Appended only when the operator passes --skip-permissions.
            "skip_permissions_flags": {
                "claude": ["--dangerously-skip-permissions"],
                "agy": ["--dangerously-skip-permissions"],
                "opencode": [],
            },
            # Appended with --telemetry (or per-task `telemetry: true`): makes the
            # child CLI emit a machine-readable usage report we mine for *measured*
            # token consumption. Output with a `usage` object is parsed regardless.
            # Appended with --telemetry / per-task telemetry: true. Only a
            # runner whose CLI actually emits a usage report should get a
            # flag here — a wrong flag makes the runner print help and exit.
            # claude -p --output-format json is verified; add your runner's
            # real usage flag (agy/opencode have none by default).
            "telemetry_flags": {
                "claude": ["--output-format", "json"],
                "agy": [],
                "opencode": [],
            },
            # Three-tier timeout ladder (all null by default → byte-identical to
            # today's blocking drain; no behavior change unless configured):
            #   idle_timeout_s   — kill after N seconds of no stdout (progress guard)
            #   hard_cap_s       — absolute in-loop ceiling, covers fast-talking livelock
            #   grace_kill_s     — SIGTERM window before SIGKILL; matches `-k 30`
            # Per-runner overrides in `timeouts:` take precedence; a per-runner
            # null explicitly disables an otherwise-set global value.
            "idle_timeout_s": None,
            "hard_cap_s": None,
            "grace_kill_s": 30,
            "timeouts": {},
            # Named model pools for the `model_pool:` task field. A pool's models
            # are round-robined across the tasks that name it, seeded by sid so
            # the assignment is reproducible per session yet spread across
            # sessions. Two forms, both accepted:
            #   sonnet: [anthropic/claude-sonnet-4-6]        # bare list
            #   free-opencode:                               # object form
            #     models: [opencode/a-free, opencode/b-free]
            #     max_concurrency: 2       # cap concurrent in-flight on this pool
            #     min_spawn_interval_s: 5  # min wall-clock gap between spawns
            #     max_retries: 2           # re-queue a rate-limited exit, backoff
            # The throttle knobs are enforced by the scheduler (clock-only — the
            # only ceiling that binds before telemetry arrives post-exit).
            # Empty by default — models are opt-in per project. A runner whose
            # template carries a `{model}` placeholder consumes the resolved
            # model; default templates have none, so they are unaffected.
            "model_pools": {},
            # S2 / Risk 7: allowlist is ON by default (empty list = only the
            # functional _ENV_BASELINE vars reach child agents — secrets in the
            # operator shell stay out of reach).  Explicit opt-out: set
            # ``coordinate.env_allowlist: null`` in config.yaml to inherit
            # the full parent environment.
            "env_allowlist": [],
            "safety": {
                # Agents may modify the folder only in a .git checkout with
                # pigeon initialized (revertible + contract-validated).
                "require_repo_setup": True,
                # The subprocess fan-out is only supported on Linux.
                "require_linux": True,
                # pip install/remove & library changes only inside a conda env,
                # virtualenv, or container — never the system interpreter.
                "require_isolated_env_for_packages": True,
                # Children inherit AGENTCTX_DEPTH; a child running `coordinate`
                # again past this depth is refused (no agent fork-bombs).
                "max_depth": 1,
            },
            # Hard spend ceilings for a run, measured via child telemetry. Once
            # exceeded, no further tasks launch (running ones finish). None = off.
            "budget": {
                "tokens": None,
                "usd": None,
            },
        },
    }


DEFAULT_CONFIG: dict[str, Any] = default_config(LEGACY_CONTRACT_DIR)


def _deep_merge(base: dict[str, Any], override: dict[str, Any],
                _depth: int = 0) -> dict[str, Any]:
    """Recursively merge ``override`` onto a copy of ``base``.

    Depth-guarded: a YAML anchor cycle (`a: &x {b: *x}`) must fail loudly
    instead of recursing forever.
    """
    if _depth > 64:
        raise ValueError("config nesting deeper than 64 levels — cyclic YAML anchors?")
    out = copy.deepcopy(base)
    for key, val in (override or {}).items():
        if key in out and isinstance(out[key], dict) and isinstance(val, dict):
            out[key] = _deep_merge(out[key], val, _depth + 1)
        else:
            out[key] = copy.deepcopy(val)
    return out


def _validate_schema(cfg: dict[str, Any]) -> None:
    """Type-check key config values at load time (DD U7).

    A mistyped value such as ``max_depth: "one"`` raises here with a clear
    message instead of detonating mid-run as a cryptic TypeError.
    """

    def _int(path: str, val: Any) -> None:
        if not isinstance(val, int) or isinstance(val, bool):
            raise ValueError(
                f"config key {path!r} must be an integer, got {type(val).__name__!r}"
            )

    def _bool(path: str, val: Any) -> None:
        if not isinstance(val, bool):
            raise ValueError(
                f"config key {path!r} must be a boolean, got {type(val).__name__!r}"
            )

    def _section(path: str, parent: dict[str, Any], key: str) -> dict[str, Any]:
        # A scalar override replacing a whole section (e.g. `retrieval: 5`) survives
        # _deep_merge; without this guard the indexing below would raise the cryptic
        # TypeError this validator exists (DD U7) to prevent.
        val = parent[key]
        if not isinstance(val, dict):
            raise ValueError(
                f"config section {path!r} must be a mapping, "
                f"got {type(val).__name__!r}"
            )
        return val

    r = _section("retrieval", cfg, "retrieval")
    _int("retrieval.max_file_bytes", r["max_file_bytes"])
    _int("retrieval.chunk_lines", r["chunk_lines"])
    _int("retrieval.chunk_overlap", r["chunk_overlap"])
    _int("retrieval.default_top_k", r["default_top_k"])
    _bool("retrieval.vector.enabled", _section("retrieval.vector", r, "vector")["enabled"])

    res = _section("resolve", cfg, "resolve")
    _bool("resolve.allow_s3", res["allow_s3"])
    _bool("resolve.allow_outside_root", res["allow_outside_root"])

    ad = cfg.get("adopt")
    if isinstance(ad, dict):
        allow = ad.get("allow")
        if allow is not None:
            if not isinstance(allow, list) or any(
                    not isinstance(x, str) for x in allow):
                raise ValueError(
                    "config key 'adopt.allow' must be a list of strings, "
                    f"got {type(allow).__name__!r}"
                )

    co = _section("coordinate", cfg, "coordinate")
    _int("coordinate.parallel_limit", co["parallel_limit"])

    al = co.get("env_allowlist")
    if al is not None:
        if not isinstance(al, list):
            raise ValueError(
                f"config key 'coordinate.env_allowlist' must be a list of strings or null, "
                f"got {type(al).__name__!r}"
            )
        nonstr = [x for x in al if not isinstance(x, str)]
        if nonstr:
            raise ValueError(
                "config key 'coordinate.env_allowlist' must contain only strings; "
                f"got non-string element(s): {nonstr!r}"
            )

    safety = _section("coordinate.safety", co, "safety")
    _int("coordinate.safety.max_depth", safety["max_depth"])
    if safety["max_depth"] < 1:
        raise ValueError(
            f"config key 'coordinate.safety.max_depth' must be >= 1, "
            f"got {safety['max_depth']!r}"
        )
    _bool("coordinate.safety.require_repo_setup", safety["require_repo_setup"])
    _bool("coordinate.safety.require_linux", safety["require_linux"])
    _bool(
        "coordinate.safety.require_isolated_env_for_packages",
        safety["require_isolated_env_for_packages"],
    )


def find_repo_root(start: Path | str | None = None) -> Path:
    """Walk upward from ``start`` (default cwd) looking for a repo root.

    A repo root is the nearest ancestor containing ``.pigeon/``,
    ``.agentctx/`` (legacy), or ``.git``. Falls back to ``start`` itself.
    """
    cur = Path(start).resolve() if start else Path.cwd().resolve()
    if cur.is_file():
        cur = cur.parent
    for candidate in (cur, *cur.parents):
        if ((candidate / CONTRACT_DIR).is_dir()
                or (candidate / LEGACY_CONTRACT_DIR).is_dir()
                or (candidate / ".git").exists()):
            return candidate
    return cur


@dataclass(frozen=True)
class Config:
    """Resolved configuration bound to a repository root.

    Path accessors return absolute :class:`pathlib.Path` objects rooted at
    :attr:`root`, so callers never join paths by hand.
    """

    root: Path
    data: dict[str, Any]

    @property
    def contract_dir(self) -> Path:
        """The repo's contract directory (.pigeon, or legacy .agentctx)."""
        return self.root / contract_dirname(self.root)

    # -- path helpers ---------------------------------------------------
    def _p(self, relpath: str) -> Path:
        return (self.root / relpath).resolve()

    @property
    def canonical(self) -> Path:
        return self._p(self.data["paths"]["canonical"])

    @property
    def generated(self) -> list[Path]:
        from . import context
        return context.resolve_generated(self)

    @property
    def manifest(self) -> Path:
        return self._p(self.data["paths"]["manifest"])

    @property
    def handoffs_dir(self) -> Path:
        return self._p(self.data["paths"]["handoffs_dir"])

    @property
    def metrics(self) -> Path:
        return self._p(self.data["paths"]["metrics"])

    @property
    def handoff_schema(self) -> Path:
        return self._p(self.data["paths"]["handoff_schema"])

    @property
    def memory_dir(self) -> Path:
        return self._p(self.data["paths"]["memory_dir"])

    @property
    def context_dir(self) -> Path:
        return self._p(self.data["paths"]["context_dir"])

    # -- section accessors ---------------------------------------------
    @property
    def manifest_cfg(self) -> dict[str, Any]:
        return self.data["manifest"]

    @property
    def retrieval_cfg(self) -> dict[str, Any]:
        return self.data["retrieval"]

    @property
    def resolve_cfg(self) -> dict[str, Any]:
        return self.data["resolve"]

    @property
    def tokens_cfg(self) -> dict[str, Any]:
        return self.data["tokens"]

    @property
    def coordinate_cfg(self) -> dict[str, Any]:
        return self.data["coordinate"]

    @property
    def skills_cfg(self) -> dict[str, Any]:
        return self.data["skills"]

    @property
    def coordinate_log_dir(self) -> Path:
        return self._p(self.data["coordinate"]["log_dir"])

    @property
    def coordinate_runs_dir(self) -> Path:
        return self._p(self.data["coordinate"]["runs_dir"])

    @property
    def coordinate_worktrees_dir(self) -> Path:
        return self._p(self.data["coordinate"]["worktrees_dir"])

    @property
    def coordinate_diffs_dir(self) -> Path:
        return self._p(self.data["coordinate"]["diffs_dir"])

    @property
    def coordinate_events_dir(self) -> Path:
        return self._p(self.data["coordinate"]["events_dir"])

    @property
    def adopt_dir(self) -> Path:
        return self.contract_dir / "adopt"

    @property
    def catalog_path(self) -> Path:
        return self.adopt_dir / "catalog.json"


def load_config(root: Path | str | None = None) -> Config:
    """Load and validate-merge the configuration for a repository.

    ``root`` may point anywhere inside the repo; the root is discovered.
    """
    repo_root = find_repo_root(root)
    dirname = contract_dirname(repo_root)
    cfg_path = repo_root / dirname / "config.yaml"
    on_disk: dict[str, Any] = {}
    if cfg_path.is_file():
        loaded = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict):
            raise ValueError(f"{cfg_path} must contain a YAML mapping at the top level")
        on_disk = loaded
    merged = _deep_merge(default_config(dirname), on_disk)
    _validate_schema(merged)
    # D3: vector retrieval is not yet implemented; catch the misconfiguration
    # here so the operator sees a clear message instead of a mid-run
    # NotImplementedError buried in retrieval code.
    if merged["retrieval"]["vector"]["enabled"]:
        raise ValueError(
            "retrieval.vector.enabled is True but vector retrieval is not yet "
            "implemented; set retrieval.vector.enabled to false (or omit the key)"
        )
    return Config(root=repo_root, data=merged)
