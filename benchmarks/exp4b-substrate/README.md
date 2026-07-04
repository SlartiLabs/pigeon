# Experiment 4b substrate — the residue across a re-derivability gradient

Substrate + held-out grader for **Exp. 4b, revised design** (see
[`../../docs/design/EXP4B-revised-design.md`](../../docs/design/EXP4B-revised-design.md)).
**Stage-1 calibration only is run from here; no confirmation arms yet.**

## Why this differs from the prereg as written (the red-team result)

The pre-registration (`EXP4B-natural-substrate-prereg.md`) proposed a 4-task-type
factorial over wild OSS commits with an N=4 calibration and a continuous-R regression.
A red-team found that design likely **uninterpretable**:

1. **N=4 cannot place a task on a continuous R axis** — R̂ ∈ {0,.25,.5,.75,1}, SE up to
   0.25; feeding that noisy R̂ into `success ~ arm × R̂` attenuates the very slope (H1)
   toward zero (errors-in-variables).
2. **Two selection effects both bias toward a false KILL**: training-contamination
   inflates pointers-only (recall masquerading as re-derivation), and the
   "discard tasks whose tests don't separate" filter keeps only test-encoded
   constraints — which are themselves high-R cues. **Exp. 5 already hit this wall and
   fell back to a semi-synthetic ledger for exactly this reason.**
3. The per-task "non-overlapping exact CIs at N=8" GO is **unmeetable at intermediate
   R** (5/8 vs 7/8 CIs overlap massively) — it is calibrated for the Exp-4 extreme.

**Revised job.** Exp. 4 owns the R≈0 endpoint (Δ huge: 8/8 vs 0/8). Exp. 5 owns the
R≈1 endpoint (Δ≈0: pointers-only 8/8). So 4b's real task is the **interpolation
between two points already in hand** — locate R\*, the boundary where the residue starts
earning its tokens. That converts a fragile factorial into a tractable 1-D curve and
**removes both selection effects**: the constraint and grader are held fixed and only
**cue salience** varies, so re-derivability R is the single manipulated variable, on a
controlled (non-memorizable) substrate.

## The R ladder (only `ledger/account.py` differs between variants)

| Variant | In-code cue | Predicted pointers-only | Anchor |
|---|---|---|---|
| `R_low/`  | **none** — no legacy boundary; the convention exists only in the held-out grader. Idiomatic default (`name/balance_cents/ISO`) is the opposite. | ≈ 0/N | Fork-A / Exp-4 analogue on the ledger |
| `R_mid/`  | keys present but **non-salient**: `_dump`/`_load` framed as an "old v1 batch dump," **no** "external clients depend" comment, neutral naming. Recoverable by reading the method; nothing flags it as the format to match. | **1–7/N (target)** | the interpolation point 4b exists to find |
| `R_high/` | full salient cue: `to_legacy`/`from_legacy` sibling + loud "EXTERNAL CLIENTS DEPEND ON THESE EXACT WIRE KEYS" comment. **Byte-identical to the Exp-5 substrate.** | 8/8 (already measured, Exp-5) | Exp-5 anchor |

The constraint (`acct/cents/ts`, epoch-int ts, omit-None note, lenient `from_wire`),
the task (`TASK.md`), and the grader (`accept.py`) are **identical across all three**.

## Files

| File | Role |
|---|---|
| `accept.py` | **held-out** grader (agents never see it), constraint-checking, **reused verbatim from Exp-5** so `R_high` literally is Exp-5. |
| `TASK.md` | neutral task — "add v2 `to_wire`/`from_wire` consistent with how the codebase serializes for the external partner." Identical across variants. |
| `<R>/ledger/account.py` | the only thing that varies — the cue at three salience levels. |
| `<R>/tests/test_account.py` | base tests — exercise only the legacy/dump boundary (or none, for R_low); never encode the v2 convention (no leak). |
| `pointers-only.tasks.json` | **null / calibration arm** — 3-hop chain, pointer only, no residue. The R meter. |
| `with-derived-derive.tasks.json` | residue arm for R_mid/R_high — architect **derives** the convention from the cue, records it in `state.derived`. |
| `with-derived-given.tasks.json` | residue arm for R_low — architect is **given** the convention out-of-band in its prompt (Exp-4 structure, since R_low has nothing to read). |
| `decoy-residue.tasks.json` | **decoy arm (now mandatory)** — carries plausible-but-irrelevant reasoning; isolates "the constraint helped" from "any prose helped." |
| `validate.py` | local grader validation (no agents). |

## Grader validation — all four properties hold on every variant

Run: `python3 validate.py`  → `VALIDATION: OK`

| Property | R_low | R_mid | R_high |
|---|---|---|---|
| **fail-pristine** (grader fails before `to_wire` exists) | ✅ rc=1 | ✅ rc=1 | ✅ rc=1 |
| **base-tests-pass** on pristine | ✅ | ✅ | ✅ |
| **pass-reference** (convention-matching impl passes) | ✅ rc=0 | ✅ rc=0 | ✅ rc=0 |
| **anti-validation** (idiomatic, self-round-tripping, WRONG keys **fails**) | ✅ rc=1 | ✅ rc=1 | ✅ rc=1 |

The 4th is load-bearing: a working-but-convention-violating impl must fail, or the
success axis is confounded.

## Ready-to-run notes (the eventual operator run)

- **Stage-1 = pointers-only across the three variants** (this is `run-calibration.sh`).
  The crux is whether `R_mid` lands in the partial regime **1–7/N**. `0/N` = too hidden
  (make the cue more salient); `N/N` = fully recoverable (= Exp-5, retune down). R_low
  should ≈ 0/N and R_high should ≈ 8/8 as sanity anchors.
- **Pristine guard (same as Exp-5):** the cue methods are named `to_legacy`/`_dump`, not
  `to_wire`, so guard on the ADDED defs — `grep -c 'def to_wire\|def from_wire'` over
  `account.py` + `tests/test_account.py` must be `0`. Do **not** grep for the keys
  (`R_mid`/`R_high` legitimately contain them).
- Two physically separate worktrees per arm, schema-1.2 + `sonnet`-runner `.pigeon`
  config, staged at `/tmp/bench/exp4b` (disposable). Discard turn-1 \$0 rate-limit
  no-ops by their physically-impossible signature; report only valid trials.
