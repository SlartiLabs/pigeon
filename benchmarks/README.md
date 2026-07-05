# Benchmarks

Two efforts live here. The **carrier-comms study** (the main, completed work) measures what
pigeon's coordination is worth and bounds it precisely. The **Tier-A launch harness** is the
with-vs-without cost method plus its opsec and repo-selection machinery; its cost result is
now Experiment 1 of the carrier-comms study.

## Carrier-comms study (complete, reproducible)

The headline is a two-sided bounded law: the carried `state.derived` residue is necessary
**if and only if** the reasoning left no recoverable trace in the artifacts. Cost is a null
(pigeon does not save tokens); the value is cross-model capability plus carrying irreducible
reasoning. Confirmed as a superiority result where the residue is needed (Fisher p < 0.001)
and equivalence tests (TOST) where it is not.

- **Report:** [`REPORT-carrier-comms.md`](REPORT-carrier-comms.md) (Exp 1-5 + 4a/4b/4c,
  tables, and the §8a statistics appendix).
- **Manuscript (draft):** [`manuscript/`](manuscript/).
- **Pre-registrations:** [`PREREG-lever2-natural.md`](PREREG-lever2-natural.md) (Exp 5),
  [`PREREG-exp4c-deep-constraint.md`](PREREG-exp4c-deep-constraint.md) (Exp 4c); Exp 4b in
  `exp4b-substrate/CALIBRATION-RESULT.md`.
- **Substrates** (each with a held-out `accept.py` grader, a `validate.py`, and a committed
  per-trial ledger):
  - `exp4b-substrate/` sharp step on trace presence (the cue-salience ladder).
  - `exp4c-substrate/` depth: dedup-before-aggregate, cells `Dr`/`Du` diff-clean.
  - `exp5-substrate/` natural recoverable constraint (`to_wire`/`from_wire`).
- **Results:** `results/*.json` (`lever2-{confirm,natural,deep-4c,3hop,screen}.json`,
  `forkA-capability.json`, `lever1-sweep.json`, `cookiecutter.json` + `marshmallow.json` for
  the Exp 1 cost benchmark, and `stats-appendix.json`).
- **Figures:** `figures/fig{1..11}_*.png` (generators `make_figures.py`,
  `make_carrier_comms_figures.py`).
- **Instruments:** `rederivable_probe.py` (the base-rate probe, gated), `report-improve.crew.json`
  (the pigeon crew that adversarially reviewed the report).

### Reproduce

```
python3 benchmarks/figures/stats_appendix.py            # recompute every statistic
python3 benchmarks/figures/make_carrier_comms_figures.py   # rebuild fig5-11
python3 benchmarks/exp4c-substrate/validate.py          # validate a held-out grader (no agents, no spend)
```

## Track-B routing (ASIA groundwork)

The learned-coordination rungs (routing log, heuristic router, prompted coordinator):

- `results/b2-router-ablation.json` a role-aware heuristic router beats the static all-sonnet
  DAG net of cost (equal success, 68% cheaper) by offloading worker tasks to the free arm.
- `results/b3-difficulty-calibration.json` the free arm's capability boundary (a weak
  difficulty split), which bounds what a learned router could add over the heuristic.

## Tier-A launch harness (the with-vs-without method + opsec)

The method behind Experiment 1 and the launch-gating machinery.

- [`PROTOCOL.md`](PROTOCOL.md) with-vs-without method, two arms / one variable, opsec rules.
- [`KILL-CRITERION.md`](KILL-CRITERION.md) kill/continue criteria, locked cold.
- [`PUBLIC-CANDIDATES.md`](PUBLIC-CANDIDATES.md), [`PUBLIC-REPO-CRITERIA.md`](PUBLIC-REPO-CRITERIA.md)
  public reproducible-repo selection.
- [`REPORT.md`](REPORT.md) the Tier-A cost report; its result is Experiment 1 of the
  carrier-comms study above (which is now the headline).
- `tasks/` per-repo task specs.
- **`check-opsec.sh`** the pre-publication identity-leak guard: it greps committed
  `benchmarks/` against the gitignored `.private-map.json` (copy from
  `.private-map.template.json`). **Run it before any public commit.**
