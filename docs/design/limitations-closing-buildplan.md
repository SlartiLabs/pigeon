# Staged plan: closing the limitations

**Anchor:** the eight limitations disclosed in the carrier-comms manuscript, Section 4.
**Ground rule:** this plan does not treat "close" as one action. Each stage states, up
front, whether the target limitation is closeable (a bounded deliverable exists),
reducible (asymptotic, no finish line), or outcome-uncertain (the experiment could
revise the headline instead of protecting it). Do not let a stage's own title imply a
guaranteed direction of result. Em-dashes removed by convention.

---

## 0. Metrics standard (applies to every stage below, not a stage in itself)

**Resolves:** the token-vs-dollar question, precisely, not by replacing one with the
other.

- **Primary comparable metric stays USD**, timestamped to the pricing snapshot in
  effect at run time (record the date; provider pricing changes, and a reader six
  months out should know which snapshot a number reflects). USD remains the only
  metric that is fair across model families, because native token counts are not:
  Claude, Gemini, and GPT segment the same text differently, and output tokens bill
  at several times the input rate, so a raw token sum flattens real cost differences
  away rather than revealing them.
- **Every trial, every stage, additionally archives:** native `input_tokens`,
  `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens` (already
  parsed for Claude, per `_extract_telemetry`; NOT yet confirmed for Gemini's usage
  schema, see Stage 0 tasks) per hop, AND the raw prompt and completion text per turn.
- **Why the raw text specifically:** it is what makes later re-derivation possible.
  With raw text archived, a canonical single-tokenizer recount (one reference
  tokenizer, applied uniformly regardless of which model actually produced the text)
  gives a genuine tokenizer-independent volume comparison, decoupled from both
  provider pricing and provider-specific segmentation. That is the rigorous version of
  "recompute this later," not a switch to native token totals. "Standard tokens" is
  not self-defining, name the tokenizer: a third-party, model-agnostic choice (tiktoken,
  `o200k_base` or similar) is the right pick specifically because it favors neither
  Claude's nor Gemini's own segmentation, which either provider's native tokenizer
  would. State this choice explicitly in the eventual Methods text, the same way the
  0.20 equivalence margin is disclosed as a stated default rather than an objective
  fact, not left implicit as though "standard" meant unambiguous.
- **This does not apply retroactively, confirmed, not assumed.** Checked directly: the
  "full per-trial ledgers" committed for Experiments 4c and 5 are aggregate CSVs (turn
  count, cost, pass/fail per trial), not raw transcripts, and no raw prompt or
  completion text exists anywhere in the current repo, for any experiment, including
  4c and 5. Canonical retokenization needs exactly the text that was never kept.
  Experiment 4's necessity result, the paper's single most load-bearing finding, has
  the same gap the Appendix already discloses for a different reason (disposable
  worktrees). None of Experiments 1 through 5, 4a, 4b, or 4c can be reported in
  canonical tokens without a fresh re-run; that re-run would be a new replicate, not a
  recomputation of the numbers already published. This applies starting Stage 0
  onward, to trials that have not happened yet, and to no trial that already has.
- **Where this earns its keep, and where it does not.** Every result currently in the
  manuscript is a within-model (Sonnet-vs-Sonnet) comparison, where USD already carries
  no tokenizer-incomparability problem to solve, the same provider's pricing applies
  throughout. Canonical retokenization becomes load-bearing specifically for
  cross-model comparisons (Stage 2 onward), where a dollar figure would otherwise
  confound genuine efficiency differences with two companies' independent, unrelated
  pricing decisions. Make it a **required** dual metric (alongside USD) for Stage 2 and
  any future cross-model stage. Do not retrofit it as a blanket requirement across the
  existing within-model results, where it would add a second number without resolving
  a problem the first number already handles correctly.
- **On "better for a journal":** true for a paper whose contribution is efficiency or
  compression, where token count is the field's own standard unit (this is how the
  LLMLingua/AutoCompressors lineage already cited in Related Work reports its results).
  Less clearly true here: this paper's own framing already demotes cost to a secondary
  null, the central claim is a pass/fail boundary, not an efficiency gain, and the
  paper's practical audience (someone deciding whether to run a coordination layer)
  is billed in dollars, not tokens. Report both where cross-model comparison requires
  it; do not present tokens as a strictly superior unit the existing results were
  wrong to use.
