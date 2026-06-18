# Benchmarks — the launch evidence (Tier A)

The launch is gated by **evidence, not polish**. This directory replaces the
constructed-counterfactual "~92.8%" with a **real, reproducible number** — even
if it's lower. A real 60% beats a synthetic 92.8%.

This is a *falsifiable experiment*, not a victory lap.

## Hypothesis
Developers who run ≥2 agent CLIs against one repo will get measurably more from
coordinating them through pigeon's token-accounted contract than from running the
same agents naked.

## Method — isolate ONE variable
Same agents, same task, two ways:
- **with pigeon:** the task run through `pigeon coordinate` (handoffs, pointers,
  worktree isolation, token accounting).
- **without pigeon:** the same agent CLI(s) run directly on the same task, same
  clean checkout.

Not "vs Aider/OpenHands" — that conflates "is coordination valuable" with "is
tool X good." Isolate coordination.

## Tasks (real work from this repo's own history, known shape)
Run each on a clean checkout (`git stash`/worktree from a fixed base SHA):
1. **`t1-version-drift`** — single-source the version + add the drift-guard test.
2. **`t2-resolve-coverage`** — raise `resolve.py` to ≥95% with real fence tests.
3. **`t3-ci-verdict`** — add the fail-closed `ci_report.py` normalizer + tests.

Start with 3; add 2 more only if the first 3 show a signal. See `tasks/`.

## Metrics (per task × per arm)
Recorded to `results/<task>-<arm>.json` (schema: `results.template.json`):
tokens · wall-clock · est. cost · success (tests green + acceptance met) ·
handoffs · merge-conflicts · human-interventions.

The headline output is **one honest number**: the with-vs-without delta on the
metric that matters most (success-rate, or tokens-to-green), published with the
methodology and the raw `results/` so anyone can re-run it.

## Honest limitations / failure catalog
`FAILURES.md` (start small, expand): the real failure modes hit while running
this — e.g. free-runner flakiness, the timeout-then-salvage path, contract drift.
This is what makes the launch credible rather than promotional.

## Kill / continue criterion — LOCK THIS COLD, BEFORE LAUNCH
A null result is information, not failure — but only if the bar is set in advance,
when you're not yet emotionally invested in the outcome.

> **Strawman (edit and lock):** 6 weeks post-launch — if **fewer than 25 external
> installs** (PyPI minus own CI) *and* **zero issues filed by a stranger** *and*
> **zero outside contributors**, the binding constraint is TAM, not polish: stop
> hardening, reconsider the thesis (or accept pigeon as an excellent tool for an
> audience of one — a complete and worthy outcome).

Weighting note: the install count is the noisiest signal (mirrors/bots/CI); the
unfakeable ones are **a stranger filing an issue** and **an external contributor**.
Weight those highest.

**Status:** harness + task-set defined; the with/without runs and the locked N are
the remaining launch-gating work (real agent runs — do before any blog post).
