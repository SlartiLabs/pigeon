# DESIGN — `pigeon adopt`: discover & adopt existing subagents, skills, and MCP servers

**Authority:** design draft — session continued from the v0.5.0 release
**Date:** 2026-06-17
**Status:** PROPOSED (no code written). Awaiting review before implementation.
**Relates to:** the skill-projection layer (`skills.py`), CLI discovery (`agents.py`),
the `coordinate` crew mechanism, and the Phase-2 "personal tool vs product" question.

This doc specifies a feature that lets pigeon **discover and reuse the agent
assets a user already has** — Claude Code subagents (`.claude/agents/*.md`),
skills (`.claude/skills/`), and configured MCP servers — so a `coordinate`
`crew:` can be staffed from the user's existing library instead of only from
pigeon's own playbooks.

---

## 0. Grounding facts (verified against source)

1. **Discovery today is binary-only.** `agents.detect_agents()` scans `$PATH`
   for a fixed `KNOWN_AGENTS` registry (claude, opencode, agy, gemini, codex,
   crush, copilot, cursor-agent, qwen, aider), probes `--version`, and marks
   each `configured` if its binary appears in a `coordinate.runners` template
   (`agents.py`). It discovers **CLIs**, not subagents/skills/MCP.

2. **Skill flow is one-directional: pigeon → runtime (projection).** Canonical
   pages live in `.pigeon/memory/playbooks/*.md` (frontmatter `name` /
   `description` / optional `tools` + a system-prompt body). `skills.project_skills()`
   renders each page into a runtime's native format for every entry in
   `config.skills.targets` — today only `{claude: .claude/agents}`, via the one
   registered renderer `_RENDERERS = {"claude": _render_claude}` (`skills.py`).
   `pigeon refresh` runs the projection. There is **no path that ingests
   existing external defs** into pigeon.

3. **Projection already protects hand-written files.** Generated files carry
   `GEN_MARKER` (`skills.py:34`); a file at the target path **without** the
   marker is treated as hand-written and left alone (recorded under `skipped`,
   `skills.py:103-108`). So the user's own `.claude/agents/*.md` are already
   safe from `refresh`. **This is the hinge for the whole design**: the marker
   already distinguishes *pigeon-generated* from *user-authored*.

4. **Crews resolve a skill by NAME, softly.** A `crew:` carries `skills: [...]`
   and `subagents: [{role, skill, verdict}]`. `crew_instructions()` renders
   prose — *"Load these skills…"* and *"Dispatch a subagent for role X loading
   skill Y … skill names resolve in `<playbooks dir>`/"* (`coordinate/__init__.py`
   ~127-149). Resolution is a **prompt instruction to the runner**, not a hard
   binding. Implication: making a name resolvable is mostly about (a) the def
   existing where the runner looks and (b) the catalog knowing the name.

5. **MCP is serve-only.** `mcp_server.py` builds a `FastMCP` server exposing
   pigeon's own tools. Pigeon never acts as an MCP **client** and has no notion
   of *other* MCP servers. Consuming external MCP is a new capability, not an
   extension of an existing one.

These five decide the design: adopt is the **inverse of projection**, it can
lean on the **marker** to stay non-destructive, name-resolution is **soft** (so
the MVP is mostly discovery + cataloguing + light wiring), and **MCP must be
phased** because nothing to build on exists yet.

---

## 1. Problem & goal

Users arrive with a rich, hand-built agent library (a `.claude/agents/`
registry of dozens of subagents, `.claude/skills/`, several configured MCP
servers). Pigeon ignores all of it: a `crew:` can only name one of pigeon's
~handful of playbook pages, and the only flow pigeon offers is to *generate
more* `.claude/agents` files from its own playbooks — pushing out, never
pulling in.

**Goal:** `pigeon adopt` — discover the user's existing subagents / skills / MCP
servers and make them first-class, referenceable inputs to `coordinate` crews
(and surface relevant MCP servers to MCP-client runners), **without** clobbering
anything, duplicating by default, or auto-trusting third-party prompt content.

