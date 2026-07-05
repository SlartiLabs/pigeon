# Carrier-Comms Optimization — design brief (pointer doc)

> A pointer doc for cross-model critique. The full executable plan is
> [`carrier-comms-buildplan.md`](buildplan.md); read code on demand
> at the `file:line` refs there rather than re-deriving.

## Scope
How *carriers* (agent CLIs) talk to each other: the handoff payload + the context
pigeon injects to convey one carrier's state to the next. NOT a repo-wide
compression pass (AGENTS.md / the manifest are out of scope).

## The rule both levers share
Spend tokens only on what the receiver **cannot cheaply regenerate.** Re-reading
code is cheap (shared disk; any carrier can grep). Re-deriving reasoning is
expensive. A handoff earns its tokens only when it carries the
expensive-to-reconstruct thing.

## Lever 1 — compress the channel. Ceiling = PARITY.
Shrinks `N·overhead`; it does **not** make coordination *create* savings. The
over-send lives in the **pack bundle + scaffolding**, not the handoff doc (the
handoff JSON is already pointer-only and tiny: `handoff_saved_pct 97.5`). Worth an
afternoon, not a headline.

**The U-curve (non-obvious floor).** Compression is not monotonically good. Past a
point a too-terse channel makes the receiver re-derive what you stripped and it
re-explores — costing *more*. Target = *minimum channel that holds the receiver's
success rate*, not the smallest channel. Every step measures tokens **AND**
success; stop at the knee.

## Lever 2 — the polymath handoff. The research question.
Payloads for *derived* knowledge, pointers for *re-derivable* knowledge. Transmit
the reasoning residue (approaches ruled out + why, the constraint discovered, the
decision rationale, the intended next action); point at everything regenerable.
The win may be a **quality win** (the receiver respects a constraint it would
otherwise violate — same tokens, fewer regressions) rather than a token win — and
the quality win may be the real one. **Measure both.**

**Two failure modes.** (a) *Residue bloat* — the `derived` payload balloons and
you've reinvented the overhead. (b) *The model re-derives cheaply anyway* — a
capable receiver reconstructs the reasoning from the pointed-to code, so the
residue saves nothing. The polymath wins **only** where the reasoning is expensive
to rediscover from the artifacts alone.

## Reality already measured (do not re-derive)
- **Cost benchmark:** pigeon is **token-neutral**, not cheaper (cookiecutter +46–59%,
  marshmallow +8.1%, tie on success). NO-GO on a "saves X%" headline.
- **Fork-A cross-model capability (DONE):** claude→opencode/mimo→agy, an off-disk
  wire contract given only to hop 1. **bridge 5/5, no-bridge 0/5 (N=5).** Cold
  carriers write working code but use idiomatic keys instead of the contract's —
  the held-out test catches it. This *is* Lever 2's quality-win arm, demonstrated:
  "the receiver respects a constraint it would otherwise violate." It is a
  *possibility* proof (pigeon enables cross-model state transfer), not a need proof.

## Locked decisions
1. `caveman` dropped (not in repo; no backing for the ~46% claim).
2. Over-send is in pack + scaffolding, not the handoff doc.
3. `derived` is an additive optional v1.1→v1.2 minor (no `derived.decisions[]`).
4. Distill stays deterministic; `derived` extraction is a separate opt-in pass.
5. Capture (i) structured self-emission first; (ii) faithful extraction opt-in.
6. Win bar = quality OR token (replicated).
7. `n=1` is noise → every gate N≥3, thresholds locked cold before the run.
8. Models present: claude, opencode (mimo/nemotron/deepseek/north free), agy, qwen.
   gemini/codex/crush absent.

## The critique we want
Where is this plan wrong? What's missing? Where will it fail? What must be measured
that isn't? Be specific and adversarial — a well-argued "this premise is false / this
gate isn't falsifiable / the honest answer here is no" is the most valuable result.

---

## Phase-0 panel synthesis (2026-06-19)

**Panel ops outcome (a finding in itself).** The free-model voices could not deliver:
`oc-mimo` and `oc-nemotron` both **timed out at 600 s** (read the doc, never produced
+wrote a critique); `agy`'s **Google OAuth expired** ("Authentication required …
timed out"). The free substrate is too weak/slow for an open-ended critique task, and
agy needs interactive re-auth. This confirms the plan's own ops-feasibility worry and
the integrator's Lens 4 — and means **the cross-model arms must lean on the
*success/quality* axis, not free-model token telemetry.** (It does NOT invalidate
Fork-A, which used agy earlier today while authed and is already banked.)

