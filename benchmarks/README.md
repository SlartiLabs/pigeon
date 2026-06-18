# Benchmarks — the launch evidence (Tier A)

The public launch is gated by **evidence, not polish**. This directory produces
the real, reproducible number that replaces the synthetic ~92.8% — even if it's
lower. A real 60% beats a synthetic 92.8%.

## Read these first
- **[`PROTOCOL.md`](PROTOCOL.md)** — the method: with-vs-without coordination, two
  arms / one variable, three repos never pooled, opsec rules, pre-publication
  checklist. **Read §0 (opsec) and §0.5 (lock the kill-N) before touching a repo.**
- **[`KILL-CRITERION.md`](KILL-CRITERION.md)** — fill and commit this **cold**,
  before the first run. A criterion chosen after seeing results is a rationalization.

## The two jobs (don't conflate them)
- **Internal decision benchmark** — private test repos; tells *you* whether pigeon
  works; drives go/no-go. Reported only as anonymized supporting data.
- **Public credibility benchmark** — the **headline number must come from a public,
  reproducible repo** (pigeon's own repo, the `pigeon-demo` repo, or a permissive
  OSS project). A number on undisclosed repos is, to a skeptic, no better than 92.8%.

## Task selection is make-or-break
Benchmark only tasks that **require carrying context across a boundary** (multi-file
/ multi-step, where step 2 needs step 1). A task one agent finishes cold has no
coordination to measure — both arms tie and pigeon looks worthless on a task that
never exercised it. See `PROTOCOL.md` §3 and `tasks/README.md`.

## Files
- `PROTOCOL.md`, `KILL-CRITERION.md` — method + kill-N (committed).
- `PUBLIC-REPO-CRITERIA.md` — rubric for picking the ~3 public repos that produce
  the reproducible headline number.
- `tasks/` — per-repo task specs (committed, public-label only).
- `results/<label>.json` — anonymized per-task/per-arm metrics (committed);
  `results.template.json` is the schema. Raw logs live in `results/raw/` (gitignored).
- `.private-map.json` — name↔label map (**gitignored**); copy from
  `.private-map.template.json`. `check-opsec.sh` greps committed `benchmarks/` for
  the private strings it lists and must pass before any public commit.

**Status:** protocol + opsec machinery in place. The with/without runs, the locked
kill-N, and the public headline number are the remaining launch-gating work — real
agent runs, done before any blog post.
