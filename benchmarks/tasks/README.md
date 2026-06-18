# Benchmark tasks

One spec per task; the **identical prompt text** feeds both arms (WITH = via
`pigeon coordinate`, WITHOUT = the same CLIs naked). See `../PROTOCOL.md` §3–§5.

## The bar: a task must REQUIRE cross-boundary context
Pick multi-file / multi-step work where step 2 needs what step 1 established. A
task one agent finishes cold has nothing for coordination to do — both arms tie
and pigeon looks worthless on a task that never exercised it. That is a measurement
error, not a finding.

**Good (coordination-requiring) shape:**
> Implement X in module A, update its callers in module B, and fix the affected
> tests in C — where B and C can't be done correctly without what A changed.

**Bad (single-boundary, finishes cold):** a one-file rename, a docstring fix, a
version-string edit. These are useful work but measure nothing here.

## Per task, pre-declare (before either arm runs)
- the exact prompt (byte-identical to both arms),
- the pinned base SHA (a clean throwaway worktree per arm),
- an **objective acceptance check** (tests pass / file contains X / behaviour Y),
- where results are recorded: `../results/<label>-<arm>.json`.

## Naming
Use the public label only (`repoA-task1.md`, …). Never a private repo/org/codename
in a committed file — `../check-opsec.sh` enforces this.