**Non-goal (this revision):** turning pigeon into an MCP client that itself
calls external MCP tools (see §5, deferred).

---

## 2. Scope

**In scope (MVP):**
- Discover Claude Code subagents (`.claude/agents/*.md`, user + project scope).
- Discover skills (`.claude/skills/*` — directory- or file-based skill defs).
- Discover configured MCP servers (parse, don't connect).
- A **catalog** of what was found, with provenance, written to `.pigeon/`.
- Let a `crew:` `skill:`/`role:` resolve against an **allow-listed** adopted name.
- Report via `pigeon adopt` (human view), à la `pigeon agents`.

**Out of scope (MVP), see §5/§9:** pigeon-as-MCP-client; auto-translating a
subagent across runtimes beyond reusing the existing renderer; mutating the
user's source files.

---

## 3. Design

### 3.1 Discovery sources (config-driven, never hard-coded paths only)
Add a `adopt:` config block (defaults shown; all overridable):

```yaml
adopt:
  enabled: true
  sources:
    subagents: ["~/.claude/agents", ".claude/agents"]   # *.md, Claude subagent frontmatter
    skills:    ["~/.claude/skills", ".claude/skills"]    # skill dirs/files
    mcp:       ["~/.claude.json", ".mcp.json", ".cursor/mcp.json"]  # server configs (parsed only)
  allow: []        # names a crew may reference; EMPTY = nothing adopted is usable until chosen
  import: false    # false = catalog/reference in place; true = copy into playbooks (see 3.4)
```

A discovered record (one per asset):
```json
{ "name": "code-architect", "kind": "subagent|skill|mcp",
  "source": "/home/<user>/.claude/agents/code-architect.md",
  "scope": "user|project", "runtime": "claude",
  "description": "…", "provenance": "user-authored|pigeon-generated",
  "allowed": false }
```
`provenance` is decided by the `GEN_MARKER` (fact 3): a discovered
`.claude/agents` file **with** the marker is pigeon's own projection (ignore for
adoption — it already came from a playbook); **without** the marker it is
user-authored and adoptable. This cleanly resolves the direction conflict.

### 3.2 The catalog
`pigeon adopt` writes `.pigeon/adopt/catalog.json` (gitignored, like other
`.pigeon` scratch) — the index of discovered assets. `pigeon adopt` with no args
prints the human view (counts by kind/scope, which are allow-listed, which
collide with a playbook name). This mirrors `agents.format_agents()`.

### 3.3 Resolution (how a crew uses an adopted asset)
Extend crew skill-name resolution to a defined order:
1. canonical playbook `name.md` (today's behavior — unchanged);
2. an **allow-listed** adopted asset of that `name` in the catalog.

For a **same-runtime** task (e.g. a `claude` runner referencing an adopted
Claude subagent), resolution is a **no-op pass-through**: the def already lives
in `.claude/agents/` where Claude's Task tool finds it; `crew_instructions()`
just needs to not warn and to name it. For a **cross-runtime** task, reuse the
`skills.py` renderer pipeline to project the adopted def into the target
runtime's format on demand (new renderers are the same extension point as
`_RENDERERS`). MVP may restrict adopted-asset use to the asset's native runtime
and defer cross-runtime projection.

### 3.4 Reference vs import (`adopt.import`)
- **Reference (default, `import: false`):** the catalog points at the source
  file in place; nothing is copied. The user's library stays the single source
  of truth; pigeon never owns or regenerates it.
