# BUILD PLAN — finishing `docs/design/PLAN.md`

**Date:** 2026-06-17 · **Authority:** roadmap session
**Companion design:** [`adopt.md`](design.md) · **Runnable P0:** [`../To_do/adopt-p0.tasks.yaml`](../../To_do/adopt-p0.tasks.yaml)

This plan answers: *what in `PLAN.md` is done, what is left, and how pigeon
builds the rest* — small tasks, each with a crew, routed by model tier.

---

## 1. Status of `PLAN.md` (verified against the working tree)

**Phases A–F are SHIPPED (v0.5.0, suite green).** Evidence (file:line):

| Phase | Capability | Where it lives | State |
|---|---|---|---|
| A | Army P1+P2 — `model:`/`model_pool:`/`{model}`, `sha1(sid)` round-robin, preflight | `config.py:138-153`, `coordinate/__init__.py:245-541` | ✅ done |
| B | Diff materialization (`diffs_dir`, worktree `.diff`) | `config.py:103,386`, `coordinate/worktree.py:172-174` | ✅ done |
| B | Reasoning Bank — distill enrichment + per-model rollup | `distill.py:60-96` | ✅ done |
| B/4a | Per-model report in `by_agent_report` | `coordinate/reporting.py:187-266` | ✅ done |
| C | Army P3 — `receives:` deferred cross-wave injection | `coordinate/__init__.py:546-609,1339-1347` | ✅ done |
| D | Edit·Review·Verify — playbook convention + verify tasks | `skills.py`, `examples/edit-review-verify.tasks.yaml`, `tests/test_phase_d.py` | ✅ done |
| E | `pigeon metrics --by-model` w/ `min_runs` floor | `cli.py:237-242,613-620`, `reporting.py:238-266` | ✅ done |
| F | Verdict re-entry — `reentry:`/`max_reentry`, self-correct on `decisions.verdict=="rework"` | `coordinate/__init__.py:317-327,1297-1300,1444-1458` | ✅ done |

**Not code, ongoing:** Phase E's decision gate ("keep outcome-aware recall iff
`kind: pack` `saved_tokens` net-positive over ≥20 sessions") is an *observe-and-rule*
item — measured via the existing token ledger, not built. Keep accumulating sessions;
rule later. Nothing to implement.

**The one substantial unbuilt item:** the **`pigeon adopt`** addendum
(`PLAN.md` §Addendum, design in `adopt.md`, status PROPOSED). Everything below is
about building it.

---

## 2. Routing policy (applied to every task)

- **Free models** (`oc-mimo`, `oc-north`, `oc-nemotron`, `oc-nex`, `nv-nano`,
  `nv-minimax`, `nv-mixtral`, `nv-mistral-large`) → **small, well-scoped first
  drafts**, one function/file each, readonly, written as a *draft artifact* (never
  repo source). Their false starts are cheap and get filtered downstream.
- **`sonnet` (+ `agy`)** → **high-thinking integration**: synthesize the drafts into
  real, tested code; `agy` also does advisory review.
- **`opus`** → **coordinator** (interface contract up front) and **gatekeeper**
  (adversarial verify of the integration); last resort for fixes.

No auto-merge anywhere: a human runs `pytest` + `pyrefly` and merges the worktree
branch after the gate. Mirrors the audit posture in `full-audit.tasks.yaml`.

---

## 3. Locked decisions (resolving `adopt.md` §9 to the proposed defaults)

The WAVE-0 `contract` task hard-codes these so the parallel drafters cannot drift:

1. **Catalog** `.pigeon/adopt/catalog.json` — **gitignored** (scratch, re-derivable).
2. **Name collision** playbook vs adopted asset — **playbook wins, warn**.
3. **Skill/MCP parsing** — **shallow**: name + description + path (+ MCP: command/url
   + `has_secrets` flag). Defer deep `SKILL.md`/resource parsing.
4. **Scope precedence** project `.claude/agents` over user `~/.claude/agents` —
   **project wins, warn**.
