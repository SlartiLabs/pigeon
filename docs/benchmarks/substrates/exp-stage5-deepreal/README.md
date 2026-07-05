# Stage 5 substrate — deep-REAL constraint (the outcome-uncertain one)

Limitations-closing plan, **Stage 5**. This is the only stage that is genuinely
*outcome-uncertain*, not just effortful: Experiment 4c already attempted a
deep-real constraint once and the structural trace stayed visible, so a second
attempt succeeding on the first design is the optimistic case, not the expected
one. Nothing here presumes the boundary closes in the hoped direction.

**Status: substrate BUILT + mechanically validated (`validate.py`, 5/5). NOT yet
run.** Pilot and confirm are gated on operator go + live-trial spend.

## The constraint (minor-unit conversion, fixed by an external fact)

`ledger/money.py :: to_minor_units(amount_major, currency)` converts a major-unit
amount to the integer number of whole minor units the clearing partner settles
in. The pristine code ships the idiomatic `x100` (correct for the live USD/EUR
desks). The task (`TASK.md`) brings two new desks online — **JPY** and **BHD** —
whose correct conversion is fixed by each currency's minor-unit exponent (ISO
4217): **JPY settles in whole yen (x1), BHD in thousandths / fils (x1000)**. The
idiomatic `x100` is silently wrong for both.

Crucially, that exponent fact appears in **no visible constant, comment, TASK.md,
or test** (asserted by `validate.py` [4]/[5]). Unlike 4c — where the dedup
*structure* stayed visible in the code — here the deciding fact lives entirely
outside the repository. A correct answer must come from external knowledge of the
currencies, not from reading the code.

## Why the no-code baseline is mandatory (the new requirement this stage adds)

A naturalistic currency rule risks being **guessable from a model's general
training-data priors** — Fork-A's arbitrary key names sidestepped this by
construction; a real business rule does not. So a pointers-only success could be
genuine recovery OR a lucky domain-prior guess, and a black-box pass/fail cannot
tell them apart. `no-code-baseline.tasks.json` measures the guessing rate
directly: the implementer gets the task description **alone** — no repo, no pack,
no residue — and writes `money.py` from priors. Its grader pass rate is the floor
every pointers-only result is interpreted against, never a clean 0%.

## Arms

| File | Arm | Role |
|---|---|---|
| `no-code-baseline.tasks.json` | task description only, no repo | the guessing **floor** |
| `pointers-only.tasks.json` | code pointers, no residue | recoverability meter |
| `with-derived.tasks.json` | code pointers **+** carried exponent fact | does residue earn its tokens |
| *(decoy)* | reuse Stage 1b's rebuilt equal-weight off-topic control | isolates content from prose |

## Locked gates (stated before any trial)

- **GATE 1 (closes toward "yes, deep-real, residue helps"):** pointers-only near
  the no-code floor (genuinely unrecoverable) AND with-derived clears both
  pointers-only and decoy with separated CIs. Strongest outcome for the headline.
- **GATE 2 (revises the headline — the more interesting paper):** pointers-only
  recovers well above the no-code floor despite the fact's absence from any
  visible trace → some other channel (prior knowledge, structural analogy) does
  the recovery, and "documentation vs structure" needs a third axis:
  prior-knowledge-independent structure.
- **GATE 3 (uninformative substrate):** neither arm separates from the guessing
  floor interpretably → redesign, as the 4b factorial was redesigned before it
  produced a single misleading result.

## Run sequence (plan Stage 5, iterative — not single-shot)

1. `python3 validate.py` — the 5/5 mechanical check (done, no spend).
2. **No-code pilot** at N=3-4 → establish the guessing floor.
3. **Pointers-only pilot** at N=3-4 → if it lands near the floor, the substrate
   hides the trace; if near the guessing rate is high, redesign (GATE 3).
4. **Confirm N=8-12** only after the pilots clear: full arm set (pointers-only,
   decoy, with-derived), read against the floor from step 2.

Budget is not the bottleneck here; design iteration is. Expect to redesign at
least once, matching this project's own precedent (4b).

```
python3 docs/benchmarks/substrates/exp-stage5-deepreal/validate.py
```

_Commits are the operator's._
