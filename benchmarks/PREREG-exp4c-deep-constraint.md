# Pre-registration — Experiment 4c: does the step survive DEPTH, net of difficulty?

**Status:** PRE-REGISTERED (thresholds locked before any run) · **Date:** 2026-07-02
**Branch:** `feat/carrier-comms` · **Authors:** carrier-comms program
**Locks:** this document is committed *before* the substrate is built and before any
arm is run. Post-hoc changes to arms, cells, N, thresholds, or the grader invalidate the
result and must be recorded as a deviation with rationale. A prereg committed after the
first trial is not a prereg; the commit ordering is the point.

**Roadmap note:** Track A Phase A1 cites this file as its blocking precondition. If the
roadmap cites the path `EXP4C-deep-constraint-prereg.md`, update the citation to this
file (`PREREG-exp4c-deep-constraint.md`) to match the repo's existing `PREREG-*.md`
convention (`PREREG-lever2-natural.md`).

---

## 0. Why this experiment exists (what 4b left open)

Experiment 4b hardened the bounding law to a **sharp step on trace presence**: the
residue is overhead the moment a *findable* trace exists (R_low 0/8 vs R_mid 8/8, CIs
separated, invariant to salience, adjacency, and distance). But 4b measured that step on
the shallowest possible constraint, a **key-naming convention**, where "a trace is
present" and "the reasoning is recoverable" are the *same question*: to see the key is to
know the rule. So the sharp step is, as of now, a property of **shallow constraints**.

4c asks the one question that can overturn the headline: **when trace-presence and
reasoning-recoverability come apart, which one governs?** A deep constraint is one where
the code is fully present (trace present) but the *rationale* is not recoverable from the
code alone (a capable reader sees what the code does, not why it must, and the idiomatic
"improvement" silently breaks it). If the step holds at depth, the law generalizes and is
far stronger. If it breaks, the governing variable was recoverability all along, and
trace-presence was only its shallow proxy. Either outcome is the paper's strongest
possible next result.

The honest possible outcomes, all publishable, are enumerated as locked gates in §5.

---

## 1. The confound this design removes (read before the hypotheses)

The naive 4c (deep-unrecoverable constraint vs shallow-recoverable constraint) is
**uninterpretable**, and we will not run it. A deep constraint on a modification task is
also simply a **harder task**, so "residue rescued the deep cell" is observationally
identical to "the task got harder and any extra context helps." Depth and difficulty are
perfectly correlated in that two-cell design.

The fix is to make the **decisive contrast hold difficulty identical by construction**.
The experiment uses **one deep constraint, expressed in two cells that differ only in
whether the rationale is recoverable**, plus the shallow constraint as the anchor back to
4b:

- **S — shallow-recoverable.** The 4b key-naming convention. Trace present, rationale
  trivially recoverable (to see the trace is to know the rule). Replicates 4b; anchors
  this experiment to the confirmed step.
- **Dr — deep-recoverable (documented control).** The deep constraint (§2), with its
  rationale stated in a docstring or an adjacent comment. Deep code, but the *why* is
  recoverable by reading. This is the **difficulty control**.
- **Du — deep-unrecoverable (target).** The **identical** deep constraint and the
  **identical** modification task as Dr, with the rationale comment **stripped**. The
  code the receiver sees is the same as Dr's runtime behaviour; only the recoverable
  explanation is removed.

Because **Dr and Du are the same constraint, the same task, and the same required code
change, differing only by a stripped rationale comment, their difficulty is held
identical by construction.** Any gap between them is recoverability, not difficulty. That
is the whole design. S is the bridge to 4b, not part of the decisive contrast.

---

## 2. The substrate and the deep constraint (selection criteria, not cherry-picked)

To avoid post-hoc task-shopping, the deep constraint is fixed here; the substrate is the
first implementation meeting all criteria, and the search is logged.

**Primary deep constraint: dedup-before-aggregate.** A function aggregates a stream of
records; **duplicate records are re-submissions, not additive**, so they must be
deduplicated before summing. The code fully present includes the dedup pass. The
**modification task** (refactor or optimize the aggregate for speed) makes the idiomatic
move, dropping the "redundant-looking" dedup pass to stream the sum, **silently break the
constraint**: the tests-as-given pass, but re-submitted records are double-counted.

- In **Dr**, a docstring on the aggregate says, in effect, "duplicates are re-submissions,
  not distinct events; dedup before summing." A carrier that reads it recovers the why.
- In **Du**, that docstring is removed. The code still dedups, but nothing explains that
  the dedup is load-bearing rather than defensive, so the idiomatic optimizer removes it.

**Alternate deep constraint (if dedup does not yield a clean grader in the search budget):
log-space numerics.** A product over many probabilities must be computed in log-space
because the direct product underflows for n > 50. Code present computes in log-space; the
idiomatic "simplify" reverts to a direct product that passes small tests and underflows at
scale. Dr documents the underflow rationale; Du strips it. Same structure.