5. **Trust** — discovery is read-only and always allowed; **use** requires the name in
   `adopt.allow` (default empty). MCP **inventory-only**, secrets never copied.

---

## 4. P0 / MVP — the runnable build (`adopt-p0.tasks.yaml`)

DAG: `contract → 6 first-drafts → integrate → gate + review-agy`.

| Task | Runner | Tier | Output |
|---|---|---|---|
| `contract` | `opus` | coordinator | interface contract → `reviews/adopt/contract.md` |
| `draft-subagent-parser` | `oc-nemotron` | free draft | `parse_claude_subagent()` draft |
| `draft-skill-parser` | `oc-north` | free draft | `discover_skills()` draft |
| `draft-mcp-parser` | `nv-mixtral` | free draft | `parse_mcp_configs()` draft (secret-safe) |
| `draft-human-view` | `nv-mistral-large` | free draft | `format_catalog()` draft |
| `draft-tests` | `oc-mimo` | free draft | `tests/test_adopt.py` draft (§8) |
| `draft-docs` | `nv-nano` | free draft | AGENTS/MANUAL/README draft |
| `integrate` | `sonnet` | integration | real `adopt.py` + config + CLI + coordinate wiring + tests, one worktree diff; `reentry≤2` self-checks tests |
| `gate` | `opus` | gatekeeper | adversarial verify diff vs contract/invariants → `reviews/adopt/gate.json` |
| `review-agy` | `agy` | advisory | independent second opinion |

**P0 delivers:** `pigeon adopt` discovery + catalog + human view (subagents +
skills), `adopt.allow` gate, same-runtime crew resolution, coordinate preflight
warning for unknown skill names, MCP inventory-only.

Run:
```
pigeon coordinate docs/To_do/adopt-p0.tasks.yaml --dry-run
pigeon coordinate docs/To_do/adopt-p0.tasks.yaml --skip-permissions --telemetry --budget-usd 25
```

---

## 5. P1 — materialize *after* P0 lands (interfaces depend on P0's real module)

A second `adopt-p1.tasks.yaml`, same shape. Scope (`adopt.md` §7 P1):

