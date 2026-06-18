# DESIGN — progress-aware timeouts + salvage-aware scheduling

**Status:** PROPOSED (no code written). 2026-06-17.
**Provenance:** produced by a multi-model design tournament (`pigeon coordinate
docs/To_do/timeout-salvage-design.tasks.yaml`) — 3 decorrelated teams
(sonnet / agy / free, each a 3-racer + judge crew) on a code-grounded problem
statement, ruled by an opus meta-judge with an adversarial-evaluator crew. Team
proposals: `.pigeon/coordinate/reviews/timeout-design/proposal-*.md`. Build via
the Phase 0–3 plan below.
**Live validation:** team-free hit the GNU `timeout` wrapper (exit 124) *after*
writing its proposal — the run reported failure, yet the deliverable was produced
and the meta-judge consumed it because it was decoupled from the flaky team. That
is the exact "timeout-after-success → red run, salvageable work" bug this design
fixes, re-demonstrated by the very run that designed the fix.

---

## RULING — progress-aware timeouts + salvage-aware scheduling

**Meta-judge** (code-architect-python) · session `timeout-design` · 2026-06-17
**Crew:** adversarial-evaluator (code-architect-python) stress-tested every proposal
against the must-not-break invariants and the real source.
**Gate applied:** reward the design that *survives adversarial scrutiny*, not the
most elaborate one.

All four proposals were read; every load-bearing claim was re-verified against the
real code, not the proposals' own line numbers. Anchors below are confirmed by
direct read of `src/pigeon/coordinate/__init__.py`, `coordinate/worktree.py`,
`coordinate/reporting.py`, and `config.py`.

---

## TL;DR ranked verdict

| Rank | Team | Part A | Part B | Verdict |
|---|---|---|---|---|
| 1 | **sonnet** | `select` idle watch, thread-free, default-**disabled** | `info["diff"]` salvage gate, `salvaged` set, contract-respecting injection | **SURVIVES** (wounded, fixable) — the spine of the ruling |
| 2 | **agy** | supervisor thread, SIGTERM→grace→SIGKILL | over-fires on `changed`/`harvested`; defaults **enabled** | **WOUNDED** — donates the kill discipline + in-loop hard cap |
| 3 | **free** | opt-in posture (right instinct) | `rc==124`-only gate (dead on default path) | **DISQUALIFIED as written** — invents an async/`aiofiles`/`pydantic` engine |
| 4 | **judge** | per-*tool* timeouts | none | **DISQUALIFIED** — solves a different problem; no salvage |

**The recommended design = sonnet's spine + agy's in-loop hard cap & kill
discipline + two fixes that *no* proposal got (reporting aggregations and the
final-summary exit-code bookkeeping).**

---

## Ground truth the ruling rests on (verified file:line)

1. **`_run_task` is a synchronous, module-level function returning a bare `int`**
   (`coordinate/__init__.py:1089-1102`). It spawns `subprocess.Popen(... text=True,
   bufsize=1)` (L1123-1128), drains with a blocking `for raw in proc.stdout:`
   (L1141), `rc = proc.wait()` (L1148), and sets `status = "exited" if rc == 0 else
   "failed"` (L1172). No `self`, no `async`, no `pydantic`. → free's and judge's
   `async _run_task(self, …)`, `aiofiles`, `pydantic_settings`, `TimeoutConfig`,
   `RunnerTemplate`, `self.sid` are **invented**; their code blocks cannot be built
   against this engine without rewriting it.
2. **A pigeon-issued kill never returns 124.** `proc.terminate()`→ rc `-15`,
   `proc.kill()`→ rc `-9`. `124` is produced *only* by the GNU `timeout` binary.
   → any salvage/timeout rule gated on `rc == 124` (free §Part B, L262) is dead on
   pigeon's own kill path.
3. **The shipped runner templates are bare** (`config.py` `DEFAULT_CONFIG`,
   e.g. `["claude","-p","{prompt}"]`). The `timeout -k 30 N` wrapper from the
   problem statement exists **only if an operator hand-added it**. → sonnet leaning
   on "the `timeout` binary stays as the hard-cap backstop" is *not* a backstop for
   default configs. A fast-talking livelock (emits tokens, never goes idle) is
   **unbounded** unless an absolute cap lives inside the poll loop. This is the one
   place sonnet's Part A is genuinely incomplete.
