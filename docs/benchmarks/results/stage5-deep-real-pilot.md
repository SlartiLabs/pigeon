# Stage 5 — deep-real substrate: pilot result (GATE 3, redesign)

**Anchor:** limitations-closing plan, Stage 5 — the only genuinely
*outcome-uncertain* stage. The plan states plainly that a first-design substrate
succeeding is the optimistic case, not the expected one. The pilot bears that out.

## Substrate

`ledger/money.py :: to_minor_units(amount, currency)` — the correct integer
minor-unit conversion for JPY and BHD is fixed by an **external** ISO-4217 fact
(JPY settles in whole yen, exponent 0; BHD in thousandths/fils, exponent 3) that
appears in no visible constant, comment, TASK.md, or test (`validate.py` 5/5). The
idiomatic `x100` is silently wrong for both. The mandatory **no-code guessing
baseline** measures how much of any pointers-only success is domain-prior guessing
rather than artifact recovery.

## Pilot result (sonnet, N=4 per arm)

| Arm | Pass | 95% CP CI | JPY ok | BHD ok |
|---|---|---|---|---|
| **no-code baseline** (task text only, no repo) | **4/4** | [0.398, 1.0] | 4/4 | 4/4 |
| **pointers-only** (full repo, no residue) | **4/4** | [0.398, 1.0] | 4/4 | 4/4 |

**Pointers-only sits exactly on the no-code floor.** Both arms get JPY and BHD
right every time — the no-code arm with *no repository at all*. So the
pointers-only "success" is **not** recovery from the artifact; it is the same
guess the model makes from its training-data priors about currencies.

## Verdict: GATE 3 — the substrate is defeated by priors, redesign

This is exactly the failure mode the plan's GATE 3 names: "if pointers-only lands
near the no-code guessing rate ... redesign before spending confirm-tier budget."
A naturalistic currency rule is guessable, so this substrate **cannot distinguish
genuine unrecoverability from a lucky domain-prior guess** — the black-box
pass/fail can't tell them apart, which is precisely why the no-code baseline was
made a hard requirement. Without it, pointers-only 4/4 would have been misread as
"the constraint is recoverable from the artifact."

A telling side-note: pointers-only cost **~2-4x more** than no-code (14-21 turns,
~$0.41-0.79 vs 6-7 turns, ~$0.15-0.35) — the agent read the whole repo and
arrived at the answer it would have guessed anyway. Repo access added cost, not
recovery.

## What a redesign needs (not run)

To achieve genuine unrecoverability, the deciding fact must be **arbitrary** with
respect to training priors — a value that cannot be guessed from domain knowledge
(Fork-A got this for free with arbitrary key names). Candidates: a
project-specific rounding threshold, an internal enum ordering, a
non-standard-but-plausible unit — something a model cannot infer from general
knowledge of the domain. The no-code baseline is the gate every candidate must
clear (guessing rate near 0) before pointers-only vs with-derived is worth
running. This is the same design-iteration the plan budgets weeks for, and the
same red-team rescope that saved the 4b factorial.

Ledgers: `stage5/no-code-N4.csv`, `stage5/pointers-only-N4.csv`. Figure:
`../figures/fig_s5_gate3.png`.

_Commits are the operator's._
