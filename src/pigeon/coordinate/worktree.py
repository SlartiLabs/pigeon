"""Git worktree isolation: set up, commit, materialize the diff, tear down.

An isolated task runs in a throwaway git worktree on its own task branch, so
parallel agents cannot trample each other's files and a misbehaving agent only
wrecks a disposable checkout. On teardown the task's net change is committed to
its branch and materialized as a ``.diff`` on the shared tree (so a downstream
review task can receive it as a pointer); :func:`cleanup` reconciles worktrees
left behind by a crashed coordinator.

The low-level git primitive ``_git`` and the process-wide ``_GIT_LOCK`` live in
the package core (``__init__``) — shared with ``preflight`` — and are reached
here through the package module (``_coord._git``) so the established
``coordinate._git`` patch point governs every git call, including these.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

import pigeon.coordinate as _coord  # scheduler core: _git, _GIT_LOCK, list_runs

from ..config import Config


def cleanup(config: Config, keep_runs: int | None = None) -> dict[str, Any]:
    """Reconcile after crashes and bound history growth.

    * ``git worktree prune`` clears git's own stale bookkeeping;
    * worktree directories belonging to runs that are not ``running``
      (crashed coordinators, SIGKILL) are force-removed — their *branches*
      are kept: committed work is never garbage;
    * with ``keep_runs``, only the N most recent run manifests (and their
      event streams) survive; logs are left for manual inspection.
    """
    removed_worktrees: list[str] = []
    pruned_runs: list[str] = []
    wt_root = config.coordinate_worktrees_dir
    if (config.root / ".git").exists() and shutil.which("git"):
        with _coord._GIT_LOCK:
            _coord._git(config.root, "worktree", "prune", check=False)
            if wt_root.is_dir():
                for run_dir in sorted(wt_root.iterdir()):
                    if not run_dir.is_dir():
                        continue
                    manifest_path = config.coordinate_runs_dir / f"{run_dir.name}.json"
                    status = None
                    if manifest_path.is_file():
                        try:
                            status = json.loads(
                                manifest_path.read_text(encoding="utf-8")).get("status")
                        except (OSError, json.JSONDecodeError):
                            status = None
                    if status == "running":
                        continue  # a live coordinator owns these
                    for wt in sorted(run_dir.iterdir()):
                        _coord._git(config.root, "worktree", "remove", "--force",
                                    str(wt), check=False)
                        shutil.rmtree(wt, ignore_errors=True)
                        removed_worktrees.append(f"{run_dir.name}/{wt.name}")
                    shutil.rmtree(run_dir, ignore_errors=True)
    if keep_runs is not None and keep_runs >= 0:
        runs = _coord.list_runs(config)
        for run in runs[: max(0, len(runs) - keep_runs)]:
            run_id = run.get("run_id")
            if not run_id:
                continue
            (config.coordinate_runs_dir / f"{run_id}.json").unlink(missing_ok=True)
            (config.coordinate_events_dir / f"{run_id}.jsonl").unlink(missing_ok=True)
            pruned_runs.append(run_id)
    return {"removed_worktrees": removed_worktrees, "pruned_runs": pruned_runs}


def _worktree_setup(config: Config, run_id: str, task_id: str) -> tuple[Path, str, str]:
    """Create a throwaway worktree + task branch off HEAD for one task.

    Isolated agents work on their own checkout — parallel tasks cannot
    trample each other's files, and a misbehaving agent wrecks a disposable
    copy, never the main checkout (the Copilot ``/delegate`` insight).

    Returns the worktree dir, its task branch, and the *base* commit the branch
    forked from. Teardown judges "did this task do work?" by whether the branch
    advanced beyond ``base`` — so work the agent COMMITTED itself is harvested,
    not orphaned by a clean-tree check (F8).
    """
    wt_dir = config.coordinate_worktrees_dir / run_id / task_id
    branch = f"pigeon/{run_id}/{task_id}"
    wt_dir.parent.mkdir(parents=True, exist_ok=True)
    with _coord._GIT_LOCK:
        _coord._git(config.root, "worktree", "add", "-q", "-b", branch, str(wt_dir), "HEAD")
        base = _coord._git(config.root, "rev-parse", "HEAD").stdout.strip()
    return wt_dir, branch, base


def _worktree_finish(
    config: Config, task_id: str, wt_dir: Path, branch: str, run_id: str = "",
    base: str = "",
) -> tuple[dict[str, Any], list[str]]:
    """Harvest handoffs, commit the task's work to its branch, remove the tree.

    Handoffs the agent appended inside its worktree are copied back to the
    main checkout *before* removal (they are gitignored, so the commit would
    not preserve them). An unchanged worktree leaves no branch behind.
    """
    harvested: list[str] = []
    handoffs_rel = config.handoffs_dir.relative_to(config.root)
    wt_handoffs = wt_dir / handoffs_rel
    if wt_handoffs.is_dir():
        config.handoffs_dir.mkdir(parents=True, exist_ok=True)
        for src in sorted(wt_handoffs.glob("*.json")):
            dest = config.handoffs_dir / src.name
            n = 1
            while True:
                try:
                    os.close(os.open(dest, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
                    break
                except FileExistsError:
                    dest = config.handoffs_dir / f"{src.stem}-wt{n}{src.suffix}"
                    n += 1
            tmp = dest.with_name(dest.name + ".harvest-tmp")
            shutil.copy2(src, tmp)
            os.replace(tmp, dest)  # readers never see a half-copied handoff
            harvested.append(str(dest.relative_to(config.root)))

    with _coord._GIT_LOCK:
        return _worktree_commit_and_remove(
            config, task_id, wt_dir, branch, harvested, run_id, base)


def _worktree_commit_and_remove(
    config: Config, task_id: str, wt_dir: Path, branch: str, harvested: list[str],
    run_id: str = "", base: str = "",
) -> tuple[dict[str, Any], list[str]]:
    # Commit any UNcommitted work, then judge "changed" by whether the branch
    # ADVANCED beyond its base — true whether the agent committed its own work
    # (F8) or left it dirty for us. A dirty-tree-only check orphaned self-
    # committed work: a clean tree read as "no work" → no diff, branch deleted.
    base = base or _coord._git(config.root, "rev-parse", "HEAD").stdout.strip()
    if _coord._git(wt_dir, "status", "--porcelain").stdout.strip():
        _coord._git(wt_dir, "add", "-A")
        _coord._git(wt_dir, "-c", "user.name=pigeon", "-c", "user.email=pigeon@local",
                    "commit", "-q", "-m", f"pigeon: task {task_id} ({branch})")
    head = _coord._git(wt_dir, "rev-parse", "HEAD").stdout.strip()
    changed = bool(base) and head != base
    info: dict[str, Any] = {"branch": branch, "changed": changed}
    if changed:
        info["commit"] = head[:7]
        # Diff base..head BY SHA — the net change the task made, whether it
        # arrived as the agent's own commits or ours. It must outlive
        # `worktree remove` (materialized on the shared tree) so a downstream
        # review task can receive it as a pointer. NEVER swallow a failure: a
        # changed branch that yields no diff is a contract breach on the data
        # path, recorded loudly instead of shipping nothing downstream.
        dproc = _coord._git(wt_dir, "diff", base, head, check=False)
        info["diffstat"] = _coord._git(
            wt_dir, "diff", "--stat", base, head, check=False
        ).stdout.strip()
        full = dproc.stdout
        if dproc.returncode != 0:
            info["diff_error"] = (
                f"git diff exited {dproc.returncode}: "
                + ((dproc.stderr or full).strip()[:500] or "<no output>")
            )
        elif not full.strip():
            info["diff_error"] = "changed branch produced an empty diff"
        else:
            diff_dir = config.coordinate_diffs_dir / (run_id or "run")
            diff_dir.mkdir(parents=True, exist_ok=True)
            diff_path = diff_dir / f"{task_id}.diff"
            diff_path.write_text(full, encoding="utf-8")
            info["diff"] = str(diff_path.relative_to(config.root))
    _coord._git(config.root, "worktree", "remove", "--force", str(wt_dir))
    if not changed:
        _coord._git(config.root, "branch", "-D", branch, check=False)
        info["branch"] = None
    return info, harvested
