"""Read-side rendering and aggregation over coordination run manifests.

Everything here is pure presentation: it reads a recorded run manifest (or the
event stream beside it) and renders a human view — the live ``pigeon status``
screen, the chronological timeline, the per-agent / per-model rollups, the
critical path. Nothing here spawns work or mutates state; the scheduler core
(the package ``__init__``) produces the manifests these functions read.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pigeon.coordinate as _coord  # scheduler core: compute_waves (call-time)

from ..config import Config


_STATUS_GLYPHS = {
    "completed": "✔", "exited": "✔", "running": "▶", "queued": "·",
    "failed": "✗", "spawn-failed": "✗", "skipped": "⊘", "dry-run": "·",
    "timed_out_idle": "⏱", "timed_out": "⏱", "salvaged": "♻",
}


def _elapsed(start_iso: str | None, end_iso: str | None = None) -> str:
    if not start_iso:
        return "—"
    try:
        start = datetime.fromisoformat(start_iso)
        end = datetime.fromisoformat(end_iso) if end_iso else datetime.now(timezone.utc)
    except ValueError:
        return "—"
    secs = max(0, int((end - start).total_seconds()))
    return f"{secs // 60}m{secs % 60:02d}s" if secs >= 60 else f"{secs}s"


def render_status(run: dict[str, Any], config: Config | None = None) -> str:
    """One glanceable screen for a run manifest — live or finished.

    Every glyph is backed by a recorded field; elapsed time and measured
    tokens are shown, percentages never (an LLM task has no honest %).
    With a config, failed tasks also show the last lines of their log —
    the answer is usually right there, no digging required.
    """
    tasks: dict[str, Any] = run.get("tasks") or {}
    by_status: dict[str, int] = {}
    for t in tasks.values():
        by_status[t.get("status", "?")] = by_status.get(t.get("status", "?"), 0) + 1
    ok = by_status.get("completed", 0) + by_status.get("exited", 0)
    failed = by_status.get("failed", 0) + by_status.get("spawn-failed", 0)
    salvaged = (by_status.get("salvaged", 0)
                + by_status.get("timed_out_idle", 0)
                + by_status.get("timed_out", 0))
    header = (
        f"{run.get('run_id', '?')}  {str(run.get('status', '?')).upper()}  "
        f"{_elapsed(run.get('started_at'), run.get('finished_at'))}   "
        f"depth {run.get('depth', 0)}   env: {run.get('isolated_env') or 'none'}   "
        f"skip-perms: {'yes' if run.get('skip_permissions') else 'no'}"
    )
    counts = (f"tasks: {ok} ok · {by_status.get('running', 0)} running · "
              f"{by_status.get('queued', 0)} queued · {failed} failed · "
              f"{by_status.get('skipped', 0)} skipped"
              + (f" · {salvaged} salvaged/timed-out" if salvaged else ""))
    budget = run.get("budget") or {}
    if budget:
        parts = [f"{budget.get('spent_tokens', 0)}"
                 + (f"/{budget['max_tokens']}" if budget.get("max_tokens") else "")
                 + " tok",
                 f"${budget.get('spent_usd', 0)}"
                 + (f"/${budget['max_usd']}" if budget.get("max_usd") else "")]
        counts += "        budget: " + " · ".join(parts)
    lines = [header, counts, ""]
    width = max((len(t) for t in tasks), default=4)
    for tid, t in tasks.items():
        status = t.get("status", "?")
        glyph = _STATUS_GLYPHS.get(status, "?")
        dur = (f"{t['duration_s']}s" if "duration_s" in t
               else _elapsed(t.get("started_at")) if status == "running" else "—")
        line = f"  {glyph} {tid:<{width}}  {status:<12} {dur:>8}  {t.get('runner', '?')}"
        extras = []
        if t.get("return_handoff"):
            extras.append(f"↩ {t['return_handoff']}")
        if (t.get("isolation") or {}).get("branch") or t.get("branch"):
            extras.append(f"⎇ {(t.get('isolation') or {}).get('branch') or t['branch']}")
        if status == "running" and t.get("log"):
            extras.append(f"log: {t['log']}")
        if t.get("needs") and status == "queued":
            extras.append("└─ needs: " + ",".join(t["needs"]))
        if t.get("skipped_because"):
            extras.append("because: " + "; ".join(t["skipped_because"]))
        if extras:
            line += "   " + "   ".join(extras)
        lines.append(line)
        if (config is not None and t.get("log")
                and status in ("failed", "spawn-failed")):
            log_path = config.root / t["log"]
            if log_path.is_file():
                try:
                    tail = log_path.read_text(
                        encoding="utf-8", errors="replace").splitlines()
                except OSError:
                    tail = []
                for ln in [x for x in tail if not x.startswith("#")][-3:]:
                    lines.append(f"        ⌙ {ln}")
    if run.get("telemetry") is not None:
        pass  # run-level flags already in header; telemetry shown per task via budget
    return "\n".join(lines)


def run_events(config: Config, run_id: str) -> list[dict[str, Any]]:
    """The chronological event stream of a run (empty for pre-events runs)."""
    path = config.coordinate_events_dir / f"{run_id}.jsonl"
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def timeline_report(config: Config, run: dict[str, Any]) -> str:
    """Chronological event view — the 'why is it stuck / where did time go'."""
    events = run_events(config, run["run_id"])
    if not events:
        return "no event stream recorded for this run (pre-0.5 run?)"
    lines = [f"timeline: {run['run_id']}"]
    for ev in events:
        clock = (ev.get("ts") or "")[11:19] or "??:??:??"
        what = ev.get("event", "?")
        subject = ev.get("task") or ""
        extras = []
        for key in ("runner", "exit_code", "duration_s", "tokens", "cost_usd",
                    "handoff", "skipped_because"):
            if key in ev and ev[key] is not None:
                extras.append(f"{key}={ev[key]}")
        if ev.get("summary"):
            extras.append(str(ev["summary"]))
        lines.append(f"  {clock}  {what:<20} {subject:<14} "
                     + ("(" + ", ".join(str(e) for e in extras) + ")" if extras else ""))
    return "\n".join(lines)


def _aggregate_tasks(run: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    """Roll up tasks by a manifest field (``runner`` or ``model``). Tasks with
    no value for ``key`` are skipped (so model rollup covers only model tasks)."""
    agg: dict[str, dict[str, Any]] = {}
    for _tid, t in (run.get("tasks") or {}).items():
        bucket = t.get(key)
        if bucket is None:
            continue
        a = agg.setdefault(bucket, {
            "tasks": 0, "ok": 0, "failed": 0, "skipped": 0, "salvaged": 0,
            "duration_s": 0.0, "tokens": 0, "cost_usd": 0.0,
        })
        a["tasks"] += 1
        status = t.get("status")
        if status in ("completed", "exited"):
            a["ok"] += 1
        elif status in ("failed", "spawn-failed"):
            a["failed"] += 1
        elif status == "skipped":
            a["skipped"] += 1
        elif status in ("salvaged", "timed_out_idle", "timed_out"):
            a["salvaged"] += 1
        a["duration_s"] += float(t.get("duration_s") or 0)
        telemetry = t.get("telemetry") or {}
        a["tokens"] += int(telemetry.get("total_tokens") or 0)
        a["cost_usd"] += float(telemetry.get("total_cost_usd") or 0)
    return agg


def _agg_lines(agg: dict[str, dict[str, Any]]) -> list[str]:
    lines = []
    for name in sorted(agg):
        a = agg[name]
        line = (f"  {name:<12} tasks={a['tasks']}  ok={a['ok']} "
                f"failed={a['failed']} skipped={a['skipped']} "
                f"salvaged={a.get('salvaged', 0)}  "
                f"busy={round(a['duration_s'], 1)}s")
        if a["tokens"]:
            line += f"  tokens={a['tokens']} (measured)  cost=${round(a['cost_usd'], 4)}"
        lines.append(line)
    return lines


def by_agent_report(run: dict[str, Any]) -> str:
    """Per-runner aggregation: who is loaded, who fails, who burns budget.

    When tasks resolved a model, a parallel ``by model:`` rollup is appended —
    the empirical record of which model did which work (Pillar 4's read-only
    feedback; the coordinator never re-sorts pools on it)."""
    lines = [f"agents: {run['run_id']}"]
    lines += _agg_lines(_aggregate_tasks(run, "runner"))
    model_agg = _aggregate_tasks(run, "model")
    if model_agg:
        lines.append("by model:")
        lines += _agg_lines(model_agg)
    return "\n".join(lines)


def model_stats(runs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Aggregate every model-tagged task across runs: the empirical track record
    behind ``pigeon metrics --by-model``. Returns a JSON-able dict per model."""
    agg: dict[str, dict[str, Any]] = {}
    for run in runs:
        rid = run.get("run_id")
        for _tid, t in (run.get("tasks") or {}).items():
            m = t.get("model")
            if not m:
                continue
            a = agg.setdefault(m, {
                "tasks": 0, "ok": 0, "failed": 0, "duration_s": 0.0,
                "tokens": 0, "cost_usd": 0.0, "_runs": set(),
            })
            a["_runs"].add(rid)
            a["tasks"] += 1
            status = t.get("status")
            if status in ("completed", "exited"):
                a["ok"] += 1
            elif status in ("failed", "spawn-failed"):
                a["failed"] += 1
            a["duration_s"] += float(t.get("duration_s") or 0)
            tel = t.get("telemetry") or {}
            a["tokens"] += int(tel.get("total_tokens") or 0)
            a["cost_usd"] += float(tel.get("total_cost_usd") or 0)
    out: dict[str, dict[str, Any]] = {}
    for m, a in agg.items():
        decided = a["ok"] + a["failed"]
        out[m] = {
            "tasks": a["tasks"], "ok": a["ok"], "failed": a["failed"],
            "runs": len(a["_runs"]),
            "win_rate": round(a["ok"] / decided, 3) if decided else None,
            "avg_duration_s": (round(a["duration_s"] / a["tasks"], 1)
                               if a["tasks"] else 0.0),
            "tokens": a["tokens"], "cost_usd": round(a["cost_usd"], 4),
        }
    return out


