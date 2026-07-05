# Limitations-closing plan — build status

Companion to [`limitations-closing-buildplan.md`](limitations-closing-buildplan.md)
(the anchor). This records what has actually been built, what is staged
ready-to-run, and the exact gate on each remaining live step. The split is
deliberate: everything that could be *built and mechanically validated without
spending live-trial money or needing agy re-auth* is done; everything that
requires paid multi-agent trials is staged to "ready-to-run" and flagged.

## Done — infrastructure + build deliverables (no agents, no spend)

### Stage 0 — metrics standard (CLOSED)

- **Task 1 (Gemini telemetry).** Confirmed: agy's `-p` print mode exposes **no**
  structured-usage flag (verified against `agy --help`; no `--output-format
  json`). So this was new parsing logic, not a config change. Built
  `_gemini_parser` / `_gemini_usage` in `src/pigeon/coordinate/telemetry.py` for
  Gemini's `usageMetadata` shape (`promptTokenCount` / `candidatesTokenCount` /
  `cachedContentTokenCount` / `totalTokenCount`), registered after the claude and
  opencode parsers (disjoint keys, so order is a tie-break only). It is the ready
  receiving half: the moment agy or a direct `generateContent` call surfaces
  `usageMetadata`, cost is captured with no scheduler-core edit. `agy` stays
  empty in `telemetry_flags` (documented as the real cost-accounting asymmetry).
- **Task 2 (token/cache split + transcript archival).** `normalize_usage`
  projects any vendor's raw usage onto the four canonical fields
  (`input_tokens` / `output_tokens` / `cache_creation_input_tokens` /
  `cache_read_input_tokens`) with Claude's conventions (uncached input only;
  reasoning/thoughts on the output side). Every measured trial now persists
  `usage_canonical` **and** a `transcript` pointer to the raw child log (already
  teed to `log_path`) in the run manifest + `metrics.jsonl`. The old "not
  retained" gap does not recur going forward.
- **Task 3 (canonical recount).** `pigeon.tokens.canonical_token_count`
  (o200k_base, named `CANONICAL_ENCODING`) recounts archived text uniformly and
  **refuses** to pass the offline heuristic off as canonical (strict by default).
  `instruments/canonical-retokenize.py` walks a run's transcript pointers and
  emits per-hop `canon_prompt` / `canon_completion` / `canon_total` alongside the
  native totals and USD. Required for Stage 2+; archived-only for within-model runs.
- **Tests:** `test_extract_telemetry_parses_gemini_usagemetadata_shape`,
  `test_normalize_usage_projects_every_vendor_onto_canonical_fields`,
  `test_canonical_token_count_named_and_strict`, and extended
  `test_telemetry_recorded_in_manifest_and_metrics`. Full suite green (the only
  failure is the pre-existing `boto3`-optional `test_resolve` case, unrelated).

### Stage 1b — decoy rebuilt (BUILT + validated)

`substrates/exp4c-depth/decoy-rebuilt.tasks.json` replaces the refused directive
decoy with four **true, verifiable, off-topic** facts about the visible test
fixtures, weight-matched to a representative `+derived` residue (88 vs 84
o200k tokens). `validate-decoy.py` asserts true + off-topic (no constraint/nudge
keyword) + weight-matched, no agents.

### Stage 3 — scale generator (BUILT)

`instruments/scale-generator.py` buries the Exp-5 `to_legacy`/`from_legacy`
convention **byte-for-byte** in synthetic repos at any file count, with
plausibly-relevant serialization decoys (shared vocabulary, different keys). The
held-out grader is placed **outside** the retrievable tree; the generator
self-checks canonical byte-identity + convention isolation + grader-held-out and
exits non-zero on any violation. Verified clean at 10/50/200/1000/5000.

### Stage 5 — deep-real substrate + no-code baseline (BUILT + validated)

`substrates/exp-stage5-deepreal/`: `to_minor_units` whose correctness for the new
JPY/BHD desks is fixed by an external ISO-4217 fact absent from every visible
constant, comment, TASK.md, or test — the hard line past 4c (where the structure
stayed visible). Ships the mandatory **no-code guessing baseline** arm
(`no-code-baseline.tasks.json`: task description alone, no repo) plus
pointers-only and with-derived. `validate.py` proves real + silent + external +
no-trace (5/5).

## Staged — live trials (gated on operator go + spend; Stage 2 also on agy re-auth)

| Stage | Ready artifact | Gate | Rough spend |
|---|---|---|---|
| 1a cost N=8 | reuse Exp-1 (cookiecutter, marshmallow) | operator go + spend | $30-50 |
| 1b confirm | `decoy-rebuilt.tasks.json` on Du, N=8-12 | operator go + spend | $10-15 |
| 2 cross-model | Fork-A + Exp-5 substrates, swap receiver to agy | **agy re-auth** + go + spend | $30-90 |
| 3 scale runs | `scale-generator.py` points, screen N=3-4 → confirm N=8 | operator go + spend | $40-120 |
| 4 base-rate `--live` | `instruments/rederivable-probe.py` | operator go + spend | $10-30 |
| 5 pilot → confirm | `exp-stage5-deepreal/` arms | go + spend; **redesign likely** | $50-200+ |

**Why the live trials were not auto-run:** each is a paid multi-agent run
(real dollars), Stage 2 additionally needs the documented agy re-auth, and a
verified `agy -p` call in this session confirmed the auth/latency wall. Spending
the operator's budget is a separate outward action from building the harness;
the harness is complete and each run is one command away.

## Suggested order when live runs are authorized

1. **Stage 0 first live trial** validates the archival path end-to-end on a real
   run (cheap; any Stage-1a trial does this incidentally).
2. **Stage 1a + 1b + 3-screen + 4** in parallel — mutually independent, cheap.
3. **Stage 2** once agy is re-authed (highest external-validity payoff).
4. **Stage 5 pilot** (no-code floor → pointers-only) before any Stage-5 confirm spend.