**Substantive critique = the integrator's four lenses** (`claude-lenses.md`). Net
refinements applied to the build (gate-level, not premise-level — no lever was wrong):

1. **G0 reconciliation target fixed.** `exp1-cost-marshmallow.json` has no per-component
   channel breakdown; `bench_join` reconciles against the raw
   `docs/benchmarks/results/raw/marshmallow/` metrics.jsonl (lumped `actual_tokens`) instead.
2. **Token axis needs a MEASURED model.** Every `oc-*` runner has `telemetry_flags: []`
   (unmeasured). The U-curve net-token rule (Phase 3) and any Phase-5 token win are
   evaluable **only on sonnet/opus**; free models give success/quality only. Verify
   `_opencode_parser` actually fires before claiming "opencode is measured."
3. **Scope Lever 1.** Best case is +8.1% → parity. Do Phase 1 + 2 + **Move 1**
   (say-once scaffolding, clearly good, ~free); do NOT pre-commit the full pack
   **sweep** (Move 3, most sonnet-$, least upside) — decide it after the G1 classification.
4. **agy re-auth** is a standing ops blocker for any NEW cross-model run (Phase-5
   optional confirm); Phase 1–4 (same-model, sonnet) and the reused Fork-A are unaffected.

**G-panel verdict: PROCEED.** No premise was falsified; the refinements tighten the
gates. Next: Phase 1 (channel instrumentation — the real prize).

---

## Phase-0 panel RE-RUN (2026-06-19 pm) — the free substrate delivered this time

The second panel run (after the `stdin=DEVNULL` fix + with `agy` re-authed) **succeeded
where the first timed out**: `critique-mimo` and `critique-agy` (Gemini) both produced
substantive adversarial critiques and handed back via the 1.2 schema; `critique-nemotron`
still hit "Upstream idle timeout exceeded" (free-model flakiness confirmed, 1/3). Full
critiques: `.pigeon/coordinate/reviews/comms/{mimo,agy}.md`. This is also a live proof the
cross-model channel + the operator-authorized `--skip-permissions` path work end to end.

**These critiques are sharp and several are premise-level. Adopted corrections (fold into the
methodology BEFORE the paid sweep):**

1. **USD-weight the win rule, and track `num_turns`** (agy). `state.derived` is *output*
   tokens (≈3–5× input price), and pointer-izing code (Move 4) can force extra tool-call
   turns that re-send the whole history — so a raw-token "win" can be a USD *loss*. The Phase 3 /
   Phase 5 rule changes from "net token win" to **net USD win** (output priced at the model's
   real multiplier), and `bench_join` must record `num_turns` so the multi-turn tool tax is
   visible. A compression config that raises turns is penalized.
2. **Add a pointers-only NULL arm for Lever 2** (mimo). Fork-A tested *contract compliance*,
   not *inference from code alone*. The honest Lever-2 test gives the receiver pointers but
   **no `derived` residue**; if a capable model re-derives the constraint anyway, the residue
   was unnecessary. This arm is now the core of Gate G-Lever2.
3. **N=3 screens, N≥8 confirms** (mimo + agy). 0.5³ = 12.5% all-pass by luck; one fluke drops
   a binary success rate from 100%→67%. Keep N=3 for cheap screening, require **N≥8** before any
   final GO on Lever 1 or Lever 2.
4. **Inject `derived` as visible markdown, not raw nested JSON** (agy). Models attend to nested
   JSON fields weakly; Fork-A carried its constraint *in the prompt*. Capture (i)'s harness
   surface should render `state.derived` as a top-level markdown block in the receiver's prompt,
   not assume the model parses it from the handoff JSON. (Affects whether Lever 2 works at all.)
5. **Lever 1 is DEFENSIVE, not optimization** (mimo). Token-neutral means Lever 1 prevents
   regression; it does not create savings. Frame it as maintenance, and state the baseline
   explicitly (today's pack/scaffold overhead) so "parity" is falsifiable.
6. **Falsification + exit ramp** (mimo). Lever 2 is abandoned if, at N≥8, the pointers-only null
   matches the with-derived arm on success AND regressions (capable models re-derive cheaply) —
   a real, publishable negative.

**Deferred (real but heavier):** run checkpointing/resumption so a hop-K failure doesn't waste
the whole cross-model pipeline (agy #5); a full power analysis toward N≥20 (mimo #3).

**G-panel-v2 verdict: PROCEED, methodology revised.** No lever was falsified, but the *measurement*
was — raw-token wins and N=3 would have measured the wrong thing. These corrections are folded into
the build plan's staged runs before any paid sweep.
