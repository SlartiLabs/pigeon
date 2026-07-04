# Experiment 5 substrate — built, validated, RUN (two-arm, N=12, TOST-confirmed)

**Status (2026-07-04):** the pre-registered primary two-arm test ran at N=12 each.
pointers-only **12/12**, +derived **12/12** (injection verified), TOST-equivalent at ±0.20
(Newcombe diff-CI [-0.184, 0.184]) = H0 confirmed (residue unnecessary when the constraint
is recoverable). Seven +derived trials first hit a session rate-limit (turn-1/$0 no-ops),
discarded and rerun; all 12 reported are valid. Per-trial ledger: `RESULTS-confirm-N12.csv`;
aggregate + TOST + verdict: `../results/lever2-natural.json`; stats: `../results/stats-appendix.json`.

---

_(original build note follows)_

Substrate + held-out grader for the pre-registered Exp. 5
([`../PREREG-lever2-natural.md`](../PREREG-lever2-natural.md)): Lever-2 on a
**natural, partially-recoverable** constraint, as opposed to Fork-A's constructed
(0 %-recoverable) one. Built per the prereg §2 criteria. **No arms have been run** —
this records the build + the grader validation only.

## Bounded substrate-search decision (prereg §2)

Primary target was a real public-repo task; the fallback was a naturalistic `ledger`
extension. **Chosen: the fallback**, for a methodological reason, not convenience: on a
wild public task the *grader* cannot cleanly separate "followed the convention" from
"wrote working-but-different code" — the binary success axis gets confounded. The
ledger extension makes the convention **grader-checkable** (exact wire keys), which is
required for clean exact-CI success rates. Stated limitation: semi-synthetic (the
repo is authored), but the constraint is **genuinely in the code and recoverable** —
the hard line vs Fork-A.

## What's here

| File | Role |
|---|---|
| `account.py` | the repo under test — `Account` + an **existing** `to_legacy`/`from_legacy` boundary (the non-salient in-code cue: keys `acct/cents/ts`, epoch-int ts, omit-null note, lenient consumer; with a comment that external clients depend on the exact keys). **No `to_wire`/`from_wire`** — that's the task. |
| `test_account.py` | base tests — exercise only the legacy boundary; do **not** encode the v2 convention (no leak). |
| `accept.py` | **held-out** grader (agents never see it): checks `to_wire`/`from_wire` honour the `acct/cents/ts` convention + leniency + round-trip. |
| `TASK.md` | neutral task — "add the v2 sync wire format, consistent with how the codebase serializes for the external partner." Does **not** state the keys; the agent must read `to_legacy`. |
| `pointers-only.tasks.json` | null arm — 3-hop chain; the architect delegates with a pointer only, no residue. |
| `with-derived.tasks.json` | residue arm — the architect records the convention it discovers in `state.derived.constraint_found`; coordinate injects it downstream. |

Both arm specs are 3-hop (`architect → to_wire → from_wire`) with **`from_wire` needing
only `to_wire`** — so the hop-1 discovery must survive transitively (exercises H2 on a
natural task).

## Grader validation (all four properties hold)

| Property | Result |
|---|---|
| **fail-pristine** — grader fails on the pristine repo (no `to_wire`) | ✅ `ACCEPT: FAIL`, rc=1 |
| **base tests pass** on pristine | ✅ 4 passed |
| **pass-reference** — a convention-matching impl passes | ✅ `ACCEPT: PASS`, rc=0 |
| **anti-validation** — an idiomatic, *round-tripping* impl with `name/balance_cents/ISO` keys **fails** | ✅ `ACCEPT: FAIL`, rc=1 |

The 4th is the load-bearing one: the grader tests the **constraint**, not "code runs."
A working-but-convention-violating implementation must fail, or the experiment is
confounded.

## Ready-to-run notes (for the eventual operator run)

- Run **pointers-only first** as the manipulation check (prereg §4): the result is a
  natural-task finding only if `0 < pointers-only pass < N`. `0/N` = too hidden (retune);
  `N/N` = fully recoverable (that *is* the H0 null).
- **Pristine guard for Exp. 5 differs from Exp. 4:** the cue `to_legacy` legitimately
  contains the `acct/cents/ts` keys in `account.py`, so do **not** grep for those.
  Assert pristine via `grep -c 'def to_wire\|def from_wire'` over `account.py` +
  `test_account.py` == 0 (the thing the agent *adds*).
- Two physically separate worktrees (`wt-derived`, `wt-pointers`) + the schema-1.2 +
  `sonnet`-runner `.pigeon` config are staged at `/tmp/bench/exp5` (disposable). N=8 per
  arm, discard rate-limit no-ops, exact-CI thresholds per prereg §5.
- Both arms dry-run clean (`repo://ledger/account.py` + `repo://TASK.md` resolve;
  permission gate clears).
