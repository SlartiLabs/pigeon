# Tier-A Coordination Benchmark — Full Report

**Subject:** Does `pigeon`'s coordination contract reduce the cost of doing
real, multi-file coding work with LLM agent CLIs, versus running the same
agents without it?
**Date:** 2026-06-18 · **Status:** complete, decisive for the cost question.
**Evidence:** `docs/benchmarks/results/{cookiecutter,marshmallow}.json` (committed),
raw logs in `docs/benchmarks/results/raw/` (gitignored), figures in
`docs/benchmarks/figures/`.

---

## 1. Executive summary

We ran real, two-arm agent benchmarks on two permissively-licensed public
repositories, each task graded by a **held-out acceptance test** plus the
project's full suite. Across every framing tested, **pigeon did not reduce
cost**, while **task success was identical** (both arms always completed):

| Repo (scale) | Comparison | Cost Δ (pigeon vs other) | Wall Δ | Success |
|---|---|---|---|---|
| cookiecutter (small) | vs solo (1 agent) | **+45.6 %** | +55.8 % | tie |
| cookiecutter (small) | vs naive multi-agent | **+59.3 %** | +43.1 % | tie |
| marshmallow (large) | vs naive multi-agent | **+8.1 %** | +79.7 % | tie |

Pigeon's overhead is approximately **fixed per agent** and therefore shrinks as
a fraction of a larger task (penalty 59 % → 8 %), but **never crosses into
savings**, even on a task deliberately designed as pigeon's best case
(Figure 2). Under the pre-registered go/no-go criterion (`KILL-CRITERION.md`:
a win on ≥ 2 of 3 public repos), **a token/cost-savings launch headline is a
decisive NO-GO** — two of two repos show no win, so the third cannot rescue it.

This is a *negative* result for the cost claim, not for pigeon: cost is simply
the wrong axis. The capabilities pigeon uniquely provides — cross-CLI handoffs,
parallel fan-out, reproducible run manifests, per-model token accounting — were
out of scope for a same-model cost benchmark and remain open (Section 6).

---

## 2. Background and hypothesis

`pigeon` coordinates multiple AI coding CLIs through a filesystem contract:
agents exchange **handoffs that carry pointers, not payloads**, and pull bounded
context on demand (`pack`, `retrieve`, a generated `manifest`). The launch had
been carrying a synthetic ~92.8 % figure; the goal here was to replace it with a
real, reproducible number.

> **H1 (pre-registered).** Pigeon's coordination contract measurably reduces the
> resources needed to complete multi-file, context-carrying tasks versus the
> same model run without pigeon — on ≥ 1 primary axis (success, human
> interventions, or tokens), on ≥ 2 of 3 public repos, with no repo materially
> worse.

The criterion and its kill conditions were locked **before** any run
(`KILL-CRITERION.md`), so that a result could not be rationalised after the fact.

---

## 3. Methods

### 3.1 Two-arm design — one variable

Every comparison holds everything constant except pigeon:

- **Model:** `claude/sonnet` on **both** arms (Config B in the kill-criterion).
- **Task spec:** byte-identical `TASK.md` to both arms.
- **Start state:** a fresh `git` worktree at a pinned commit SHA.
- **Variable:** WITHOUT = the agents run without pigeon; WITH = the same model(s)
  driven by `pigeon coordinate` (handoff pointers + packed/retrieved context).

Two WITHOUT baselines were used:

