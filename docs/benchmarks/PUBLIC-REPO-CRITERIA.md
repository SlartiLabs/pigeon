# Public-repo selection criteria (the reproducible headline substrate)

The launch headline number must come from **public, reproducible** repos — a
skeptic has to be able to re-run it (a number on undisclosed private repos is no
better than the synthetic 92.8%). Pick **~3** public repos by this rubric; the 3
private repos remain internal-only, anonymized supporting data (see `PROTOCOL.md`).

## MUST-HAVE gates (a candidate that fails ANY is out)
1. **Permissive OSS license** (MIT / Apache-2.0 / BSD) — so we can run it and
   publish results. No-license or copyleft-with-doubt → skip.
2. **Public, pinnable** — on a public forge, runnable at an exact commit SHA.
3. **Real, passing test suite at the pinned SHA** — "success" must be an objective
   check (`pytest`/equivalent green). No tests → no objective success signal → out.
4. **Cheap, hermetic local run** — installs and tests with **no secrets, no cloud,
   no GPU, no large dataset download**. Both arms must run in a throwaway worktree.
5. **Multi-module structure that admits cross-boundary tasks** (PROTOCOL §3) — work
   where step 2 needs step 1. A single-file library has no coordination to measure.
6. **Agent-friendly language** — Python is first choice (matches the CLIs' strength
   and pigeon's ecosystem); at most one polyglot pick for diversity.
7. **Identity-neutral** — a third-party OSS project, **never** a repo tied to the
   author or the alias. The public benchmark must not bridge back to you.

## TIE-BREAKERS (prefer, among gate-passers)
- **Mid size:** ~3k–40k LOC, a handful of modules. Big enough to coordinate, small
  enough for an agent to hold and for runs to stay cheap.
- **Findable real work:** open issues (good-first-issue), TODOs, or a clearly
  missing feature — so the benchmark task is genuine, not contrived.
- **Fast suite** (≲2 min) → clean success signal + affordable reruns.
- **Legible domain** — correctness you can judge, so acceptance is objective.
- **Low churn** at the pinned SHA (stable to re-run later).

## ANTI-CRITERIA (reject)
- Needs API keys / cloud / GPU / big data to test (you'd measure env-wrangling, not
  coordination).
- Flaky or very slow tests (unreliable success signal).
- Trivial / single-file (both arms tie → pigeon looks worthless).
- Mega-repo (>~100k LOC) — agents can't load it; setup dominates.
- The build itself is the hard part (measures the build, not coordination).
- Restrictive/absent license; anything identity-linked to you.

## DIVERSITY across the ~3 (don't pick three of a kind)
Vary domain + size (and maybe one language). Three numbers, **never pooled** —
"helps on a CLI, not on a library" is a finding. A workable spread:
- one **CLI tool**, one **library/SDK**, one **small service/app**; or
- `pigeon-demo` (controlled, fully reproducible) + **2 external OSS** projects.
Use **at least 1–2 EXTERNAL** OSS repos so the result doesn't read as self-selected.

## TASK ARCHETYPES (pre-declare one coordination-requiring task per repo)
Pick a task that spans a boundary, with a pre-declared objective acceptance check:
- **feature-across-layers** — implement X in module A, update its callers in B, fix
  the affected tests in C.
- **cross-cutting bugfix** — a bug that spans parse → validate → report.
- **interface refactor** — change a signature used in N call sites + fix tests.
Feed the **identical prompt** to both arms (a richer WITH prompt measures prompt
quality, not coordination).

## Per-candidate verification checklist (do BEFORE committing a choice)
- [ ] License is permissive (record which)
- [ ] Clones + installs offline; suite green at SHA `<pin it>`
- [ ] ≥ a few modules; one concrete cross-boundary task identified + its acceptance check
- [ ] No secrets / cloud / GPU / large data needed
- [ ] Not identity-linked to the author/alias
- [ ] SHA pinned and recorded (in `.private-map.json` if you want metadata; the repo
      itself is public so its name MAY appear in committed results)

## Credibility / ethics
Run at a pinned SHA; attribute the project fairly; don't imply endorsement. Publish
methodology + raw `results/` so anyone can reproduce. We benchmark a snapshot, not
the maintainers.
