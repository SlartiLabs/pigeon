<img width="900" height="675" alt="image" src="https://github.com/user-attachments/assets/6b215b7f-0e83-4c80-856c-742be2b3f1d0" />


# pigeon

Carrier for cross-model agent context (formerly **agentctx**; the `agentctx`
command remains as an alias). Like its namesake, pigeon delivers a small,
bounded message — never the whole library. Lets multiple AI runtimes (Claude Code,
Antigravity, Codex) and their sub-agents **share project context and hand work
to each other efficiently** — minimal tokens, no re-transmission of state,
validated messages. Small enough to live inside any repository.

The canonical project context is [`AGENTS.md`](AGENTS.md); this README is the
narrative tour. **The complete reference — every command, config key, tasks-file
field, MCP tool, and troubleshooting table — is [`docs/MANUAL.md`](docs/MANUAL.md).**

> **Field note (June 2026).** When Google sunset Gemini CLI in favor of
> Antigravity, repos using agentctx needed **zero changes**: Antigravity reads
> the canonical `AGENTS.md` natively, and the generated `GEMINI.md` pointer
> doubles as its override file. Single-sourcing the context is the point —
> tools come and go; the contract stays.

**Status:** beta. Built for the author's own multi-agent work and published
as-is — MIT, PRs welcome, no support SLA implied. The installed package is the
single source of version truth (`pigeon --version`).

## Design in one paragraph

Three decoupled layers. (1) **Canonical context** — plain repo files every CLI
already reads, single-sourced so there is no drift. (2) **Handoff contract** — a
JSON-Schema-validated message carrying sparse state deltas plus *pointers*
(never payloads), because separate CLIs share no memory: the contract is the
filesystem, not anyone's context window. (3) **Retrieval** — hybrid lexical
(ripgrep) + BM25 over the repo and a generated manifest. Vector retrieval is
deferred; the lightweight derived wiki-link graph (`graph.py`) — `[[wiki-links]]`
+ handoff provenance → `graph.json` — ships today. The guiding rule: **start
simple, measure token cost, and only graduate to heavier machinery where
measurement proves it is the bottleneck.**

## Install

The package is published on PyPI as **`carrier-pigeon`** — the bare `pigeon`
name is already taken there:

```bash
pip install carrier-pigeon            # from PyPI
# or editable from source:
python -m pip install -e .            # runtime
python -m pip install -e ".[dev]"     # + pytest
# optional extras:
#   .[tokens]  exact token counts via tiktoken (else a deterministic heuristic)
#   .[vector]  local vector retrieval (off by default; see config)
#   .[mcp]     `pigeon mcp` — serve the contract over the Model Context Protocol
#   .[tui]     `pigeon status --tui` — full-screen terminal dashboard
```