- **`--import <name>`** — copy a selected def into `.pigeon/memory/playbooks/`
  *without* `GEN_MARKER` (so `refresh` won't clobber it; it travels with the repo).
- **Cross-runtime projection** — new `skills._RENDERERS` targets (e.g. `opencode`,
  `gemini`) so an adopted Claude subagent can be projected for a non-Claude runner.
- **`pigeon agents` ↔ `pigeon adopt` cross-reference** in both human views.
- **Quiet the preflight (found dogfooding the timeout tournament).**
  `crew_skill_warnings` warns for *every* crew skill that isn't a playbook or
  allow-listed adopted asset — so it fires for legitimate plugin/registry skills
  the runner resolves natively (e.g. `code-architect-python`), and once *per
  reference* (5× for the same skill on one task). Fixes: dedupe per
  `(task, skill)`; and either discover plugin/registry skills, suppress unless
  adopt is actively in use, or make it opt-in. Cosmetic (non-blocking) but noisy.

Routing: free models draft the renderer stubs + import-copy fn + tests → `sonnet`
integrates → `opus` gates → `agy` advisory.

## 6. P2 — MCP pass-through (after P1)

- A task declares the adopted MCP servers it expects; `coordinate` **verifies** they
  are configured for that runtime before dispatch (config check, no connection).

Routing: one free-model draft of the verify-check + tests → `sonnet` integrates into
the coordinate preflight → `opus` gates.

## 7. P3 — pigeon as MCP client — OUT OF SCOPE

Substantial new subsystem (transport, lifecycle, auth, trust). Needs its own design
doc before any task plan. Not scheduled here.

---

## 8. Why this shape

Free models do **breadth** (six independent first drafts in parallel, ~free); the
contract up front means they cannot disagree on a name or schema; `sonnet` does the
**one** integration that needs real cross-file judgment (a single reviewable diff,
not six colliding worktrees); `opus` only spends tokens **gatekeeping** the result.
Every change moves as a pointer (draft artifact, materialized diff) — the
pointers-not-payloads invariant pigeon is built on.

---

## 9. Run-1 outcome (run `adopt-p0-2`, 2026-06-17) & lessons

**Result: the integration SUCCEEDED but the run reported failure at the finish line.**
`integrate` (sonnet) committed the complete P0 to branch
`pigeon/adopt-p0-2/integrate` (commit `213916a`, +884 lines: `adopt.py` 354,
`test_adopt.py` 437, plus config/cli/coordinate/init wiring). Verified out-of-band:
**full suite 373 passing** (342 + 31 new), `import pigeon.adopt` clean, no new
pyrefly errors. Diff materialized at
`.pigeon/coordinate/diffs/adopt-p0-2/integrate.diff`.

**Two real failures, both now fixed in the tasks files:**
1. **`readonly: true` is a hard "create no file" constraint** (`coordinate/__init__.py:110`),
   not just "don't touch source." Every task that must WRITE an artifact (the
   contract, the drafts, the gate) was self-contradictory; rule-following agents
   (opus `contract`, oc-north `skill-parser`) correctly refused the write. **Fix:**
   removed `readonly:` from all artifact-writing tasks; rely on the `doing` line
   "do not edit repo source." The `contract` text was salvaged from its handoff
   (`adopt-p0-3.json`) into `reviews/adopt/contract.md` by the coordinator.
2. **`integrate` hit `exit 124`** — `timeout -k 30 900` (15 min) killed sonnet
   during its *post-build* full-suite run; the code was already committed. **Fix:**
   `integrate` now runs only targeted checks (`import pigeon.adopt` +
   `pytest tests/test_adopt.py`); the full suite + pyrefly are the gate's/human's
   job. (Alternatively bump the `sonnet`/`opus` runner timeout in `.pigeon/config.yaml`.)
3. **Flaky free runners:** `nv-mixtral` 404'd, `nv-nano` produced no handoff →
   swapped to `oc-nex` / `nv-minimax`.

**As-built deviations** (integrate ran without the contract, which wasn't written
that run): public API names diverged from the contract (`parse_mcp_config`,
`discover`, `write_catalog(entries,config)`, `crew_skill_warnings`, `update_allow`,
`Config.catalog_path`) — behavior matches, names don't; reconcile in P1. Default
`adopt.sources` shipped **project-only** (dropped the design's `~/.claude/...`) —
conservative, but the user's home library isn't discovered until opted in. See
`reviews/adopt/contract.md` "as-built deltas".

**Gate (run `adopt-gate-2`, 2026-06-17):** opus gate = **changes-needed** ($2.94),
agy = concerns; both converged. Two blockers + cheap correctness items, all fixed on
the branch (commit `26dbda0`):
- **A (blocker):** MCP secrets could leak via `url` userinfo/query and `args` — only
  `env` was scrubbed. Fixed: redact url, drop args, broaden `has_secrets`.
- **B (blocker):** `update_allow` silently wiped `config.yaml` on a YAML error and
  stripped all comments. Fixed: refuse-on-unparseable + comment-preserving targeted
  edit.
- **C/D/E:** `parse_skill` GEN_MARKER gate; `discover` survives unreadable dirs;
  `adopt.allow` type-validated at load. +14 regression tests → **387 green**.
- Endorsed (not fixed): project-only default sources (avoids slurping
  `~/.claude.json` secrets); the allow-gate is **advisory-only by design** (§8) — the
  contract's "catalogued but unusable" overstated it (softened in `contract.md`).
  `resolve_adopted` is currently dead code retained for P1.

**State:** branch `pigeon/adopt-p0-2/integrate` = 2 commits (`213916a` build +
`26dbda0` gate-fixes), 387 tests green, gate verdict in
`reviews/adopt/gate.json`. No auto-merge — awaiting human merge to master.
