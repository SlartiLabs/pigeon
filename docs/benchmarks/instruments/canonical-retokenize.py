#!/usr/bin/env python3
"""Canonical single-tokenizer recount of archived coordinate transcripts.

Stage 0 / Stage 2 instrument (limitations-closing plan). Every measured trial
now archives the raw child transcript and a pointer to it in the run manifest
(``tasks.<id>.telemetry.transcript``). This tool walks those pointers and
recounts the archived text under one model-agnostic tokenizer
(:data:`pigeon.tokens.CANONICAL_ENCODING` = ``o200k_base``), applied uniformly
regardless of which model produced the text. That is the rigorous version of
"recompute this later": a tokenizer-independent volume comparison, decoupled
from both provider pricing and provider-specific segmentation.

USD stays the primary comparable metric (see Stage 0 of the plan); this second
number becomes *required* only for cross-model stages (Stage 2 onward), where a
dollar figure would otherwise confound genuine efficiency differences with two
companies' independent pricing decisions. Within-model runs need only USD.

Usage
-----
    python canonical-retokenize.py RUN.json [RUN.json ...]        # explicit manifests
    python canonical-retokenize.py --runs-dir .pigeon/coordinate/runs
    python canonical-retokenize.py RUN.json --csv out.csv --json out.json

Each transcript is a tee of one child run: the first line is ``$ <argv>`` (the
prompt is embedded in the argv), the body is the child's completion, and a final
``# exit N`` marker closes it. We report three canonical counts per hop so the
prompt/completion split is preserved, not flattened:

    canon_prompt      - tokens in the ``$ argv`` line (carries the prompt)
    canon_completion  - tokens in the completion body (between argv and exit)
    canon_total       - prompt + completion

alongside the archived native ``total_tokens`` and ``cost_usd`` for provenance.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

# Run from anywhere: make the package importable without an install step.
_SRC = Path(__file__).resolve().parents[3] / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from pigeon.tokens import CANONICAL_ENCODING, canonical_token_count  # noqa: E402


def _split_transcript(text: str) -> tuple[str, str]:
    """Return (prompt_line, completion_body) from an archived transcript.

    The harness writes a leading ``$ <argv>`` line and a trailing ``# exit N``
    marker; everything between is the child's own output. Missing markers are
    tolerated (older/partial logs) — a whole-body fallback still recounts
    uniformly, which is the property that matters."""
    lines = text.splitlines()
    prompt = ""
    if lines and lines[0].startswith("$ "):
        prompt = lines[0][2:]
        lines = lines[1:]
    if lines and lines[-1].startswith("# exit"):
        lines = lines[:-1]
    return prompt, "\n".join(lines)


def _iter_manifests(paths: list[Path], runs_dir: Path | None):
    for p in paths:
        yield p
    if runs_dir:
        yield from sorted(runs_dir.glob("*.json"))


def recount_run(manifest: Path, root: Path) -> list[dict]:
    """Recount every archived transcript referenced by one run manifest."""
    data = json.loads(manifest.read_text(encoding="utf-8"))
    rows: list[dict] = []
    for task_id, t in (data.get("tasks") or {}).items():
        telem = t.get("telemetry") or {}
        # Prefer the task-level transcript pointer (recorded for EVERY hop,
        # including untelemetered ones like agy/Gemini); fall back to the one
        # nested under telemetry for older manifests.
        pointer = t.get("transcript") or telem.get("transcript")
        if not pointer:
            continue
        tpath = (root / pointer) if not Path(pointer).is_absolute() else Path(pointer)
        if not tpath.is_file():
            rows.append({"run_id": data.get("run_id"), "task": task_id,
                         "runner": t.get("runner"), "model": t.get("model", ""),
                         "transcript": pointer, "status": "MISSING",
                         "native_total_tokens": telem.get("total_tokens"),
                         "cost_usd": telem.get("cost_usd", telem.get("total_cost_usd", "")),
                         "canon_prompt": "", "canon_completion": "", "canon_total": ""})
            continue
        prompt, body = _split_transcript(tpath.read_text(encoding="utf-8", errors="replace"))
        cp = canonical_token_count(prompt) if prompt else 0
        cc = canonical_token_count(body) if body else 0
        rows.append({"run_id": data.get("run_id"), "task": task_id,
                     "runner": t.get("runner"), "model": t.get("model", ""),
                     "transcript": pointer, "status": "ok",
                     "native_total_tokens": telem.get("total_tokens"),
                     "cost_usd": telem.get("cost_usd", telem.get("total_cost_usd", "")),
                     "canon_prompt": cp, "canon_completion": cc, "canon_total": cp + cc})
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifests", nargs="*", type=Path, help="run manifest JSON files")
    ap.add_argument("--runs-dir", type=Path, default=None,
                    help="also recount every *.json manifest in this directory")
    ap.add_argument("--root", type=Path, default=Path.cwd(),
                    help="repo root the transcript pointers are relative to (default cwd)")
    ap.add_argument("--csv", type=Path, default=None, help="write rows to this CSV")
    ap.add_argument("--json", dest="json_out", type=Path, default=None,
                    help="write rows to this JSON")
    args = ap.parse_args(argv)

    if not args.manifests and not args.runs_dir:
        ap.error("give at least one manifest or --runs-dir")

    rows: list[dict] = []
    for m in _iter_manifests(args.manifests, args.runs_dir):
        rows.extend(recount_run(m, args.root))

    cols = ["run_id", "task", "runner", "model", "status", "native_total_tokens",
            "cost_usd", "canon_prompt", "canon_completion", "canon_total", "transcript"]
    w = csv.DictWriter(sys.stdout, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)
    print(f"# encoding={CANONICAL_ENCODING} rows={len(rows)} "
          f"canon_total_sum={sum(r['canon_total'] for r in rows if r['canon_total'] != '')}",
          file=sys.stderr)

    if args.csv:
        with args.csv.open("w", newline="", encoding="utf-8") as fh:
            cw = csv.DictWriter(fh, fieldnames=cols)
            cw.writeheader()
            cw.writerows(rows)
    if args.json_out:
        args.json_out.write_text(
            json.dumps({"encoding": CANONICAL_ENCODING, "rows": rows}, indent=2) + "\n",
            encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