Requires Python ≥ 3.11 and [ripgrep](https://github.com/BurntSushi/ripgrep)
(`rg`) on `PATH` for the lexical layer. Without `rg`, retrieval degrades to
BM25-only and stays fully offline. If `rg` is shadowed or not on `PATH`, set
`PIGEON_RG=/path/to/rg` (legacy `AGENTCTX_RG` also works) or `retrieval.ripgrep_path` in config.

`uv` is the preferred installer if available (`uv pip install -e ".[dev]"`).

## Commands

```bash
pigeon init [PATH]                  # scaffold pigeon into a repo (idempotent)
pigeon refresh                      # rebuild manifest.json + sync CLAUDE.md/GEMINI.md
pigeon retrieve "validate handoff"  # hybrid ripgrep + BM25; --top-k N, --json
pigeon retrieve "auth" --scope history --since 2026-06-01   # episodic log only
pigeon distill [SID]                # handoffs+runs -> committed memory files
pigeon handoff --sid s1 --from Planner --to Executor \
    --done analyze --done design --doing implement \
    --artifact repo://AGENTS.md --decision auth=oauth2_pkce \
    --context-ref manifest@HEAD       # build, validate, append; prints token cost
pigeon handoff --validate path.json # validate an existing handoff (exit 2 on failure)
pigeon handoff --json-in - --no-write < handoff.json   # validate piped JSON, print, don't append
pigeon metrics                      # token-accounting report
pigeon demo                         # whole-MVP acceptance over this repo's real files
pigeon coordinate tasks.yaml        # fan tasks out to agent CLIs in parallel
pigeon runs [SID] [--json]          # recorded run manifests (status, exits, pointers)
pigeon mcp                          # serve the contract over MCP (stdio)
```

`make context` / `make test` / `make demo` / `make metrics` wrap the above.

### Use in another repo

```bash
cd /path/to/your/repo
pigeon init . --with-hook        # scaffolds .pigeon/, schema, starter AGENTS.md
# edit AGENTS.md (fill the TODOs) and .pigeon/config.yaml (include globs)
pigeon refresh                   # manifest + CLAUDE.md/GEMINI.md
pigeon retrieve "your query"
```

`init` is idempotent (existing files are skipped unless `--force`); `--with-hook`
installs a pre-commit hook that re-runs `refresh`. `retrieve` and `metrics` also
work with no scaffolding at all via `pigeon --root /path/to/repo …`.

### Coordinate: parallel agent CLIs

`pigeon coordinate tasks.yaml` writes one validated handoff per task, then
spawns each task's runner CLI (`claude` / `agy` / `opencode`; argv templates in
`coordinate.runners`) concurrently with prefixed live output and per-task logs.
A safety preflight refuses to spawn unless the repo is a `.git` checkout with
pigeon initialized; package-mutating tasks (`mutates_packages: true`) require
a conda env, virtualenv, or container; the same policy is embedded in every
handoff's `constraints`. Unattended flags (`--dangerously-skip-permissions`)
are appended only with explicit `--skip-permissions`.

**Runner routing — read this before your first real run.** A task with no
`runner:` is **refused** unless `coordinate.default_runner` is set: a name
routes all unassigned tasks there, a *list* round-robins across it. Spread
load off your metered CLI:

```yaml
coordinate:
  default_runner: [agy, opencode]   # claude only where a task asks for it
```

Mark review/audit tasks `readonly: true` — pigeon injects a read-only
constraint *and* runs them in a worktree by default, so a contract violation
(an agent or its subagent writing anyway) is contained to a throwaway branch,
never the working tree. The constraint is isolation-aware: a `readonly` task on
`isolation: shared` may still write its findings artifact under `.pigeon/`,
while the default worktree form is findings-only. `pigeon refresh` also upgrades a stale on-disk
`handoff.schema.json` in place, so repos scaffolded under older releases
accept current handoff fields like `crew`.

Cost containment is layered: `--budget-tokens/--budget-usd` are hard
ceilings but count **measured** spend — pair them with `--telemetry` (or
per-task `telemetry: true`) or they cannot see untracked runners. How an agent
staffs its work internally is its own judgment — contract a `crew:` when
you want that decided deterministically, and use budgets + telemetry as
the spend backstop.

Tasks may declare `needs: [other-id]` — an acyclic dependency graph. A task
launches once everything it needs has exited 0; everything downstream of a
failure is skipped, never run. Tasks without edges stay fully parallel.

`isolation: worktree` runs a task in a throwaway git worktree on branch
`pigeon/<run_id>/<task_id>`: parallel agents cannot trample each other, and
a rogue agent wrecks a disposable copy. Work is committed to the task branch
(diffstat in the manifest), handoffs written inside the worktree are harvested
back, and an unchanged run leaves no branch behind.

Two guards bound a run: children inherit `PIGEON_DEPTH`, and a child trying
to coordinate past `coordinate.safety.max_depth` (default 1) is refused — no
agent fork-bombs. `--budget-tokens` / `--budget-usd` set hard ceilings on
telemetry-measured spend: once crossed, nothing new launches and the
remainder is recorded as skipped.

### Memory: distill + temporal retrieval

`pigeon distill [SID]` consolidates the episodic log (handoffs + run
manifests) into deterministic Markdown under `.pigeon/memory/` — per-session
records and a cross-session decision ledger with provenance. Memory is
**committed** (the events themselves are gitignored), so distilled knowledge
survives a clone, and being Markdown it is retrievable like any other context:

```bash
pigeon retrieve "what did we decide about auth" --scope memory
pigeon retrieve "build-api" --scope history --since 2026-06-01
```

Scopes: `code` (the repo), `history` (raw handoffs + runs), `memory`
(distilled), `all` (default, the union).

### Crews and skill projection