def model_report(runs: list[dict[str, Any]], *, min_runs: int = 3) -> str:
    """Offline, read-only per-model track record — win-rate, speed, spend, ranked.

    Purely diagnostic: a human or agent reads it to edit a ``model_pool`` by hand.
    The coordinator NEVER consumes it to re-sort round-robin (PLAN.md ruling #8 —
    auto-demotion would starve a model on one transient failure). ``min_runs`` is
    the sample-size floor below which a model shows as 'insufficient data'."""
    stats = model_stats(runs)
    if not stats:
        return "by model: no model-tagged tasks recorded yet"
    enough = {m: s for m, s in stats.items() if s["tasks"] >= min_runs}
    thin = {m: s for m, s in stats.items() if s["tasks"] < min_runs}
    lines = [f"model track record (ranked by win-rate; min_runs={min_runs}):"]
    for m in sorted(enough, key=lambda m: (enough[m]["win_rate"] or 0,
                                           enough[m]["tasks"]), reverse=True):
        s = enough[m]
        wr = f"{round(100 * s['win_rate'])}%" if s["win_rate"] is not None else "n/a"
        line = (f"  {m:<32} win={wr:<4} n={s['tasks']} "
                f"({s['ok']} ok/{s['failed']} fail)  avg={s['avg_duration_s']}s  "
                f"runs={s['runs']}")
        if s["tokens"]:
            line += f"  tokens={s['tokens']}"
        if s["cost_usd"]:
            line += f"  cost=${s['cost_usd']}"
        lines.append(line)
    for m in sorted(thin):
        lines.append(f"  {m:<32} insufficient data "
                     f"(n={thin[m]['tasks']} < {min_runs})")
    lines.append("  (diagnostic only — edit your model_pool by hand; the "
                 "coordinator never auto-sorts on this)")
    return "\n".join(lines)


