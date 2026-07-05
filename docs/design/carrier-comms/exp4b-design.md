# Experiment 4b — revised design & reconciliation with Exp. 5

**Status:** design locked after red-team; Stage-1 calibration running. **Supersedes the
methodology of** `EXP4B-natural-substrate-prereg.md` (kept for provenance) **without
changing its scientific question.** Substrate: `docs/benchmarks/substrates/exp4b-trace-presence/`.

## 1. What the red-team changed (and what it did not)

The question is unchanged: **does the `state.derived` residue generalize off the rigged
R≈0 point of Exp. 4 — and where is the boundary R\* at which it stops earning its
tokens?** What changed is the *instrument*, because the prereg's instrument was shown to
be likely uninterpretable:

| Prereg-as-written | Red-team finding | Revised design |
|---|---|---|
| Wild OSS commits, 4 task types, factorial | Two selection effects (training-recall inflates pointers-only; "discard tasks whose tests don't separate" keeps only test-encoded = high-R constraints) both bias toward a **false KILL**. Exp. 5 already hit this and fell back to semi-synthetic. | One **controlled** constraint; vary only **cue salience**. R is the single manipulated variable; nothing is memorizable. |
| N=4 calibration → **continuous-R regression** `success ~ arm×R̂` | R̂∈{0,.25,.5,.75,1}, SE≤0.25; a noisy regressor **attenuates the H1 slope toward zero** (errors-in-variables) — biases against the very curve it tests. | R is **ordinal** (3 pre-set bins), never a noisy covariate. No regression-to-the-ceiling, no errors-in-variables. |
| Per-task GO = non-overlapping exact CIs at N=8 | **Unmeetable at intermediate R** (5/8 vs 7/8 CIs overlap heavily); calibrated for the Exp-4 extreme only. | Pooled across the ladder; intermediate bin powered to **N≈20** at Stage 2 (Stage-1 calibration locates it first). |
| Decoy arm "optional" | It is the only arm that separates "the constraint helped" from "any prose helped" — load-bearing, not optional. | **Decoy arm mandatory** in the intermediate bin. |
| KILL = "indistinguishable from zero" | Conflates absence-of-evidence with evidence-of-absence under multiplicity. | KILL is a **TOST equivalence** claim (Δ bounded within margin), not a failed rejection. |
| H2 (task-type generality) headline | Type and R are likely collinear in any real pool (architectural ≈ low-R, API-contract ≈ high-R); H2 probably unsatisfiable. | Type **demoted to descriptive**; the **mechanism taxonomy (§7 of the prereg)** promoted to co-headline — it is the robust deliverable. |

## 2. The revised design in one line

Exp. 4 owns the **R≈0** endpoint (Δ huge: 8/8 vs 0/8). Exp. 5 owns the **R≈1** endpoint
(Δ≈0: pointers-only 8/8). **4b interpolates between two points already in hand** to find
**R\***, the boundary where the residue starts paying for itself — on a substrate where
the constraint, the task, and the held-out grader are **held fixed** and only the
in-code **cue salience** varies (`docs/benchmarks/substrates/exp4b-trace-presence/`, the R ladder
`R_low / R_mid / R_high`).

## 3. Reconciliation with the shipped Exp. 5

This design does not compete with Exp. 5 — it **absorbs it as an anchor and discharges
its stated open limitation.**

1. **R_high *is* Exp. 5, byte-identical.** `exp4b-substrate/R_high/ledger/account.py`
   `diff`s clean against `exp5-substrate/account.py`, and `accept.py` is reused verbatim.
   So the R≈1 anchor reuses Exp. 5's measured **pointers-only 8/8**; no re-run of that
   point is needed. The ladder is "Exp. 5, plus two more rungs of lower salience."

2. **4b answers the exact question Exp. 5 flagged as untested.** The report's §7b
   limitation reads: *"a subtler cue might land pointers-only in the partial regime
   (1–7/8) — that boundary is untested."* `R_mid` (keys present, framed as a neutral
   `_dump`/`_load` "old batch dump," no "external clients depend" comment) **is that
   subtler cue.** 4b's calibration tests precisely whether the boundary exists and where.

