# Benchmark protocol — with-vs-without coordination (Tier A)

Produces the honest number that replaces the synthetic ~92.8%, and the evidence
that gates the public launch. **Read §0 and §0.5 before touching a repo.**

This file is the repo-safe (public-label-only) protocol. The private name↔label
mapping lives in `docs/benchmarks/.private-map.json` (gitignored), never here.

---

## §0 — OPSEC (non-negotiable)
`pigeon` ships under an alias and goes public. Some test substrate is on
real-identity / collaboration repos. Naming any of them in a public artifact
bridges the alias to the author permanently.

1. Private test repos are **local substrate only**.
2. Public artifacts (`docs/benchmarks/`, blog, README) carry **numbers + generalized
   descriptions only** — e.g. "Repo A: ~N-kLOC R/Python research codebase." Never
   names, orgs, URLs, codenames, or anything that reads back to the author.
3. The name↔label mapping is `docs/benchmarks/.private-map.json` — **gitignored**.
4. Before any public commit or blog draft, run `docs/benchmarks/check-opsec.sh`
   (greps `docs/benchmarks/` for identity strings; must return nothing). It's also a
   pre-publication checklist item (§8).

### Internal vs. public benchmark — different jobs
- **Internal decision benchmark** (private repos): tells *you* whether pigeon
  works; use it to lock the kill-N and make go/no-go.
- **Public credibility benchmark** (blog/README): a number on undisclosed repos
  isn't reproducible — to a skeptic it's no better than 92.8%. The **published
  number must come from at least one public, reproducible repo** run under the
  alias (pigeon's own repo, the `pigeon-demo` repo, or a permissive-license OSS
  project). The private three are anonymized *supporting* data points, never the
  headline.

---

## §0.5 — Lock the kill-N FIRST
A kill-criterion chosen after seeing results is a rationalization. Fill and commit
`docs/benchmarks/KILL-CRITERION.md` — cold — before the first run.

---

## §1 — Design
- **Three benchmarks, never pooled.** Three domains → three honest per-repo
  numbers. "Helps on B, not A" is a *finding*, not noise to average. A single
  blended "pigeon saves X%" is forbidden.
- **Two arms, one variable.** The only difference is pigeon's coordination:
  - **WITH:** agents via `pigeon coordinate` (handoffs, shared context).
  - **WITHOUT:** the same CLIs, same models, naked on the same tasks.
- Everything else identical — same repo SHA, byte-for-byte same task text to both
  arms, same models, same starting context. Can't hold a variable constant? Log
  it as a caveat; don't let it bias the number.

## §2 — Per-repo setup
For each repo: **pin an exact commit SHA** (branches move; a malformed/ moving ref
like `v-.1.0` is not reproducible). Record SHA + private metadata (LOC, language,
test count) in `.private-map.json` under the public label. Run both arms against a
clean checkout of that SHA in a throwaway worktree.

## §3 — Task selection (make-or-break)
Per repo, pick **3–5 tasks that genuinely require carrying context across a
boundary** — multi-step / multi-file work where step 2 needs what step 1
established ("implement X in A, update callers in B, fix tests in C"). **A task one
agent finishes cold has no coordination to measure** — both arms tie and pigeon
looks worthless on a task that never exercised it. Write **one** prompt spec per
task; feed identical text to both arms (a richer WITH prompt measures prompt
quality, not coordination).

## §4 — Metrics (per task, per arm)
tokens (WITH: `pigeon metrics --by-model`; WITHOUT: the CLIs' own accounting) ·
wall-clock · success (a **pre-declared objective check** per task) · handoffs
(WITH only) · merge conflicts · human interventions (count every step-in).

## §5 — Run procedure (per task)
1. Fresh worktree at the pinned SHA → **WITHOUT** arm → record → reset.
2. Fresh worktree at the same SHA → **WITH** arm → record.
3. Prefer fresh worktrees with no shared learning; otherwise alternate arm order
   across tasks to avoid you learning the task between arms.

## §6 — Recording
- `docs/benchmarks/.private-map.json` (**gitignored**): label → repo, SHA, metadata.
- `docs/benchmarks/results/<label>.json` (committable, anonymized): per-task/per-arm
  metrics under the public label only (schema: `results.template.json`).
- Raw run logs stay local (`docs/benchmarks/results/raw/`, gitignored) — they contain
  repo paths and code.

## §7 — Analysis
Per repo: WITH vs WITHOUT deltas on tokens / success / interventions — **one honest
number per repo, no pooling.** State nulls plainly: "Repo A: tokens −X%,
interventions N→M; Repo B: no measurable difference." A real 60% with a caveat
beats a synthetic 92.8%. The README number is the **public** repo's; the private
three are anonymized supporting points.

## §8 — Pre-publication checklist
- [ ] `KILL-CRITERION.md` filled and committed (§0.5)
- [ ] `docs/benchmarks/check-opsec.sh` returns nothing (§0)
- [ ] `.private-map.json` gitignored and not staged
- [ ] Public number is from a reproducible public repo, not the private three
- [ ] Each published delta carries its baseline + caveats (no bare percentages)
- [ ] Every repo's SHA confirmed and pinned (no malformed/moving refs)
