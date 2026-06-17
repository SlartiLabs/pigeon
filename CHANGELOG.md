# Changelog

All notable changes to `pigeon` (install name: `carrier-pigeon`) are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased] — v0.5.0

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

[Unreleased]: https://github.com/SlartiLabs/pigeon/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/SlartiLabs/pigeon/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/SlartiLabs/pigeon/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/SlartiLabs/pigeon/compare/v0.1.3...v0.2.0
[0.1.3]: https://github.com/SlartiLabs/pigeon/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/SlartiLabs/pigeon/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/SlartiLabs/pigeon/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/SlartiLabs/pigeon/releases/tag/v0.1.0