A valid substrate requires all of:

1. **Trace present in every cell.** The constrained code is fully visible; nothing is
   invented. This is the hard line vs Fork-A (0% recoverable): here the *code* is always
   recoverable, only the *rationale* varies (Dr documented, Du stripped).
2. **Idiomatic default breaks the constraint.** The natural modification, pattern-matched
   from the codebase or the language default, gets it wrong. This is what lets
   pointers-only fail in Du rather than never.
3. **Dr and Du are byte-identical except the rationale comment/docstring.** No other
   difference in code, task, pointers, or grader. Verified by diff before any run.
4. **Held-out, binary, mechanical grader.** An `accept.py` the agents never see,
   validated fail-on-pristine-optimization / pass-on-reference before any arm runs, and
   crucially failing a double-counting implementation that otherwise runs (§6).
5. **A touch probe is definable.** From the run log we can tell whether a trial actually
   engaged the constrained region (the aggregate/product function); trials that never
   touched it are uninformative and excluded from the primary test (§4).

---

## 3. Design, arms, N (locked)

Same model throughout (**claude/sonnet**) to isolate residue value from any cross-model
confound; **two physically separate worktrees** per arm (the leak guard from Exp. 4 §9);
schema 1.2; pristine-asserted per trial. The optional cross-model **cold** arm is not
central (Exp. 2 settled cross-model capability); run it only if the writeup needs a
matched cold point on this substrate.

**Arms, run in every cell (S, Dr, Du):**

| Arm | Receiver sees | Tests |
|---|---|---|
| **cold** (no bridge) | pristine code pointers only | floor reference |
| **pointers-only** (the recoverability meter) | pristine code pointers only | re-derivation rate per cell (§4) |
| **pointers + derived** | code pointers **+** carried `state.derived` rationale | does residue earn its tokens |
| **decoy** (mandatory) | code pointers **+** equal-budget *irrelevant* prose residue | isolates carried rationale *content* from any-extra-prose |

The **decoy** carries a residue of the same token budget as `+derived` but with content
unrelated to the constraint. It is mandatory: without it, "+derived beat pointers-only"
cannot distinguish "the rationale helped" from "any prose in the prompt helped."

**Two-stage N (locked):**

- **Stage 1 (calibration, small N=4 per cell, pointers-only only).** Locate PO_S, PO_Dr,
  PO_Du. This routes interpretation (§4) and tells us which decisive contrast is powered
  before spending confirm-tier trials.
- **Stage 2 (confirm, N=8 per arm)** on the decisive cells (Dr, Du) and their residue
  arms. If a decisive contrast lands within one count of ceiling or floor (a near-tie that
  N=8 cannot resolve), **pre-commit to escalate that contrast to N=16** before peeking
  again. S is confirmed at N=8 as the 4b anchor.

**Estimated effort/cost:** ~2-3 days build (constructing Dr/Du that are difficulty-matched
and diff-clean is the main work and the main threat, see §8), ~$25-45 run.

---

## 4. Manipulation check (the gate that makes the decisive contrast meaningful)

The recoverability meter is the **pointers-only** pass rate per cell, run first, routing
interpretation before any residue arm is compared.

- **In-regime (the comparison is meaningful):** `PO_Dr` high (the documented deep
  constraint is recoverable, e.g. ≥ 6/8) **and** `0 < PO_Du < PO_Dr`. Depth-with-doc
  recovers; stripping the doc costs recovery. **Proceed to the decisive test (§5).**
- **Deep substrate too hard (out of regime, difficulty floor):** `PO_Dr` also low (e.g.
  ≤ 2/8). The deep task is unrecoverable even when documented, so difficulty, not
  recoverability, dominates and Dr cannot serve as the control. **Report as "deep
  substrate too hard"; retune difficulty down** (simpler deep constraint) or fall back to
  the alternate constraint. This is the analogue of Exp. 5's "too hidden" branch.
- **Deep constraint trivially recoverable from code (no depth achieved):** `PO_Du` high
  (`≈ PO_Dr`, both near ceiling). Stripping the rationale did **not** reduce recovery: a
  capable model re-derives the deep rationale from the code alone. This is **not** a
  substrate failure; it is a **real result** (Gate 2, §5): trace presence suffices even
  at depth.

The touch probe applies here: only trials that engaged the constrained region count
toward PO. A pass that never touched the aggregate is excluded, not scored as recovery.

---

## 5. Locked thresholds and the discrimination logic (the gates)

Held-out success per cell, **exact 95% Clopper-Pearson CIs**, two-sided
**Barnard's / Fisher's exact** on each 2×2. The **decisive contrast is Dr vs Du**, whose
difficulty is identical by construction (§1).

