# Kill / continue criteria — LOCK COLD, before the first run

A criterion chosen after seeing results is a rationalization, not a criterion.
Both blocks below are locked **before** any benchmark run or launch. This file
carries no opsec risk and is committed deliberately.

There are **two** criteria, doing two different jobs:
- **A. Benchmark go/no-go** — decides, cold, what Tier-A result would make us NOT
  publish a "coordination helps" headline. Gates the launch claim.
- **B. Adoption kill-criterion** — decides, cold, when to stop hardening pigeon
  post-launch. Gates continued investment.

---

## A. Benchmark go/no-go  (lock before the first measured run)  — LOCKED 2026-06-18

```
HYPOTHESIS: pigeon's coordination contract (handoffs + shared, token-accounted
            context) measurably helps multiple agent CLIs do multi-file,
            context-carrying work versus the same CLIs run naked.

SETUP:  3 public repos (reproducible headline) + 3 private (anonymized support).
        Per repo: coordination-requiring tasks (PROTOCOL §3), two arms
        (WITH = pigeon coordinate, WITHOUT = same CLIs naked), IDENTICAL prompt
        text to both arms, fresh worktree at a pinned SHA. Per-repo numbers,
        NEVER pooled.

AXES (pre-declared, per task):
  1. success           = the task's objective acceptance check passes
  2. human interventions = count of every manual step-in
  3. tokens
  4. wall-clock

GO (publish + launch the "coordination helps" claim) IF:
  on >= 2 of the 3 PUBLIC repos, WITH beats WITHOUT by a material margin on
  >= 1 primary axis -- ANY of:
     - completes >= 1 MORE task at acceptance, OR
     - >= 30% FEWER human interventions at equal-or-better success, OR
     - >= 20% FEWER tokens at equal success
  AND no public repo shows pigeon materially WORSE
     (> 20% regression on any axis with no compensating gain).

NO-GO / REFRAME IF:
  >= 2 of 3 public repos show no measurable difference (tie), OR pigeon is
  net-negative on a majority. Then DO NOT publish a savings headline; either
  reframe the value prop (token-accounting / observability, not savings) or
  accept pigeon as a complete, worthy tool for an audience of one.

HONEST-NULL CLAUSE:
  a tie is itself a publishable finding ("no measurable coordination benefit on
  single-CLI-tractable tasks") -- report it, do not bury it.
```

---

## B. Adoption kill-criterion  (post-launch)  — LOCKED 2026-06-18

```
LAUNCH HYPOTHESIS: developers running >=2 agent CLIs against one repo will adopt
                   a token-accounted coordination contract.

WINDOW:            8 weeks post-launch

KILL IF BOTH of the unfakeable signals are zero:
  - stranger-filed issues   = 0   AND
  - external contributors   = 0
  (Install count is REPORTED but does NOT gate: PyPI installs are mirrors, bots,
   and CI -- the noisiest signal. The unfakeable ones are a stranger filing an
   issue and an external contributor; the gate keys on those alone.)

THEN: the binding constraint is TAM, not polish -> stop hardening; reconsider the
      thesis (or accept pigeon as an excellent tool for an audience of one -- a
      complete and worthy outcome).
```

A null result is *information*, not failure — but only because these blocks were
locked before anyone was emotionally invested in the outcome.