4. **`info["diff"]` is the correct, tight salvage signal** (`worktree.py:176`): set
   *only* when the branch advanced **and** the diff is non-empty and `git diff`
   succeeded. `changed` (L149) is set on *any* branch advance — including the
   empty-diff contract-breach branch (L170) — and `harvested` is non-empty whenever
   a handoff was written. → sonnet's `info.get("diff")` gate fires for the
   motivating adopt-p0-2 case and does **not** over-fire; **agy's**
   `changed`/`harvested` gate over-fires (false-positive salvage with nothing to
   hand downstream).
5. **Reentry is structurally safe under every proposal**: it fires only on
   `rc == 0 AND verdict == "rework"` (L1510-1514). Salvaged/timed-out tasks keep
   `rc != 0`, so the branch is unreachable for them. No proposal corrupts reentry.
6. **Two gaps every proposal missed:**
   - **Reporting aggregations count by explicit string membership**
     (`reporting.py:51-52`: `ok = completed+exited`, `failed = failed+spawn-failed`;
     same pattern in the by-model / timeline rollups). A new `salvaged`/`timed_out`
     status is counted as *neither* and silently vanishes from every rollup. The
     `_STATUS_GLYPHS.get(status, "?")` catch-all (L74) only saves the per-task
     glyph, not the aggregate counts. → sonnet's "no change needed in reporting" is
     **false**.
   - **The final summary marks salvage as a hard failure.**
     `failed = [tid for tid, rc in results.items() if rc not in (0, None)]` (L1576)
     puts any `rc != 0` task — including a salvaged one — into `failed`, flips
     `run_status` to `"failed"` (L1599), prints `FAILED (exit {rc})` (L1590), and
     forces `return 1` (L1616). → unless this loop is amended, "downstream
     proceeds" still reports the run red and exits non-zero, defeating the purpose.

---

## RECOMMENDED DESIGN

### Part A — progress-aware timeout (sonnet spine + agy graft)

**Mechanism.** Replace the blocking drain at `coordinate/__init__.py:1141-1148`
with a poll loop that watches *both* idle silence and absolute elapsed time, and
keep supervision **inside `_run_task`** (no new threads):

```python
# thread the resolved timeouts in via _resolve_timeouts(config, runner) (new helper)
idle_s, hard_s, grace_s = _resolve_timeouts(config, runner)
started = time.monotonic()
last_output = started
kill_reason: str | None = None
# select on the RAW fd, not the bufsize=1 TextIOWrapper (see Risks)
fd = proc.stdout.buffer if hasattr(proc.stdout, "buffer") else proc.stdout
while True:
    if idle_s or hard_s:
        budget_idle = (idle_s - (time.monotonic() - last_output)) if idle_s else None
        budget_hard = (hard_s - (time.monotonic() - started))     if hard_s else None
        wait_s = min([w for w in (budget_idle, budget_hard, 5.0) if w is not None])
        ready, _, _ = select.select([fd], [], [], max(0.1, wait_s))
        now = time.monotonic()
        if idle_s and (now - last_output) >= idle_s:
            kill_reason = "idle";  _kill(proc, grace_s); break
        if hard_s and (now - started) >= hard_s:
            kill_reason = "hard";  _kill(proc, grace_s); break
        if not ready:
            continue
    raw = fd.readline()
    if not raw:            # EOF -> child ended
        break
    last_output = time.monotonic()
    ... decode/log/print exactly as today ...
rc = proc.wait()
```

- **`_kill(proc, grace_s)`** = `proc.terminate()` → wait up to `grace_s` →
  `proc.kill()` (agy's discipline; matches the existing `-k 30` semantics and gives
  the agent a window to flush/commit, which *raises* salvage rates). sonnet's bare
  `proc.kill()` is rejected — abrupt SIGKILL forfeits committed-but-unflushed work.
