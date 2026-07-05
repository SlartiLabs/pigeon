# When Carried Reasoning Earns Its Tokens: A Bounded Law for Multi-Agent Handoffs

**Author:** SlartiLabs
**Artifact:** `carrier-pigeon` (PyPI), `github.com/SlartiLabs/pigeon`
**Status:** DRAFT (derived from `docs/benchmarks/report.md`; numbers verified against `docs/benchmarks/results/*.json`). References and venue are placeholders to be completed.

---

## Abstract

Multi-agent systems built from command-line coding agents that share no memory must coordinate through some channel: a handoff message plus whatever context the orchestrator injects. A natural hope is that better coordination lowers cost. We show, on a reproducible benchmark of held-out software tasks, that it does not: adding a filesystem-as-contract coordinator (`pigeon`) is token-neutral to mildly negative (+8% to +59% USD, success unchanged), and the coordination overhead asymptotes to parity from above, never crossing into savings. The value of the channel lies elsewhere. We isolate one mechanism, a carried *reasoning residue* (`state.derived`), and bound exactly when it earns its tokens. Across five pre-registered experiments we establish a two-sided law: the residue is **necessary** when the constraint left no recoverable trace in the artifacts (8/8 with residue versus 0/8 without, N=8, Fisher's exact p = 0.000155), and **unnecessary** when the constraint is recoverable from the code, whether the recoverability is shallow (a naming convention) or deeper (a load-bearing deduplication whose rationale is undocumented). The unnecessary side is confirmed by two-one-sided equivalence tests at N=12 (Newcombe 90% interval within a pre-set 0.20 margin) rather than by coincident point estimates. The result sharpens a simple design rule for multi-agent handoffs: spend channel tokens only on what the receiver cannot cheaply regenerate. We release the substrates, held-out graders, per-trial ledgers, and statistics so the numbers reproduce.

---

## 1. Introduction

A multi-agent system assembled from heterogeneous coding agents (each a separate process, each with its own context window and no shared memory) has to move information between agents somehow. `pigeon` takes the position that the contract is the filesystem, not anyone's context window: the shared working tree carries everything a receiver can re-derive on demand, and a small transient *handoff channel* carries pointers to that tree plus a *derived residue*, the reasoning a receiver cannot cheaply regenerate.

Two hopes motivate such a system. The first is efficiency: a well-curated channel might let downstream agents do less exploratory work, lowering cost. The second is capability: a carried constraint might let a downstream agent succeed where it would otherwise fail. This paper separates the two and finds the first is a null and the second is real but bounded.

**Contributions.**

1. A reproducible cost benchmark showing the coordinator is token-neutral to mildly negative, with an arithmetic argument that its overhead can only approach parity from above (§4.1, §2).
2. A demonstration that the channel's value is carrying reasoning across a model boundary that would otherwise be lost (§4.2).
3. A two-sided **bounded law** for the reasoning residue: necessary iff the reasoning left no recoverable trace, established with a superiority test on the necessary side and equivalence (TOST) tests on the unnecessary side, at the same exact-confidence-interval standard (§4.4 to §4.6, §5).
4. A released benchmark: substrates, held-out graders, per-trial ledgers, figures, and a recomputable statistics appendix (§6, Appendix A).

We also report two incidental findings that a reader relying on the pre-registrations should know: a mandatory control arm could not be realized because the model refused to carry deliberately misleading residue (§4.5), and the deepest form of the necessity question remains open because our deep constraint kept a recoverable structural trace (§6).

---

## 2. The system and the two ceilings

`pigeon` coordinates *carriers*: CLI agents that are separate processes with no shared memory. Two things cross between them. The **working tree** is shared and greppable, so anything in it is re-derivable and is passed by pointer (via a bounded, ranked context `pack`). The **handoff channel** is transient and per-spawn; it carries pointers plus a `state.derived` residue (ruled-out approaches, a discovered constraint, the rationale, the next action). A durable board (`.pigeon/memory`) persists handoffs, metrics, and distilled decisions across sessions.

Two levers could in principle improve this channel, and each has a ceiling.

**Lever 1, compress the channel.** Shrink the per-spawn overhead (the pack plus scaffolding). Writing total cost as `Cost = Sigma_work + N * overhead`, the overhead term is non-negative, so `Cost_WITH - Cost_WITHOUT = N * overhead >= 0`. Compression reduces overhead toward zero and therefore approaches parity **from above**; it can never produce a net saving by this route. Lever 1 is defensive (prevent regression), not a source of savings.

**Lever 2, the polymath handoff.** Carry the irreducible reasoning residue and point at everything regenerable. Only `Sigma_work` (agents doing less work because they did not have to re-derive something) could ever produce a saving, and that is a *quality* effect. This paper is largely about when Lever 2's residue is load-bearing.

---

## 3. Experimental design

All experiments share a common discipline, fixed before running.

- **Held-out graders.** Each substrate ships an `accept.py` the agents never see, validated before any arm runs: it fails on the pristine or idiomatic-but-wrong artifact and passes on a reference that honors the constraint. Success is binary per trial.
- **Isolation.** Each arm runs in two physically separate git worktrees so a contract cannot leak between arms. Every trial is pristine-asserted before it runs.
- **Metric.** Cost is measured in USD (the child agent's reported `total_cost_usd`), the only quantity comparable across arms and models; raw token counts are reported only where they diverge from USD.
- **Confidence.** Success rates are reported with exact Clopper-Pearson 95% intervals. Superiority contrasts use Fisher's and Barnard's exact tests. Equivalence (no-difference) claims use two-one-sided tests (TOST) via the Newcombe hybrid-score interval on the risk difference, against a margin fixed a priori at 0.20; we report the full interval so a reader may substitute their own margin.
- **Pre-registration.** Substrates, arms, N, and decision thresholds are committed before the corresponding run. Deviations are disclosed (§4.5, §6).
- **Physical-plausibility check.** Every trial is sanity-checked for turns, cost, and wall-clock; physically impossible trials (turn-1, zero-cost, few-second no-ops, the signature of a rate limit) are discarded and rerun, never counted as data.

The model is Anthropic Sonnet throughout the within-model experiments (to isolate residue value from a cross-model confound), and a heterogeneous chain (Claude, opencode/MiMo, Antigravity) for the cross-model experiment.

---

## 4. Results

### 4.1 Cost is a null (Experiment 1)

Two public repositories, two arms each (with `pigeon` versus without), same model, identical task spec, fresh worktree at a pinned commit, held-out acceptance gate. On the small-file repository, per-task cost was solo $0.439, naive $0.402, and `pigeon` $0.640 (+46% to +59%); on the large-file three-agent task, naive $1.112 versus `pigeon` $1.202 (+8.1%). Success tied in both. The overhead share shrinks with task size but stays positive: `pigeon`'s pack and retrieve did not cut the exploration cost (Figures 1 to 5). This is a single trial per arm per repository, disclosed as such; it is reported as a NULL, not an equivalence claim.

**Verdict.** A "saves X%" headline is not available. `pigeon` is token-neutral to mildly negative even at its best.

### 4.2 Cross-model capability (Experiment 2)

Three agents that share no memory (Claude then opencode/MiMo then Antigravity) implement a `ledger` wire contract given only to the first hop and never written into the code. With the bridge (the handoff carrying the contract), 5/5 held-out passes; without it, 0/5 (N=5). The cold arm writes working, round-tripping code with idiomatic keys that the held-out test rejects: the state lived only in the handoff, so only the bridged chain reproduced it.

**Verdict.** Possibility proven: `pigeon` can carry state across a model boundary that would otherwise be lost. This is a capability result, paired honestly with the cost null.

### 4.3 Lever 1 is maintenance (Experiment 3)

A pack-size sweep holds success at 3/3 across the tested [1k, 4k] token range: the default pack is over-provisioned and can be compressed to 1k with no loss of success (firm). The cost-win from compression is directional at N=3 with overlapping intervals; the knee below 1k is untested and not pursued. Consistent with §2, Lever 1 is a defensive knob, not a source of savings.

### 4.4 Residue is necessary when no recoverable trace exists (Experiment 4, 4b)

On a constraint deliberately absent from the code (the Fork-A wire contract, ~0% recoverable), the carried `state.derived` residue is **necessary**: with residue 8/8, without 0/8 (N=8, exact intervals separated; Fisher's exact p = 0.000155, Barnard's p = 3.1e-5), at parity cost ($0.417 with residue versus $0.436 without, within noise). The mechanism is productionized, not a proxy: the architect emits the constraint into `state.derived` and the coordinator injects it as a "## Carried reasoning" block into each downstream prompt; injection fired on 8/8 with-residue trials. The effect survives a three-hop chain in which the final hop directly needs only its immediate predecessor (3/3), exercising a transitive-injection path.

Experiment 4b sharpens this into a **step function on trace presence**. On a fixed constraint, task, and grader, varying only the salience of an in-code cue, pointers-only recovery is 0/8 with no findable trace and 8/8 with any findable trace (intervals separated), invariant to how non-salient or distant the trace is. A capable receiver re-derives the convention from a non-salient cue as reliably as from a loud one; the boundary is presence, not salience.

### 4.5 The step generalizes to depth (Experiment 4c)

Experiments 4 and 4b use shallow constraints, where "a trace is present" and "the reasoning is recoverable" are the same question. Experiment 4c separates them on a **deep** constraint: a `settle()` function must deduplicate re-submitted transactions by id before summing (gateway retries are not additive), where the code is fully present but the idiomatic single-pass refactor silently drops the dedup and passes the visible tests (which carry no duplicates). Difficulty is held constant *by construction*: the decisive cells **Dr** (rationale documented in a docstring) and **Du** (identical code and task, docstring stripped) are byte-identical modulo that docstring, so the only thing that varies is whether the rationale is recoverable.

Stripping the rationale did **not** reduce recovery. Pointers-only recovery is 12/12 in Du and 12/12 in Dr; carried residue adds nothing above that ceiling (with-derived 12/12). All reported trials engaged the constrained region (each refactored `settle` to the risky streaming form) and preserved the dedup, and some Du trials re-derived the rationale in their own docstrings. Both equivalences are TOST-confirmed at the 0.20 margin (Newcombe 90% interval [-0.184, +0.184]); the residue is genuinely carried (injection verified in the downstream prompt) and still unnecessary (Figure 10).

**Two disclosures.** (i) The pre-registered mandatory *decoy* arm (carry irrelevant residue, to separate carried content from generic prose) could not be realized: the model recognized the decoy instruction as an attempt to plant a bug-inducing rationale and **refused it**, carrying the true constraint instead. The content-versus-prose control is therefore unavailable for this model, and moot here since with-derived does not exceed pointers-only. (ii) Du stripped the *rationale* but the dedup *structure* stayed visible in the code, so "trace present" remained strong; this is a deep-*toy*, not a deep-*real* constraint. True behavior-unrecoverability (code present, behavior not inferable) remains untested.

### 4.6 Residue is unnecessary when recoverable (Experiment 5)

On a natural, semi-synthetic substrate where the wire convention lives in an existing in-code boundary with a comment that external clients depend on the keys, a capable receiver re-derives the convention for free. The pre-registered two-arm primary test at N=12 gives pointers-only 12/12 and with-derived 12/12, TOST-equivalent at the 0.20 margin (Newcombe [-0.184, +0.184]); the residue was carried (injection verified) and added nothing. (Seven with-derived trials first hit a session rate limit and were discarded and rerun per the physical-plausibility rule; all twelve reported are valid.)

### 4.7 Statistics summary

The confirmed structure is a superiority result on the necessary side and equivalence results on the unnecessary side (Appendix A, `docs/benchmarks/results/stats-appendix.json`):

| Claim | Arms | Test | Result |
|---|---|---|---|
| Exp 4: residue necessary | 8/8 vs 0/8 | Fisher / Barnard exact | p = 0.000155 / 3.1e-5 |
| Exp 4b: sharp step | 8/8 vs 0/8 | Fisher / Barnard exact | p = 0.000155 / 3.1e-5 |
| Exp 4c Gate 2: Du = Dr | 12/12 vs 12/12 | Newcombe TOST, margin 0.20 | equivalent, [-0.184, +0.184] |
| Exp 4c residue-null | 12/12 vs 12/12 | Newcombe TOST, margin 0.20 | equivalent, [-0.184, +0.184] |
| Exp 5: +derived = pointers-only | 12/12 vs 12/12 | Newcombe TOST, margin 0.20 | equivalent, [-0.184, +0.184] |

Superiority claims are robust to small N (a rejection is not weakened by sample size); the equivalence claims are the ones that required N=12, because two arms both at ceiling have a Newcombe floor of 0.25 at N=8, which cannot clear a 0.20 margin. We raised N rather than widen the margin.

---

## 5. The bounded law

The results pin a single rule from both sides. Let a carried constraint be *recoverable* if a capable same-model receiver, given only the pointed-at code, reconstructs it. Then:

> The `state.derived` reasoning residue earns its tokens **if and only if** the constraint left no recoverable trace in the artifacts.

The necessary side is a confirmed superiority (Experiment 4: absent trace, residue required, 8/8 versus 0/8). The unnecessary side is confirmed equivalence across a shallow constraint (Experiment 5) and a deeper one (Experiment 4c), with the sharp boundary being trace *presence* rather than salience (Experiment 4b) or, as far as our deep-toy reaches, depth. This sharpens the opening design rule for multi-agent handoffs: **spend channel tokens only on what the receiver cannot cheaply regenerate.** Everything else should be a pointer into the shared tree.

The practical consequence for a coordinator is a decision, not a default: carry residue when, and only when, the reasoning that produced an artifact is not recoverable from the artifact. How often that regime occurs in real traffic is a base-rate question we do not answer here (§6).

---

## 6. Limitations

- **Deep-toy, not deep-real.** Experiment 4c stripped the rationale but not the structural trace, so its "unrecoverable" cell was still recoverable. The regime the necessity side is really about (code fully present, behavior not inferable) is untested; real analytical constraints are deeper still.
- **Base rate unmeasured.** The law says the residue helps when the trace is absent; it does not say how often real handoffs carry such low-recoverability constraints. An instrument for measuring this over real traffic is released (`docs/benchmarks/instruments/rederivable-probe.py`) but not run here.
- **One substrate per regime.** Each point rests on a single constructed or semi-synthetic substrate; external validity compounds with more.
- **Cost single-shot.** Experiment 1 is one trial per arm per repository; it is framed as a NULL, not an equivalence.
- **Model-specific control gap.** The decoy control is unavailable for this model because it refused to carry misleading residue; a different model, or a non-adversarial decoy design, would be needed to isolate carried content from generic prose.
- **Lever 1 knee.** Compression below 1k tokens is untested.

---

## 7. Related work

`pigeon`'s architectural thesis (heterogeneous frontier models, no shared memory, no merge, a filesystem contract) is consistent with recent multi-agent systems that deliver a coordinated ensemble as a single system and that treat coordination as a first-class, potentially learned component [Sakana AI, Fugu / Trinity, 2026, citation to verify]. Those systems locate their value in *learned* coordination (an evolved or trained conductor that decides routing and writes per-worker instructions), which `pigeon` does not have: its DAG is hand-written and deterministic. Our contribution is orthogonal and upstream: a measured, bounded law for one channel mechanism, on which such a coordinator's carry-or-point decision could rest. The statistical methods are standard [Clopper and Pearson 1934; Wilson 1927; Barnard 1945; Schuirmann 1987; Newcombe 1998 — citations to complete].

---

## 8. Conclusion

Better multi-agent coordination is not, in this setting, a way to save tokens: the overhead can only approach parity from above. Its value is carrying reasoning a receiver cannot re-derive, and that value is sharply bounded: the carried residue is necessary if and only if the reasoning left no recoverable trace. We confirm the necessary side by superiority and the unnecessary side by equivalence, at one exact-interval standard, and release the benchmark so the boundary can be pushed toward genuinely deep, real constraints. The design rule that follows is small and testable: pointers, not payloads, for everything the receiver can regenerate; residue only for what it cannot.

---

## Appendix A. Reproducibility

The benchmark is committed at `github.com/SlartiLabs/pigeon` under `docs/benchmarks/`.

```
# statistics (recomputes CIs, Fisher/Barnard, Newcombe TOST from the result JSONs)
python3 docs/benchmarks/figures/stats_appendix.py        # -> docs/benchmarks/results/stats-appendix.json

# figures 1-11
python3 docs/benchmarks/figures/make_figures.py
python3 docs/benchmarks/figures/make_carrier_comms_figures.py

# validate a substrate's held-out grader (no agents, no spend)
python3 docs/benchmarks/substrates/exp4c-depth/validate.py
```

- **Substrates + per-trial ledgers:** `docs/benchmarks/exp{4b,4c,5}-substrate/` (each with `validate.py`, the held-out `accept.py`, and committed `RESULTS-*.csv`).
- **Pre-registrations:** `docs/benchmarks/preregistrations/exp5-natural-substrate.md`, `docs/benchmarks/preregistrations/exp4c-deep-constraint.md`; Experiment 4b in `docs/benchmarks/substrates/exp4b-trace-presence/CALIBRATION-RESULT.md`.
- **Result data:** `docs/benchmarks/results/lever2-{confirm,natural,deep-4c,3hop,screen}.json`, `lever1-sweep.json`, `forkA-capability.json`, and `stats-appendix.json`.
- **Working report (source of this manuscript):** `docs/benchmarks/report.md`.

Note on ledgers: the Experiment 4/4b live runs executed in disposable worktrees whose per-trial transcripts were not retained; those experiments reproduce the setup and the summary counts and exact intervals, not the per-trial transcript ledger. Experiments 4c and 5 commit their full per-trial ledgers.

---

## References

*To complete. Confirm venue and full citations before submission.*

1. Clopper, C. J., and Pearson, E. S. (1934). The use of confidence or fiducial limits illustrated in the case of the binomial. *Biometrika*.
2. Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. *JASA*.
3. Barnard, G. A. (1945). A new test for 2x2 tables. *Nature*.
4. Schuirmann, D. J. (1987). A comparison of the two one-sided tests procedure and the power approach for assessing the equivalence of average bioavailability. *J. Pharmacokinet. Biopharm.*
5. Newcombe, R. G. (1998). Interval estimation for the difference between independent proportions. *Statistics in Medicine*.
6. Sakana AI (2026). Fugu / Trinity: multi-agent systems as a single model with an evolved coordinator. *[venue/title to verify].*
