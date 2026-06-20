# BUILD PLAN — Carrier-Comms Optimization (two levers)

**Date:** 2026-06-19 · **Authority:** carrier-comms design session
**Executor:** a Claude terminal (interactive Claude Code), step by step — **not** a
free-model coordinate fan-out, except the two coordinate runs called out in Phase 0 and Phase 4.
**Companion:** the two-lever design brief is embedded in §0 below (it has no on-disk home yet).
**Reads first:** [`AGENTS.md`](../../AGENTS.md), `.pigeon/manifest.json`, this file.

This plan answers: *how to compress the carrier-to-carrier channel (Lever 1, parity
ceiling) and build + test the polymath handoff (Lever 2, the research question)* — as a
sequence of small, measured steps, each with a gate that can stop the program. It is written
so the executing Claude **does not re-derive** what this session already established: every
load-bearing fact below is verified against the working tree at the cited `file:line`.

---

## 0. Design brief (the thing being built)

**Scope.** How *carriers* (agent CLIs) talk to each other: the handoff payload + the context
pigeon injects to convey one carrier's state to the next. NOT a repo-wide compression pass
(AGENTS.md / the manifest are repo-wide and out of scope).

**The rule both levers share.** Spend tokens only on what the receiver *cannot cheaply
regenerate.* Re-reading code is cheap (shared disk; any carrier can grep). Re-deriving
reasoning is expensive. A handoff earns its tokens only when it carries the
expensive-to-reconstruct thing.

**Lever 1 — compress the channel. Ceiling = PARITY.** It shrinks `N·overhead`; it does not
make coordination *create* savings. Worth an afternoon, not a headline.

**Lever 2 — the polymath handoff. The research question.** Payloads for *derived* knowledge,
pointers for *re-derivable* knowledge. Transmit the reasoning residue (approaches ruled out +
why, the constraint discovered, the decision rationale, the intended next action); point at
everything regenerable. The win may be a **quality win** (the receiver respects a constraint
it would otherwise violate, same tokens, fewer regressions) rather than a token win — and the
quality win may be the real one. **Measure both.**