- **What NOT to do:** do not report a summed native token total as a headline
  comparison metric, cross-model or otherwise. Report USD as the claim; report tokens
  and raw text as the archive that lets someone else re-derive a different claim later.

**Stage 0 tasks (infrastructure, precedes live trials in every stage below):**
1. Confirm whether `_extract_telemetry` (or the agy-side equivalent) parses Gemini's
   usage-reporting schema into the same `input_tokens`/`output_tokens`/cache fields
   used for Claude. If not, this is new parsing logic, not a config change, budget it
   as such.
2. Extend the result-JSON schema (whatever currently holds `cost_usd`, `turns`,
   `pass`) to persist the token/cache split and a pointer to the archived raw
   transcript, for every future trial. Stop discarding per-trial transcripts as a
   default; the "not retained" note in the current Appendix A should not recur.
3. One-line schema-version tag on every result file going forward, since "which
   pricing snapshot" and "which schema version" are the same kind of provenance
   question and should be answered the same way.

**Effort:** small, 1 to 3 days of plumbing. Blocks nothing conceptually, but should be
in place before Stage 1's first live trial, or the archival gap just gets inherited by
every subsequent stage the way it already was for Experiments 4 and 4b.

---

## Stage 1: The cheap, independent, no-design-risk batch

Two items, both **closeable** to a bounded, publication-adequate standard. Reuse
existing, validated infrastructure. Can run in either order, or in parallel, and
neither blocks nor is blocked by Stages 2 to 5.

### 1a. Cost single-shot -> powered estimate

- **Design:** identical to Experiment 1 (cookiecutter, marshmallow; naive vs pigeon
  arms), rerun at N=8 per arm per repository instead of N=1.
- **No new substrate, no new statistics.** Clopper-Pearson framing does not apply here
  (cost is continuous, not binomial); report mean and a bootstrap or t-based CI per arm,
  and the paired difference's CI, so the "token-neutral to mildly negative" claim gets
  an interval instead of a point estimate.
- **Kill-criterion:** none in the falsification sense, this is a precision upgrade, not
  a hypothesis test. The thing that would matter is if the CI on the difference turns
  out to include a comfortably negative region, i.e. a real saving, which nothing in the
  current data suggests but which N=1 genuinely cannot rule out.
- **Budget:** ~32 trials (2 arms x 2 repos x N=8), roughly $30 to $50 in USD at current
  pricing, allowing for the rate-limit discard rate seen elsewhere in this project.
  Under 200K tokens total.

### 1b. Decoy, rebuilt to the design that was actually locked

- **What went wrong, verified against the source, not assumed:** `PREREG-exp4c-deep-
  constraint.md` locks the decoy as "content unrelated to the constraint," equal token
  budget, to isolate carried rationale from any-extra-prose. What was actually built
  and run appears to have drifted toward a plausible-but-false rationale, which is a
  meaningfully different (and more adversarial) thing, and is almost certainly why it
  read as bug-planting and got refused.
- **Design:** rebuild the decoy as a true, verifiable, off-topic fact about the
  substrate (e.g. a correct but irrelevant note about test-fixture structure), matched
  in token weight to the real `state.derived` residue. Run at confirm-tier N=8 to 12 on
  4c's `Du` cell, the cell where the content-vs-prose question is actually live.
- **Why this matters now and not just eventually:** it is currently moot everywhere in
  the paper, because no reported result has with-derived beating pointers-only. It
  becomes load-bearing the moment any future stage (most likely Stage 5) produces that
  result, so build it before Stage 5's confirm run, not after.
- **Kill-criterion:** if the rebuilt decoy is ALSO refused, that is itself a finding
  worth reporting (the refusal generalizes beyond a single poorly-specified prompt),
  not a dead end. If it is accepted and shows no effect (decoy = pointers-only = with-
  derived, all at whatever ceiling the target substrate sits at), the control is
  validated and banked for reuse.
- **Budget:** 8 to 12 trials, roughly $10 to $15.

---

## Stage 2: Cross-model replication (Gemini, via agy)

