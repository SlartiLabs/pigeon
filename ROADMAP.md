# Roadmap

`pigeon` is a context layer for a fleet of coding-agent CLIs that never share a
context window. This roadmap reflects the **evidence-first** path to a public
launch: the engineering is mostly done; the launch is gated by *real numbers*,
not polish.

Status legend: ✅ shipped · 🔜 in progress · ⏳ planned · ❄️ deferred

## Shipped (through v0.5.x)
- ✅ Canonical context (`AGENTS.md` → generated `CLAUDE.md`/`GEMINI.md`), validated
  handoff contract, hybrid ripgrep + BM25 retrieval, token accounting.
- ✅ `coordinate`: multi-model "army" runners, `receives:` cross-wave injection,
  worktree isolation + diff materialization, pool throttling.
- ✅ Progress-aware timeouts (idle + hard cap) and **salvage-aware scheduling** —
  a timed-out task that committed work no longer skips its gate.
- ✅ `pigeon adopt`: discover/catalog/import existing subagents, skills, MCP
  servers (allow-list gated); cross-runtime skill renderers (Claude, opencode, agy).
- ✅ `pigeon probe`: free-runner qualification (respond/protocol/latency).
- ✅ Distilled memory + decision ledger; `pigeon metrics --by-model`.

## Toward launch (v0.6)
### Tier A — Evidence (the launch gate)
- ⏳ **Benchmark harness** — reproducible runs on real repos recording tokens /
  time / cost / success-rate / handoffs / interventions, committed under
  `benchmarks/`. Replaces the constructed-counterfactual figure with a real,
  repeatable one.
- ⏳ **Isolated comparative eval** — same agents, same tasks, *with vs. without*
  pigeon's coordination. Isolates the one variable; publishes methodology + raw data.
- ⏳ **Honest limitations / failure catalog.**

### Tier B — Correctness & hardening
- 🔜 `uv.lock` pinning · `ruff` lint/format · coverage raised then gated
  (overall ≥90%, `resolve.py` ≥95%) · structured fail-closed CI verdict ·
  PyPI trusted-publisher (OIDC) release workflow · version single-sourcing guard.

### Tier C — Adoption-enabling
- ⏳ Five-minute success path (install → init → run → see value).
- ⏳ Zero-config `pigeon-demo` repo (delegation + memory + retrieval + isolation).
- 🔜 PR template, this roadmap, PyPI classifier, repo metadata.

### Tier D — Architecture (independent)
- ⏳ Orchestrator extraction from the `coordinate` package (pinned engine, human-gated).

## Deferred / out of scope
- ❄️ Feature surfaces beyond the contract (compliance layer, viz dashboard,
  schema v1.2, etc.) — scope-creep into a platform on a small maintainer base.
- ❄️ Bare `gemini` CLI renderer (no subagent concept); MCP proxying/orchestration.
- ❄️ mkdocs site, standalone binary, chat community — premature pre-adoption.
- ❄️ `vs Aider/OpenHands` eval and full reliability-engineering — post-launch.

The launch is run as a **falsifiable experiment** with a kill/continue criterion
set in advance — a null result is information, not failure.
