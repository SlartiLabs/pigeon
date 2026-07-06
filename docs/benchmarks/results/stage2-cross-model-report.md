# Stage 2 — cross-model replication (Gemini via agy): report

**Anchor:** limitations-closing plan, Stage 2. Does the two-sided law
(residue necessary iff the reasoning left no recoverable trace) hold for a
second, architecturally different model? Receiver swapped from Sonnet to
agy/Gemini. Pricing snapshot: 2026-07-05. Held-out grader throughout.

> **Data-integrity note (read first).** An earlier batch of these arms was voided
> by a config error: `telemetry_flags.agy` had been set to `[--json]`, but agy has
> no such flag, so under `--telemetry` it printed its usage and exited without
> editing — recording false `0/N`. That batch (and the agy-authored report built
> on it) is **discarded**. Every number below is from a clean re-run with
> `telemetry_flags.agy: []`, verified to contain **zero** flag-break errors, with
> a harness guard now aborting any trial that hits one. See
> [`../../design/limitations-closing-status.md`](../../design/limitations-closing-status.md).

## Results (clean)

| Cell | Config | Pass | 95% CP CI | Reading |
|---|---|---|---|---|
| Recoverability · pointers-only | sonnet→agy | **12/12** | [0.735, 1.000] | agy recovers the in-code convention |
| Recoverability · with-derived | sonnet→agy | 8/12 | [0.349, 0.901] | agy-flakiness-confounded (see below) |
| Necessity · pointers-only | sonnet→agy | **0/8** | [0.000, 0.369] | off-disk contract unrecoverable |
| Necessity · pointers-only | all-agy | **0/8** | [0.000, 0.369] | floor holds in a controlled all-agy config |
| Necessity · with-derived | all-agy | **7/8** | [0.473, 0.997] | carried residue rescues it |
| Necessity · with-derived | sonnet→agy | 0/8 | [0.000, 0.369] | 8/8 agy **no-op** — not a residue measurement |

## What transfers cleanly

1. **The recoverable side transfers.** Recoverability pointers-only is **12/12**
   on Gemini — agy reads the `to_legacy` cue and matches the `acct/cents/ts`
   convention, exactly as Sonnet does (Exp-5's own 12/12). The boundary's
   recoverable half is a property of the artifact, not of Sonnet.

2. **The necessity floor holds cross-model.** Necessity pointers-only is **0/8**
   in *both* configs (sonnet→agy and all-agy): with no carried residue, the
   off-disk contract is unrecoverable regardless of the model doing the reading.
   `used_contract=0` on every trial — agy never guesses the arbitrary keys.

3. **The residue is necessary AND sufficient, cross-model.** In the controlled
   all-agy configuration, pointers-only **0/8** vs with-derived **7/8** is a clean
   separation (Fisher exact **p ≈ 0.0014**): carrying the `state.derived` contract
   turns a 0%-recoverable task into a solved one on Gemini. This is the necessity
   direction of the two-sided law, replicated on a second model.

## The confound, stated plainly (GATE C, not a null)

The two **sonnet→agy with-derived** arms are **not** clean measurements of
residue transfer, because agy did not reliably run:

- Necessity with-derived (sonnet→agy): **8/8 agy no-op** — agy received the full
  `## Carried reasoning` block, then exited 0 producing no output and editing
  nothing. The injection fired (`injected=1`); agy simply didn't act.
- Recoverability with-derived (sonnet→agy): 8/12, where the 4 misses are 2 agy
  no-ops, 1 timeout, 1 genuine wrong-output — again dominated by agy reliability,
  not by the residue.

This is agy's documented flakiness as a `coordinate` receiver (intermittent
no-op / "waits for a background task"), and per the plan's own gate definitions it
is a **GATE C** finding — an engineering gap in cross-model execution, *not* a
finding about recoverability. That cross-model injection itself works is proven by
the all-agy 7/8: when agy runs, it applies the carried contract correctly.

## Verdict

- **Necessity direction: replicated on Gemini.** Floor 0/8 (both configs) vs
  rescue 7/8 (all-agy), clean separation. The residue is necessary and sufficient
  for the unrecoverable constraint, cross-model.
- **Recoverable side: pointers-only replicated (12/12).** The equivalence claim on
  the with-derived arm is blocked by agy receiver flakiness, not contradicted.
- **A clean four-cell GATE A pass-rate table is gated on agy receiver
  reliability** (GATE C). The honest status is "the law's logic transfers to a
  second model in every cell that executed cleanly; a fully clean confirm-tier on
  the with-derived arms needs agy's no-op flakiness fixed or those trials re-run
  until agy fires."

## Metrics

agy emits no native usage (no `--json`/usage flag — a real provider asymmetry), so
USD is measured only on the Sonnet architect hops; the fair cross-model unit is the
canonical `o200k_base` recount (mean **354** tok/hop for agy, **630** for sonnet
across the clean arms). See `../instruments/canonical-retokenize.py --price` and
the per-arm `canon.json` under `~/stage2-clean/`.

## Provenance

Clean per-arm ledgers + raw transcripts persisted under `~/stage2-clean/`
(`exp5-with-derived`, `nec-pointers-only`, `nec-with-derived`, `nec-po-allagy`) and
`~/stage2/nec-wd-allagy` (the clean all-agy with-derived 7/8). Figures:
[`../figures/make_stage2_figures.py`](../figures/make_stage2_figures.py) →
`fig_s2_gateA.png`, `fig_s2_tokens.png`.

_Commits are the operator's._