- **GATE 1 — RECOVERABILITY GOVERNS (residue earns its tokens at depth).**
  `PO_Du` below `PO_Dr` with **non-overlapping 95% CIs** (stripping the rationale costs
  recovery, at identical difficulty), **and** `+derived` above `PO_Du` **and** above
  `decoy` in the Du cell (the carried *rationale content* rescues it, not mere prose).
  Reading: the residue earns its tokens specifically when the rationale is **unrecoverable
  despite a present trace**, and this cannot be difficulty because Dr is equally deep and
  recovers. The headline **sharpens** from "trace presence governs" to "**recoverability**
  governs, of which trace presence is the shallow proxy." Strongest generalization.

- **GATE 2 — STEP GENERALIZES (publishable; 4b holds and broadens).**
  `PO_Du` equivalent to `PO_Dr` by **TOST** (both recover, stripping the doc did not
  matter). Reading: a capable same-model receiver re-derives even the deep rationale from
  the code, so **trace presence suffices regardless of depth**; the residue is overhead
  whenever the code is present, depth included. The 4b law holds unchanged and is broader.

- **GATE 3 — DIFFICULTY FLOOR (substrate out of regime, not a result about the law).**
  `PO_Dr` low (deep task unrecoverable even when documented, §4). The control cannot do
  its job; the Dr/Du gap would confound recoverability with raw difficulty. **Report as
  substrate-too-hard, retune or fall back.** Do not report a law claim from this branch.

- **Cost.** Parity unless a USD win **replicates at N ≥ 8**. Report mean measured USD and
  `num_turns` per arm. Do **not** repeat the N=3 screen's "cheaper" error (the 4.4% gap
  that was noise; corrected in the report's cost line). USD is ground truth, not raw
  tokens.

**Mechanism coding (how, not just that).** For every Du pointers-only trial, code from the
run log whether the agent engaged the dedup/log-space region and what it did:
passed having preserved the constraint (genuine, rare in Du by hypothesis); failed by
applying the idiomatic optimization that drops it (supports the recoverability premise);
never engaged (excluded by the touch probe). This turns "+derived has a higher number"
into a mechanism: residue helps **because** the pointers-only carrier cannot recover *why*
the constrained code must stay, and removes it.

---

## 6. Held-out grader requirements (locked)

- `accept.py` encodes the constraint as assertions; **agents never see it**.
- Validated **before** any arm: it **fails** on a plausible idiomatic optimization (the
  dedup pass removed / the direct product) and **passes** on a reference implementation
  that preserves the constraint.
- The failing input must **run and pass the naive functional tests** but violate the
  constraint (double-counted re-submissions / underflow at n > 50). A grader that only
  checks "code runs" is invalid; it must catch the *silent* break, which is the entire
  point of a deep constraint.
- Binary pass/fail per trial, no partial credit (keeps the CI logic clean).
- The Dr and Du substrates are diffed before any run to confirm they differ **only** in
  the rationale comment/docstring (§2 criterion 3).

---

## 7. Stop / kill / report rules

- Run **pointers-only first across all cells** (Stage 1 calibration + manipulation check,
  §4) → route interpretation into Gate 1, 2, or 3 before spending confirm trials.
- Then the **residue arms (+derived, decoy) at N=8** on the decisive cell(s).
- **Discard-and-rerun** any trial that is a rate-limit / infra no-op (turn-1, $0, < ~10 s
  wall, the signature from Exp. 4 §9). Every reported trial is a valid real run. Sanity
  check turns/cost/wall on every trial; physically-impossible numbers are bugs, not data.
- **Report all branches honestly** (Gate 1 helps-at-depth / Gate 2 step-generalizes /
  Gate 3 substrate-too-hard). The experiment is designed to be able to return the null and
  to falsify the current headline; that is the point.
- Lock this file's thresholds **before** the first run; any change is a logged deviation
  with rationale.

---

## 8. What this settles and does not settle

**Settles:** whether the confirmed sharp step is governed by **trace presence** (Gate 2)
or by **reasoning-recoverability** (Gate 1), by separating the two on a deep constraint
whose difficulty is held identical across the decisive cells. This is the one experiment
that can overturn the shallow-law headline, so passing it either way makes the paper
strictly stronger.

**Does not settle:** (i) **base rate**, how often real handoffs carry low-recoverability
deep constraints (a separate study on natural traffic, Track A3, explicitly out of scope
here); (ii) **deep real**, this is a *constructed* deep constraint, so it moves the result
from "shallow toy" to "deep toy," not to "deep real" analytical constraints like the
32-agent biology runs, which are deeper still. State this limitation in the result.

**Main threat to validity:** if Dr and Du are not truly difficulty-matched (the stripped
rationale incidentally changed how hard the task reads), Gate 1's inference weakens. The
diff-clean requirement (§2.3, §6) and the Dr manipulation check (§4) are the guards; if
`PO_Dr` is not high, the control has failed and Gate 3 applies.

---

_Commits are the operator's. Results append to `results/lever2-deep-4c.json` and a new
report section once the run completes._