Tasks can contract their staffing: a `crew:` block (validated by handoff
schema 1.2) names the skills to load and the subagents to dispatch, with
optional verdict gates. The receiving agent spawns them via its own native
mechanism — but *who* runs is decided in the contract, deterministically.

Skill names resolve against one knowledge tree: playbook pages in
`.pigeon/memory/playbooks/` that declare YAML frontmatter (`name`,
`description`, optional `tools`) are **projected** by `pigeon refresh` into
each runtime's native subagent format (Claude Code: `.claude/agents/<name>.md`;
more targets via `skills.targets` config). One canonical page, every CLI's
dialect, drift impossible. Hand-written agent files are never clobbered.

Different runners mean different finetuning — exploit it with a
**tournament**: same `doing`, N runners, isolated worktrees, one judge:

```yaml
sid: tourney
tasks:
  - {id: api-claude,  runner: claude,   doing: &t implement /v1/exchange-events,
     isolation: worktree, telemetry: true}
  - {id: api-agy,     runner: agy,      doing: *t, isolation: worktree, telemetry: true}
  - {id: api-opencode, runner: opencode, doing: *t, isolation: worktree, telemetry: true}
  - id: judge
    runner: claude
    needs: [api-claude, api-agy, api-opencode]
    doing: >
      compare branches pigeon/<run>/api-* (diffstats in the run manifest),
      pick the winner, record the choice as a decision in your hand-back
    crew:
      subagents:
        - {role: correctness-judge, skill: advanced-python-backend}
        - {role: security-judge,    skill: security-audit}
```

Three solutions on three branches, measured cost per contestant, a staffed
judge, and the verdict lands in the decision ledger via `pigeon distill`.

### Watching a run

`pigeon status [SID] --watch` is a glanceable, daemon-free view of the
latest run — it just re-reads the atomically-updated run manifest:
state glyphs, elapsed times, measured budget, branches, return handoffs,
and what each queued task is waiting on. No progress percentages: an LLM
task has no honest %. Detaching never touches the run. `pigeon plan`
shows the same shape *before* dispatch.

With the `[tui]` extra, `pigeon status --tui` opens a full-screen Textual
dashboard — task table (arrows/`j`/`k`), the selected task's live log tail,
header with budget — still a pure reader of the same files, so a finished
run replays identically to a live one. Post-mortems come from the event
stream: every run also appends `coordinate/events/<run_id>.jsonl`
(`run.started`, `handoff.dispatched`, `task.*`, …), and `pigeon runs`
renders it as `--timeline` (where did time go), `--by-agent` (who is
loaded, who fails, who burns budget), and `--critical-path`
(duration-weighted chain that bounds the wall-clock).

### Operations

Exit codes: `0` all green · `1` task failures / invalid handoffs / budget
skips · `2` refused (preflight, bad tasks file) · `130` aborted (Ctrl-C —
spawned agents are terminated, the manifest is marked `aborted`).

After a crash (`SIGKILL`, OOM), `pigeon cleanup` reconciles: orphan
worktrees of non-running runs are removed (their **branches survive** —
committed work is never garbage), and `--keep-runs N` prunes old run
manifests + event streams. `pigeon metrics --prune N` bounds the
accounting log.

Two hardening knobs: task/session ids are restricted to `[A-Za-z0-9._-]`
(they become filenames, branches, and CLI args), and
`coordinate.env_allowlist` switches agents from inherit-everything to a
strict allowlist plus a functional baseline (`PATH`, `HOME`, …) — secrets
in the operator's shell stay out of spawned agents' reach.

Merging parallel branches is deliberately *not* automatic: pigeon records
each task's branch + diffstat in the manifest, and the judge pattern (see
the tournament) decides; a deterministic `pigeon merge` helper for the
conflict-free case is on the 0.6 roadmap.

### The brain: pack, playbooks, graph

`pigeon pack "<task>"` answers the question retrieval can't: *which context
space should the agent load before work begins?* It assembles one bounded
bundle — distilled memory, the manifest repo map, code slices, recent
history — deduplicated and cut to `--max-tokens`, written under
`.pigeon/context/`. Coordinate tasks opt in with `pack: true`, attaching
the bundle to their handoff so spawned agents start warm.