- **Import (`import: true`, opt-in per-name):** copy a selected def into
  `.pigeon/memory/playbooks/` as a canonical page **without** `GEN_MARKER` (so a
  later `refresh` won't overwrite it), so it travels with the repo and projects
  like a native skill. Use when a def should be versioned with the project.

Either way **`refresh` is unchanged** and still only writes marked files —
adopt and projection cannot fight over a path (fact 3).

### 3.5 CLI surface
- `pigeon adopt` — discover + write catalog + print the human view.
- `pigeon adopt --allow <name>...` — add names to `adopt.allow` (the trust gate).
- `pigeon adopt --import <name>...` — copy selected defs into playbooks.
- `coordinate` gains a preflight warning when a crew references a name that is
  neither a playbook nor an allow-listed adopted asset (today it silently trusts
  the runner to find it).

---

## 5. MCP servers (phased)

- **MVP — inventory only.** Parse the configured MCP servers from the `mcp:`
  sources (`~/.claude.json`, `.mcp.json`, `.cursor/mcp.json`) and catalogue
  `{name, command/url, scope}`. Surface them in `pigeon adopt` output. Do **not**
  connect. Value: visibility, and for runners that are themselves MCP clients
  (claude, opencode), pigeon can confirm/echo which servers a task will have.
- **P2 — pass-through.** For MCP-client runners, let a task declare which adopted
  MCP servers it expects, and have coordinate verify they're configured for that
  runtime before dispatch (config check, still not a pigeon-side connection).
- **P3 — pigeon as MCP client (deferred, own design doc).** Pigeon connecting to
  external MCP servers and exposing/relaying their tools is a substantial new
  subsystem (transport, lifecycle, auth, trust) — explicitly **out of scope** here.

---

## 6. Trust & safety

Adopted subagent/skill files are **executable instructions** that will be loaded
into an agent's context. Adoption is therefore **opt-in and explicit**:
- Discovery is safe (read-only) and always allowed; **use** requires the name to
  be in `adopt.allow` (default empty → nothing is usable until chosen).
- `pigeon adopt` shows a one-line description + source path per asset so the user
  reviews before allow-listing.
- MCP configs are **parsed, never executed**; secrets in those configs
  (tokens/env) are **not** copied into the catalog (record name + presence, not
  values) — consistent with the S2 env-allowlist posture (`config.py` env
  handling).
- Nothing under the user's source paths is ever modified; `import` only ever
  writes into `.pigeon/memory/playbooks/`.

---

## 7. Phasing

- **P0 (MVP):** `pigeon adopt` discovery + catalog + human view, for subagents &
  skills; `adopt.allow` gate; same-runtime reference resolution in crews;
  coordinate preflight warning for unknown skill names; MCP **inventory only**.
- **P1:** `--import` into playbooks; cross-runtime projection of adopted defs
  (new `_RENDERERS` targets); `pigeon agents` and `pigeon adopt` cross-reference.
- **P2:** MCP pass-through declaration + verification for MCP-client runners.
- **P3 (separate doc):** pigeon as an MCP client.

---

## 8. Test plan

- `parse` unit tests for each source format (Claude subagent frontmatter; skill
  def; each MCP config shape) incl. malformed/empty.
- Provenance: a marked `.claude/agents` file → `pigeon-generated` (excluded);
  unmarked → `user-authored` (adoptable). Round-trips with `skills.project_skills`.
- Allow-gate: an un-allow-listed name is catalogued but a crew referencing it
  trips the coordinate preflight warning; allow-listing clears it.
- Non-destruction: adopt + `refresh` in any order never modifies a user source
  file and never overwrites an unmarked target.
- MCP: secret values never land in `catalog.json`.

---

## 9. Open questions / decisions needed

1. **Catalog location/tracking:** `.pigeon/adopt/catalog.json` gitignored
   (scratch, re-derivable) vs tracked (shareable team library)? Default: gitignored.
2. **Name collisions** between a playbook and an adopted asset of the same name —
   playbook wins (3.3) or error? Proposed: playbook wins, warn.
3. **Skill format coverage:** `.claude/skills/` layout varies (SKILL.md +
   resources). MVP: catalogue name + description + path; defer deep parsing.
4. **Scope precedence:** project `.claude/agents` vs user `~/.claude/agents` of
   the same name — project wins (closer scope), warn.
5. **Is this in scope for "pigeon as a personal tool" or only "product"?**
   (Phase-2 framing.) Adoption is arguably most valuable for the personal-tool
   case — a fast way to field your own library — which may raise its priority.