**Status:** the single highest-convergence item across your own roadmap and both
external documents that engaged with it seriously. **Closeable to a real, if bounded,
standard**: this does not answer "does the boundary hold for all models," it answers
"does it hold for a second, architecturally different model," which is the correct,
honest scope.

**Pre-flight (do this before anything else in this stage):** agy re-auth is a
documented standing blocker for new cross-model runs per your own design docs. Confirm
a live, authenticated agy session before spending anything on trial design review.

**What is reused, not rebuilt:** the multi-CLI orchestration plumbing is already
proven end to end (Experiment 2's claude -> opencode/mimo -> agy chain, and the
adversarial mimo/agy review panel already run against this exact benchmark). This
stage does not need new transport engineering, only a role swap in two already-
validated substrates.

**Design, two arms of evidence, matching the two-sided law's own structure:**

1. **Necessity side.** Reuse the Fork-A off-disk contract exactly as specified in
   Methods 2.2. Swap the receiving hop (the one whose success depends on the carried
   constraint) from Sonnet to agy/Gemini. Two arms: pointers-only, pointers+derived.
   Confirm-tier N=8 per arm, in two physically separate worktrees, identical isolation
   discipline to Experiment 4.
2. **Recoverability side.** Reuse the natural `to_legacy`/`from_legacy` convention
   exactly as specified in Methods 2.2 (Experiment 5's substrate). Swap the receiver to
   agy/Gemini. Two arms: pointers-only, pointers+derived. Confirm-tier N=12 per arm
   (matching Experiment 5's own N, for the same reason, a ceiling-vs-ceiling
   equivalence claim needs the larger N to clear the stated margin).
3. **Metrics, per Stage 0, non-optional here specifically.** Archive raw prompt and
   completion text for every turn on both the Sonnet and Gemini hops, and report cost
   two ways: USD at the pricing snapshot on the run date, and a canonical single-
   tokenizer recount (tiktoken `o200k_base` or an equivalent stated choice) applied
   uniformly to both models' archived text. This is the first stage in the project
   where a dollar comparison would otherwise be confounded by two companies'
   independent pricing, so it is the first stage where the second metric is required
   rather than merely archived for later.

**Locked gates, stated before any trial runs:**

- **GATE A (boundary transfers):** necessity side separates (0/8 vs 8/8-style, non-
  overlapping exact CIs) AND recoverability side is TOST-equivalent at the same 0.20
  margin used throughout. Reading: the boundary is a property of the task and
  artifacts, not of Sonnet specifically. This is the result worth having.
- **GATE B (boundary shifts):** either side lands at an intermediate rate rather than a
  clean separation or ceiling (e.g. necessity side shows partial recovery instead of
  0/8, or recoverability side fails to reach ceiling). Reading: the boundary's exact
  location is receiver-dependent, a real and reportable finding, and a more
  interesting one scientifically than Gate A, since it would mean recoverability is
  partly a property of the receiving model's own capability, not purely of the
  artifact. Do not treat this as a failed replication; treat it as the boundary having
  a second dimension you had not yet measured.
- **GATE C (mechanism fails):** injection does not fire, or agy's tool-use format
  breaks the `## Carried reasoning` block parsing. Reading: an engineering gap in
  cross-model injection, not a finding about recoverability at all. Fix and rerun
  before drawing any scientific conclusion.

**Budget:** roughly 16 to 24 live trials across both sides, $30 to $90 depending on
agy's actual per-call pricing and discard rate (unknown until the pre-flight
re-auth check and a small pilot; do not assume Sonnet's per-trial cost transfers).
Record Gemini's native usage fields per the Stage 0 schema; if agy's telemetry does not
cleanly map to input/output/cache fields, that gap itself is worth noting in the
eventual write-up, since it is a real asymmetry in how cleanly different providers
expose cost accounting.

---

## Stage 3: Scale as a confound (independent of Stage 5, not the same experiment)

**Status:** reducible to a concrete, bounded engineering task, not open-ended. This is
a **different experiment from the deep-real substrate**, and conflating them would
produce the wrong design: this stage tests whether the `pack`'s retrieval step
surfaces a trace that would be recoverable if seen; Stage 5 tests whether a trace stays
unrecoverable even when fully seen. Keep them separate.

**Design:** take the already-validated natural convention (`to_legacy`/`from_legacy`,
known to recover 12/12 at small scale) and bury it inside a synthetic repository at
increasing file counts, holding the underlying semantic recoverability of the
constraint constant and varying only how much decoy material the pack has to rank
against. Decoy files should be plausibly relevant-looking, not obviously irrelevant, or
the pack's ranking has no real discrimination problem to fail at.

- **Sweep:** 4 to 5 scale points (e.g. 10, 50, 200, 1000, 5000 files), pointers-only
  arm only at each point (this stage is about retrieval, not about residue value, so
  the with-derived arm is not needed until a failure point is located).
- **Two-stage N**, mirroring 4b's own precedent: screen each scale point at N=3 to 4
  first, locate where (if anywhere) recovery starts degrading, then confirm at N=8 on
  the decisive point(s) only, rather than spending confirm-tier N at every scale level
  up front.
- **What to look for, explicitly:** given the rest of this paper's character, do not
  assume a gradual degradation is the only possible shape. A sharp retrieval-ranking
  cutoff (recovery holds until some corpus size, then falls off abruptly) would be a
  second sharp-step finding, and worth reporting as such if that is what the data show.

**Kill-criterion:** if recovery holds at 12/12-equivalent all the way to the largest
tested scale, the honest conclusion is "not tested large enough to find the failure
point," not "scale does not matter," since the tested substrates remain semi-synthetic
and bounded.

**Budget:** generator script, 1 to 2 days of dev. Trials: roughly 15 to 20 at screen
tier plus 8 to 16 at confirm tier on the decisive point(s), $40 to $120, with larger-
scale trials likely costing more per trial due to increased pack/retrieval token
volume, budget the high end.

---

## Stage 4: Base-rate probe (cheap, but produces a softer kind of evidence, say so)

**Status:** the instrument already exists (`benchmarks/rederivable_probe.py`) and its
own docstring is explicit about its limits: an LLM-judge semantic-match, not the held-
out functional grader standard used everywhere else in this paper, and reflexively
biased toward your team's traffic after they already knew the mechanism. Running it is
cheap. Treating its output as equivalent evidence to the confirm-tier experiments would
not be honest, and the write-up should say so as plainly as the tool's own docstring
does.

**Design:**
1. Assemble the available corpus of real `state.derived.constraint_found` handoffs.
2. Explicitly check whether any pre-mechanism-awareness traffic survives, per the
   tool's own recommendation. If none does (plausible, since the mechanism exists
   because it was deliberately built), say so, and report the base rate as "this team's
   current, mechanism-aware rate," a narrower and still useful claim, not "the general
   rate," the way one additional survey site narrows but never closes a generalization
   claim about a population.