3. **The bounded headline is refined, not contradicted — calibration result: the step is
   SHARP.** The report's law — *"residue earns its tokens iff the reasoning left no
   recoverable trace in the code"* — was a **step function asserted from two endpoints.**
   Stage-1 calibration (2026-06-20, `docs/benchmarks/substrates/exp4b-trace-presence/CALIBRATION-RESULT.md`)
   measured the middle and found the transition is a **sharp step on trace *presence***,
   not a gradient on salience:
   - **R_low (no trace): 0/8, CI95 [0, 0.369]** — residue necessary (Fork-A/Exp-4 analogue).
   - **R_mid (non-salient trace: keys in `_dump`, no comment): 8/8, CI95 [0.631, 1.0],
     read-cue 8/8** — the receiver re-derives from a *non-salient* cue just as reliably as
     a salient one. The loud comment in R_high was **not load-bearing.** This is the
     pre-stated "R_mid lands N/N → step is sharp → *hardens* the headline" branch.
   - **R_high (= Exp-5): 4/4, read-cue 4/4** — reproduces Exp-5's 8/8.
   - **R_mid2 (distant cue in a sibling `sync_codec.py`): convention recovered 4/4** (bare
     pass rate 1/4 was a leniency-*implementation* artifact, orthogonal to R — all four
     grepped out and used the convention). Adjacency is not the bottleneck either.

   **CIs separated** (0.369 < 0.631), confirmed at N=8 — the same rigor as Exp-4 and
   Exp-5. So the refined law: **residue is overhead the moment a *findable* trace exists,
   not merely when the trace is salient.** R\* is a sharp step on trace *presence*; the
   cue-subtlety dimensions (salience, adjacency, distance) are flat at ceiling.

4. **Method continuity is exact.** Same grader (reused), same two-physically-separate-
   worktree discipline, same pristine-guard-on-**added-defs** (`def to_wire|from_wire`,
   not the keys — `R_mid`/`R_high` legitimately contain them), same turn-1-\$0 no-op
   discard, same exact Clopper-Pearson CIs. Nothing in the Exp. 1–5 disciplines is
   loosened.

5. **The scope limit (prereg §13) is preserved verbatim.** Mapping the Δ(R) curve still
   says **nothing about base rate** — how often real handoffs land below R\*. "We located
   R\*" must not become "residue helps in practice." That remains a separate
   observational study (`rederivable_fraction` on natural traffic).

## 4. Stage-1 calibration (running) and the locked Stage-2 plan

- **Stage 1 (this run):** pointers-only, N=4, across `{R_low, R_mid, R_high}`. Purpose:
  confirm the anchors (R_low≈0, R_high≈8/8) and **locate R_mid**. The pass rate is the R
  meter; `read_cue` confirms re-derivation is mechanism, not luck. Outcome routing per §3.
- **Stage 2 (locked, not yet run):** on the calibrated ladder, run **cold / pointers-only
  / pointers+derived / decoy** at **N≥8** (intermediate bin **N≈20**). Δ analyzed against
  the **ordinal** R bin. KILL = TOST equivalence at intermediate R. Mechanism: code every
  pointers-only failure by proximate cause (A missing-constraint / B incorrect-assumption
  / C lost-rationale), two coders + Cohen's κ, codebook pre-seeded from the 8 Exp-4 Type-A
  failures.

## 5. Where this lands in the program

4b adds **one interpolating row** between Exp-4 and Exp-5 in the results table:

| Constraint trace in the artifacts | Residue | Evidence |
|---|---|---|
| **absent** (Fork-A / R_low) | necessary | 8/8 vs 0/8 (Exp. 4); **R_low 0/8, CI [0,.369]** (4b) |
| **present, non-salient** (R_mid) | **unnecessary — re-derived 8/8** | **R_mid 8/8, CI [.631,1], read-cue 8/8** (4b) |
| **present, distant** (R_mid2) | unnecessary — recovered 4/4 | R_mid2 (convention found 4/4; 1/4 = leniency artifact) |
| **present & salient** (Exp. 5 = R_high) | unnecessary — re-derived 8/8 | 8/8 (Exp. 5); R_high 4/4 (4b) |

The boundary R\* is **sharp** (CI-separated at N=8) and sits at trace *presence*: every
cue-subtlety axis tested — salience, adjacency, distance — is flat at ceiling, so the
partial regime Exp. 5 hypothesized does **not** appear along the cue-subtlety axis.

It does not change the program's binding constraint (adoption, not mechanism); it
sharpens the *operating boundary* of the one lever that earns its keep.
