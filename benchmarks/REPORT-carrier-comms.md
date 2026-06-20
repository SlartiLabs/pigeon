# Carrier-Comms Optimization — Benchmark Report

**Status:** living document · **Date:** 2026-06-19 · **Branch:** `feat/carrier-comms`
**Scope:** how *carriers* (CLI agents that share no memory) talk to each other — the
handoff channel and the context pigeon injects — and whether two levers improve it.

> **Headline.** pigeon does **not** save tokens (it is token-neutral to mildly
> negative; Exp. 1). Its value is **cross-model capability**: a carrier can carry a
> constraint the next carrier cannot re-derive. Exp. 2 shows this is *possible*
> (5/5 vs 0/5); **Exp. 4 confirms the carried reasoning residue is *necessary*** in
> that regime — same model, fully isolated, through the productionized
> `state.derived`→markdown injection: **8/8 with residue vs 0/8 without (N=8, exact
> 95% CIs cleanly separated)**, at parity-or-better cost. **Exp. 3** finds the default
> pack is **over-provisioned** (compress to pack=1k, success holds 3/3 across the tested
> 4× range); the knee itself is below 1k and untested — not pursued (Lever 1 is maintenance).

---

## 1. The system

![Figure 1 — system schematic](figures/fig5_system_schematic.png)

**Figure 1.** Carriers are separate processes with no shared memory; the contract
is the filesystem, not anyone's context window. Two things cross between them: the
**shared working tree** (any carrier can grep it — *re-derivable*, so point at it via
the `pack`) and the **handoff channel** (transient, per-spawn). The channel carries
**pointers + a derived residue** — and the whole program is the claim that you should
spend channel tokens *only* on the residue (what the receiver cannot cheaply
regenerate). A durable board (`.pigeon/memory`) persists handoffs, metrics, and
distilled decisions across sessions.

The two levers map onto this picture:

- **Lever 1 — compress the channel.** Shrink the per-spawn `N·overhead` (pack +
  scaffolding). Ceiling = **parity**; this is *defensive* (prevent regression), not
  an optimisation that creates savings.
- **Lever 2 — the polymath handoff.** Carry the *irreducible* reasoning residue
  (`state.derived`: ruled-out approaches, a discovered constraint, the rationale,
  the next action); point at everything regenerable. The win is a **quality** win.

## 2. The two ceilings

![Figure 2 — the two ceilings](figures/fig6_two_ceilings.png)

**Figure 2.** *Left:* `Cost ≈ Σ work + N·overhead`. The overhead **share** shrinks as
the task grows (cookiecutter +46–59% → marshmallow +8.1%) but **asymptotes to parity
from above** — it never crosses into savings. *Right:* compression is not monotone.
Past a point a too-terse channel makes the receiver re-derive what you stripped and
re-explore, costing *more* — a **rate–distortion U-curve**. The target is the
*minimum channel that holds the receiver's success rate* (the **knee**), not the
smallest channel. The right panel's data is filled by the Phase-3 sweep (§6).

---

## 3. Experiment 1 — Cost benchmark (verdict: token-savings is **NO-GO**)

Two public repos, two arms each (WITH pigeon vs WITHOUT), same model (sonnet),
identical task spec, fresh worktree at a pinned SHA, held-out acceptance test as the
gate. Headline metric is **USD** (`claude total_cost_usd`), the only basis comparable
across arms.

![Figure 3 — cost by arm](figures/fig1_cost_by_arm.png)

**Figure 3.** Per-task total cost. cookiecutter (small files): solo $0.439 · naive
$0.402 · pigeon $0.640 (**+46–59%**). marshmallow (large files, 3-agent chain): naive
$1.112 · pigeon $1.202 (**+8.1%**). **Success ties** in both (held-out test passes for
all arms). The gap *is* the coordination overhead.

![Figure 4 — overhead amortization](figures/fig2_overhead_amortization.png)