- **solo** — one agent does the whole task (the realistic "do I even need
  coordination?" baseline).
- **naive multi-agent** — the *same* N-step decomposition as the pigeon arm
  (e.g. plan → implement → review), coordinated **by hand**: agents share the
  filesystem (as separate CLIs really do) and the manual handoff forwards the
  prior step's plan text. We deliberately did **not** paste whole source files
  between steps — nobody coordinating real CLIs does that when the files are on
  disk, and doing so would be a strawman that flatters pigeon. This is the
  honest, hardest baseline for pigeon to beat.

### 3.2 Repository selection

Candidates were screened against `PUBLIC-REPO-CRITERIA.md` (permissive licence,
public + pinnable, real passing suite, hermetic/cheap, multi-module,
agent-friendly language, identity-neutral) and **verified by actually cloning,
installing, and running each test suite at a pinned SHA**. Three passed, giving a
CLI / library / service spread; two were used for runs:

| Slot | Repo | Licence | Pinned SHA | Pkg LOC | Suite |
|---|---|---|---|---|---|
| CLI | cookiecutter | BSD-3 | `c88fbe9` | 3,186 | 379✓/4skip, ~6 s |
| Library | marshmallow | MIT | `7b4ab6a` | 4,830 | 1178✓, ~3 s |
| Service | flask | BSD-3 | `36e4a82` | 6,961 | 491✓, ~2 s |

flask was held in reserve (the cost question was settled before it was needed);
starlette is a verified backup. **Per-repo numbers are never pooled.**

### 3.3 Task design and integrity (held-out acceptance)

Each task is a real cross-module feature (PROTOCOL §3 — work where step 2 needs
step 1), chosen so a single edit cannot finish it:

- **cookiecutter:** add a built-in `shoutcase` Jinja2 filter, available *by
  default* — forces edits in both `extensions.py` (define) **and**
  `environment.py` (register in `default_extensions`).
- **marshmallow:** add a `Slug` validator (`validate.py`, 708 lines) **and** a
  `Slug` String-field that wires it (`fields.py`, 2148 lines), mirroring the
  `Email`/`Url`/`Regexp` conventions — forcing the agent to *explore* two large
  files. This is pigeon's best case: heavy per-agent work + curated context could
  plausibly cut exploration.

**Integrity guard.** Success is judged by an acceptance test the agents **never
see** (`accept.py`), run identically against each arm after it finishes, plus the
project's full pre-existing suite as a regression gate. Each gate was validated
**both directions** before any run: it *fails* on the pristine repo (feature
absent) and *passes* on a reference implementation. This prevents an agent from
"passing" by writing a weak test of its own.

### 3.4 Harness and execution

For each arm: a fresh worktree at the pinned SHA + its own venv (editable
install + test deps). The WITH arm adds `pigeon init`, a sonnet-only runner in
`.pigeon/config.yaml`, a `refresh`ed manifest, and an N-wave `*.tasks.yaml`, then
`pigeon coordinate --telemetry`. All agents run unattended
(`--dangerously-skip-permissions`); pigeon waves are chained by `needs:` with
`receives:` pointers. Both arms `pigeon plan` / `--dry-run` validated before
spending. Total spend across all runs ≈ **$3.50**.

### 3.5 Metrics

Per arm, per task: **cost (USD)**, **wall-clock (s)**, **success** (held-out test
+ suite green), **tokens**, **handoffs** (WITH), **human interventions**.

- **Cost is the headline metric** because it is the only one measured on an
  identical basis for every arm — claude's own `total_cost_usd` (WITHOUT via the
  CLI's `--output-format json`; WITH via pigeon `--telemetry`, which records the
  same field). Cost also normalises prompt-cache discounts automatically.
- **Tokens are reported but not headlined.** WITHOUT/solo token totals are
  claude's usage sum (incl. cache); pigeon's are its own tiktoken accounting —
  **different bases, not directly comparable.**
- **Human interventions were 0/0 everywhere** — an automated harness cannot
  exercise this axis; it only carries signal with a human in the loop (deferred
  to the private-repo runs).

### 3.6 "Statistics used" — what we can and cannot infer

This is a **pilot/exploratory measurement, not an inferential study**, and the
report is deliberately explicit about that:

- **n = 1 run per cell.** No replication → no variance estimate, no confidence
  intervals, no significance tests. Reported quantities are **point estimates**
  and **percentage deltas**, not statistics with error bars.
- **LLM agent runs are stochastic** (sampling, tool-use path branching), so each
  cell has unmeasured run-to-run variance. Consequently:
  - The **+8.1 %** marshmallow result is **within plausible run-to-run noise** —
    read it as *effective parity*, not a reliable "pigeon is 8 % worse."
  - The **+46–59 %** cookiecutter results are large enough to be **directionally
    robust** despite n = 1.
