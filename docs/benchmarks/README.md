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
  - `exp5-natural/` natural recoverable constraint (`to_wire`/`from_wire`).
- **Results:** [`results/`](results/) (`lever2-*.json`, `forkA-capability.json`,
  `lever1-sweep.json`, `cookiecutter.json` + `marshmallow.json` for Exp 1, `stats-appendix.json`).
- **Figures:** [`figures/`](figures/) (`fig{1..11}_*.png`, generators `make_figures.py`,
  `make_carrier_comms_figures.py`).
- **Instruments:** [`instruments/`](instruments/) (`rederivable-probe.py`, the base-rate
  probe; `report-review-crew.json`, the pigeon crew that adversarially reviewed the report).

### Reproduce

```
python3 docs/benchmarks/figures/stats_appendix.py                 # recompute every statistic
python3 docs/benchmarks/figures/make_carrier_comms_figures.py     # rebuild fig5-11
python3 docs/benchmarks/substrates/exp4c-depth/validate.py        # validate a held-out grader (no agents, no spend)
```

## Track-B routing (ASIA groundwork)

The learned-coordination rungs (routing log, heuristic router, prompted coordinator):

- `results/b2-router-ablation.json` a role-aware heuristic router beats the static all-sonnet
  DAG net of cost (equal success, 68% cheaper) by offloading worker tasks to the free arm.
- `results/b3-difficulty-calibration.json` the free arm's capability boundary (a weak
  difficulty split), which bounds what a learned router could add over the heuristic.

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
