# Design records

Forward-looking design docs for pigeon, most produced by dogfooding pigeon's own
`coordinate` layer (a multi-model army drafts in parallel, independent reviewers gate, a
final authority reconciles). They live here, out of the gitignored `.pigeon/coordinate/`
runtime, so they survive a `git clean` and stay reviewable in history. The
"Authority: verdict (...)" headers record which model rendered each verdict; they are
proposals that were acted on, not commitments.

Status key: **shipped** (the feature is in a release), **archival** (the work it planned is
done; kept for provenance), **proposed** (not built).

## Roadmap and army

| Doc | What it is | Status |
|-----|------------|--------|
| [`PLAN.md`](PLAN.md) | The roadmap: four pillars, the local learning loop, a phased build (A-F), success metrics, and a "not building" list. | shipped through v0.5.x |
| [`DESIGN.md`](DESIGN.md) | Pillar 1 in full: first-class multi-model ("army") support (`model:` / `model_pool:`, seeded round-robin, cross-wave `receives:` injection, throttling). | shipped |

## `pigeon adopt` ([`adopt/`](adopt/), shipped v0.5.0)

| Doc | What it is |
|-----|------------|
| [`adopt/design.md`](adopt/design.md) | The design: discover / catalog / import existing subagents, skills, and MCP servers behind an allow-list. |
| [`adopt/p1-contract.md`](adopt/p1-contract.md) | The authoritative P1 contract (plus memory-page typing). |
| [`adopt/buildplan.md`](adopt/buildplan.md) | The build plan that finished it. |

## Carrier-comms study ([`carrier-comms/`](carrier-comms/), complete)

Design records behind the two-lever study. The **result** lives in
[`../../benchmarks/`](../../benchmarks/) (report, manuscript, reproducible statistics).

| Doc | What it is |
|-----|------------|
| [`carrier-comms/brief.md`](carrier-comms/brief.md) | The design brief (pointer doc for cross-model critique). |
| [`carrier-comms/buildplan.md`](carrier-comms/buildplan.md) | The executable two-lever build plan. |
| [`carrier-comms/exp4b-design.md`](carrier-comms/exp4b-design.md) | Experiment 4b revised design (red-teamed; referenced by the report). |

## Standalone feature designs

| Doc | What it is | Status |
|-----|------------|--------|
| [`free-runner-harness.md`](free-runner-harness.md) | `pigeon probe`: free-runner qualification. | shipped |
| [`timeout-salvage.md`](timeout-salvage.md) | Progress-aware timeouts + salvage-aware scheduling. | shipped |
| [`review-artifact.md`](review-artifact.md) | The review-artifact convention (Phase D). | proposed |
| [`measuring-recall.md`](measuring-recall.md) | Measuring the learning loop (Phase E gate, Reasoning Bank). | proposed |

## Provenance artifacts

- [`panel-reviews/`](panel-reviews/) the cross-model critiques that gated the carrier-comms brief.
- [`examples/`](examples/) example task specs.
- [`remediation/`](remediation/) DD remediation-loop coordinate files.
