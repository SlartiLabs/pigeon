# Changelog

All notable changes to `pigeon` (install name: `carrier-pigeon`) are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.5.2] — 2026-07-04

### Added
- `routing-log`: `pigeon routing-log` records, per task in every coordination run, the routing decision (runner/model, DAG depth, whether it carried `state.derived` residue) joined to the outcome (status, turns, cost, tokens) in `.pigeon/routing_log.jsonl`, and prints a probe: *do routings vary in ways that change outcomes?* (`--backfill` rebuilds from existing run manifests; `--json` for machine use). Observation-only, written best-effort at run finish; it never changes routing or breaks a run.

### Docs
- `docs/benchmarks/`: the carrier-comms study (the two-sided bounded law for carried reasoning residue) with a manuscript-grade report, a recomputable statistics appendix (Clopper-Pearson, Fisher/Barnard, Newcombe TOST), 11 figures, committed per-trial ledgers, and a draft manuscript under `docs/benchmarks/manuscript/`.

---

## [0.5.1] — 2026-06-18

### Added
- `adopt`: `pigeon adopt` discovers and catalogs existing Claude subagents, skills, and MCP servers (inventory-only) behind an allow-list trust gate; `--import <name>` copies an adopted asset into playbooks (unmarked, so `refresh` won't clobber it); deep `.claude/skills` parsing (body, tools, bundled resources).
- `adopt`: thin MCP pass-through — a task may declare `mcp: [names]`; coordinate warns (non-blocking) when a declared server isn't configured. Validation only — no connect/proxy/orchestration.
- `probe`: `pigeon probe` qualifies configured runners (ok / slow / protocol_fail / dead) into `.pigeon/probe.json`; `--free-only` skips the trusted CLIs. Advisory — never edits the pool.
- `coordinate`: progress-aware timeouts — in-process idle-watch + absolute hard cap (SIGTERM→grace→SIGKILL over the process group), default-off; salvage-aware scheduling — a worktree task that exits non-zero but committed a diff is `salvaged`, and its downstream review/gate runs against the materialized diff (`block_on_salvage` opts out).
- `skills`: cross-runtime renderers — project playbook pages to opencode and agy/antigravity, not just Claude (opt-in via `skills.targets`).
- `skills`: memory-page typing — pages declare `record_type` (skill/playbook/decision/reference); a decision/reference page is no longer mis-projected as a subagent, and an unknown type fails loud.
- `agents`/`adopt`: cross-reference between the two human views.

### Changed
- `coordinate`: the `readonly` constraint is isolation-aware — a shared-tree readonly task may write its artifact under `.pigeon/`; a worktree-isolated one stays findings-only.
- `coordinate`: `crew_skill_warnings` deduped per (task, skill) + `assume_known_skills` escape hatch.

### Fixed
- `coordinate`: timeouts and EOF-then-hang no longer bypass the caps (caps bound total subprocess lifetime); a timed-out task that already committed work no longer silently skips its downstream gate.

---

## [0.5.0] — 2026-06-17

### Added
- `coordinate`: opencode free-model army runners; per-model telemetry parsing ready.
- `coordinate`: worktree isolation fix — opencode runners can now read main-tree handoff.
- `config`: clear error when a config section is overridden by a scalar value.
- `docs`: v2 distribution plan (full + staged, claims-disciplined).
- `docs`: launch files — CONTRIBUTING, SECURITY, CODE_OF_CONDUCT (Contributor Covenant 2.1), and bug/feature issue templates.
- `chore`: project metadata — license, authors, repository URLs in `pyproject.toml`.

### Changed
- `pyproject`: distribution renamed `pigeon` → `carrier-pigeon` (the `pigeon` CLI command and import package are unchanged); version bumped 0.4.0 → 0.5.0.
- `docs`: README "what it saves" figures reconciled to the measured ledger — demo ~92.8% (~3,087 vs ~43,117 tokens, against a constructed-counterfactual baseline on this repo's 6,302 source LOC); removed the never-measured near-empty-repo figure.

---

## [0.4.0] — 2026-06-13

### Added
- `coordinate`: pool-throttle enforcement — parallel slots are hard-capped at `parallel_limit`.
- `coordinate`: verdict-and-fix re-entry — a `reentry:` task re-queues itself on `verdict: rework` (prior fix list injected) up to `max_reentry`.
- `coordinate`: harvest agent-committed worktree work (F8).
- `coordinate`: efficient handback lookup (U4) + worktree-prune preflight (U5).
- `coordinate`: package split — scheduler + `reporting` / `worktree` / `telemetry` sub-modules.
- `handoff`: schema version gate + `pigeon migrate`; fix schema `$id` (DD D1).
- `config`: guard vector key, `env_allowlist` default-on, validate config at load (DD D3/S2/U7).
- `security`: confine pointer resolution to the repo root (S1).
- `mcp`: clamp `coordinate_run` `parallel_limit` (U3).
- `tests`: DAG-invariant + telemetry-parser property tests.
- `tests`: env default excludes secrets; `null` opts out (completes S2).
- `ci`: GitHub Actions pipeline (pytest + pyrefly + demo); fix two pyrefly errors.
- `context`: AGENTS.md repo-map updated for coordinate package split.

### Changed
- `coordinate`: materialise worktree diff by SHA; surface failures loudly.
- `coordinate`: parse opencode usage telemetry (tokens/cost shape).
- `coordinate`: measure claude-family runner telemetry; warn when unmeasured.
- `handoff/config`: address advisory review nits.

---

## [0.3.0] — 2026-06-13

### Added
- `observability`: `metrics --by-model` breakdown.
- `coordinate`: agent CLI auto-discovery (Phase E).

---

## [0.2.0] — 2026-06-13

### Added
- `coordinate`: first-class multi-model "army" support (Army P1+P2).
- `coordinate+distill`: diff materialisation + Reasoning Bank core (Phase B).
- `coordinate`: `receives:` cross-wave pointer injection (Army P3 / Phase C).
- `review pipeline`: `code-reviewer` + concordance playbooks; edit-review-verify example (Phase D).
- `docs`: army DESIGN + roadmap PLAN records; hardened army runners.

---

## [0.1.3] — 2026-06-12

### Added
- Auto-detect agent CLIs when generating pointer files (`CLAUDE.md` / `GEMINI.md`).

---

## [0.1.2] — 2026-06-12

### Fixed
- Schema upgrade, agy telemetry parsing, and readonly containment from live-testing hardening.

---

## [0.1.1] — 2026-06-12

### Changed
- Runner routing: never default to a metered CLI.

---

## [0.1.0] — 2026-06-12

### Added
- Initial release: carrier for cross-model agent context.
- Canonical context layer (`AGENTS.md` → generated `CLAUDE.md` / `GEMINI.md`).
- Validated handoff contract (JSON Schema, append-only log).
- Hybrid ripgrep + BM25 retrieval.
- Token instrumentation and `.pigeon/metrics.jsonl` accounting.
- `pigeon` CLI (`agentctx` kept as alias).

---

[0.5.2]: https://github.com/SlartiLabs/pigeon/compare/v0.5.1...v0.5.2
[0.5.1]: https://github.com/SlartiLabs/pigeon/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/SlartiLabs/pigeon/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/SlartiLabs/pigeon/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/SlartiLabs/pigeon/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/SlartiLabs/pigeon/compare/v0.1.3...v0.2.0
[0.1.3]: https://github.com/SlartiLabs/pigeon/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/SlartiLabs/pigeon/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/SlartiLabs/pigeon/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/SlartiLabs/pigeon/releases/tag/v0.1.0
