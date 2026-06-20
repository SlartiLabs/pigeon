# Pre-registration — Experiment 5: Lever-2 on a *natural* multi-hop substrate

**Status:** PRE-REGISTERED (thresholds locked before any run) · **Date:** 2026-06-20
**Branch:** `feat/carrier-comms` · **Authors:** carrier-comms program
**Locks:** this document is committed *before* the substrate is built and before any
arm is run. Post-hoc changes to arms, N, thresholds, or the grader invalidate the
result and must be recorded as a deviation with rationale.

---

## 0. Why this experiment exists (the binding constraint)

Experiment 4 confirmed at **N=8 (CIs separated)** that a carried `state.derived`
constraint is **necessary** — *on a task engineered to need it.* The Fork-A contract
was deliberately anti-idiomatic and **invisible in the final code**: the idiomatic
default was the exact opposite of the contract, so the constraint was **~0 %
recoverable** from the artifacts. That proves *a regime exists*. It does **not** show
the regime is common, or that residue helps when the reasoning is **not** artificially
hidden.

This is the mesocosm problem: the effect is real and clean, but the mesocosm was built
to express it. **Experiment 5 asks the external-validity question:** when the
constraint is **partially — but not fully — recoverable** from the code (a careful
carrier could re-derive it; a hasty one defaults wrong), does carrying the residue
still help, and does it survive a real chain?

The honest possible outcomes, all publishable:
- **Residue helps on natural tasks** (with-derived > pointers-only, CIs separated) →
  the effect generalizes beyond contrived contracts. Lever 2 is a real feature.
- **Capable models re-derive anyway** (pointers-only ≈ with-derived, both high) → the
  Fork-A regime is contrived/rare; Lever 2 is a niche that fires on hidden constraints.
- **Substrate out of regime** (manipulation check fails, §4) → not a result about
  Lever 2; the substrate needs retuning. Reported, not hidden.

---

## 1. Hypotheses (directional, locked)

- **H1 (effect).** On a partially-recoverable constraint, held-out success is higher
  with the residue carried than pointers-only: `P(pass | +derived) > P(pass | pointers)`.
- **H0 (null — capable re-derivation).** `P(pass | +derived) ≈ P(pass | pointers)`:
  a capable same-model receiver reconstructs the constraint from the code, so the
  residue adds nothing. This is the *expected* outcome the experiment must be able to
  return, and a real finding.
- **H2 (multi-hop survival).** The effect persists at hop 3 of a chain where hop 3 only
  directly `needs` hop 2 — i.e. the transitive-injection fix (committed `2691520`) is
  load-bearing on a natural task, not just the unit test.

---

## 2. The substrate (selection criteria, not a cherry-picked task)

To avoid post-hoc task-shopping, the substrate is defined by **criteria fixed here**;
the first task meeting them all is used, and the search is logged.

A valid substrate is a small repo + a multi-file implementation task where:

1. **The constraint lives in the code, but is non-salient.** The correct behaviour is
   recoverable by reading an existing sibling (a comment, a sibling method, an adjacent
   module) — *not* invented. This is the hard line vs Fork-A (0 % recoverable).
2. **The idiomatic default differs from the constraint.** A carrier that pattern-matches
   the codebase majority, or reaches for the language default, gets it **wrong**. This
   is what makes pointers-only fail *sometimes* rather than never.
3. **Held-out, binary, mechanical grader.** An `accept.py` the agents never see,
   validated **fail-on-pristine / pass-on-reference** before any arm runs.
4. **Genuine 3-hop chain** (plan/architect → implement → review or equivalent), where
   the final hop directly `needs` only its immediate predecessor (tests H2).
5. **The discovering hop is hop 1.** The architect explores and records the constraint
   in `state.derived.constraint_found`; the question is whether it survives downstream.

**Primary substrate (target):** a task on a **real public repo** (the cost-benchmark
pool — marshmallow/cookiecutter class) where an added feature must honour a
present-but-subtle convention (e.g. an error-message key the base class dispatches on,
a serialization boundary documented in an adjacent comment, a registry key an external
client depends on). External validity is highest here.

**Fallback substrate (if no clean public task is found in a fixed search budget):** a
**naturalistic extension of the `ledger` repo** — add `to_wire`/`from_wire` for a new
boundary that must match an **existing, in-code** `to_legacy()` method (with the
`acct/cents/ts` keys + a comment "external clients depend on these exact keys"). Unlike
Fork-A, the convention is **in the code** (recoverable via `to_legacy`) but easy to
miss (the idiomatic default differs). This is the honest "partial recovery" middle, and
it keeps the grader reusable. If the fallback is used, that is a stated limitation
(semi-synthetic, not a wild public task).

---

## 3. Design, arms, N (locked)

Same model throughout (**claude/sonnet ×3**) to isolate residue value from any
cross-model confound; **two physically separate worktrees** per arm (the leak guard
from Exp. 4 §9); schema 1.2; pristine-asserted per trial.

| Arm | Hop-1 emits residue? | Downstream receives | Tests |
|---|---|---|---|
| **pointers-only** (null) | no | pristine code pointers only | re-derivation rate (manipulation check) |
| **pointers + derived** | yes — `state.derived.constraint_found` → markdown injection | code pointers **+** carried residue | H1, H2 |

