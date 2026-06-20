# Adversarial Critique — carrier-comms design brief

**critique-mimo · 2026-06-19**

---

## 1. The "parity" ceiling is a red herring

Lever 1 claims its ceiling is parity. This is presented as modesty, but it conceals a deeper problem: **parity with what?** The doc never defines the baseline. Is it parity with current pack overhead? With a hypothetical zero-overhead channel? Without a baseline, "parity" is unfalsifiable — you can always claim you hit it.

Worse: if parity is the ceiling, the entire Lever 1 investment (instrumentation, compression work, U-curve measurement) is justified by *not making things worse*. That's a maintenance task, not an optimization. The doc spends tokens on "Worth an afternoon, not a headline" but then devotes two full sections and a measurement framework to it. The framing doesn't match the claimed value.

## 2. The quality win is unmeasurable with the stated model matrix

The doc's most interesting claim is that Lever 2's win is a *quality* win — "the receiver respects a constraint it would otherwise violate." But Phase-0 already proved the measurement substrate is broken:

- `oc-mimo` and `oc-nemotron`: timed out at 600s. Never produced output.
- `agy`: Google OAuth expired. Cannot run.
- Remaining: `sonnet`, `opus`, `deepseek`, `north`, `qwen`.

To get statistical significance at N≥3 across the model matrix on the *quality* axis, you need to run cross-model handoffs (the Fork-A pattern) with enough repetitions on enough models. But free models either time out or aren't instrumented (`telemetry_flags: []`). Paid models are expensive. The doc acknowledges this ("the cross-model arms must lean on the success/quality axis, not free-model token telemetry") but doesn't solve it. **The honest answer is: you cannot measure the quality win you're betting on.**

## 3. N≥3 is arbitrary and insufficient

"Every gate N≥3, thresholds locked cold before the run." Why 3? For a binary outcome (pass/fail), 3 trials gives you ~12.5% chance of seeing all-pass by luck alone (0.5³ = 0.125). For a quality metric on a 5-point scale, 3 samples is noise. The doc locks thresholds without justifying them, which is cargo-cult rigor — it *looks* like a controlled experiment but isn't one.

If you're serious about measurement, you need a power analysis: what effect size are you looking for, how many samples to detect it at p<0.05? The answer is probably N≥20, which the doc already knows (it references "Rung 4 — recall-proof gate, ≥ 20 sessions") but doesn't apply to the quality gate.

## 4. The U-curve is not operationalized

The doc says "Target = minimum channel that holds the receiver's success rate" and "stop at the knee." But:

- **Success is binary.** Code works or it doesn't. A U-curve on a binary metric is a step function — you won't see a smooth knee, you'll see cliff collapse. You need a continuous quality metric (test coverage, number of regressions, semantic correctness score) to detect a U-curve.
- **The knee detector is undefined.** How do you know you've hit the knee? What's the stopping rule? Without it, you're just compressing until something breaks, which is the naive approach the doc claims to improve on.

## 5. The "re-derive cheaply" failure mode is identified but not tested

The doc says Lever 2 fails if "a capable receiver reconstructs the reasoning from the pointed-to code." This is the most likely failure mode — modern LLMs are good at reading code and inferring intent. But the doc proposes no test for it. The Fork-A result (5/5 bridge, 0/5 no-bridge) tests *compliance with an explicit contract*, not *inference from code alone*. You need a test where the receiver gets only pointers (no residue) and must still respect the constraint. If it succeeds, the residue was unnecessary.

## 6. Token-neutral is not a win — it's a cost

The doc states pigeon is token-neutral (cookiecutter +46–59%, marshmallow +8.1%, tie on success). This means Lever 1 doesn't save tokens. The doc frames this as "do not re-derive" (don't expect savings), but the entire plan is an *optimization* plan. If the result is parity, you've spent engineering effort to stay in place. The doc should be honest: Lever 1 is a *defensive* measure (prevent regression), not an *offensive* one (create savings). Don't dress it up as optimization.

## 7. The Phase-0 panel failure is a feature, not a confirmation

The doc frames free-model timeouts and auth expiry as "confirming the plan's own ops-feasibility worry." This is spin. The plan's feasibility worry was *qualitative* ("the free substrate may be too weak"). Phase-0 *quantified* it: 2/3 free models failed entirely, 1/1 had auth issues. That's not a confirmation — it's a **hard constraint on what you can measure**. The doc should say: "We cannot run the cross-model quality measurement we designed. The plan needs revision, not just refinement."

## 8. What's missing

- **A falsification criterion.** The doc asks "where is this plan wrong?" but provides no mechanism to *prove* it wrong. What result would make you abandon Lever 2? If the answer is "nothing," it's not a research question — it's a commitment.
- **A cost model.** Token-neutral means cost-neutral only if model mix is constant. If you shift toward paid models for quality measurement, costs increase. The doc doesn't model this.
- **An exit ramp.** If Lever 2 doesn't produce a quality win after N≥20, what happens? The doc says "win bar = quality OR token (replicated)" but doesn't say what "not replicated" triggers.

---

**Bottom line:** The two levers are sound in principle, but the measurement plan cannot deliver on its own promises with the available substrate. The most honest move is to (1) treat Lever 1 as maintenance, not optimization; (2) redesign the quality measurement to work within the paid-model budget; and (3) define explicit falsification criteria before running anything.
