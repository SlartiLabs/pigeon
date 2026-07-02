# Exp-4c substrate — does the sharp step survive DEPTH, net of difficulty?

Pre-registration: [`../PREREG-exp4c-deep-constraint.md`](../PREREG-exp4c-deep-constraint.md).
**Status: substrate built + mechanically validated. NO arms run** (the live run is a
separate spend decision, per the prereg precondition).

## What this tests

Exp-4b found a sharp step on *trace presence*, but on a shallow constraint (a key-naming
convention) where "a trace is present" and "the reasoning is recoverable" are the same
question. 4c separates them on a **deep** constraint: the code is fully present but the
*rationale* is not recoverable from it. The governing question: does trace presence still
govern (Gate 2, 4b generalizes), or does **recoverability** govern (Gate 1, residue earns
its tokens at depth)? See the prereg for the locked gates.

## The deep constraint (dedup-before-aggregate)

`ledger/reconcile.py :: settle(entries)` totals a settlement batch. Entries sharing a
`txn_id` are **re-submissions** of one transaction (gateway retries), **not additive**, so
`settle` dedups by `txn_id` (keep-last) before summing. The code always dedups on pristine.
The task (`TASK.md`) asks to *streamline* `settle` into a single pass with no intermediate
dict — and the idiomatic single-pass `sum(e.amount_cents for e in entries)` **silently
drops the dedup**, double-counting retries. The visible tests carry no duplicate `txn_id`,
so the break passes them; the held-out grader (`accept.py`, with re-submissions) catches it.

## The cells (difficulty held constant by construction)

| Cell | What | Role |
|---|---|---|
| **Dr** — deep-recoverable | deep constraint, rationale **documented** in the `settle` docstring | difficulty control |
| **Du** — deep-unrecoverable | the **identical** code + task, docstring **stripped** of the rationale | target cell |
| **S** — shallow-recoverable | the Exp-4b `R_mid` substrate, reused verbatim | anchor back to 4b (not rebuilt here; see `../exp4b-substrate/`) |

`Dr` and `Du` are **identical modulo the docstring/comment** (asserted by
`validate.py`'s diff-clean check), so the only thing that varies between them is whether
the rationale is recoverable. Difficulty is therefore held constant by construction, not
by statistical control. The decisive contrast is **PO_Du vs PO_Dr** (pointers-only, the
recoverability meter); `S` anchors the ladder to the confirmed 4b step.

## Arms (run in each cell; cell = working dir)

- `pointers-only.tasks.json` — the recoverability meter (no carried rationale).
- `with-derived.tasks.json` — architect emits the rationale into `state.derived` → `##
  Carried reasoning` injection (schema 1.2, same mechanism as 4b/5).
- `decoy.tasks.json` — equal-weight but irrelevant residue; isolates carried *content*
  from generic added prose. (It even nudges toward the break, making it a strong control.)

## Validate (no agents, local only)

```
python3 benchmarks/exp4c-substrate/validate.py
```

Asserts, for both Dr and Du: [1] grader passes pristine, [2] visible tests pass pristine,
[3] the idiomatic single-pass break **fails** the grader (constraint is real), [4] that
break still passes the visible-test inputs (the break is **silent**), and [5] Dr/Du are
identical modulo docstrings/comments (difficulty held constant). Results append to
`../results/lever2-deep-4c.json` once the run completes.

_Commits are the operator's._