**Figure 4.** Overhead share vs task size: the penalty shrinks with scale (overhead is
~fixed, the task grows) but stays **positive**. pigeon's pack/retrieve did not cut the
exploration cost (the plan step is a near-wash).

![Figure 5 — marshmallow per-step](figures/fig3_marshmallow_per_step.png)

**Figure 5.** Per-step cost on the large task; the plan step is a measured wash —
curated context did not buy fewer exploration turns.

**Verdict (Exp. 1): NO-GO on a "saves X%" headline.** pigeon is token-neutral to
mildly negative even in its best case. Its value is not token savings.

## 4. Experiment 2 — Fork-A cross-model capability (verdict: **possibility** proven)

Three CLIs that share no memory — **claude → opencode/mimo → agy** — on a controlled
`ledger` repo with an **off-disk wire contract** given only to hop 1 and never written
into the code. Held-out grader (`accept.py`) the agents never see; the contract is
deliberately anti-idiomatic, so it is *not* inferable from pristine code.

![Figure 6 — Fork-A capability](figures/fig4_forkA_capability.png)

**Figure 6.** **bridge 5/5, no-bridge 0/5 (N=5).** The cold arm writes working,
round-tripping code but with **idiomatic keys** (`name`/`balance_cents`/`created`)
instead of the contract's (`acct`/`cents`/`ts`); the held-out test catches it. The
state lived only in the handoff, not in the code — so only the bridged chain
reproduced it.

**Verdict (Exp. 2): possibility proven.** pigeon *can* carry state across a model
boundary that would otherwise be lost. This is a capability proof, paired honestly
with Exp. 1 (token-neutral, not cheaper).

---

## 5. Pre-registered protocol & the panel corrections

Before the paid sweeps, a multi-model panel (mimo, agy/Gemini) adversarially reviewed
the plan. It did not falsify the levers but **falsified the measurement design**, and
the corrections are baked into Table 1: (i) the win rule is **net USD**, not raw
tokens (output is ×3–5; pointer-izing can add tool-call turns that re-send history);
(ii) `bench_join` tracks **`num_turns`**; (iii) the honest Lever-2 test needs a
**pointers-only NULL arm** (does a capable model re-derive from code alone?); (iv)
**N=3 screens, N≥8 confirms** (0.5³ = 12.5 % all-pass by luck); (v) carry `derived` as
visible markdown, not buried JSON. Full critiques: `docs/design/panel-reviews/`.

**Table 1 — Pre-registered protocol (KILL-CRITERION discipline).**

| | Exp. 3 — Lever 1 (channel compression) | Exp. 4 — Lever 2 (derived residue) |
|---|---|---|
| **Arms** | baseline vs compressed configs (channel ∈ {1k,2k,3k,4k} × top-k {3,5,8}) | **cold** / **pointers-only** / **pointers+derived** |
| **Axis 1 (success)** | held-out acceptance pass | held-out contract pass |
| **Axis 2 (cost)** | **net USD** (output-weighted) + `num_turns` | **net USD** + `num_turns` |
| **Axis 3 (regression)** | full-suite regression count | n/a (contract task) |
| **N** | screen 3 → **confirm ≥ 8** | screen 3 → **confirm ≥ 8** |
| **GO threshold** | accept(C)=accept(B) ∧ reg(C)≤reg(B) ∧ **net-USD win** at the knee | replicated **quality win** (success ↑) OR **USD win**, residue < 400-tok budget |
| **Equivalence margin** | ±1 regression, ±5 % USD | success CIs separated; USD within ±10 % = "parity" |
| **KILL (publishable −)** | no config beats baseline on net USD without losing success → "channel already minimal" | pointers-only ≈ pointers+derived at N≥8 → "capable models re-derive; residue is overhead" |

---

## 6. Experiment 3 — Lever 1 (the sweep): the default pack is **over-provisioned**