`.pigeon/memory/playbooks/` holds procedural memory: short Markdown
routines, committed and shared between humans and agents. Set
`coordinate.auto_distill: true` and every run consolidates itself on finish
(the sleep cycle).

`pigeon graph "<query>" --hops N` walks a **derived** entity graph —
sessions, decisions, artifacts, agents, and memory pages connected by
`[[wiki-links]]` (the memory directory is an Obsidian-compatible vault).
Edges carry provenance back to source handoffs; unresolved links become
stub nodes (memory worth writing). The graph is `graph.json`, regenerated
by every distill — multi-hop reasoning from a clone, offline, no Neo4j.

With `--telemetry` (or per-task `telemetry: true`) each runner's JSON-output
flags are appended and the child's **measured** token usage and cost are mined
from its output, recorded in the run manifest, and appended to `metrics.jsonl`
as `agent_run` events — so `pigeon metrics` reports both what pigeon
transmitted and what the agents actually consumed, in separate ledgers.

Every run records a live, atomically-updated manifest under
`.pigeon/coordinate/runs/<sid>-<n>.json` — per-task status
(`queued/running/completed/exited/failed/skipped`), exit codes, durations,
telemetry, log + handoff pointers. A task that appends a valid handoff back to
`Coordinator` counts as `completed`; one that merely exits 0 is `exited`.
Inspect with `pigeon runs`.

### MCP server

```bash
pip install -e ".[mcp]"
claude mcp add pigeon -- pigeon --root /path/to/repo mcp
# servers connect at session startup — restart the session after adding
```

Pigeon **works as an MCP server**: any MCP client (Claude Code, Codex, Gemini
CLI, opencode, IDEs) gets **13 native tools** over stdio — `retrieve`, `pack`,
`coordinate_plan` / `coordinate_run` / `coordinate_status`, `handoff_write` /
`handoff_read` / `handoff_validate`, `distill`, `graph_query`,
`metrics_summary`, `repo_manifest`, and `refresh` — the entire contract
without shelling out, through the same validation and token-accounting paths
as the CLI. Coordinate's live output goes to stderr so the protocol stream
stays clean, and config is re-read per call (no server restarts on config
edits).