def critical_path_report(run: dict[str, Any]) -> str:
    """Duration-weighted longest chain — where wall-clock optimization pays."""
    tasks = run.get("tasks") or {}
    pseudo = [{"id": tid, "needs": t.get("needs") or []} for tid, t in tasks.items()]
    dur = {tid: float(t.get("duration_s") or 0) for tid, t in tasks.items()}
    best: dict[str, tuple[float, list[str]]] = {}
    for wave in _coord.compute_waves(pseudo):
        for tid in wave:
            prev: tuple[float, list[str]] = (0.0, [])
            for need in tasks[tid].get("needs") or []:
                if need in best and best[need][0] > prev[0]:
                    prev = best[need]
            best[tid] = (prev[0] + dur[tid], prev[1] + [tid])
    if not best:
        return "no tasks"
    total, path = max(best.values(), key=lambda v: v[0])
    wall = _elapsed(run.get("started_at"), run.get("finished_at"))
    lines = [f"critical path: {run['run_id']}  (wall-clock {wall})"]
    lines += [f"  {tid}  {round(dur[tid], 1)}s" for tid in path]
    lines.append(f"  total: {round(total, 1)}s — speeding up anything off this "
                 "chain does not move the wall-clock")
    return "\n".join(lines)


def list_runs(config: Config, sid: str | None = None) -> list[dict[str, Any]]:
    """All recorded run manifests (optionally for one session), oldest first."""
    runs_dir = config.coordinate_runs_dir
    if not runs_dir.is_dir():
        return []
    out = []
    for path in runs_dir.glob("*.json"):
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if sid is None or obj.get("sid") == sid:
            out.append(obj)
    return sorted(out, key=lambda o: (o.get("started_at") or "", o.get("run_id") or ""))