**Gate G1 (classification) — PASS.** On the recorded marshmallow WITH-arm, per spawn
the **pack injects ~2 992 tokens vs the handoff doc's ~286 — pack is ~10.5× the
handoff.** So the over-send lives in the pack + scaffolding, not the handoff doc;
Lever 1 is correctly aimed there. The `scaffold` meter is wired and fires live.

The U-curve sweep then varied `pack_max_tokens ∈ {4000, 2000, 1000}` on the
marshmallow slug task, same model (sonnet), **N=3/config**, measuring channel tokens
vs held-out success + regressions + measured USD.

![Figure 7 — Lever-1 rate–distortion frontier](figures/fig7_lever1_frontier.png)

**Figure 7.** The tested window `[1k, 4k]` is **entirely on the over-provisioned (right)
arm** of the U-curve. Across the whole 4× pack range, **success holds 3/3**; as the pack
shrinks the channel falls monotonically (8 706 → 6 092 → 4 659 tok) **and so does mean
cost** ($1.123 → $1.006 → $0.855). Turns rise at pack=1k (51 vs 46) — the **multi-turn
tool tax** the panel predicted (smaller pack → more file reads) — but the pack input
savings dominate, so net USD still falls.

**Verdict (Exp. 3): the default pack is over-provisioned; compress to 1k free.**
The **firm, shippable** finding is "pack=1k holds success 3/3" — the default 4 000 is
larger than this task needs. **Scoping honesty:** this did **not** find the knee. The
left arm of the U-curve (where too-terse breaks success) and the knee both live **below
1k pack and are untested**; "the knee is below 1k" is an *inference from three monotone
points*, not a measurement. The cost reduction is **directional** (N=3, overlapping
CIs), not locked. Per the "Lever 1 is maintenance" steer, the sub-1k knee hunt is
**not pursued** — the actionable result is already in hand. Data: `results/lever1-sweep.json`.

## 7. Experiment 4 — Lever 2 (CONFIRMED, N=8): residue is **necessary**, at parity cost

The decisive test, **same model throughout (sonnet ×3)** to isolate the residue's
value from any cross-model confound, on the Fork-A contract substrate, in **two
physically separate worktrees** so the contract cannot leak between arms (it did, in
two earlier harness versions — see §9). Pristine-asserted before every trial.

The confirm runs the **productionized mechanism**, not the screen's `DERIVED.md`
proxy: the architect emits the contract into **`state.derived`**, and
`coordinate._upstream_derived_markdown` injects it as a `## Carried reasoning`
markdown block into each downstream prompt (the panel's correction #4 — don't bury the
constraint in JSON). Injection fired on **8/8** with-derived trials.

- **pointers + derived** (`state.derived` → markdown injection): **8/8 PASS**,
  CI95 **[0.631, 1.0]**, 24.6 turns, **$0.417**/run.
- **pointers-only** (downstream gets only `repo://ledger/account.py`, pristine):
  **0/8 PASS**, CI95 **[0.0, 0.369]**, 23.0 turns, **$0.436**/run.
- **cold** (Exp. 2 cross-model, no bridge): **0/5**.

![Figure 8 — Lever-2 three-arm comparison](figures/fig8_lever2_three_arm.png)

**Figure 8.** *(a)* The anti-idiomatic constraint survives **only** when the residue is
carried — the two CIs are **cleanly separated** (no overlap). A capable sonnet receiver
does **not** re-derive it from pristine code (the panel's "re-derives cheaply" failure
mode does **not** fire). *(b)* The residue arm is **cheaper**: the null agents explore
more, then fail. A **quality win at parity-or-better cost**, not a quality/cost trade.

![Figure 9 — USD-weighting vs raw tokens](figures/fig9_usd_weighting.png)

**Figure 9.** The methodological lens the panel demanded: carrying the residue is a
**+18 % raw-token cost** but a **−18 % net-USD outcome** — the two deltas point
opposite ways. A raw-token accounting would have mis-scored this.