3. Flip `--live` on a representative sample (not the full corpus, if it is large; a
   stratified sample is cheaper and avoids implying more precision than an LLM-judge
   estimate supports).

**Budget:** cheap, this is per-constraint judge calls, not full multi-agent trials.
Likely $10 to $30 depending on corpus size. No hard N target, since this produces an
estimate with a stated soft-probe caveat, not a hypothesis test with a gate.

---

## Stage 5: Deep-real substrate (the one that might not close in the hoped direction)

**Status:** the only stage in this plan that is genuinely **outcome-uncertain**, not
just effortful. Say this plainly rather than let the stage's presence in a "closing
plan" imply the outcome is favorable. Experiment 4c already attempted this exact goal
once and the structural trace stayed visible anyway; a second attempt succeeding on the
first design is the optimistic case, not the expected one.

**New requirement this stage adds that no prior experiment needed:** a no-code,
prompt-only guessing baseline. Any realistic (non-arbitrary) deep constraint risks
being guessable from a model's general training-data priors about the domain, which
Fork-A's arbitrary key names sidestepped by construction and a naturalistic business
rule will not. Without this control, a pointers-only success could be genuine recovery
from the artifact or could be a lucky domain-prior guess, and a black-box pass/fail
cannot tell these apart.

**Design (iterative, not single-shot):**
1. **Candidate substrate:** a constraint whose correct behavior is fixed by a fact
   external to the codebase entirely and appears in no visible constant, comment, or
   test fixture (the rounding-mode class of example discussed previously is one
   candidate, not the only one worth considering).