**The U-curve (Lever 1's non-obvious floor).** Compression is not monotonically good. Past a
point a too-terse channel makes the receiver re-derive what you stripped and it re-explores —
costing *more*. Target = *minimum channel that holds the receiver's success rate*, not
smallest channel. Every step measures tokens **AND** success; stop at the knee.

**Two failure modes for Lever 2.** (a) *Residue bloat* — the `derived` payload itself balloons
and you've reinvented the overhead. (b) *The model re-derives cheaply anyway* — a capable
receiver reconstructs the reasoning from the pointed-to code, so the residue saves nothing.
The polymath wins **only** where the reasoning is expensive to rediscover from the artifacts
alone (a non-obvious constraint found through failed experiments, invisible in the final code).

---

## 1. Status — verified against the working tree (2026-06-19)

### What already exists (reuse, do not rebuild)

| Capability | Where (file:line) | Note |
|---|---|---|
| Handoff contract v1.1, **pointers-only** | [`.pigeon/handoff.schema.json`](../../.pigeon/handoff.schema.json) `state` `additionalProperties:false` @43; `artifacts` @56-62; `decisions` (freeform, forward-only) @63-67 | **No derived-reasoning field exists** — this is Lever 2's gap |
| Handoff token accounting | [`tokens.py`](../../src/pigeon/tokens.py) `account_handoff` @142-166 (**single chokepoint**, 6 call sites); `_prose_baseline_for_handoff` @108-139; `summarize` @201-231 (sums only known fields); `record` @85-92 | One lumped `actual_tokens` per handoff |
| Pack bundle (the real over-send) | [`pack.py`](../../src/pigeon/pack.py) `_LAYERS` @28-34 (mem 20/manifest 10/code 50/hist 20); `pack()` @70-157; header/footer @121-128; inlined code fences @89-90 | 4000-tok default; **this is what lands in the receiver's window** |
| Scaffolding (never counted) | [`coordinate/__init__.py`](../../src/pigeon/coordinate/__init__.py) `DEFAULT_PROMPT` @148-154; `crew_instructions` @156-180; readonly-constraint blocks @114-134; [`context.py`](../../src/pigeon/context.py) `generated_body` @30-63 | Re-emitted every spawn, invisible to the ledger |
| Distill (post-hoc reasoning capture) | [`distill.py`](../../src/pigeon/distill.py) **deterministic, no LLM** (docstring @12-17); `list_runs` use @162; `sessions.session_handoffs` (sessions.py:17) | Natural base for capture (ii) — **keep the core deterministic** |
| Coordinate / runners | `config.py` runners @135-139 (`claude`/`agy`/`opencode`), `telemetry_flags` @154-158, `model_pools` @185 (empty), `env_allowlist` @191 (`[]` strips secrets); [`agents.py`](../../src/pigeon/agents.py) KNOWN_AGENTS @37-62 (opencode `-m {model}` @40; gemini @46) | `USAGE_PARSERS` registry [`coordinate/telemetry.py`](../../src/pigeon/coordinate/telemetry.py) @102 |
| Benchmark harness | `benchmarks/PROTOCOL.md` (two-arm WITH/WITHOUT, same-model, identical prompt, fresh worktree @ pinned SHA, held-out acceptance test §3); `benchmarks/KILL-CRITERION.md` (axes + GO/NO-GO, locked) | Cost(USD) is the headline; token bases differ across arms |
| Marshmallow result | `benchmarks/results/marshmallow.json` — plan step naive $0.4555 vs pigeon $0.4419 (~parity); overall **+8.1%**, same 1178 tests; `handoff_saved_pct 97.5`, `pack_saved_pct 92.1` (vs re-transmission, **not** a real cross-arm saving) | Plan step is a measured wash |
| **Fork-A cross-model — DONE** | `benchmarks/results/forkA-capability.json` + `benchmarks/figures/fig4_forkA_capability.png` | See §2 |

### Uncommitted, PRESERVE — do not clobber

- `src/pigeon/coordinate/__init__.py` @~1235-1245 — runner `Popen` now passes
  `stdin=subprocess.DEVNULL` (headless runners must not block reading stdin; root cause of
  `agy` hanging). **"full pigeon suite green, UNCOMMITTED pending review."** It is *required*
  for `agy` to participate in any coordinate run below. Leave it in place; build on top of it.
  When committing this program, commit that fix as its own first commit with that rationale.

---

## 2. The Fork-A finding — already proves Lever 2's quality win (reuse)

`forkA-capability.json` (2026-06-19) ran the exact cross-model substrate this program would
use — **claude (architect) → opencode/mimo-v2.5-free → agy/Antigravity**, three CLIs, no
shared memory — on a controlled `ledger` repo with an **off-disk wire contract** given only to
hop 1 and never written into the code. Held-out grader `accept.py` (agents never see it),
validated fail-pristine / pass-reference.

**Result: bridge 5/5, no-bridge 0/5 (N=5).** The no-bridge failure mode is identical every
trial: cold implementers write working, round-tripping code but use **idiomatic keys**
(`name/balance_cents/created`) instead of the contract's (`acct/cents/ts`, epoch-int, lenient).
The held-out test catches the contract violation.

**This *is* Lever 2's quality-win arm.** The bridge carries a non-re-derivable constraint; the
cold receiver violates it 0/5; the bridged receiver respects it 5/5 — "the receiver respects a
constraint it would otherwise violate." It is a *capability/possibility* proof, paired honestly
with the cost benchmark (pigeon is token-neutral, not cheaper).

**Decision (locked):** **reuse this as the demonstrated quality win.** Do **not** re-run it
from scratch — that re-derives a clean result. The structured `derived` schema (Phase 3) makes
the bridged payload *explicit and measurable* where Fork-A carried it implicitly via the
existing handoff fields; Phase 4 does **one optional confirmation re-run** through that schema
plus the token axis, time permitting.

---

## 3. Locked decisions (resolve the brief's open choices, cold)

1. **`caveman` is dropped.** It does not exist in this repo; Lever 1 Move 2's ~46% claim has no
   backing tool. Lever 1 is hand-tuning with a parity ceiling. Do not cite the figure.
2. **The over-send is in the pack + scaffolding, NOT the handoff.** The handoff JSON is already
   pointer-only and tiny (`handoff_saved_pct 97.5`). Aim Lever 1 at `pack.py` + the scaffolding,
   never at the handoff doc.
3. **`derived` is an additive, optional v1.1→v1.2 minor.** No `derived.decisions[]` — it would
   duplicate the existing freeform `state.decisions` that distill + graph already read.
4. **Distill stays deterministic.** Capture (ii) is a *separate* opt-in extraction pass that
   *appends* a handoff; never put an LLM inside `distill_session`.
5. **Capture mechanism (i) — structured self-emission — first.** Cheapest; tells us whether
   self-reported residue is even useful before building extraction (ii).
6. **Win bar (quality OR token).** Cross-model GO iff a *replicated* net-token saving OR a
   *replicated* regression-reduction. Consistent with `KILL-CRITERION.md` axes (success / human
   interventions / tokens / wall-clock).
7. **`n=1` is noise** (`PROTOCOL.md §3.6`). Every gate below requires **N≥3** runs. Lock each
   gate's threshold *before* its first run (the KILL-CRITERION.md discipline).
8. **Models available now:** `claude`, `opencode` (free-model army incl. `mimo`, via `-m
   provider/model`), `agy`, `qwen`. **`gemini`/`codex`/`crush` are absent** on PATH — do not
   plan on them.

---

## 4. Routing — who does what

The executing **Claude terminal does all source edits and all measurement** directly
(Phases 1–3, 4-token-axis). It is the integrator; this is not a free-model drafting job.

`pigeon coordinate` + free models are used in exactly two places:
- **Phase 0 panel** — diverse-model critique of *this plan* (the user's "different opinions"
  ask), and a live dogfood of the cross-model channel.
- **Phase 4 confirm** (optional) — the one Fork-A re-run through the `derived` schema.

No auto-merge. A human runs `pytest` + `pyrefly` and merges the branch after each gate.

---

## PHASE 0 (optional, recommended first) — multi-model panel critique

Dogfood pigeon's own cross-model path to pressure-test this plan before building, and produce
the "different opinions from different models" the user asked for.

1. Write `docs/design/carrier-comms.md` = this brief (§0) + the Fork-A reality (§2), as a
   **pointer** doc the carriers resolve.
2. Create `docs/To_do/comms-panel.tasks.yaml` (mirror `timeout-salvage-design.tasks.yaml`
   shape). One readonly critique task per voice, each handed a *pointer* to the design doc and
   the same prompt: *"Critique this two-lever plan. Where is it wrong, what's missing, where
   will it fail, what must be measured? Return structured findings as a handoff (pointers, not
   payloads)."*

   ```yaml
   # docs/To_do/comms-panel.tasks.yaml  (sketch — adjust model ids to `opencode models`)
   sid: comms-panel
   tasks:
     - id: critique-mimo
       runner: opencode
       model: opencode/mimo-v2.5-free
       isolation: worktree
       doing: "Critique docs/design/carrier-comms.md. Do not edit repo source; write findings to .pigeon/coordinate/reviews/comms/mimo.md and hand back."
     - id: critique-free2
       runner: opencode
       model: opencode/<a-second-free-model>   # pick a distinct provider from `opencode models`
       isolation: worktree
       doing: "Same critique, independent. Write .pigeon/coordinate/reviews/comms/free2.md and hand back."
     - id: critique-agy
       runner: agy
       isolation: worktree
       doing: "Same critique, independent. Write .pigeon/coordinate/reviews/comms/agy.md and hand back."
   ```
   Run: `pigeon coordinate docs/To_do/comms-panel.tasks.yaml --dry-run` then
   `… --skip-permissions --telemetry`. (The `stdin=DEVNULL` fix in §1 must be present for `agy`.)
3. **Claude multi-lens** (run by the terminal Claude itself, in parallel, no coordinate needed):
   four lenses — *skeptic* (where's the null?), *cost-realist* (is Lever 1 worth the afternoon
   given +8.1% and known-neutral cost?), *measurement-rigor* (are the gates falsifiable?),
   *ops-feasibility* (free-model flakiness, env_allowlist, telemetry parsers).
4. **Synthesis:** reconcile all voices into a *refined* design appended to
   `docs/design/carrier-comms.md`, with an explicit list of where the honest answer is most
   likely "no." `pigeon metrics` / `coordinate_status` show each model's voice was recorded.

**Gate G-panel:** if the panel surfaces a premise this plan got wrong, fix the plan before
building. (A "no" here is cheap and welcome.)

---

## PHASE 1 — Channel instrumentation (Step 0; prerequisite for everything)

No contract change. Nothing downstream is interpretable without per-spawn token + success
breakdown.

**1a. Sub-component split inside the handoff record.** In `account_handoff`
([`tokens.py:142`](../../src/pigeon/tokens.py)) build a `components` sub-dict before `record()`:
`{pointers, decisions, constraints, derived, crew, rag}`, each an independent `count_tokens` of
that serialized slice (reuse `count_tokens` + `serialize_handoff`). Keep `actual_tokens` as the
total. `summarize` (@201) sums only known fields, so `components` is **purely additive — no
migration, no test breakage**. `components.derived` is the residue-bloat meter (0 until Phase 3).

**1b. The missing `scaffold` kind.** Add `tokens.account_scaffold(config, *, prompt_text,
kind_detail)` recording `{"kind":"scaffold", actual_tokens, ...}`. Call it from `_build_command`
([`coordinate/__init__.py:963`](../../src/pigeon/coordinate/__init__.py), right after the prompt
is finalized @979-982) on the **exact** finalized prompt + crew string. Count `generated_body`
**once** via `sync_context` ([`context.py:130`](../../src/pigeon/context.py)) so the per-repo
constant isn't double-counted per wave. `format_summary` (@234) renders new kinds for free.

**1c. Join SUCCESS to tokens — new module `src/pigeon/bench_join.py`.** Do **not** put success
in `metrics.jsonl` (token-only by design). The reporter reads: `metrics.jsonl` filtered by `sid`
(add `sid` to the `pack`/`retrieval` events too while here) + the run manifest via
`coordinate.list_runs` (as `distill.py:162` does) for `exit_code`/`status`/`telemetry` + an
operator-written `benchmarks/results/raw/<label>/acceptance.json` (`{task_id:{pass:bool}}`, the
held-out gate). Emits one row per task:
`{task, runner, model, channel_tokens(=handoff+pack+scaffold), agent_tokens, cost_usd,
exit_code, accept_pass, regression_count}`. **This row is the single artifact every later phase
reports.**

**Gate G0 (lock cold):** `bench_join` reproduces the recorded `marshmallow.json` totals
(channel tokens reconcile; the success tie matches). Full suite green (≈352+ tests). If it
can't reproduce known numbers, fix the meter before measuring anything new.

---

## PHASE 2 — Classify the over-send (Step 1)

Run the **existing** marshmallow `t1-slug` WITH-arm once, instrumented.

**Gate G1 (confirm-or-kill, lock cold):** pack tokens ≫ handoff-doc tokens (predicted by
`handoff_saved_pct 97.5` / `pack_saved_pct 92.1`). *Confirmed* → Lever 1 targets pack +
scaffold (Phase… next). *Killed* (handoff dominates) → the brief's premise was wrong; retarget.
This classification alone is worth more than any compression.

---

## PHASE 3 — Lever 1: compress the channel to the U-curve knee

Each move re-runs marshmallow plan→implement, **N≥3, same-model**, measuring tokens AND success
via `bench_join`.

- **Move 1 — say-once scaffolding.** `DEFAULT_PROMPT` (@148-154) duplicates protocol prose
  already in the auto-loaded CLAUDE.md (`generated_body`). Cut it to the irreducible per-task
  delta (task_id, sid, handoff path, "do only the doing step, hand back"); let the pointer file
  carry the protocol. Pointer-ize the crew block (it's already in the `crew` field) instead of
  re-rendering `crew_instructions` (@156-180) inline. Measured by the `scaffold` kind dropping.
- **Move 2 — tighten static templates.** Terser `generated_body` (@30-63) + readonly-constraint
  blocks (@114-134). **U-curve risk:** the readonly constraint is safety-load-bearing — do not
  compress past where the agent honors it; re-measure success here specifically.
- **Move 3 — tunable pack + sweep.** Expose `pack_max_tokens` / `pack_top_k` /
  `pack_layer_shares` as `coordinate` config keys (defaults = today's 4000 / 5 / 20-10-50-20;
  coordinate already reads `pack_max_tokens` @1445). Sweep `max_tokens ∈ {1k,2k,3k,4k}` ×
  `top_k ∈ {3,5,8}`, recording `(channel_tokens, agent_tokens, accept_pass, regression_count)`.
- **Move 4 — pointer-ize re-derivable pack slices.** Replace inlined code bodies (`pack.py`
  @89-90) with `repo://path:start-end` + the one-line docstring for slices cheap to re-fetch
  (same-CLI shares the FS).

**U-curve stop rule (operational, lock cold).** Accept config C over baseline B iff, across
**N≥3** runs: `accept(C)=accept(B)=pass` ∧ `regressions(C) ≤ regressions(B)` ∧
`channel(B)−channel(C) > agent(C)−agent(B)` (net token win, net of the re-derivation tax). The
first config breaking any clause is too terse; the prior config is the knee.

**Gate G-Lever1 / KILL:** if no config beats baseline on the net-token rule without losing
success, the knee is at the current default → publish "channel already minimal" (clean null).
Honest expectation: movement toward parity, **never** savings. Bank it and stop.

---

## PHASE 4 — Lever 2: the `derived` schema + same-model bloat check

**4a. Add `derived` to the schema.** Under `state.properties` in
[`.pigeon/handoff.schema.json`](../../.pigeon/handoff.schema.json) (state is
`additionalProperties:false` @43 → must be explicit). Optional object, caps bound worst-case
residue at ~900–1100 tokens:

```json
"derived": {
  "type": "object", "additionalProperties": false,
  "description": "Reasoning the receiver cannot cheaply re-derive from the pointed-to artifacts. PAYLOAD for hard-won reasoning, never re-derivable facts.",
  "properties": {
    "ruled_out": {"type":"array","maxItems":8,"items":{"type":"object","required":["path","reason"],"additionalProperties":false,
      "properties":{"path":{"type":"string","maxLength":120},"reason":{"type":"string","maxLength":240}}}},
    "constraint_found": {"type":"array","maxItems":6,"items":{"type":"string","maxLength":240}},
    "next_action": {"type":"string","maxLength":280},
    "open_questions": {"type":"array","maxItems":6,"items":{"type":"string","maxLength":200}},
    "rationale": {"type":"string","maxLength":400}
  }
}
```

**4b. Forward-compat v1.1 → v1.2.** Bump `SCHEMA_VERSION` in
[`src/pigeon/__init__.py`](../../src/pigeon/__init__.py); rename schema `$id` to
`handoff-1.2.json`; register a **no-op** `_MIGRATIONS["1.1"]→("1.2", …)` in
[`handoff.py`](../../src/pigeon/handoff.py) @132 (mirror `_migrate_1_0_to_1_1` @122); thread a
`derived` kwarg into `build_handoff` @176 (like `decisions`/`salvaged_upstream` @196-199), and
into the MCP/CLI `handoff_write` signatures. Because `derived` is optional, every existing 1.1
handoff still validates under 1.2 (superset). Add a **soft** budget *warn* (never reject) in
`validate_handoff` when `components.derived` > `coordinate.derived_token_budget` (default ~400).

**4c. Capture (i) — self-emission (default).** Extend `DEFAULT_PROMPT` + AGENTS.md so hand-back
instructs: record ruled-out approaches / discovered constraints / open questions in
`state.derived`, **one line each**, point at code for anything re-derivable. Risk: self-reports
confabulate — Phase 4's quality axis (and Phase 5) is what catches noise.

**4d. Capture (ii) — faithful extraction (opt-in, for the cross-model arm).** A *separate*
`distill.extract_derived(config, sid, task_id)` reads the per-task log
(`coordinate/__init__.py:1230`), extracts the residue, and **appends a new handoff** (append-only;
never mutates the deterministic distill). Behind `coordinate.extract_derived: false`. Reuse
`sessions.session_handoffs` (sessions.py:17).

Re-run marshmallow plan→implement **same-model** with `derived` populated.
**Gate G2a (bloat check, lock cold):** `components.derived` < budget AND cost stays at
**parity** with the no-derived run. *Parity = working* (overhead shrank by exactly the residue
added back). *Worse = bloated* → tighten caps or drop (i) for (ii). Same-model is **expected**
to be a wash on quality too (same capable model re-derives) — this is a bloat check, not a win
test. The win test is Phase 5.

---

## PHASE 5 — Cross-model: reconcile with Fork-A; add the token axis (optional confirm)

The quality-win arm is **already demonstrated** (§2: 5/5 vs 0/5). This phase is *confirm-later*:

- **Reuse** `forkA-capability.json` as the quality-win evidence in any writeup; cite
  `fig4_forkA_capability.png`.
- **Optional confirmation re-run (time permitting):** re-cast the bridge's off-disk contract as
  a structured `state.derived.constraint_found` (+ `ruled_out` for the idiomatic defaults the
  cold arm falls into), run the same claude→opencode/mimo→agy chain **N≥3**, with `bench_join`
  now recording the **token axis** (`channel_tokens` incl. the isolated `derived` component +
  `agent_tokens`) alongside held-out success.
  - Cold consumer telemetry: `opencode` is measured (`_opencode_parser` exists @
    `coordinate/telemetry.py:102`). `agy` emits no usage by default → treat agy tokens as
    best-effort; rely on agy for the *success* axis only, unless it prints a `usage` object
    (then add `_agy_usage` to `USAGE_PARSERS`).

**Gate G-Lever2 (lock cold; win bar = quality OR token):**
- *Token win:* with-derived total (channel+agent) < without-derived, replicated N≥3.
  **Likely "no"** for a capable consumer on a well-pointed task (the re-derives-cheaply mode);
  and the cost benchmark already showed token-neutrality. Report it honestly either way.
- *Quality win:* `regressions(with-derived) < regressions(without-derived)` at similar tokens.
  **Already true** at the capability level (5/5 vs 0/5). The schema'd re-run confirms it holds
  when the constraint is carried as structured `derived` rather than prose.
- **GO** if either replicates. **KILL** if both fail under the schema'd form → "capable models
  re-derive reasoning from artifacts; the structured residue adds overhead without payoff" — a
  real, publishable negative.

---

## 6. Critical files

| File | Change | Phase |
|---|---|---|
| [`src/pigeon/tokens.py`](../../src/pigeon/tokens.py) | `account_handoff` `components` (@142); `account_scaffold` + `scaffold` kind; `summarize`/`format_summary` absorb new kinds | 1 |
| **`src/pigeon/bench_join.py`** (new) | tokens×success join reporter (reuse `coordinate.list_runs`) | 1 |
| [`.pigeon/handoff.schema.json`](../../.pigeon/handoff.schema.json) | optional `derived` under `state.properties` (@43); `$id`→1.2 | 4 |
| [`src/pigeon/handoff.py`](../../src/pigeon/handoff.py) | `SCHEMA_VERSION` bump; `_MIGRATIONS` 1.1→1.2 no-op (@132); `build_handoff` derived kwarg (@176); soft budget warn | 4 |
| [`src/pigeon/coordinate/__init__.py`](../../src/pigeon/coordinate/__init__.py) | trim `DEFAULT_PROMPT`/`crew_instructions` (@148-180); `account_scaffold` in `_build_command` (@963); expose pack knobs (@1445). **Preserve the `stdin=DEVNULL` fix @~1235.** | 1,3 |
| [`src/pigeon/config.py`](../../src/pigeon/config.py) | pack-sweep keys; `derived_token_budget`; `extract_derived` flag; opencode `-m {model}` + a free-model `model_pool` for Phase 0 | 0,3,4 |
| [`src/pigeon/pack.py`](../../src/pigeon/pack.py) | tunable layer shares (@28-34); pointer-ize inlined slices (@89-90) | 3 |
| [`src/pigeon/distill.py`](../../src/pigeon/distill.py) | opt-in `extract_derived` (reuse `sessions.py`); **keep the core deterministic** | 4 |
| `benchmarks/results/raw/<label>/acceptance.json` (operator) | held-out pass/fail per task → `bench_join` | 1+ |
| `docs/design/carrier-comms.md`, `docs/To_do/comms-panel.tasks.yaml` (new) | brief + panel synthesis; panel coordinate file | 0 |

---

## 7. Verification

- **Phase 1:** `pigeon metrics` shows the `components` breakdown + `scaffold` kind; `bench_join`
  reproduces `marshmallow.json` totals + the recorded tie; full suite green (G0).
- **Schema:** `mcp pigeon handoff_validate` accepts both a 1.1 and a 1.2 handoff; `pigeon
  migrate` 1.1→1.2 is a no-op; every existing `.pigeon/handoffs/*.json` still validates.
- **Phase 2:** instrumented WITH-arm run → component split shows pack ≫ handoff (G1).
- **Phase 3:** sweep table of `(channel_tokens, accept_pass, regression_count)`, N≥3; knee
  identified by the stop rule; full suite + held-out acceptance hold at the chosen config (G-Lever1).
- **Phase 4:** `components.derived` < budget; same-model cost parity vs no-derived (G2a).
- **Phase 5:** (optional) claude→opencode/mimo→agy, with- vs without-`derived`, N≥3; report
  token delta + held-out pass + regression count; GO iff quality OR token win replicates (G-Lever2).

---

## 8. Why this shape

Lever 1 is cheap, scoped, tops out at parity — do it, find the U-curve knee, bank it, stop.
Lever 2 is the real question, and its capability/quality arm is **already answered** (Fork-A,
§2) — so the new work is the *structured, measurable* `derived` payload and the token axis, not
a fresh experiment. Every change moves as a **pointer** (draft artifact, materialized diff,
handoff) — the pointers-not-payloads invariant pigeon is built on. **This very document is a
polymath handoff:** it carries the derived reasoning (verified `file:line`, locked decisions,
the Fork-A reconciliation, the gotchas) so the executing Claude reads code on demand instead of
re-deriving what this session already paid to discover.

**Drift guard.** Designing the polymath is not evidence it works. Phase 2 might show the
handoff already mostly minimal (premise wrong). Phase 5 (schema'd) might show capable models
re-derive cheaply (no token win). Both are welcome, publishable numbers. Do not let "we built
the polymath" become "it saves tokens" before a locked gate says so. Lock each gate's threshold
**before** its first run.

---

## 9. Next steps — live (execution underway on `feat/carrier-comms`)

**Done (committed):**
- `2a87f66` — `stdin=DEVNULL` runner fix (prerequisite for any `agy` coordinate run; §1).
- `be8a6ac` — Tier-A report + Fork-A capability result (bridge 5/5 vs cold 0/5; §2). **This is
  Lever 2's quality win — reuse it.**
- `b813df3` — this handoff doc set (build plan + `carrier-comms.md` brief + `comms-panel.tasks.yaml`).

**In progress:** Phase 1 instrumentation — `src/pigeon/tokens.py` has the `account_handoff`
`components` split + `scaffold` kind started (uncommitted). Finish and commit it before measuring.

**Do next, in order (each step ends at its gate; lock the threshold before the run):**
1. **Finish Phase 1.** Complete `account_scaffold` + its call in `_build_command`
   (`coordinate/__init__.py:963`); add `src/pigeon/bench_join.py` (tokens×success join); run the
   suite. Commit `tokens.py` + `bench_join.py`. → **Gate G0:** `bench_join` reproduces
   `marshmallow.json` totals + the recorded success tie; full suite green.
2. **(Optional, runnable now) Phase 0 panel.** `pigeon coordinate docs/To_do/comms-panel.tasks.yaml
   --dry-run`, then `--skip-permissions --telemetry`. Synthesize the mimo/nemotron/agy critiques
   into `carrier-comms.md`; fold any valid premise-correction back into this plan **before** building further.
3. **Phase 2.** Instrumented marshmallow `t1-slug` WITH-arm run. → **Gate G1:** pack ≫ handoff.
4. **Phase 3 (Lever 1).** Moves 1–4 + pack/top-k sweep → U-curve knee. → **Gate G-Lever1** (or the
   clean "channel already minimal" null).
5. **Phase 4 (Lever 2).** `derived` v1.2 schema + capture (i); same-model re-run. → **Gate G2a**
   (bloat check; parity = working).
6. **Phase 5.** Optional cross-model confirm re-run through the `derived` schema (reuse Fork-A as
   the standing quality win); add the token axis. → **Gate G-Lever2** (quality OR token).

**Housekeeping:** commit each phase on `feat/carrier-comms`; **lock each gate's threshold before
its first run** (the `KILL-CRITERION.md` discipline); **do not push** until a clean stopping point
and only after the active session has paused (concurrency hazard); commits are the user's — no
Claude attribution.

---

## 10. Run log & lessons

### Phase 1 — instrument (Gate G0) ✅ PASS

- **As built.** `tokens.py`: `_handoff_components()` (per-slice handoff breakdown incl. the
  `derived` residue meter) + `account_scaffold()` (new `scaffold` kind) landed; `summarize()`
  refactored to delegate to a new pure-path engine `aggregate_metrics(path)` so off-ledger files
  aggregate through the *same* code as `pigeon metrics`. New `src/pigeon/bench_join.py` joins a
  recorded ledger to its held-out acceptance + regression gate, exposing
  `(channel_tokens, accept_pass, regression_count)` per arm. New `tests/test_bench_join.py` (5).
- **Gate G0 verdict — PASS.** `bench_join` over `benchmarks/results/raw/marshmallow` reproduces the
  published `marshmallow.json` accounting exactly: events 16, overall 95.5%, handoff 97.5%, pack
  92.1%, channel (handoff actual) 3142, pack 5985 — and the recorded success **tie** (both arms
  PASS). Full suite **477 passed**; ruff clean; `pigeon metrics` unaffected.
- **As-built delta vs the plan.** `account_scaffold`'s call-site wiring in `_build_command`
  (`coordinate/__init__.py:963`) is **deferred to Phase 3** (the finalized prompt isn't cleanly
  available at the spawn chokepoint — it's embedded in runner-dependent argv and needs a small
  thread-through G0 doesn't require). The accounting fn + `scaffold` kind exist now; the scaffold
  *measurement* happens in Phase 3 where the scaffold-drop is the thing being measured.
- **Continue.** Next: Phase 0 panel (optional, runnable now) or Phase 2 (instrumented WITH-arm run →
  G1: pack ≫ handoff).

### Phase 0 — multi-model panel (Gate G-panel) ✅ PROCEED (carried over from prior session)

Already executed by the prior terminal and recorded in
[`carrier-comms.md`](carrier-comms.md) §"Phase-0 panel synthesis": the free-model voices
(`oc-mimo`, `oc-nemotron`) **timed out at 600 s** and `agy`'s **Google OAuth had expired** — an
ops finding, not a critique. The substantive pass was the integrator's four lenses; verdict
**PROCEED**, no premise falsified, four gate-level refinements applied. Re-running the panel this
session was attempted but **blocked by the harness auto-mode** (spawning `--skip-permissions`
sub-agents needs explicit operator authorization) — and would only have re-hit the same
free-model wall. **Adopted refinements:** (#1) reconcile G0 against the raw `metrics.jsonl`, not
the published JSON — which is exactly what `bench_join` does; (#3) **do not pre-commit the full
pack sweep (Move 3); decide it after G1.**

### Phase 4 — Lever 2 `derived` schema + machinery (4a/4b/4c) ✅ BUILT & GREEN

Committed `45dc920`. As built: optional `state.derived` under the schema (caps bound residue to
~900–1100 tok); `$id`→`handoff-1.2.json` + bundled template kept byte-identical; `SCHEMA_VERSION`
1.1→1.2 with a no-op `_migrate_1_1_to_1_2` (1.2 is a pure superset — every 1.1 handoff still
validates); `build_handoff` / MCP `handoff_write` / impl gained a `derived` arg; `tokens` flags
`derived_over_budget` and `derived_budget_status()` backs a soft write-time warn (never rejects);
new `coordinate.derived_token_budget` (400). Capture (i) self-emission guidance added to AGENTS.md
("carry the residue, point at the rest"). 8 new tests in `test_derived.py`. **Schema verification
(plan §7) holds:** a 1.1 and a 1.2 handoff both validate; 1.1→1.2 migrate is a no-op.
**Not built:** capture (ii) `distill.extract_derived` — opt-in, used *only* by the Phase-5
cross-model arm, which is a blocked live run; staged below rather than written speculatively.

### Phase 2 — classify the over-send (Gate G1) ✅ PASS (from the recorded ledger)

`bench_join` / `aggregate_metrics` over `benchmarks/results/raw/marshmallow/with.metrics.jsonl`:
per spawn the **pack injects ~2992 tok vs the handoff doc's ~286 — pack is ~10.5× the handoff**
(lumped pack 5985 vs handoff 3142 across the run). **Confirmed:** the over-send lives in the pack
+ scaffolding, not the handoff doc (locked decision #2 holds; Lever 1 is correctly aimed). Caveat:
this is the single recorded run (n=1); G1 is a *classification of where tokens live*, not a
win-claim, so n=1 is adequate to aim Lever 1 — but any *compression* claim still needs the N≥3
discipline below.

### Phase 3 — Lever 1 channel compression: instrument ready, compression STAGED

`account_scaffold()` (the scaffold meter) is built and unit-tested (`test_derived.py`). Its
**live-path wiring is deliberately deferred** (not forced): the prompt is rebuilt at three spawn
sites (`__init__.py:1567/1581/1699` via `_spawn_prepare`), so threading the finalized text risks
a double-count or dry-run pollution in the core path, and the meter's only payoff is the Move-1
measurement — a blocked live run. Per panel refinement #3, **Move 3's pack sweep is not
pre-committed.** Moves 1/2/4 are behavior-changing and, by the plan's own measure-before-compress
rule, must not flip defaults without an N≥3 success run — so they are staged, not silently landed.

### Phase 5 — cross-model (Gate G-Lever2): quality win REUSED; token-axis confirm STAGED

Fork-A (`forkA-capability.json`, bridge 5/5 vs cold 0/5) stands as the demonstrated quality win;
no re-run needed. The optional schema'd token-axis confirm is a blocked live run (and `agy` needs
re-auth) — staged below.

---

## 11. Staged live runs (need operator authorization — `--skip-permissions` + real spend)

The harness auto-mode blocks an agent from firing `pigeon coordinate --skip-permissions`
autonomously, and these consume real API budget. Each is one command; lock the threshold before
the first run (KILL-CRITERION discipline). **Do not push until a clean stopping point.**

1. **Phase 0 panel re-run (optional, free models).** `pigeon coordinate
   docs/To_do/comms-panel.tasks.yaml --skip-permissions --telemetry`. Needs `agy` re-auth; expect
   the documented free-model timeouts. Low value — the verdict is already PROCEED.
2. **Phase 2 confirm (1 sonnet run).** Re-run marshmallow `t1-slug` WITH-arm against `/tmp/bench`,
   instrumented, to confirm G1 on a fresh ledger (the recorded-data verdict already passed).
3. **Phase 3 Lever-1 (N≥3 sonnet).** Land Move 1 (say-once scaffolding) + wire `account_scaffold`,
   re-run marshmallow plan→implement N≥3, apply the U-curve stop rule. **Decide Move 3 (pack
   sweep) only if G1's margin says the pack is worth it** (it is — 10.5×). Threshold: accept C over
   B iff `accept(C)=accept(B)=pass ∧ regressions(C)≤regressions(B) ∧ channel(B)−channel(C) >
   agent(C)−agent(B)`.
4. **Phase 4 G2a (N≥3 sonnet).** Re-run same-model with `state.derived` populated (capture i).
   Threshold: `components.derived < 400` AND cost parity vs the no-derived run. Parity = working.
5. **Phase 5 G-Lever2 (N≥3 cross-model).** Build capture (ii) `distill.extract_derived`, recast
   Fork-A's contract as structured `state.derived`, run claude→opencode/mimo→agy with the token
   axis. GO iff a replicated quality OR token win; KILL (publishable) iff both fail under the
   schema'd form. Needs `agy` re-auth.

_(Per-phase run outcomes for the staged runs get filled here as they execute. Commits are the
user's; no Claude attribution.)_
