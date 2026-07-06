# Stage 4 — base-rate probe: result

**Anchor:** limitations-closing plan, Stage 4. The bounded law settles *when* the
carried residue helps (iff no recoverable trace). Stage 4 asks *how often* real
handoffs carry such low-recoverability constraints — a softer kind of evidence,
by design (an LLM-judge semantic match, not the held-out functional grader used
elsewhere).

## What was done

1. **Wired the instrument for live use.** `instruments/rederivable-probe.py`'s
   `judge_live` is now implemented (two `claude`/sonnet calls per constraint:
   reconstruct-from-code, then a semantic-match verdict on whether the
   reconstruction covers the carried constraint). `--selftest` still passes
   offline. The probe is ready for any future real-traffic corpus.

2. **Assembled the available corpus of real `state.derived.constraint_found`
   handoffs** and checked its viability, per the plan's step 2.

## Finding: no viable corpus for a base rate right now

The available real (non-experiment) traffic is **4 carried constraints across 3
handoffs**, all from the pre-launch audit session (`audit-code`, `audit-opsec`,
`synthesis`). This corpus cannot yield a meaningful code-recoverability base rate:

- **All 4 are mechanism-aware.** They were written after the team knew Lever 2, so
  at best they estimate "this team's current, mechanism-aware rate," never a
  general one (the plan's stated caveat). No pre-mechanism-awareness traffic
  survives — plausible, since the mechanism exists because it was built.
- **The pointers do not isolate code-recoverability.** Each handoff points at an
  audit *review* markdown (`.pigeon/coordinate/reviews/audit/*.md`), not the
  source the constraint is about — and those review files have since been
  cleaned, so the pointers do not even resolve. A pointers-only reconstruction
  would therefore see nothing (or, had they survived, the review's own restatement
  of the finding — circular). Either way it does not measure whether a receiver
  re-derives the constraint from *code*.
- **n = 4 is far too small** for an interval anyone should cite.

Running `--live` on this corpus would produce noise dressed as a rate. The honest
Stage 4 outcome is therefore the one the plan explicitly anticipates: **the base
rate is not estimable from currently-available traffic; the probe is wired and
waiting for a real corpus** (many genuine `state.derived` handoffs, ideally with
`repo://` pointers to source, accumulated during ordinary use).

## Excluded on purpose

The `/tmp/bench/*` experiment handoffs (exp4c, exp5, Fork-A) carry constraints
that were *constructed* to be unrecoverable (or recoverable). Including them would
report the base rate of contrived substrates (~100% low-recoverability by
construction), not of real traffic — so they are excluded from the corpus.

## To run it later (one command, gated on a real corpus)

```
python3 docs/benchmarks/instruments/rederivable-probe.py <handoffs-dir> --repo . --live
```

_Commits are the operator's._
