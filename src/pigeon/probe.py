"""probe: a point-in-time qualification check for configured runners.

Free-provider model rosters churn, so runner trust must be **measured, not
hardcoded**. ``pigeon probe`` fills each runner template with a trivial prompt,
runs it under a short timeout, and classifies the result
(``ok`` / ``slow`` / ``protocol_fail`` / ``dead``) into a ranked report and
``.pigeon/probe.json``. Advisory only — it never edits the runner pool
(Pillar-4: empirical, offline, human-acted).
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any

from .config import Config
from .coordinate import (_child_env, _fill, _opencode_permission_env,
                         _seed_opencode_creds)

PROBE_PROMPT = "Reply with exactly this line and nothing else: PIGEON_OK"
PROBE_TOKEN = "PIGEON_OK"
# The trusted trio resolve to these binaries (sonnet/opus -> claude, agy -> agy);
# --free-only skips them so a probe doesn't spend on paid runners.
_TRUSTED_BINS = ("claude", "agy")
_VERDICT_ORDER = {"dead": 0, "protocol_fail": 1, "slow": 2, "ok": 3}


def _is_free(template: list[str]) -> bool:
    """True when a runner template invokes no trusted (claude/agy) binary."""
    return not any(part in _TRUSTED_BINS for part in template)


def _model_of(template: list[str]) -> str:
    """Best-effort model id from a template (the token after ``-m``)."""
    if "-m" in template:
        i = template.index("-m")
        if i + 1 < len(template):
            return template[i + 1]
    return ""


def build_probe_cmd(template: list[str], prompt: str = PROBE_PROMPT) -> list[str]:
    """Fill a runner template with the probe prompt (other placeholders left)."""
    return [_fill(part, {"prompt": prompt}) for part in template]


def classify(rc: int, out: str, elapsed: float, *, timed_out: bool,
             soft_s: float) -> tuple[str, str]:
    """Map a probe result to ``(verdict, note)``."""
    if timed_out:
        return "dead", f"timed out (>{int(round(elapsed))}s)"
    if rc != 0:
        return "dead", f"exit {rc}"
    if PROBE_TOKEN not in out:
        return "protocol_fail", "responded but did not echo PIGEON_OK"
    if elapsed > soft_s:
        return "slow", f"{elapsed:.1f}s > {soft_s:.0f}s soft budget"
    return "ok", f"{elapsed:.1f}s"


def run_probe(runner: str, template: list[str], config: Config, *,
              timeout_s: float, soft_s: float) -> dict[str, Any]:
    """Run one runner's probe and return a classified record."""
    cmd = build_probe_cmd(template)
    env = _child_env(config)
    try:                              # opencode runners need seeded creds + perms
        _seed_opencode_creds(cmd)
        env.update(_opencode_permission_env(cmd, config))
    except Exception:                 # never let env prep abort the probe
        pass
    started = time.monotonic()
    timed_out, rc, out = False, 1, ""
    try:
        proc = subprocess.run(cmd, cwd=config.root, env=env,
                              capture_output=True, text=True, timeout=timeout_s)
        rc = proc.returncode
        out = (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        out = exc.stdout if isinstance(exc.stdout, str) else ""
    except (FileNotFoundError, OSError) as exc:
        rc, out = 127, f"spawn error: {exc}"
    elapsed = time.monotonic() - started
    verdict, note = classify(rc, out, elapsed, timed_out=timed_out, soft_s=soft_s)
    return {"runner": runner, "model": _model_of(template), "verdict": verdict,
            "exit_code": rc, "elapsed_s": round(elapsed, 2), "note": note}


def probe(config: Config, *, free_only: bool = False, timeout_s: float = 60.0,
          soft_s: float = 30.0) -> list[dict[str, Any]]:
    """Probe each configured runner; return records sorted worst-first."""
    runners = config.coordinate_cfg.get("runners") or {}
    records: list[dict[str, Any]] = []
    for name in sorted(runners):
        template = runners[name]
        if not isinstance(template, list) or not template:
            continue
        if free_only and not _is_free(template):
            continue
        records.append(run_probe(name, template, config,
                                 timeout_s=timeout_s, soft_s=soft_s))
    records.sort(key=lambda r: (_VERDICT_ORDER.get(r["verdict"], 9), r["runner"]))
    return records


def format_probe(records: list[dict[str, Any]]) -> str:
    """Human-readable table, worst runners first."""
    if not records:
        return "probe: no runners configured."
    glyph = {"ok": "✔", "slow": "~", "protocol_fail": "?", "dead": "✗"}
    lines = ["runner probe (worst first; free rosters churn — re-run to refresh):"]
    for r in records:
        lines.append(f"  {glyph.get(r['verdict'], '?')} {r['runner']:<18} "
                     f"{r['verdict']:<14} {r['note']}")
    counts: dict[str, int] = {}
    for r in records:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    lines.append("  (" + ", ".join(f"{n} {v}" for v, n in sorted(counts.items())) + ")")
    return "\n".join(lines)


def write_probe(records: list[dict[str, Any]], config: Config) -> Path:
    """Persist probe records to ``.pigeon/probe.json`` (gitignored scratch)."""
    path = config.contract_dir / "probe.json"
    path.write_text(json.dumps(records, indent=2, ensure_ascii=False),
                    encoding="utf-8")
    return path