- **Three tiers, explicit:** `idle_timeout_s` < `hard_cap_s` (both in-loop) <
  `budget` ceiling (untouched, `BudgetTracker.exhausted()` at L1426 — gates *new
  launches*, never kills a running child). The in-loop `hard_cap_s` is the agy/free
  graft that covers the livelock case sonnet left unbounded (Ground-truth #3).
- **Status from a flag, not an exit code.** `_run_task` returns
  `tuple[int, str | None]` = `(rc, kill_reason)`; a new pure
  `_classify_status(rc, kill_reason)` maps `rc==0→"exited"`,
  `kill_reason=="idle"→"timed_out_idle"`, `kill_reason=="hard"→"timed_out"`,
  else `"failed"`. **Never** key off `rc==124` (Ground-truth #2). Two call sites
  (the `_execute` closures) update for the tuple — both are local, no public-API
  change.

**Config schema (default-disabled = byte-identical back-compat).** Add to
`DEFAULT_CONFIG["coordinate"]` (`config.py`):

```yaml
coordinate:
  idle_timeout_s: null     # null = disabled (back-compat). N = kill after N s of no stdout.
  hard_cap_s:     null     # null = disabled. Absolute in-loop ceiling (covers livelock).
  grace_kill_s:   30       # SIGTERM -> wait -> SIGKILL; matches the existing `-k 30`.
  timeouts:                # optional per-runner overrides
    opencode: { idle_timeout_s: 600, hard_cap_s: 3600 }
    opus:     { idle_timeout_s: null }   # opus reasons silently — keep idle off for it
```

`_resolve_timeouts(config, runner)` = per-runner override → global → `None`.
**All-null default → `select` never arms → the loop is functionally the blocking
drain it replaces → existing runs are unchanged.** This is sonnet's posture
(default-disabled), chosen over **agy's default 300s/1800s**, which would silently
start killing legitimately-quiet long tasks on upgrade — a back-compat regression.

### Part B — salvage-aware scheduling (sonnet, hardened)

**Detection rule** (in `_execute`, after `_worktree_finish` returns `info`):

```
salvaged  ⇔  rc != 0  AND  task.isolation == "worktree"  AND  info.get("diff")
```

Tight by construction (Ground-truth #4): `info["diff"]` is present only for a
real, non-empty, materialized diff on the shared tree. On hit:
`recorder.task(tid, status="salvaged", salvage_diff=info["diff"])`,
`recorder.event("salvage.detected", …)`, and a **loud banner** to stdout. Non-
worktree failures and clean/empty-diff worktree exits fall through to `"failed"`
unchanged. `recorder.task` does `.update()` under a lock (verified) so the
`"salvaged"` override of the earlier `"failed"` is thread-safe.

**New status values (additive):** `"timed_out_idle"`, `"timed_out"`, `"salvaged"`.

**Scheduler change** (`coordinate/__init__.py:1418-1525`): add a third set.

```python
succeeded: set[str] = set()
blocked:   set[str] = set()
salvaged:  set[str] = set()          # NEW
...
bad = deps[tid] & (blocked - salvaged)             # L1439: salvaged != blocked
...
if not (deps[tid] <= (succeeded | salvaged)):      # L1452: salvaged satisfies needs
    continue
...
# L1525, three-way:
if rc == 0:                       succeeded.add(tid)
elif _status_of(tid) == "salvaged": salvaged.add(tid)
else:                             blocked.add(tid)
```

**Downstream behavior — RULING on the open question.** Default = **proceed in
advisory mode, do not silently skip** (this is the whole point of the adopt-p0-2
motivation). A downstream task whose `needs` are met by `succeeded ∪ salvaged`
launches; if any satisfied dep is in `salvaged`, the task's handoff receives:
(a) the upstream `salvage_diff` **as a `repo://` pointer injected through the
existing `_spawn_prepare` / `_resolve_receives` / `_write_handoff_cmd` path**
(L1407, L1472) — staying inside the validated, append-only handoff contract (no
env-var side channel), and (b) a `state.salvaged_upstream: [tid,…]` marker so the
gate/review knows it is judging *materialized-but-unverified* work.

**Safety valve (the one piece of agy worth keeping):** a task may set
`block_on_salvage: true` to restore the old conservative cascade-skip for that
specific gate (e.g. a deploy gate that must never run on partial work). Default
`false`. This gives agy's `allow_salvaged` caution **inverted to the right
default** — proceed-advisory is the common case; opt *out* for the rare hard gate.

**Build note (honest gap):** `_spawn_prepare` runs only for tasks in the
`deferred` set (L1471-1472). Review/gate tasks that consume an upstream diff are
already deferred (they carry `receives:`/cross-wave `needs`), so injection reaches
them. The build must ensure any task that `needs` a worktree task *eligible to
salvage* is in `deferred`; otherwise its command is frozen up-front and the
pointer never lands. This is a one-line widening of the `deferred` predicate, not
a new mechanism.

### The two fixes no proposal had (mandatory, or the feature is invisible/red)

1. **Final summary** (`coordinate/__init__.py:1576-1616`): exclude salvaged from
   the hard-failure list and give it its own line/exit policy:
   ```python
   failed   = [t for t,rc in results.items() if rc not in (0,None) and t not in salvaged]
   salv     = sorted(salvaged)
   # per-task print: add a "SALVAGED (exit {rc}; diff at …)" branch before the FAILED branch
   run_status = "completed" if not failed and not skipped and not invalid else "failed"
   ```
   **Exit-code ruling:** a salvaged task does **not**, by itself, fail the run; the
   run's red/green is driven by genuine `blocked`/`failed` and by the outcome of the
   now-unblocked downstream gate. (A salvaged task with *no* consumer, or one with
   `block_on_salvage`, counts toward failure — there is nothing to validate it.)
2. **Reporting** (`coordinate/reporting.py:51-52` and the by-model / timeline
   aggregations): add `salvaged`/`timed_out*` to an explicit `salvaged` bucket and
   stop letting them fall between `ok` and `failed`. Add the glyphs to
   `_STATUS_GLYPHS` so they don't render as `"?"`.

### Invariants — preserved (verified)

- **`--dry-run`:** exits before the scheduler/`_run_task`; commands are built
  up-front by `_build_command`/`_write_handoff_cmd`. Supervision is pure runtime
  inside `_run_task` (never reached). Salvage injection is a spawn-time rewrite of
  a *deferred* task's handoff — the **same** class of mutation the engine already
  performs for cross-wave `receives:` and reentry fix-lists (L1407), so it does not
  weaken "deterministic up-front build" any more than today's deferred path does.
  Dry-run output is unchanged. ✓
- **Budget ceiling:** untouched hard cap at L1426-1434; orthogonal to the in-loop
  timers. Partial-run telemetry is still mined from the tail before the kill
  (L1152-1166). ✓
- **Append-only handoffs:** `_worktree_finish` harvests the agent's handoffs before
  commit regardless of rc; salvage adds a *pointer* into a downstream handoff via
  the validated builder — no rewrite of any existing handoff. ✓
- **Reentry:** fires only on `rc==0 && verdict=="rework"` (L1510); salvaged tasks
  have `rc!=0` → unreachable. A salvaged→rework loop is explicitly **out of scope**
  (see rejected agy incremental-resume). ✓

---

## Phased build plan

- **Phase 0 — mechanism, zero behavior change.** Add config keys (all `null`),
  `_resolve_timeouts`, `_classify_status`, change `_run_task` → `(rc, kill_reason)`
  and the `select`+elapsed poll loop reading the **raw** fd. With null defaults the
  loop is a no-op equivalent to the blocking drain. Update the two `_execute` call
  sites. *Gate: full existing suite green, byte-identical dry-run.*
- **Phase 1 — idle + hard cap live.** Wire `idle_timeout_s`/`hard_cap_s`/
  `grace_kill_s`, the `_kill` SIGTERM→grace→SIGKILL helper, statuses
  `timed_out_idle`/`timed_out`. Patch reporting aggregations + final-summary so a
  pure timeout is *labeled* (not `FAILED (exit -9)`) and counted.
- **Phase 2 — salvage detection + status.** `info["diff"]` rule in `_execute`,
  `recorder.task(status="salvaged", salvage_diff=…)`, event + loud banner. Final-
  summary `failed`-list exclusion + `SALVAGED` print line. Reporting `salvaged`
  bucket + glyph.
- **Phase 3 — salvage-aware scheduling.** `salvaged` set; cascade exemption
  (`blocked - salvaged`); readiness `deps[tid] <= (succeeded | salvaged)`; advisory
  diff-pointer injection + `salvaged_upstream` marker via `_spawn_prepare`; widen
  `deferred` predicate; `block_on_salvage` opt-out; run-level exit-code policy.
  *Gate: adopt-p0-2 replay — `integrate` killed-with-diff → `salvaged` → gate runs
  advisory against the materialized diff and passes → run exits 0.*

## Test plan

**Unit**
- `_resolve_timeouts`: absent keys → `(None,None,30)`; global set; per-runner
  override incl. per-runner `null` masking a global value.
- `_classify_status` matrix incl. the real kill codes: `(0,None)→exited`,
  `(-9,"idle")→timed_out_idle`, `(-9,"hard")→timed_out`, `(1,None)→failed`.
  Explicitly assert **no** branch keys off `124`.
- Poll loop: mock `select`+`time.monotonic` for (a) EOF → `kill_reason=None`,
  (b) idle fire → terminate→kill, (c) hard-cap fire on a never-idle stream
  (livelock), (d) all-null → no arming, output byte-identical to the blocking drain.
- Salvage rule: `rc!=0 + worktree + info["diff"]` → `salvaged`;
  `changed but empty-diff` (`diff_error`) → `failed` (regression guard against
  agy's over-fire); non-worktree `rc!=0` → `failed`.

**Integration** (extend `tests/test_coordinate_run.py`)
- Worktree task writes a file then is idle-killed → `salvaged`; downstream gate
  runs and its handoff `state.artifacts` includes the `repo://…diff` pointer and
  `state.salvaged_upstream`.
- `block_on_salvage: true` → downstream cascade-skips (old behavior restored).
- Non-worktree `rc=1` still cascades (regression).
- `--dry-run` prints identical commands with the feature configured.
- Reentry still fires only on `rc==0 && rework`; a salvaged task never self-re-enters.
- Reporting: a `salvaged` task is counted in the `salvaged` bucket, not lost; run
  with one salvaged-then-gated task exits 0; a salvaged task with no consumer exits 1.

## Risks / migration

- **`select` on a `bufsize=1` `TextIOWrapper` is a footgun** — select sees the raw
  fd while `readline()` reads the buffer; they can disagree. Read the **raw fd**
  (`proc.stdout.buffer`) in the poll loop and decode per line. (Missed by sonnet,
  which selected on the text wrapper.)
- **SIGKILL orphans grandchildren** (subshell runners). Harden with
  `start_new_session=True` on the `Popen` + `os.killpg` in `_kill`; note the
  existing `KeyboardInterrupt` path (L1532) only `terminate()`s direct children, so
  this is a pre-existing gap, improved not regressed.
- **Migration: none required.** All keys default `null`/`false`; new statuses are
  additive; downstream manifest readers already tolerate unknown statuses via the
  glyph catch-all (and the aggregations are now patched).

---

## What was rejected, and why

- **judge (whole proposal) — DISQUALIFIED, off-target.** Designs per-*tool*-call
  timeouts (`bash`/`pytest`/`grep`, `tool_overrides`, `get_timeout(tool_name=…)`)
  with `pydantic` `BaseSettings` and a `default_timeout_ms=120000` (the *harness*
  Bash default). It never touches `_run_task`, the scheduler, or `worktree.py`, and
  has **no Part B / salvage** at all. It is a meta-eval of two upstream proposals
  that were themselves mis-scoped. Contributes nothing buildable to this engine.
- **free (implementation) — DISQUALIFIED as written.** Right *instincts* (opt-in
  default, advisory mode) but the code invents an async engine: `await
  asyncio.create_subprocess_exec`, `aiofiles`, `async def _run_task(self,…)`,
  `pydantic_settings`, `RunnerTemplate`, `self.sid`, "read config from AgentDB."
  None exist; `grep` over `src/pigeon/` returns zero hits. Its salvage gate keys on
  `rc==124` only → dead on pigeon's own kill and on any default-config run. The
  opt-in/advisory *framing* survives and informed the ruling; the implementation
  does not.
- **agy — donor, not winner.** Keep its **SIGTERM→grace→SIGKILL discipline** and
  the **in-loop absolute hard cap** (which fixes sonnet's livelock gap). Reject:
  (1) defaults *enabled* (300s/1800s) — a silent back-compat regression on upgrade;
  (2) salvage on `changed`/`harvested` — over-fires on empty-diff contract breaches
  and handoff-only tasks; (3) the fabricated `124/126` exit-code mapping —
  `terminate()/kill()` yield `-15/-9`; (4) **incremental worktree resume**
  (`git worktree add <path> <branch>` on reentry) — unrequired scope and a genuine
  git footgun (`branch already checked out`/exists); the current code deletes the
  branch on a clean teardown (`worktree.py:178-179`), so the crash it "fixes"
  isn't there. `allow_salvaged` is kept but **inverted** to `block_on_salvage`
  (default-proceed, opt-out) to match the problem's "don't silently skip" mandate.
- **sonnet — adopted as the spine**, with three corrections it got wrong: it relies
  on a `timeout` binary that isn't in default configs (→ add the in-loop hard cap);
  it selects on a buffered text wrapper (→ read the raw fd); and it claims reporting
  needs no change (→ it does, in two places, or salvage is invisible and the run
  reports red).
