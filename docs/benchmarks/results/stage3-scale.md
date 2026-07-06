# Stage 3 — scale as a confound for retrieval: result

**Anchor:** limitations-closing plan, Stage 3. Tests whether the `pack`'s
retrieval step still *surfaces* the Exp-5 convention as the corpus grows — a
different question from Stage 5 (which tests whether a trace stays unrecoverable
when fully seen). Recoverability is held constant (the canonical `account.py` is
byte-identical at every scale via `scale-generator.py`); only decoy count varies.

## Result (sonnet + pack, N=3 screen per point)

| Repo size | recovery (grader pass) | pack surfaced `account.py` | mean cost |
|---|---|---|---|
| 10 | 3/3 | 3/3 | $0.71 |
| 50 | 3/3 | 3/3 | $0.86 |
| 200 | 3/3 | 3/3 | $0.74 |
| 1000 | 3/3 | 3/3 | $0.79 |
| **5000** | **2/3** | **3/3** | $0.82 |

## Reading: retrieval did NOT degrade in the tested range

**The thing under test — whether `pack` ranks the buried convention into the
context bundle — held at 3/3 at every scale, including 5000 files.** ripgrep
retrieval surfaced `ledger/account.py` in all 15 trials. So there is **no
retrieval-ranking cutoff** in the tested range.

The single recovery miss at 5000 (2/3) is **not** a retrieval failure: `pack`
surfaced the trace in that trial too (`packed_account=1`), so the agent had the
legacy boundary in context and still produced a non-matching `to_wire`. That is
an implementation / context-dilution miss (a larger bundle competing for
attention) or N=3 variance — a different failure mode from the retrieval-ranking
one this stage targets.

## Verdict (kill-criterion, per plan)

Per the plan's locked kill-criterion: *"if recovery holds at 12/12-equivalent all
the way to the largest tested scale, the honest conclusion is 'not tested large
enough to find the failure point', not 'scale does not matter'."* Retrieval held
to 5000 files, so: **no retrieval-ranking failure point was found in the tested
range (≤5000 files); the honest conclusion is "not tested large enough," not
"scale does not confound retrieval."** The tested substrate is semi-synthetic and
ripgrep-based; a vector-retrieval or a genuinely adversarial decoy set could
break sooner.

## Honest limitations

- **N=3 screen tier.** The 5000-point 2/3 would need confirm-tier N (8+) to
  separate context-dilution from variance; but since retrieval itself held 3/3,
  the decisive metric for *this* stage did not degrade regardless.
- **Semi-synthetic decoys.** The generator's decoys share vocabulary but are
  templated; a hand-crafted near-duplicate of `account.py` would be a harder
  ranking test.
- **ripgrep retrieval, pack_top_k=5.** A different retriever or a smaller top-k
  would move the failure point.

Ledgers: `stage3/scale-{10,50,200,1000,5000}-N3.csv`. Figure:
`../figures/fig_s3_scale.png`. Generator: `../instruments/scale-generator.py`;
runner: `../instruments/run-stage3-scale.sh`.

_Commits are the operator's._
