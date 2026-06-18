# DESIGN — free-runner qualification harness (`pigeon probe`)

**Status:** PROPOSED → building (after adopt P1 merges; both touch cli.py).
2026-06-18. Workstream 3. Motivated by *observed* failure: this session
`nv-mixtral` 404'd, `nv-nano` produced no hand-back, `nv-mistral-large` was too
slow for a design task, and `oc-nemotron` ignored its readonly constraint. Free
provider rosters churn, so trust must be **measured, not hardcoded** (Pillar-4
philosophy: empirical, offline, advisory).

## Goal
`pigeon probe` runs a fixed, trivial probe through each configured runner under a
short timeout, classifies the result, and emits a ranked report + a JSON the user
(or a crew author) reads to pick reliable runners. It never edits repo source.

## Design
- **CLI:** `pigeon probe [--free-only] [--timeout S=60] [--json]`. Default probes
  every `coordinate.runners` entry; `--free-only` skips claude/agy/opus (the trusted
  trio) and probes the oc-*/nv-* free pool.
- **Probe prompt** (the standard task): `Reply with exactly this line and nothing
  else: PIGEON_OK` — a combined connectivity + instruction-following check, cheap.
- **Execution:** fill each runner template with the probe prompt (reuse
  `coordinate._build_command`/`_fill`-style substitution; NOT the handoff protocol —
  a probe is a bare prompt), spawn under `timeout S` with the existing per-runner
  env handling (XDG_DATA_HOME for opencode). Capture exit code, elapsed, stdout tail.
- **Classification** per runner:
  | verdict | condition |
  |---|---|
  | `ok` | exit 0, output contains `PIGEON_OK`, elapsed ≤ soft budget |
  | `slow` | ok but elapsed > soft budget (default 30s) |
  | `protocol_fail` | exit 0 but output lacks `PIGEON_OK` (responded, didn't follow) |
  | `dead` | non-zero exit / spawn error / timeout (e.g. 404, hang) |
- **Output:** a human table à la `agents.format_agents` (runner · verdict · elapsed ·
  note) sorted worst-first, plus `.pigeon/probe.json` (gitignored): one record per
  runner `{runner, model, verdict, exit_code, elapsed_s, note, probed_at}`. A footer
  reminds that rosters churn — re-run to refresh.
- **Module:** `src/pigeon/probe.py` (`build_probe_cmd`, `run_probe`, `classify`,
  `format_probe`, `write_probe`); CLI `cmd_probe` in cli.py; MCP exposure deferred.

## Invariants
- Read-only w.r.t. the repo (only writes `.pigeon/probe.json`). Probing is always
  safe to run. No change to `coordinate` or the runner templates. `.pigeon/probe.json`
  added to .gitignore (derivable scratch).

## Tests
- `classify` matrix: ok / slow / protocol_fail (exit 0 no token) / dead (nonzero) /
  dead (timeout) — pure, no subprocess.
- `build_probe_cmd`: a `{prompt}` template gets the probe substituted; a `{model}`
  template without a model is left to the runner (probe doesn't resolve pools).
- Integration with a fake runner (python -c): a runner that echoes PIGEON_OK → ok;
  one that prints junk → protocol_fail; one that exits 1 → dead; one that sleeps past
  the timeout → dead. Use a tiny `--timeout` so the test is fast.
- `write_probe` never writes outside `.pigeon/`; secrets/env never recorded.

## Out of scope
Auto-editing the runner pool from results (advisory only, Pillar-4); scheduling
periodic probes; feeding probe verdicts into coordinate round-robin.