The optional **cold** (cross-model, no bridge) arm is **not** central here — Exp. 2
already settled cross-model capability. Run it only if the cross-model writeup needs a
matched cold point on this substrate.

**N = 8 per arm** (the confirm tier from the locked KILL-CRITERION; N=3 was screen).
**Chain topology:** hop3 `needs: [hop2]` only — H2 rides on every trial.

---

## 4. Manipulation check (the gate that makes the comparison meaningful)

The substrate is only in the target regime if the constraint is **genuinely partially
recoverable**. This is **verified from the pointers-only arm, not assumed**:

- **Valid (in-regime):** `0 < pointers-only pass < 8`. The constraint is recoverable
  but missable — the comparison with +derived is meaningful. **Proceed to the H1 test.**
- **Too hidden (Fork-A redux):** pointers-only `= 0/8`. The constraint was *not*
  recoverable from code → this is another constructed task, not a natural one. **Report
  as "substrate too hidden"; H1 is not a natural-task result.** Retune (make the
  in-code cue more present) or fall back.
- **Fully idiomatic:** pointers-only `= 8/8`. The constraint is trivially recoverable →
  no headroom for residue to help. **Report as "constraint re-derived for free" — this
  is H0, and a real finding** (residue is unnecessary for recoverable constraints).

The pointers-only arm is therefore run **first** as the manipulation check, and its
outcome routes interpretation **before** the +derived arm is compared.

---

## 5. Locked thresholds & the discrimination logic

**Primary test (H1 vs H0).** Held-out success, +derived vs pointers-only, **N=8 each**,
**exact 95 % Clopper-Pearson CIs**, two-sided **Barnard's / Fisher's exact** on the 2×2.

- **GO (residue helps on natural tasks):** +derived success > pointers-only **and the
  two 95 % CIs do not overlap** (the Exp. 4 bar). Effect size = the success-rate gap.
- **NULL / H0 (re-derived anyway):** CIs overlap **and** pointers-only ≥ 6/8 — the
  model recovers the constraint without help. A real, publishable negative.
- **Inconclusive:** CIs overlap with pointers-only in `[1, 5]/8` — underpowered;
  escalate N (pre-commit to N=16 before peeking again) or accept as a weak signal.

**Cost axis (USD-weighted, per the panel).** Report mean measured USD + `num_turns`
both arms. A success-equal but cheaper +derived arm is a secondary win; a success-equal
but *dearer* +derived arm (residue bloat) counts against it. USD is the ground truth,
not raw tokens (Exp. 4 Fig. 9).

**Mechanism coding (how we tell helped-vs-re-derived, not just that):** for every
pointers-only trial, code from the run log whether the agent **read the in-code cue**
(the sibling method / comment) before implementing:
- passed **and** read the cue → genuine re-derivation (supports H0).
- passed **without** reading the cue → lucky idiomatic match (check the grader isn't
  too lenient).
- failed → defaulted to the idiomatic wrong convention (supports H1's premise).
This turns "+derived has a higher number" into a *mechanism*: residue helps **because**
pointers-only carriers miss the cue, not because the task is impossible.

**H2 (multi-hop survival).** On +derived trials, log injection at hop 2 and hop 3
(`inject(hop2, hop3)`). Survival holds iff hop-3 injection fires on ≥ 7/8 trials **and**
the hop-3 implementation honours the constraint. (Pilot on the Fork-A 3-hop run already
shows hop3 injection firing with `needs:[hop2]` only — this confirms it on a natural task.)

---

## 6. Held-out grader requirements (locked)

- `accept.py` encodes the constraint as assertions; **agents never see it**.
- Validated **before** any arm: **fails** on the pristine repo (constraint absent) and
  **passes** on a hand-written reference implementation that honours the constraint.
- Binary pass/fail per trial; no partial credit (keeps the success axis clean for CIs).
- The grader checks the **constraint**, not just "code runs" — a round-tripping but
  convention-violating implementation must **fail** (the Fork-A grader's key property).

---

## 7. Stop / kill / report rules

- Run **pointers-only first** (manipulation check, §4) → route interpretation.
- Then **+derived, N=8** → primary test (§5).
- **Discard-and-rerun** any trial that is a rate-limit / infra no-op (turn-1, $0, < ~10 s
  wall — the signature from Exp. 4 §9); every reported trial is a valid real run.
- **Report all three regime outcomes honestly** (helps / re-derived / too-hidden). The
  experiment is designed to be able to *fail to find* an effect; that is the point.
- Lock this file's thresholds **before** the first run; any change is a logged deviation.

---

## 8. What this does and does not settle

**Settles:** whether the confirmed Lever-2 effect survives the move from a constructed
constraint to a partially-recoverable one, on a real chain — the difference between "a
regime exists" and "this matters in practice."

**Does not settle:** how *frequent* irreducible reasoning is in real multi-agent work
(the `rederivable_fraction` frequency question — a separate study on natural handoff
corpora, explicitly out of scope here). And it is **one** substrate; external validity
compounds with more, but one natural task is the decisive next datum.

---

_Commits are the operator's. Results append to `results/lever2-natural.json` and the
report's Table 2 once the run completes._
