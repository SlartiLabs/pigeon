# Stage 1a — cost single-shot -> powered estimate: result

**Anchor:** limitations-closing plan, Stage 1a. A precision upgrade on Experiment
1's "token-neutral to mildly negative" cost claim: rerun at N=8 per arm so the
paired difference gets an interval, not a point. Substrate: cookiecutter's
`shoutcase` filter task at the Exp-1 base SHA (`c88fbe9`), naive (single claude
call) vs pigeon (a two-hop `coordinate`: architect scopes, implementer edits),
same model (sonnet), same task.

## Result (N=8 per arm, both arms 8/8 success)

The reported unit is the **standardized token**: the `o200k_base` recount of the
wire (argv prompt + stdout body), applied uniformly to both arms, so the number is
tokenizer-independent and carries no pricing-snapshot dependency. Measured USD is
retained as corroboration only.

| Arm | mean tokens/task | bootstrap 95% CI | (measured USD) |
|---|---|---|---|
| naive (single call) | **548 tok** | [534, 563] | $0.166 |
| pigeon (coordinate) | **1238 tok** | [1207, 1278] | $0.670 |

**Difference (pigeon − naive): +690 tok / task, 95% CI [+653, +732]** — the interval
is **entirely positive and excludes zero**. pigeon spends ~**2.3×** the naive single
call's wire volume on this task. The measured USD agrees in direction (+$0.50/task);
it is a larger ratio there only because provider billing includes tool-read/cache
context that is off-wire and so uncounted in the standardized token — which is
exactly why the tokenizer-independent recount is the honest cross-arm unit.

## Reading

The plan framed the decisive question precisely: *"the thing that would matter is
if the CI on the difference turns out to include a comfortably negative region,
i.e. a real saving."* **It does not.** The powered estimate confirms and sharpens
the headline: pigeon's coordination is a measurable **cost**, not a saving. The
overhead is the architect scoping hop, the handoff, and the per-spawn scaffold —
all pure additions over a single call for a self-contained task.

This is *more* clearly negative than Exp-1's "token-neutral to mildly negative,"
for a design reason worth stating: this pigeon arm carries an explicit architect
hop, so the coordination overhead is larger than a bare single-agent pigeon path
would show. The **direction** (coordination is a cost) is the robust, expected
result, and it is exactly consistent with the carrier-comms thesis — cost is a
null; pigeon's value is *capability* (cross-model handoff, carrying irreducible
reasoning), never token savings.

## Honest scope

- **One task, one repo.** The plan's full 1a is cookiecutter *and* marshmallow;
  this ran the cookiecutter `shoutcase` task only (marshmallow not rerun — its
  Exp-1 grader/harness were not committed). The single-substrate interval is
  real but narrower in external validity than the two-repo matrix.
- **Simple task.** `shoutcase` is a 2-file feature; coordination overhead is
  proportionally largest on small tasks. On a large multi-file task the ratio
  would compress (fixed overhead amortized), though the sign would not flip —
  nothing here suggests a saving at any size.
- **Structural success check.** Success is "filter defined + registered by
  default," not the full held-out functional grader + pytest regression of
  Exp-1; both arms hit 8/8, so success does not confound the cost comparison.

Ledger: `stage1a-cost-N8.csv` (the `canon_total` column is the standardized token).
Figure: `../figures/fig_s1a_cost.png`. Runner: `../instruments/run-stage1a-cost.sh`;
the ledger's `canon_total` is rebuilt from a run's persisted transcripts by
`../instruments/build-stage1a-token-ledger.py`.

_Commits are the operator's._
