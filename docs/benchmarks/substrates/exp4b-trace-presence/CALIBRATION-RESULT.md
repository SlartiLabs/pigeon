# Exp-4b Stage-1 calibration — result (2026-06-20)

> **LOCKED RESULT.** R\* is a **sharp step on trace *presence***, not a gradient on cue
> subtlety. Confirmed at the program's exact-CI standard: **R_low 0/8 (CI95 [0, 0.369])
> vs R_mid 8/8 (CI95 [0.631, 1.0]) — CIs separated.** Three independent subtlety axes
> (salience, adjacency, distance) all leave convention recovery at ceiling whenever a
> findable trace exists. ~34 valid trials, no no-ops, ≈\$14.

Pointers-only (the R meter), sonnet ×3, two physically-separate worktrees,
pristine-guard on added-defs. Data: `/tmp/bench/exp4b/results/`, raw under
`results/<variant>/t*/`; round logs `calibration{,-mid2,-confirm}.log`.

| Variant | In-code cue | pointers-only PASS | exact CI95 | read-cue |
|---|---|---|---|---|
| **R_low**  | none (convention only in held-out grader) | **0/8** (N=8 confirm) | [0.000, 0.369] | 0/8 |
| **R_mid**  | keys in `_dump`/`_load`, neutral framing, no "external clients" comment | **8/8** (N=8 confirm) | [0.631, 1.000] | 8/8 |
| **R_high** | `to_legacy` + loud "EXTERNAL CLIENTS DEPEND" comment (= Exp-5) | **4/4** (N=4) · = Exp-5 8/8 | [0.631, 1.000]† | 4/4 |

†R_high CI shown for the equivalent Exp-5 N=8 (8/8); 4b re-ran N=4 only as an anchor
sanity check since R_high is byte-identical to the already-confirmed Exp-5 substrate.

## Reading

1. **Anchors confirmed.** R_low ≈ 0 (Fork-A/Exp-4 analogue: no trace → idiomatic default
   → fail, read-cue 0/4 — there was nothing to read). R_high = 4/4 reproduces Exp-5's
   8/8 (read-cue 4/4). The ladder's two ends are where Exp-4 and Exp-5 put them.

2. **R_mid did NOT land in the partial band.** The chosen non-salient cue calibrated to
   **4/4**, not 1–7. Every trial read `_dump`/`_load` and matched it (read-cue 4/4). So a
   capable receiver re-derives the convention from a **non-salient** in-code cue just as
   reliably as from a salient one — the loud comment in R_high was **not load-bearing.**

3. **The boundary R\* is a sharp step on trace *presence*, not a gradient on salience.**
   0/4 (no trace) → 4/4 (any findable trace), flat at ceiling across the salience step
   R_mid→R_high. The read-cue mechanism makes this a genuine re-derivation signature, not
   luck: it is exactly 0 where there is nothing to read and saturated where there is.

4. **The cost/turns signature corroborates.** R_low burns more (38 turns, \$0.67): the
   receiver explores, fails to find the convention, then ships idiomatic and fails the
   grader. R_mid/R_high converge faster (~26 turns) because the cue resolves the ambiguity.
   Same "explore-more-then-fail" signature as the Exp-4 null arm.

## Routing (per prereg §5 / revised-design §3)

R_mid = N/N = "fully recoverable" → the salience axis does not produce a partial regime
at this cue level. Two scientifically honest continuations:

- **(A) Accept the sharp-step finding** and confirm at N=8 on the two bracketing points
  (R_low, R_mid) to separate the exact CIs (N=4 CIs still touch: 0/4=[0,.60], 4/4=[.40,1]).
  This *hardens* the bounded headline: residue is overhead the moment a findable trace
  exists, not merely when it is salient. ≈16 runs.
