# Task t1 — single-source the version + drift guard

**Why this task:** real work from this repo's history (the README pinned "0.4"
while pyproject was 0.5.0); known shape, verifiable acceptance.

**Prompt (identical for both arms):**
> The README pins a version string that drifts from `pyproject.toml`. Make
> pyproject the single source of truth and add a test that fails on any
> README/pyproject version mismatch. Keep the suite green.

**Clean start:** check out `<base_sha>` into a fresh worktree (a SHA *before*
`64de4d7`, where the drift is live).

**Acceptance (success = true only if all hold):**
- No hardcoded `(X.Y)` version in the README Status line.
- A test exists that fails on a deliberately mismatched README.
- `pytest -q` green; `ruff check` clean.

**Arms:**
- *with-pigeon:* run via `pigeon coordinate` (an edit task + a verify task that
  receives the diff); record from the run manifest + token ledger.
- *without-pigeon:* run the same agent CLI directly on the same checkout; record
  tokens/time by hand or the CLI's own telemetry.

Record both to `results/t1-version-drift-<arm>.json`.