- **Why the conclusion is still decisive despite n = 1.** It does not rest on a
  single number reaching significance. It rests on **(a) a consistent direction
  across two independent repos and three framings** (pigeon never cheaper), and
  **(b) a structural argument** (Section 5.2): under Config B the WITH arm runs
  *at least as many* agent invocations as WITHOUT and adds fixed per-agent
  context loading, so a cost *saving* would require coordination to avert work
  that the baseline never wasted — which we did not observe. A pre-registered
  ≥2/3 criterion with 2/2 nulls is mathematically unrescuable by the third repo.
- **Recommended follow-up to harden any published delta:** 3–5 repeats per cell
  to estimate variance, and a paired design across more tasks. Not done here
  because the directional + structural result already answers the launch
  question (no savings) without it.

---

## 4. Results

### 4.1 cookiecutter (small files)

| Arm | Cost (USD) | Wall (s) | Success | Notes |
|---|---|---|---|---|
| solo (1 agent) | 0.4394 | 113 | ✅ | 19 turns; added its own test (380 passed) |
| naive (2 agents) | 0.4016 | 123 | ✅ | implement $0.270 + review $0.131 |
| **pigeon (2 agents)** | **0.6397** | 176 | ✅ | 8 handoffs |

Pigeon is the highest-cost arm: **+45.6 %** vs solo, **+59.3 %** vs naive, for an
identical successful outcome. On a task this small, pigeon's per-agent
scaffolding dwarfs the ~2.5 k-token payload its pointers save.

### 4.2 marshmallow (large files, 3-agent chain — pigeon's best case)

| Arm | Cost (USD) | Wall (s) | Success |
|---|---|---|---|
| naive (3 agents: plan→implement→review) | 1.1117 | 133 | ✅ (1178 green) |
| **pigeon (3 agents, same chain)** | **1.2016** | 239 | ✅ (1178 green) |

Pigeon: **+8.1 % cost**, **+79.7 % wall**, tie on success. Critically, pigeon's
`pack`+`retrieve` did **not** make the exploration-heavy *plan* step cheaper than
naive cold exploration ($0.44 vs $0.46 — a wash, Figure 3); the overhead instead
concentrated in the *implement* step ($0.44 vs $0.28).

### 4.3 Cross-repo: the amortization trend

The pigeon-vs-naive penalty falls from **+59 %** (small) to **+8 %** (large) as
task scale grows — consistent with overhead that is roughly **fixed per agent**
and amortises over heavier work — but it does not reach the savings region
(Figure 2). pigeon's own internal "reduction" metric (87.9 % on cookiecutter,
95.5 % on marshmallow) measures handoff/pack pointers vs a *whole-file
re-transmission* baseline; since realistic coordination does not re-transmit
whole files, **that number is not a real total-cost saving** and must not be
quoted as one.

### 4.4 Figures

**Figure 1 — Cost per successful task by arm.** `figures/fig1_cost_by_arm.png`
Pigeon is the highest bar in both repos; all arms succeeded.

**Figure 2 — Overhead amortization.** `figures/fig2_overhead_amortization.png`
Penalty 59 % → 8 % with task scale; the savings region is never reached.

**Figure 3 — marshmallow per-step cost.** `figures/fig3_marshmallow_per_step.png`
Pigeon's overhead concentrates in the implement step; the plan step is a wash, so
curated context did not buy the hoped-for exploration savings.

---

## 5. Discussion

### 5.1 Why pigeon is net-negative on cost
Pigeon does not remove work; it **adds** a coordination layer (the AGENTS.md
protocol, a packed context bundle, a `retrieve` call, and a handoff document
loaded into *each* agent). Those tokens are paid on every wave. The thing it
saves — re-transmitting context between agents — is cheap when agents share a
filesystem (they just re-read the files), so the saving is small and the
scaffolding dominates.