2. **New control arm:** present the task description alone, no repository access at
   all, and measure the guessing rate. This sets the floor that any subsequent
   pointers-only result must be interpreted against, not treated as a clean 0 percent
   baseline the way Fork-A's arbitrary schema allowed.
3. **Pilot at screen-tier N (3 to 4)** on pointers-only specifically. This is the step
   that actually tests whether the substrate achieves genuine unrecoverability. If
   pointers-only lands near the no-code guessing rate, the design failed to hide the
   structural trace (4c's failure mode recurring) or the guessing rate itself is high
   enough to contaminate the result either way, redesign before spending confirm-tier
   budget.
4. **Confirm at N=8 to 12** only after the pilot clears, full arm set (cold if
   applicable, pointers-only, decoy (reuse Stage 1b's rebuilt version), with-derived).

**Locked gates:**
- **GATE 1 (closes toward "yes, deep-real, and residue helps"):** pointers-only near
  the no-code guessing floor (genuinely unrecoverable) AND with-derived clears both
  pointers-only and decoy with separated CIs. This is the strongest possible outcome
  for the current headline.
- **GATE 2 (revises the headline, and this would be the more interesting paper):**
  pointers-only recovers well above the no-code floor despite the constraint's absence
  from any visible trace, meaning some other channel (prior knowledge, structural
  analogy to something else in the repo) is doing the recovery. This would mean the
  step is not purely about trace presence, and the "documentation vs structure"
  framing from 4c would need a third axis added: prior-knowledge-independent structure.
- **GATE 3 (substrate too hard or too easy to be informative):** neither arm separates
  from the guessing floor in an interpretable way. Redesign, as happened once already
  in this project's own history (the 4b factorial that a red-team killed before it
  produced a single misleading result).

**Budget:** the widest range in this plan, $50 to $200+ across pilot, likely redesign,
and eventual confirm, spread over what should be budgeted as weeks, not days, of
design iteration. The dollar cost is not the bottleneck here; the design uncertainty
is, the same way it was for 4b before the red-team rescoped it.

---

## Stage 6: Substrate breadth (ongoing, no stage-completion criterion)

**Status:** genuinely open-ended, listed last because it should be pursued
opportunistically alongside the above, not sequenced as a hard dependency on anything.
Every substrate here has been a variant of one domain, wire-format keys and dedup-by-
id, both belonging to the same "ledger" family. A new substrate in a structurally
different domain (a config-schema convention, a concurrency/locking rule) would extend
external validity the way an additional field site extends an ecological survey's
generalization, incrementally, and without a point at which the question is closed.
Budget each new substrate comparably to a standalone 4b or 4c, days of design, $30 to
$80 in trials, and do not present the count of substrates as approaching completion.

---

## Sequencing and dependency summary

Stage 0 precedes live trials in every other stage; it is infrastructure, not science.
Stages 1, 2, 3, and 4 are mutually independent and can run in parallel or in any order
your calendar allows, none blocks or is blocked by the others. Stage 5 depends on
nothing technically but benefits from Stage 1b's rebuilt decoy being ready first, since
Stage 5 is the most likely place a real with-derived effect could appear that would
need the content-vs-prose control to interpret cleanly. Stage 6 has no dependencies and
no end state; treat it as background work, not a milestone.

## Budget rollup

Labor: Stage 0 a few days; Stages 1, 2, 4 each a few days of design plus run time;
Stage 3 slightly more (a generator to build); Stage 5 weeks, with real variance since
it may need more than one design iteration, matching this project's own precedent.
Spend: roughly $150 to $400 total in USD at current pricing across Stages 0 through 4,
plus $50 to $200+ for Stage 5 depending on how many iterations it needs, plus whatever
ongoing trickle Stage 6 accrues. None of this is large in dollar terms; the actual
constraint throughout is design time and attention, the same asymmetry that has held
for every experiment in this project so far.

## Drift-watch for this plan specifically

Six stages running in parallel is exactly the condition under which scope quietly
inflates: a stage that was supposed to be a bounded rerun starts growing a second
research question, or Stage 6's open-endedness starts absorbing time that Stage 5
actually needs. If a stage's actual work stops matching its stated closeable, reducible,
or uncertain status here, that is the signal to stop and rescope, not to keep going
because momentum exists.