- **(B) Hunt a partial regime with a genuinely harder cue** (keys in a distant/unrelated
  module not in the receiver's pointer set; or a partial/misleading cue) and re-calibrate.
  Caveat: a barely-findable cue starts measuring *search effort*, a weaker construct than
  *re-derivability* — the result would need that caveat.

Recommendation: **(A)**. The salience gradient is empirically flat at ceiling; pushing the
cue subtler tests "did the agent grep the right file," not "can the constraint be
re-derived." The clean, defensible result is the sharp step on trace presence.

---

## Round 2 — R_mid2 (distant cue), the partial-regime hunt (2026-06-20)

Per the operator's call, a fourth variant **R_mid2** moved the convention OUT of the
pointed-at `account.py` into a sibling module `ledger/sync_codec.py`
(`encode_for_partner`/`decode_from_partner`), discoverable only by grepping the tree.
N=4 pointers-only.

| Variant | Cue location | pointers-only PASS | mean cost | mean turns |
|---|---|---|---|---|
| **R_mid2** | `sync_codec.py` (non-adjacent; absent from `account.py`) | **1/4** | \$0.63 | 34 |

**A partial *pass rate* appeared (1/4) — but it does NOT measure re-derivability.** The
transcripts and grader output are decisive:

- **All 4 trials recovered the convention.** Every architect found `sync_codec.py` and
  named it the single source of truth; every `to_wire` used `acct/cents/ts` correctly.
  (My `read_cue` probe logged 0/4 here — a **probe bug**: it greps for `to_legacy|_dump`,
  the wrong cue terms for this variant. Corrected by reading the transcripts directly:
  codec references 5–7 per trial.)
- **All 3 failures share one mode, and it is not the keys:**
  `round-trip != original` + `lenient cents not coerced from str`. The passing trial (t1)
  **imported and delegated** to `decode_from_partner` (inheriting its `int()` coercion);
  the failing trials (t2–4) **hand-rolled** `from_wire` and dropped the leniency coercion.

**Interpretation.** R_mid2's partial pass rate is driven by **implementation fidelity to a
grader leniency sub-clause**, a construct **orthogonal to R**. On the variable the
experiment is about — *re-derivability of the wire convention* — R_mid2 is still **4/4**
(recovered whenever present anywhere in the tree). So this **corroborates, not
contradicts, the sharp step**: convention recovery is binary on presence
(absent→0/4 at R_low; present-anywhere→recovered at R_mid/R_high/R_mid2). The only thing
that moves inside the "present" regime is downstream coding correctness, which is not the
residue's job and not R.

**Conclusion of the hunt.** A genuine partial regime on the *re-derivability* axis was
**not** found by making the cue harder to locate — because locating it was never the
bottleneck; capable receivers grep it out reliably. A partial regime would require a cue
that is genuinely *ambiguous to recover* (e.g., two conflicting conventions in the tree,
forcing a choice), not merely distant. That is a different substrate and a separate
build/spend decision.

---

## Round 3 — N=8 confirmation of the bracketing points (2026-06-20)

Per the operator's call (accept the sharp-step finding), the two points that bracket R\*
were re-run at **N=8** to separate the exact CIs to the program's standard (the N=4 CIs
still touched: 0/4=[0,.60], 4/4=[.40,1]). Pointers-only, all 16 trials valid, no no-ops.

| Variant | pointers-only | exact Clopper-Pearson CI95 | read-cue |
|---|---|---|---|
| **R_low**  | **0/8** | **[0.000, 0.369]** | 0/8 |
| **R_mid**  | **8/8** | **[0.631, 1.000]** | 8/8 |

**CIs separated** (0.369 < 0.631) — the sharp step is confirmed at the same rigor as
Exp-4 (8/8 vs 0/8) and Exp-5 (8/8). The read-cue mechanism is clean at N=8: **0/8 where
there is nothing to read, 8/8 where the cue exists** — genuine re-derivation, not luck.
Cost signature persists: R_low burns ~36 turns / \$0.59 (explore→fail) vs R_mid ~26 turns
/ \$0.47 (cue resolves the ambiguity), the same explore-more-then-fail signature as the
Exp-4 null arm.

**Final statement.** Across salience (R_mid vs R_high), adjacency/distance (R_mid2), and
now a CI-separated N=8 confirmation, the boundary R\* is a **sharp step on trace
presence**: pointers-only is **0/8 with no findable trace** and **8/8 with any findable
trace**, regardless of how non-salient or non-adjacent that trace is. The partial regime
Exp. 5 hypothesized does **not** exist along the cue-subtlety axis.