### 5.2 The fixed-overhead model (why the trend, and why decisive)
Treat each agent's cost as `work(task) + overhead_pigeon`. Then
`cost_WITH ≈ Σ work + N·overhead` while `cost_naive ≈ Σ work` (the naive agents
read what they need without pigeon's bundle). The penalty
`N·overhead / Σ work` shrinks as `work` grows — exactly the 59 % → 8 % trend —
but stays positive for any positive overhead. To go *negative*, pigeon would have
to make `work` itself smaller (e.g. curated context → far fewer exploration
turns). Figure 3 shows that did not happen here: the plan step, where such a
saving should appear, was a wash.

### 5.3 Threats to validity
- **n = 1** (Section 3.6): the marshmallow +8 % is within noise; treat as parity.
- **Sequential only:** `parallel_limit = 1` and linear chains, chosen for clean
  cost attribution — this *suppresses* pigeon's parallel fan-out, a real strength
  (Section 6.2). Wall-clock results are therefore pessimistic for pigeon.
- **Same model, single CLI:** the benchmark cannot show pigeon's cross-CLI value.
- **Small-context regime is pigeon-hostile** but real; the large-context regime
  was chosen to be pigeon-favourable and still did not produce a saving.
- **Two repos, not three:** flask unrun — immaterial to the cost verdict (2/2
  nulls already fail a ≥2/3 criterion).

---

## 6. Possible solutions / paths forward

1. **Reduce the fixed per-agent overhead (engineering).** Profile where the WITH
   tokens go (pack slice size, manifest size, `retrieve` top-k, AGENTS.md length,
   handoff scaffolding). If overhead can be cut several-fold, the curves in
   Figure 2 could reach parity-or-better on mid-size tasks. This is the only path
   that would salvage a *cost* story.
2. **Measure and claim parallelism (wall-clock) — recommended.** pigeon runs
   *independent* subtasks concurrently; hand-rolling runs them one at a time. The
   benchmark forced sequential execution, hiding this. A task with N independent
   subtasks, `parallel_limit > 1` vs sequential hand-rolling, would test whether
   pigeon finishes ~N× faster at parity cost — an **honest quantitative headline
   on pigeon's real strength.** (~$2–4.)
3. **Benchmark the cross-CLI capability.** Hand off claude → opencode → gemini
   (which share no memory). Without a contract this is effectively impossible;
   the claim there is *capability*, not cost — and is not gameable by the naive
   baseline.
4. **Reframe the value proposition (no number).** The evidence supports
   "token-*neutral* on real-sized tasks (+8 % at scale ≈ parity), and uniquely
   provides cross-CLI coordination, reproducible run manifests, per-model token
   accounting, and an audit trail." Drop "saves X %" entirely.
5. **Pick the regime honestly.** If a cost claim is ever made, scope it to where
   it holds (it currently holds nowhere) rather than averaging a blended number —
   per the protocol's "never pool" rule.

---

## 7. Conclusion

A pre-registered, integrity-guarded, two-arm benchmark on two public
repositories shows that **pigeon does not reduce the cost of agentic coding work
versus running the same model without it** — it is +46–59 % on small tasks and
≈ parity (+8 %, within noise) on a large task built to favour it, with **no
success difference anywhere**. The overhead is structural and fixed, amortising
with scale but never turning into a saving. Under the locked go/no-go criterion,
**the cost/token-savings launch headline is a decisive NO-GO**, and the synthetic
92.8 % figure should be retired rather than replaced.

The right conclusion is not that pigeon lacks value, but that **cost is the wrong
axis to sell it on.** Its defensible, still-unmeasured advantages are
*capability and ergonomics*: parallel fan-out (wall-clock), cross-CLI handoffs,
reproducibility, and observability. The recommended next step is a single
parallelism/wall-clock test (Section 6.2) to convert pigeon's genuine structural
strength into an honest, quantitative claim — and, in parallel, the overhead
profiling of Section 6.1 if a cost story is still wanted.

The benchmark cost ~$3.50 and caught an unsupportable headline **before**
publication. That is the harness working as designed: a real, unwelcome number is
worth more than a flattering synthetic one.
