#!/usr/bin/env python3
"""Rebuild the committed Stage 1a ledger from a re-run's persisted data.

Reads the raw arm/trial rows the cost harness left in <run>/results.csv and adds
a `canon_total` column: each trial's wire volume recounted under the canonical
tokenizer (pigeon.tokens.canonical_token_count = o200k_base), on the SAME basis
as canonical-retokenize.py and fig_s2/fig_s5 — canon(prompt sent) + canon(full
stdout body), summed across a task's model calls.

    naive  : one `claude -p` call. prompt = the shared TASK; body = out.json
             (the raw JSON claude emitted). canon_total = canon(TASK)+canon(body).
    pigeon : a 2-hop coordinate chain. Each persisted hop log is `$ <argv>` +
             body + `# exit N`; recount every log the same way and sum.

Writes docs/benchmarks/results/stage1a-cost-N<N>.csv (canon_total is the reported
"standardized token"; cost_usd is retained as rate-snapshot-dependent
corroboration) so the figure is reproducible from committed data — the raw
transcripts live outside the repo.

    python3 build-stage1a-token-ledger.py <RUN_DIR>   # e.g. ~/stage1a-tokens
"""
from __future__ import annotations

import csv
import glob
import pathlib
import re
import sys

_SRC = pathlib.Path(__file__).resolve().parents[3] / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
from pigeon.tokens import CANONICAL_ENCODING, canonical_token_count as ctok  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
SCRIPT = HERE / "run-stage1a-cost.sh"
RESULTS = HERE.parent / "results"


def _task_prompt() -> str:
    """The exact TASK string both arms are given (single source: the harness)."""
    m = re.search(r"TASK='(.*?)'", SCRIPT.read_text(), re.S)
    if not m:
        raise SystemExit("could not extract TASK from run-stage1a-cost.sh")
    return m.group(1)


def _recount_log(path: pathlib.Path) -> int:
    """canon(prompt argv line) + canon(body), matching canonical-retokenize.py."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    prompt = lines[0][2:] if lines and lines[0].startswith("$ ") else ""
    body = "\n".join(l for l in lines[1:] if not l.startswith("# exit"))
    return ctok(prompt) + ctok(body)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        raise SystemExit(__doc__)
    run = pathlib.Path(argv[1]).expanduser()
    res = run / "results.csv"
    if not res.is_file():
        raise SystemExit(f"no results.csv under {run}")
    task_tok = ctok(_task_prompt())

    rows = list(csv.DictReader(res.read_text().splitlines()))
    out = []
    for r in rows:
        arm, trial = r["arm"], r["trial"]
        rdir = run / f"{arm}-{trial}"
        if arm == "naive":
            oj = rdir / "out.json"
            canon = task_tok + ctok(oj.read_text(encoding="utf-8", errors="replace")) if oj.is_file() else ""
        else:  # pigeon: sum the persisted hop logs
            logs = sorted(glob.glob(str(rdir / ".pigeon" / "coordinate" / "logs" / "*.log")))
            canon = sum(_recount_log(pathlib.Path(l)) for l in logs) if logs else ""
        out.append([arm, trial, r["success"], r["cost_usd"], canon, r["turns"], r["wall_s"]])
        print(f"[{arm} t{trial}] success={r['success']} cost_usd={r['cost_usd']} canon_total={canon}")

    N = max(int(r["trial"]) for r in rows)
    dst = RESULTS / f"stage1a-cost-N{N}.csv"
    with dst.open("w", newline="") as fh:
        fh.write("# Stage 1a cost clean ledger (cookiecutter shoutcase, naive vs pigeon), N="
                 f"{N}/arm, sonnet.\n")
        fh.write(f"# canon_total = {CANONICAL_ENCODING} recount of argv prompt + stdout body "
                 "(standardized token, the reported unit);\n")
        fh.write("# cost_usd is the measured provider spend, retained as rate-snapshot-dependent corroboration.\n")
        w = csv.writer(fh)
        w.writerow(["arm", "trial", "success", "cost_usd", "canon_total", "turns", "wall_s"])
        w.writerows(out)
    for arm in ("naive", "pigeon"):
        xs = [o[4] for o in out if o[0] == arm and o[4] != ""]
        if xs:
            print(f"{arm}: mean canon_total = {sum(xs)/len(xs):.0f}  n={len(xs)}")
    print("wrote", dst)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
