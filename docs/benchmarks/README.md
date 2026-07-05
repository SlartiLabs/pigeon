# Benchmarks

Two efforts live here. The **carrier-comms study** (the main, completed work) measures what
pigeon's coordination is worth and bounds it precisely. The **Tier-A launch harness**
([`tier-a/`](tier-a/)) is the with-vs-without cost method plus its opsec and repo-selection
machinery; its cost result is now Experiment 1 of the carrier-comms study.

## Carrier-comms study (complete, reproducible)

The headline is a two-sided bounded law: the carried `state.derived` residue is necessary
**if and only if** the reasoning left no recoverable trace in the artifacts. Cost is a null
(pigeon does not save tokens); the value is cross-model capability plus carrying irreducible
reasoning. Confirmed as a superiority result where the residue is needed (Fisher p < 0.001)
and equivalence tests (TOST) where it is not.

- **Report:** [`report.md`](report.md) (Exp 1-5 + 4a/4b/4c, tables, and the §8a statistics
  appendix).
- **Manuscript (draft):** [`manuscript/paper.md`](manuscript/paper.md).
- **Pre-registrations:** [`preregistrations/`](preregistrations/)
  (`exp4c-deep-constraint.md`, `exp5-natural-substrate.md`); Exp 4b in
  `substrates/exp4b-trace-presence/CALIBRATION-RESULT.md`.
- **Substrates:** [`substrates/`](substrates/), each with a held-out `accept.py` grader, a
  `validate.py`, and a committed per-trial ledger:
  - `exp4b-trace-presence/` the sharp step on trace presence (cue-salience ladder).
  - `exp4c-depth/` depth: dedup-before-aggregate, cells `Dr`/`Du` diff-clean.
  - `exp5-natural/` natural recoverable constraint (`to_wire`/`from_wire`); also holds the
    Stage 2 cross-model agy arms + `run-stage2-agy-pilot.sh` (recoverability side).
  - `forkA-necessity/` the Stage 2 necessity side: pristine `account.py`, off-disk contract
    0%-recoverable, agy-receiver arms + `run-stage2-forkA-agy.sh`.
- **Results:** [`results/`](results/) (`lever2-*.json`, `exp2-cross-model.json`,
  `exp3-pack-sweep.json`, `exp1-cost-cookiecutter.json` + `exp1-cost-marshmallow.json` for Exp 1, `statistics.json`).
- **Figures:** [`figures/`](figures/) (`fig{1..11}_*.png`, generators `make_figures.py`,
  `make_carrier_comms_figures.py`).
- **Instruments:** [`instruments/`](instruments/) (`rederivable-probe.py`, the base-rate
  probe; `report-review-crew.json`, the pigeon crew that adversarially reviewed the report;
  `canonical-retokenize.py`, the Stage-0 single-tokenizer recount — the fair cross-model metric
  when a provider (agy/Gemini) emits no usage; `--price prices.template.json` adds an ESTIMATED
  USD for those unmeasured arms; `scale-generator.py`, the Stage-3 synthetic-repo generator).

### Reproduce

```
python3 docs/benchmarks/figures/stats_appendix.py                 # recompute every statistic
python3 docs/benchmarks/figures/make_carrier_comms_figures.py     # rebuild fig5-11
python3 docs/benchmarks/substrates/exp4c-depth/validate.py        # validate a held-out grader (no agents, no spend)
python3 docs/benchmarks/substrates/exp4c-depth/validate-decoy.py         # Stage 1b: rebuilt decoy is true/off-topic/weight-matched
python3 docs/benchmarks/substrates/exp-stage5-deepreal/validate.py       # Stage 5: substrate real/silent/external/no-trace
python3 docs/benchmarks/instruments/scale-generator.py --out /tmp/s200 --files 200  # Stage 3: build a scale point
```

## Track-B routing (ASIA groundwork)

The learned-coordination rungs (routing log, heuristic router, prompted coordinator):

- `results/b2-router-ablation.json` a role-aware heuristic router beats the static all-sonnet
  DAG net of cost (equal success, 68% cheaper) by offloading worker tasks to the free arm.
- `results/b3-difficulty-calibration.json` the free arm's capability boundary (a weak
  difficulty split), which bounds what a learned router could add over the heuristic.

## Limitations-closing plan ([`../design/limitations-closing-buildplan.md`](../design/limitations-closing-buildplan.md))

Staged work against the eight disclosed limitations. The infrastructure and build
deliverables are done and self-validating (no agents, no spend); the live trials are staged
ready-to-run, gated on operator go + spend (and, for Stage 2, agy re-auth).

- **Stage 0 (metrics standard) — DONE.** Gemini `usageMetadata` telemetry parser
  (`src/pigeon/coordinate/telemetry.py :: _gemini_parser`) + a uniform `normalize_usage`
  token/cache split; every measured trial now archives the split and a pointer to its raw
  transcript in the run manifest; `canonical_token_count` (o200k_base) + the
  `instruments/canonical-retokenize.py` recount for cross-model (Stage 2+) comparison.
  Finding: agy's `-p` print mode exposes no structured-usage flag today (a real
  cost-accounting asymmetry), so the parser is the ready receiving half.
- **Stage 1b (decoy rebuilt) — BUILT + validated.**
  `substrates/exp4c-depth/decoy-rebuilt.tasks.json`: a true, off-topic, weight-matched
  residue replacing the old directive one that was refused. `validate-decoy.py` proves
  true + off-topic + weight-matched (no spend). Ready for confirm-tier N=8-12 on Du.
- **Stage 3 (scale as a confound) — generator BUILT.** `instruments/scale-generator.py`
  buries the Exp-5 convention byte-for-byte in synthetic repos at 10/50/200/1000/5000 files
  with plausibly-relevant decoys; grader held out of the retrievable tree; self-checks
  byte-identity + convention isolation. Screen N=3-4 → confirm N=8 on the decisive point.
- **Stage 5 (deep-real substrate) — BUILT + validated, outcome-uncertain.**
  `substrates/exp-stage5-deepreal/`: minor-unit conversion fixed by an external ISO-4217
  fact absent from every visible trace, plus the mandatory no-code guessing baseline arm.
  `validate.py` proves real + silent + external + no-trace (5/5). Pilot before confirm.

## Tier-A launch harness ([`tier-a/`](tier-a/))

The with-vs-without cost method behind Experiment 1, plus the launch-gating machinery.

- [`tier-a/report.md`](tier-a/report.md) the Tier-A cost report (its result is Experiment 1
  above, now the headline).
- [`tier-a/protocol.md`](tier-a/protocol.md), [`tier-a/kill-criterion.md`](tier-a/kill-criterion.md)
  the method and the cold-locked kill criteria.
- [`tier-a/public-candidates.md`](tier-a/public-candidates.md),
  [`tier-a/public-repo-criteria.md`](tier-a/public-repo-criteria.md) reproducible-repo selection.
- [`tier-a/tasks/`](tier-a/tasks/) per-repo task specs.
- **[`tier-a/check-opsec.sh`](tier-a/check-opsec.sh)** the pre-publication identity-leak
  guard: greps committed `docs/benchmarks/` against the gitignored `tier-a/private-map.json`
  (copy from `tier-a/private-map.template.json`). **Run it before any public commit.**