The coordinator loop for an orchestrating agent: `coordinate_plan` (look
before leaping) → `coordinate_run` (budgets + telemetry on) →
`coordinate_status` → `distill`. Full tool signatures in
[`docs/MANUAL.md` §7](docs/MANUAL.md#7-the-mcp-server).

## Layout

```
AGENTS.md                  canonical context — single source of truth
CLAUDE.md / GEMINI.md      generated pointers, one per agent CLI on PATH
                           (auto-detected; Codex/opencode read AGENTS.md directly)
.pigeon/                   contract dir (repos scaffolded before the rename
                           use `.agentctx/` — honored forever, never migrated)
  config.yaml              paths, retrieval settings, feature flags
  manifest.json            generated deterministic manifest (gitignored)
  handoff.schema.json      JSON Schema (draft 2020-12) for handoffs
  handoffs/                append-only log: <sid>-<n>.json (gitignored)
  metrics.jsonl            token-accounting log (gitignored)
src/pigeon/                manifest / context / handoff / resolve / retrieval / tokens / cli
                           + coordinate / distill / graph / pack / skills / mcp_server / tui
scripts/refresh-context.sh regenerate manifest + sync context (wire to pre-commit)
```

### Pointers

Handoffs carry pointers, resolved on demand by `resolve.py`:

- `repo://<relpath>` — relative to the repo root
- `file://<abspath>` — absolute file URL
- `<path>` — a bare path, resolved against the repo root
- `manifest@HEAD` / `manifest@<gitrev>` — the generated manifest (latest / at a revision)
- `s3://<bucket>/<key>` — only with `resolve.allow_s3: true` and the `boto3` extra

### Pre-commit hook

Keep generated context fresh automatically:

```bash
ln -sf ../../scripts/refresh-context.sh .git/hooks/pre-commit
```

## Why these choices

- **Heavy graph (Graphiti / GraphRAG) is deferred.** Fast-churn repos rewrite
  state every few minutes; a knowledge graph's LLM-based ingestion cost is
  wasted on state that doesn't sit still. Its payoff needs a high
  read-to-write ratio. The lightweight derived wiki-link graph in `graph.py` —
  `[[wiki-links]]` + handoff provenance → `graph.json` — ships today; it
  needs no LLM and no external service.
- **JSON, not YAML, for the contract.** Every model's tool-calling is trained
  heavily on JSON; YAML's significant whitespace is a cross-model failure mode.
  (Config is YAML only because it is human-edited.)
- **Pointers need a resolver**, so one ships — pointers are never an assumption.
- **Measure, don't assume.** Every handoff and retrieval is token-accounted
  against a naive baseline; `pigeon metrics` and `pigeon demo` print the numbers
  on your actual repo (the channel counterfactual, not net savings; see below).

## What it costs, and what it is for (measured)

**pigeon does not save you tokens.** We measured it on real held-out tasks, and adding
pigeon is token-neutral to mildly negative (roughly +8% to +59% USD, with success
unchanged). The arithmetic is why: total cost is `work + N * overhead`, the overhead term
cannot go negative, so cost approaches parity from above and never crosses into savings. If
you came for a "saves X%" headline, this is not it, and the benchmark below will tell you so
in numbers you can reproduce.

What pigeon *is* for is the thing tokens cannot buy back: **carrying reasoning the next
agent cannot re-derive.** Two results bound this precisely, both pre-registered and
reproducible:

- **Cross-model capability.** A constraint given only to the first agent and never written
  into the code survives a heterogeneous chain (Claude, then a free model, then Antigravity)
  only when pigeon carries it: 5/5 held-out passes with the bridge, 0/5 without.
- **A two-sided bounded law.** The carried `state.derived` residue is necessary *if and only
  if* the reasoning left no recoverable trace in the artifacts. Confirmed as a superiority
  result where it is needed (8/8 with residue vs 0/8 without, Fisher exact p < 0.001) and as
  equivalence tests where it is not (residue is redundant when the constraint is recoverable
  from the code, whether shallow or deep, TOST-confirmed at a 0.20 margin).

So the value proposition is a rule, not a discount: **spend channel tokens only on what the
receiver cannot cheaply regenerate, and point at everything else.**

The channel itself *is* efficient (pointers, not payloads). `pigeon demo` prints exact token
totals for pigeon's 3-hop handoff versus a constructed counterfactual that re-transmits every
pointer's content as prose and sends whole files instead of ranked slices (about 3,087 vs
43,117 tokens on this repo). That is a channel-level comparison, not a real-world A/B: the
channel efficiency is real, but it does *not* net out to savings once coordination overhead
is counted, which is exactly what the real-task benchmark above measures. `pigeon metrics`
reports your own cumulative numbers from real usage.

### Reproduce the benchmark

The claims above are committed, not marketing. Substrates, held-out graders, per-trial
ledgers, exact statistics, and 11 figures live under [`docs/benchmarks/`](docs/benchmarks/):

- Report: [`docs/benchmarks/report.md`](docs/benchmarks/report.md); draft
  manuscript: [`docs/benchmarks/manuscript/`](docs/benchmarks/manuscript/).
- Recompute every statistic (exact Clopper-Pearson CIs, Fisher/Barnard, Newcombe TOST) from
  the committed result JSONs: `python3 docs/benchmarks/figures/stats_appendix.py`.
- Validate a substrate's held-out grader with no agents and no spend:
  `python3 docs/benchmarks/substrates/exp4c-depth/validate.py`.

Run them yourself; the numbers reproduce.

## Future (Phase 2 — deferred, not built)

These are documented intentionally and **not implemented** in this MVP:

- **Heavy graph layer (Graphiti + MCP server).** An optional bolt-on *on top
  of* the same store, exposing one shared knowledge-graph memory to all three
  CLIs via MCP. **Revisit only when** metrics show relational / multi-hop
  queries dominate *and* hybrid retrieval is returning too much — and apply it
  only to the stable core of a project, never to fast-churn state. (The
  lightweight derived wiki-link graph in `graph.py` is already implemented and
  ships today.)
- **Shared service store.** If file-based context outgrows the repo, promote the
  store to a small service all agents hit.

## Out of scope (now)

No graph database, no Neo4j/FalkorDB, no default vector store, no cloud infra,
no orchestration framework. The surface stays small enough to live inside any
repo.
