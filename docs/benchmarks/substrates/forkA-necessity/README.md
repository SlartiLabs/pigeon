# Fork-A necessity substrate — Stage 2 (cross-model), receiver = agy/Gemini

The **necessity** half of Stage 2's two-sided law, matching the recoverability
half in `../exp5-natural/` (the agy arms there). Both halves use the SAME held-out
grader and the SAME acct/cents/ts contract; only the substrate differs.

**Status: BUILT + mechanically validated (`validate.py`, 3/3). NOT yet run.** The
recoverability-side pilot already passed (Exp-5 agy, N=1); this side is staged
ready to run alongside it.

## The two sides, one law

| Side | Substrate | Cue in code? | Expected pointers-only | Expected with-derived |
|---|---|---|---|---|
| Recoverability (`../exp5-natural`) | `account.py` **has** `to_legacy` | yes (non-salient) | recovers (Exp-5 12/12) | equivalent (residue not needed) |
| **Necessity (here)** | `account.py` **pristine**, contract off-disk | **no** | **~0/8** (cannot recover) | **~8/8** (residue is needed) |

The only structural difference is the `to_legacy` boundary: present in Exp-5
(recoverable), absent here (unrecoverable). `validate.py` proves the contract is
0%-recoverable — the keys `acct/cents/ts` appear in no visible file, and the
idiomatic Python default (`name/balance_cents/created` as ISO) FAILS the grader.

## Arms (receiver swapped to agy; roles freely reassignable)

- `pointers-only-agy.tasks.json` — architect carries NO residue; agy receivers
  must guess the wire format from pristine code → cannot → ~0/8.
- `with-derived-agy.tasks.json` — architect is given the contract and carries it
  in `state.derived` → injected as `## Carried reasoning` → agy receivers
  implement it exactly → ~8/8. agy can be the architect too (`ARCH=agy RECV=agy`),
  since v1.0.16 runs the `pigeon handoff` shell call synchronously.

## Locked gate (Stage 2)

- **GATE A (boundary transfers):** necessity side separates (pointers-only ~0/8
  vs with-derived ~8/8, non-overlapping exact CIs) AND the recoverability side is
  TOST-equivalent at ±0.20. Reading: the boundary is a property of the task and
  artifacts, not of Sonnet specifically.
- **GATE B (boundary shifts):** an intermediate rate on either side → the exact
  location is receiver-dependent (a real, more interesting finding).
- **GATE C (mechanism fails):** injection does not fire / agy's edit format
  breaks parsing → engineering gap, fix and rerun (the Exp-5 pilot already
  cleared this).

## Validate + run

```
python3 docs/benchmarks/substrates/forkA-necessity/validate.py                       # 3/3, no spend
bash    docs/benchmarks/substrates/forkA-necessity/run-stage2-forkA-agy.sh 1 pointers-only-agy   # pilot
bash    docs/benchmarks/substrates/forkA-necessity/run-stage2-forkA-agy.sh 8 pointers-only-agy   # confirm
bash    docs/benchmarks/substrates/forkA-necessity/run-stage2-forkA-agy.sh 8 with-derived-agy    # confirm
```

_Commits are the operator's._
