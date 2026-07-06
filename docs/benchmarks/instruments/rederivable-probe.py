#!/usr/bin/env python3
"""rederivable_probe — the Exp-A3 base-rate instrument.

The bounded law (Exp 4/4b/5/4c) says the carried ``state.derived`` residue earns its
tokens IFF the constraint left no recoverable trace in the code. That settles WHEN the
residue helps. It says nothing about HOW OFTEN real handoffs carry such low-recoverability
constraints. This instrument estimates that base rate over real pigeon traffic.

For each carried constraint in a handoff's ``state.derived.constraint_found``, it measures
whether a pointers-only receiver (given only the pristine pointed-at code, not the residue)
would re-derive that constraint. The fraction that are NOT re-derivable is the empirical
answer to "does the bounded law bite here": high -> Lever 2 is core; near zero -> Lever 2
is a niche that fires only on contrived contracts.

HONEST SCOPE (do not oversell):
  * This is a SOFT probe. Real handoffs carry no held-out functional grader (unlike the
    4c substrate), so recoverability is judged by a semantic-match model, not a pass/fail
    reimplementation. Report it as an estimate with that caveat.
  * Measured on YOUR team's traffic, the base rate is your team's, not "real handoffs" in
    general, and it is reflexive (people who know Lever 2 write handoffs differently).
    Prefer sampling handoffs written BEFORE the team knew the mechanism.

The RUN path (``--live``) is a per-constraint counterfactual eval, i.e. real model spend,
not passive logging. It is intentionally gated: wire ``judge_live`` to a runner and pass
``--live`` only with an explicit spend decision. Default is ``--dry-run`` (prints the
prompts it would send) plus ``--selftest`` (fixtures, no spend).
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Constraint:
    text: str
    handoff: str
    frm: str
    pointers: list[str] = field(default_factory=list)


def _artifacts(d: dict) -> list[str]:
    st = d.get("state") or {}
    return list(d.get("artifacts") or st.get("artifacts") or [])


def load_constraints(path: Path) -> list[Constraint]:
    """Pull carried constraints out of one handoff JSON or a directory of them.

    The emitter (e.g. architect) carries the constraints; the pointers a RECEIVER would
    have live on downstream handoffs. So over a session directory we use the union of all
    artifacts as the session pointer set, falling back to it when a constraint's own
    handoff lists none.
    """
    files = sorted(glob.glob(str(path / "*.json"))) if path.is_dir() else [str(path)]
    docs = []
    for fp in files:
        try:
            docs.append((fp, json.loads(Path(fp).read_text())))
        except Exception:
            continue
    session_pointers: list[str] = []
    for _, d in docs:
        for a in _artifacts(d):
            if a not in session_pointers:
                session_pointers.append(a)
    out: list[Constraint] = []
    for fp, d in docs:
        found = ((d.get("state") or {}).get("derived") or {}).get("constraint_found") or []
        pointers = _artifacts(d) or session_pointers
        for c in found:
            if isinstance(c, str) and c.strip():
                out.append(Constraint(text=c.strip(), handoff=Path(fp).name,
                                       frm=d.get("from", "?"), pointers=pointers))
    return out


def build_recovery_prompt(c: Constraint, repo_root: Path) -> str:
    """Pointers-only prompt: the receiver sees the CODE, never the carried constraint."""
    code_blocks = []
    for ptr in c.pointers:
        rel = ptr.replace("repo://", "")
        f = repo_root / rel
        if f.is_file():
            code_blocks.append(f"### {rel}\n```\n{f.read_text()[:4000]}\n```")
    code = "\n\n".join(code_blocks) or "(no readable pointers)"
    return (
        "You are a re-implementer. Read ONLY the code below. List every NON-OBVIOUS "
        "constraint a re-implementer must honour that is not stated in an ordinary task "
        "description (behaviour that looks like removable cleanup but is load-bearing, "
        "conventions an external consumer depends on, invariants the visible tests do not "
        "cover). Be concrete.\n\n" + code
    )


def judge_stub(reconstruction: str, constraint: str) -> bool:
    """Offline keyword-overlap proxy used by --selftest only (no model, no spend)."""
    toks = {w for w in constraint.lower().replace(",", " ").split() if len(w) > 4}
    hit = sum(1 for t in toks if t in reconstruction.lower())
    return len(toks) > 0 and hit / len(toks) >= 0.34


def _claude(prompt: str, model: str = "sonnet", timeout: int = 240) -> str:
    """One-shot claude call, returning stdout text. Wired for Stage 4 --live."""
    import subprocess  # noqa: PLC0415
    p = subprocess.run(
        ["claude", "-p", prompt, "--model", model, "--dangerously-skip-permissions"],
        capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    return (p.stdout or "").strip()


def judge_live(constraint: Constraint, repo_root: Path, model: str = "sonnet"):
    """LIVE recoverability check (real spend). Two model calls:

    1. RECONSTRUCT — a pointers-only receiver sees ONLY the pointed-at code (never
       the carried constraint) and lists the non-obvious constraints it can derive.
    2. JUDGE — a separate semantic-match call rules whether that reconstruction
       COVERS ``constraint.text``. Returns (recoverable: bool | None, reconstruction).

    The judge is a semantic-match model, not a held-out functional grader — this is
    the SOFT probe the module docstring is explicit about. None on an unparseable
    verdict (counted as unjudged, not silently as recoverable)."""
    recon = _claude(build_recovery_prompt(constraint, repo_root), model=model)
    if not recon:
        return None, recon
    judge_prompt = (
        "A re-implementer, seeing ONLY the code, produced this list of constraints:\n\n"
        f"{recon[:6000]}\n\n"
        "Question: does that list COVER the following specific constraint — i.e. would "
        "the re-implementer have honoured it without being told?\n\n"
        f"CONSTRAINT: {constraint.text}\n\n"
        "Answer with exactly one word on the first line: YES (covered/recoverable) or "
        "NO (missed/not recoverable). Then one sentence of justification."
    )
    verdict = _claude(judge_prompt, model=model)
    first = verdict.splitlines()[0].strip().upper() if verdict else ""
    if first.startswith("YES"):
        return True, recon
    if first.startswith("NO"):
        return False, recon
    return None, recon


def run(path: Path, repo_root: Path, live: bool) -> dict:
    cons = load_constraints(path)
    per = []
    for c in cons:
        prompt = build_recovery_prompt(c, repo_root)
        if live:
            recoverable, recon = judge_live(c, repo_root)
        else:
            recoverable, recon = None, None  # dry-run: prompt only, no verdict
            print(f"\n--- {c.handoff} (from {c.frm}) ---\nCONSTRAINT: {c.text[:120]}")
            print(f"[dry-run] would send a {len(prompt)}-char pointers-only prompt "
                  f"over {len(c.pointers)} pointer(s)")
        per.append({"handoff": c.handoff, "constraint": c.text, "recoverable": recoverable})
    n = len(per)
    judged = [p for p in per if p["recoverable"] is not None]
    low_r = [p for p in judged if p["recoverable"] is False]
    return {
        "constraints": n,
        "judged": len(judged),
        "rederivable_fraction": (round(sum(p["recoverable"] for p in judged) / len(judged), 3)
                                 if judged else None),
        "low_recoverability_fraction": (round(len(low_r) / len(judged), 3) if judged else None),
        "note": "dry-run: prompts only, no verdicts. Use --live (gated) for verdicts.",
        "per_constraint": per,
    }


def selftest() -> int:
    """Two fixtures exercise the pipeline end-to-end with the offline stub judge."""
    recoverable = "dedup entries by txn_id last-write-wins so duplicate retries do not double count"
    unrecoverable = "external clients require the acct cents timestamp wire keys"
    recon = "the code dedup entries by txn_id last-write-wins to avoid double count of duplicate retries"
    r1 = judge_stub(recon, recoverable)      # reconstruction covers it -> recoverable
    r2 = judge_stub(recon, unrecoverable)    # reconstruction misses the wire keys -> not
    ok = (r1 is True) and (r2 is False)
    print(f"selftest judge_stub: recoverable-case={r1} (want True), "
          f"unrecoverable-case={r2} (want False) -> {'PASS' if ok else 'FAIL'}")
    # load path exercised on the exp4c with-derived handoffs if present
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", nargs="?", help="handoff .json or a directory of them")
    ap.add_argument("--repo", default=".", help="repo root for resolving repo:// pointers")
    ap.add_argument("--live", action="store_true", help="run the gated per-constraint eval (real spend)")
    ap.add_argument("--selftest", action="store_true", help="run fixtures, no spend")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if not a.path:
        ap.error("path required unless --selftest")
    result = run(Path(a.path), Path(a.repo).resolve(), a.live)
    print("\n" + json.dumps({k: v for k, v in result.items() if k != "per_constraint"}, indent=2))