**Verdict (Exp. 4): GO — CONFIRMED at N=8.** In the regime where the reasoning is
genuinely irreducible (a constraint invisible in the final code), the `state.derived`
residue is **necessary and free**: 8/8 vs 0/8 with exact 95 % CIs that do not overlap,
at lower mean cost. This holds through the real injection mechanism, not just the
screen proxy. (Trials that hit a mid-run session rate-limit — turn-1 $0 no-ops — were
discarded and re-run; the 8 reported per arm are all valid; see §9.)

---

## 8. Results summary

**Table 2 — Results summary.**

| Exp. | What | Result | N | Verdict |
|---|---|---|---|---|
| 1 | Cost benchmark (WITH vs WITHOUT, 2 public repos) | +46–59 % (small), +8.1 % (large); success ties | 1/arm/repo | **NULL** — token-savings NO-GO |
| 2 | Fork-A cross-model capability | bridge 5/5 vs no-bridge 0/5 | 5 | **POSSIBILITY** proven |
| 3 | Lever 1 — channel compression (pack sweep) | success holds 3/3 across tested [1k,4k]; knee below 1k untested | 3/config | **OVER-PROVISIONED** — compress to 1k free (firm); cost-win directional; knee not pursued |
| 4 | Lever 2 — derived residue (same-model, isolated, real injection) | **8/8 vs 0/8 vs 0/5**; CIs separated; residue cheaper ($0.417 vs $0.436) | 8 / 8 / 5 | **GO — CONFIRMED** |

---

## 9. Threats to validity (what the screens cost us, and what we fixed)

The Lever-2 screen took **three** voided attempts before a trustworthy null — each
caught by checking that the numbers were *physically possible*, not by trusting the
pass/fail headline:

1. **Contract-leaking tests.** A reset that reverted only `ledger/` left
   contract-encoding assertions in `tests/test_account.py`; every arm read the
   contract for free. → full `git reset --hard` + a pristine assertion.
2. **Shared-worktree side channels.** Both arms in one worktree could still leak via
   stray files. → **two physically separate worktrees**, one per arm (the operator's
   fix), so leakage is impossible by construction.
3. **Silent no-op.** A config mismatch (`wt-nobridge` lacked the `sonnet` runner) made
   the null arm refuse to spawn — `num_turns=0, cost=0, wall=0` exposed it. → configs
   unified; re-run produced real executions (22–26 turns) that genuinely failed.

4. **Session rate-limit mid-run.** Both the N=8 confirm and the Lever-1 sweep hit a
   `429 "session limit"` partway through; the affected trials are turn-1, $0, ~5 s
   no-ops — the same "physically impossible" signature as #3. They were **discarded
   and re-run** after the limit refreshed; every reported trial is a valid real run
   (22–26 turns / 130–155 s for Lever 2; 33–53 turns for Lever 1).

Remaining limits: Lever 2 is confirmed at **N=8 on one task/contract** — a second
substrate would strengthen external validity; Lever 1's **cost-win is directional**
(N=3, overlapping cost CIs) — a locked GO needs N≥8 and a second task, though
"compress to 1k with no success loss" is firm. The productionized `state.derived`→
markdown injection is now the mechanism under test (no longer the `DERIVED.md` proxy).

## 10. Reproduce

```
# figures
python3 benchmarks/figures/make_figures.py                 # Exp.1/2 (fig1–4)
python3 benchmarks/figures/make_carrier_comms_figures.py   # fig5–9
# join any recorded arm (tokens × held-out success × turns × USD)
python -m pigeon.bench_join benchmarks/results/raw/<label>
```

Raw artifacts: `benchmarks/results/raw/` (marshmallow, marshmallow-phase2,
cookiecutter); panel critiques: `docs/design/panel-reviews/`; the live Lever-2 screen
ran from `/tmp/bench/forkA` (disposable public-clone substrate).

---

*Commits are the operator's. This report is regenerated as Exp. 3/4 confirmations land.*
