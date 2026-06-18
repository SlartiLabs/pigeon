# DESIGN — `pigeon adopt` P1 (+ memory-page typing)

**Status:** PROPOSED → building. 2026-06-18. **Authoritative contract** for the
P1 crew build; the design wins on any conflict with the free-model drafts.
**Builds on:** the merged P0 (`src/pigeon/adopt.py`, `coordinate.crew_skill_warnings`,
`skills.py` projection) and resolves the over-warning found dogfooding the timeout
tournament. Scope is deliberately bounded; cross-runtime `_RENDERERS` targets are
**out of scope** (a later P1.5).

## Grounding (verified against the merged tree)
- `skills.py`: `parse_playbook(path)` → frontmatter (`name`/`description`/`tools`) +
  body; `playbooks(config)` lists pages under `.pigeon/memory/playbooks/` that have a
  `name`; `project_skills(config)` renders each via `_RENDERERS = {"claude": _render_claude}`
  to `config.skills.targets`; `GEN_MARKER` marks generated files.
- `adopt.py`: `discover`, `write_catalog`/`load_catalog`, `check_allow`, `resolve_adopted`,
  `update_allow`, `format_catalog`. P0 catalogs subagents+skills+MCP behind `adopt.allow`.
- `coordinate.crew_skill_warnings(config, spec)`: warns when a crew skill name is neither
  a playbook nor an allow-listed adopted asset — currently once **per reference** and for
  legit native plugin skills (e.g. `code-architect-python`), which is noise.

## Three features (all additive, default-safe, test-first)

### F1 — Memory-page typing: `record_type` + loud resolution (the user's #4)
- **Self-declaring pages.** `parse_playbook` reads an optional frontmatter key
  `record_type` ∈ {`skill`, `playbook`, `decision`, `reference`}. **Default when absent
  = `skill`** (back-compat: today every playbook page projects as a subagent).
- **Projection reads the declared type, not the path.** `project_skills` projects only
  pages with `record_type` in {`skill`, `playbook`}; a `record_type: decision`/`reference`
  page under `playbooks/` is **never** projected as a subagent (fixes the mis-projection
  class). An **unknown** `record_type` value is a **loud** `ValueError` at refresh, not a
  silent skip.
- **Loud crew resolution.** Add `skills.resolve_skill(config, name) -> page|None`. A crew
  skill name that resolves to neither a playbook page nor an allow-listed adopted asset is
  reported by `crew_skill_warnings` (F3) — the silent no-op is gone.
- Tests: page with each `record_type` parses; `decision` page not projected; unknown
  `record_type` → ValueError; absent → projects as today (regression).

### F2 — `pigeon adopt --import <name>...`
- Copy a discovered, allow-listed asset into `.pigeon/memory/playbooks/<name>.md` as a
  canonical page: frontmatter `name`/`description`/`record_type: skill` + the asset's body,
  **without `GEN_MARKER`** (so `refresh` treats it as hand-written and never clobbers it;
  it now travels with the repo and projects like a native playbook).
- Refuses (clear error, exit 2) if: the name isn't in the catalog; a playbook of that name
  already exists (no overwrite); or the name isn't allow-listed. MCP records are not
  importable (inventory-only) — clear message.
- Tests: import writes an unmarked page that `playbooks()` then lists and `project_skills`
  renders; re-import refuses; import of an un-allow-listed/unknown/MCP name refuses;
  `refresh` after import does not touch the imported page.

### F3 — Preflight de-noise (fixes the over-warning)
- `crew_skill_warnings` dedupes per `(task_id, skill_name)` (no more 5× per skill) and
  emits **one** concise advisory per unknown skill. A name that resolves via F1
  (`resolve_skill`) or `check_allow` produces no warning.
- A config escape hatch `coordinate.assume_known_skills: []` (default empty) lists skill
  names to treat as runner-native and never warn about (so a project that leans on plugin
  skills like `code-architect-python` can silence them without adoption).
- Tests: duplicate refs collapse to one warning; an `assume_known_skills` entry is silent;
  an imported (F2) skill is silent; a genuinely-unknown name still warns once.

## Invariants (must hold)
- `refresh` still only writes `GEN_MARKER` files; `--import` writes unmarked pages it then
  leaves alone. Adopt never modifies a user source file. Default config (`record_type`
  absent, `assume_known_skills` empty) is byte-equivalent to today. No handoff-schema bump.

## Out of scope (P1.5+)
Cross-runtime `_RENDERERS` (opencode/gemini projection of adopted defs); `pigeon agents`↔
`pigeon adopt` cross-reference view; deep `.claude/skills` resource parsing.

## P1.5 — cross-runtime renderers (DONE, 2026-06-18)
Added `_RENDERERS["opencode"] = _render_opencode` (verified against opencode 1.16 agent
files: `description` + `mode: subagent` frontmatter, body; name from filename; Claude
`tools` vocab not projected). Available as a `skills.targets` opt-in
(`opencode: .opencode/agent`); default stays claude-only (byte-equivalent). **gemini
deferred** — not installed and has no subagent concept to project into; revisit if/when a
gemini agent format is verifiable. Factored the shared frontmatter+marker+body shape into
`_render_marked`. Still open: `pigeon agents`↔`adopt` cross-ref, deep `.claude/skills` parse,
MCP pass-through (P2).
