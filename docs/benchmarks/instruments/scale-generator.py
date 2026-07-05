#!/usr/bin/env python3
"""Stage 3 substrate generator — scale as a confound for retrieval.

Limitations-closing plan, Stage 3. This is a DIFFERENT experiment from the
deep-real substrate (Stage 5): it tests whether the `pack`'s retrieval step
still *surfaces* a trace that would be recoverable if seen, as the corpus grows;
it does NOT test whether a trace stays unrecoverable when fully seen.

Design: take the already-validated natural convention from Experiment 5
(`ledger/account.py`'s `to_legacy`/`from_legacy` wire keys `acct/cents/ts`, known
to recover 12/12 at small scale) and bury it, byte-for-byte, inside a synthetic
repository at increasing file counts. The underlying semantic recoverability is
held constant (the canonical file is identical at every scale); the ONLY thing
that varies is how much plausibly-relevant decoy material the retriever must rank
`account.py` against. Decoy files are serialization/ledger/partner-export modules
that share the task's vocabulary (serialize, wire, Account, clearing partner,
dict) so the ranking has a real discrimination problem — but NONE of them carries
the `acct/cents/ts` convention, so retrieval that surfaces a decoy instead of the
canonical file genuinely loses the trace.

A generated repo is a ready-to-run pigeon substrate: canonical `ledger/account.py`,
`TASK.md`, held-out `accept.py`, and a `pointers-only-pack.tasks.json` whose
implementer relies on `pack:true` retrieval (NOT an explicit account.py pointer),
so the retrieval step is the thing under test. A `SCALE-MANIFEST.json` records
the seed, file count, canonical path, and the leak-check result.

Usage
-----
    python scale-generator.py --out /tmp/scale-200 --files 200 --seed 1
    for n in 10 50 200 1000 5000; do
      python scale-generator.py --out /tmp/scale-$n --files $n --seed 1
    done

Then, per the plan's two-stage N: screen each point at N=3-4 pointers-only,
locate where recovery degrades, confirm N=8 on the decisive point(s) only.
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP5 = HERE.parent / "substrates" / "exp5-natural"

# The convention's own wire keys — no decoy may contain these as string
# literals, or the trace leaks and the ranking problem is fake.
CANON_KEYS = ("acct", "cents", "ts")
CANON_MARKERS = ("to_legacy", "from_legacy")

# Decoy building blocks: plausible-but-different serialization domains. Each
# shares retrieval vocabulary with the task (serialize / wire / dict / partner /
# Account-like entities) yet uses DIFFERENT keys, so none reveals acct/cents/ts.
_ENTITIES = [
    ("Invoice", ["number", "total_usd", "issued_at", "customer"]),
    ("Shipment", ["tracking", "weight_kg", "dispatched", "carrier"]),
    ("Subscription", ["plan", "seats", "renews_on", "owner"]),
    ("Payout", ["reference", "gross_minor", "settled_on", "beneficiary"]),
    ("Invoice", ["inv_no", "amount", "created_at", "party"]),
    ("Ledger", ["book", "running_total", "as_of", "unit"]),
    ("Transfer", ["handle", "value", "posted", "counterparty"]),
    ("Statement", ["period", "closing", "generated", "holder"]),
]
_MODULES = ["export", "serialize", "wire", "sync", "codec", "adapter",
            "partner", "feed", "transform", "marshal"]
_PKGS = ["ledger", "billing", "sync", "exports", "partners", "clearing",
         "reporting", "integrations", "vendors", "settlement"]

_DECOY_TEMPLATE = '''\
"""{pkg}.{mod}_{idx} — {entity} serialization for the {pkg} partner feed.

This module serializes a {entity} to a JSON-ready dict for an external partner
integration. It is one of several partner export boundaries in this codebase.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class {entity}:
    """A {pkg} {entity_lower}. Serialized to the partner wire format below."""

    {f0}: str
    {f1}: int
    {f2}: datetime
    {f3}: str | None = None

    def to_partner(self) -> dict:
        """Serialize this {entity_lower} for the external partner importer."""
        d = {{
            "{f0}": self.{f0},
            "{f1}": self.{f1},
            "{f2}": self.{f2}.isoformat(),
        }}
        if self.{f3} is not None:
            d["{f3}"] = self.{f3}
        return d

    @classmethod
    def from_partner(cls, w: dict) -> "{entity}":
        return cls(
            {f0}=w["{f0}"],
            {f1}=int(w["{f1}"]),
            {f2}=datetime.fromisoformat(w["{f2}"]),
            {f3}=w.get("{f3}"),
        )
'''


def _make_decoy(rng: random.Random, idx: int) -> tuple[str, str]:
    """Return (relative_path, source) for one plausibly-relevant decoy module."""
    entity, fields = rng.choice(_ENTITIES)
    pkg = rng.choice(_PKGS)
    mod = rng.choice(_MODULES)
    f0, f1, f2, f3 = fields
    src = _DECOY_TEMPLATE.format(
        pkg=pkg, mod=mod, idx=idx, entity=entity, entity_lower=entity.lower(),
        f0=f0, f1=f1, f2=f2, f3=f3)
    rel = f"{pkg}/{mod}_{idx}.py"
    return rel, src


# Files in the retrievable tree that legitimately reference the convention: the
# canonical module itself, and the visible tests (which exercise the legacy
# boundary as the in-code cue but never spell out the acct/cents/ts keys). The
# held-out grader is NOT here — it lives OUTSIDE the retrievable tree entirely.
def _leak_check(repo: Path, canonical_rel: str) -> dict:
    """Assert the wire convention's *keys* appear in no decoy file.

    Scans every decoy (everything in the retrievable tree except the canonical
    module, package ``__init__`` files, and the visible ``tests/``). A decoy
    leaks only if it carries the quoted wire keys — sharing generic vocabulary
    (serialize, partner, wire) is the whole point and is not a leak."""
    exempt = {canonical_rel}
    offenders: list[str] = []
    for p in sorted(repo.rglob("*.py")):
        rel = str(p.relative_to(repo))
        if rel in exempt or p.name == "__init__.py" or rel.startswith("tests/"):
            continue
        text = p.read_text(encoding="utf-8")
        if any(f'"{k}"' in text for k in CANON_KEYS) or any(m in text for m in CANON_MARKERS):
            offenders.append(rel)
    return {"clean": not offenders, "offenders": offenders}


_PACK_TASKS = {
    "sid": "scale-null",
    "_note": ("Stage 3 pointers-only arm. The implementer relies on pack:true "
              "retrieval over the whole synthetic repo (NO explicit account.py "
              "pointer), so the retrieval-ranking step is the thing under test: "
              "does pack still surface ledger/account.py's legacy boundary when "
              "it must rank against the decoy corpus? Held-out grader: accept.py."),
    "tasks": [
        {
            "id": "architect",
            "runner": "sonnet",
            "doing": ("You are the architect. The task (TASK.md) is to add a v2 "
                      "sync wire format (Account.to_wire / from_wire) to "
                      "ledger/account.py, consistent with how this codebase "
                      "already serializes an Account for the external clearing "
                      "partner. Do NOT edit any file. Hand off to the implementer "
                      "with a brief pointer only: tell them to implement to_wire "
                      "and from_wire in ledger/account.py per TASK.md. Do NOT "
                      "write any wire-format details (key names, types) into your "
                      "handoff."),
            "pack": True,
        },
        {
            "id": "to_wire",
            "runner": "sonnet",
            "needs": ["architect"],
            "pack": True,
            "doing": ("Implement Account.to_wire(self) -> dict and "
                      "Account.from_wire(cls, w) -> Account in ledger/account.py "
                      "per TASK.md, serializing an Account for the external "
                      "clearing partner consistently with how this codebase "
                      "already serializes an Account for that partner. Use the "
                      "packed context bundle to find the existing partner "
                      "serialization boundary. Do NOT run shell commands or "
                      "tests — just edit ledger/account.py, then record your "
                      "handoff."),
        },
    ],
}


_RUN_MD = """\
# Stage 3 scale substrate (seed={seed}, {files} files)

Layout — the held-out grader is OUTSIDE the retrievable tree, by construction:

    repo/                       <- agent-visible, pack-retrievable substrate
      ledger/account.py         <- canonical convention (identical to Exp 5)
      TASK.md, tests/           <- task + visible tests (the in-code cue)
      <decoys...>               <- {decoys} plausibly-relevant modules
    accept.py                   <- HELD-OUT grader (never inside repo/)
    pointers-only-pack.tasks.json
    SCALE-MANIFEST.json

Run (per scale point):

    cd repo && git init -q && pigeon init && pigeon refresh
    pigeon coordinate ../pointers-only-pack.tasks.json --skip-permissions --telemetry --budget-usd 3
    PYTHONPATH=repo python accept.py     # held-out check, from the parent dir

Two-stage N (plan): screen each point at N=3-4 pointers-only, locate where
recovery degrades, confirm N=8 on the decisive point(s) only. Watch for a sharp
retrieval-ranking cutoff, not only gradual decay. Kill-criterion: if recovery
holds at 12/12-equivalent to the largest tested scale, report "not tested large
enough to find the failure point", NOT "scale does not matter".
"""


def generate(out: Path, files: int, seed: int) -> dict:
    if files < 2:
        raise SystemExit("need --files >= 2 (1 canonical + >=1 decoy)")
    if out.exists():
        shutil.rmtree(out)
    repo = out / "repo"                      # the retrievable, agent-visible tree
    repo.mkdir(parents=True)
    rng = random.Random(seed)

    # 1. Canonical convention, byte-for-byte from Exp 5 (recoverability constant).
    (repo / "ledger").mkdir(parents=True, exist_ok=True)
    canonical_rel = "ledger/account.py"
    shutil.copyfile(EXP5 / "account.py", repo / canonical_rel)
    (repo / "ledger" / "__init__.py").write_text("", encoding="utf-8")
    # Task + visible tests are IN the tree; the grader is held OUT (sibling).
    shutil.copyfile(EXP5 / "TASK.md", repo / "TASK.md")
    (repo / "tests").mkdir(exist_ok=True)
    shutil.copyfile(EXP5 / "test_account.py", repo / "tests" / "test_account.py")
    shutil.copyfile(EXP5 / "accept.py", out / "accept.py")   # OUTSIDE repo/

    # 2. Decoys — plausibly-relevant, none carrying the convention.
    seen: set[str] = {canonical_rel}
    n_decoys = files - 1
    made = 0
    i = 0
    while made < n_decoys:
        rel, src = _make_decoy(rng, i)
        i += 1
        if rel in seen:
            continue
        seen.add(rel)
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if not (p.parent / "__init__.py").exists():
            (p.parent / "__init__.py").write_text("", encoding="utf-8")
        p.write_text(src, encoding="utf-8")
        made += 1

    # 3. Ready-to-run pointers-only (pack) tasks file + run notes (siblings).
    (out / "pointers-only-pack.tasks.json").write_text(
        json.dumps(_PACK_TASKS, indent=2) + "\n", encoding="utf-8")
    (out / "RUN.md").write_text(
        _RUN_MD.format(seed=seed, files=files, decoys=made), encoding="utf-8")

    # 4. Integrity: canonical unchanged, convention isolated, grader held out.
    canon_ok = (repo / canonical_rel).read_text(encoding="utf-8") == \
        (EXP5 / "account.py").read_text(encoding="utf-8")
    leak = _leak_check(repo, canonical_rel)
    grader_held_out = not (repo / "accept.py").exists() and (out / "accept.py").exists()
    py_total = sum(1 for _ in repo.rglob("*.py"))

    manifest = {
        "stage": 3,
        "seed": seed,
        "requested_files": files,
        "repo_dir": "repo",
        "canonical_path": canonical_rel,
        "canonical_byte_identical_to_exp5": canon_ok,
        "decoy_modules": made,
        "python_files_in_repo": py_total,
        "leak_check": leak,
        "grader_held_out_of_repo": grader_held_out,
        "arms": ["pointers-only-pack.tasks.json"],
        "grader": "accept.py (sibling of repo/, never retrievable)",
        "note": ("Recoverability held constant (canonical file identical at every "
                 "scale). Vary only decoy count. Screen N=3-4, confirm N=8 on the "
                 "decisive point(s). If recovery holds to the largest tested scale, "
                 "the honest conclusion is 'not tested large enough', not 'scale "
                 "does not matter'."),
    }
    (out / "SCALE-MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True, help="output repo directory")
    ap.add_argument("--files", type=int, required=True,
                    help="total .py file count (1 canonical + files-1 decoys)")
    ap.add_argument("--seed", type=int, default=1, help="RNG seed (reproducible)")
    args = ap.parse_args(argv)
    m = generate(args.out, args.files, args.seed)
    print(json.dumps(m, indent=2))
    if not m["canonical_byte_identical_to_exp5"]:
        print("FAIL: canonical file drifted from Exp 5 source", flush=True)
        return 2
    if not m["leak_check"]["clean"]:
        print(f"FAIL: convention leaked into decoys: {m['leak_check']['offenders']}")
        return 3
    if not m["grader_held_out_of_repo"]:
        print("FAIL: grader is not held out of the retrievable tree")
        return 4
    print(f"\nOK: {m['python_files_in_repo']} .py files in repo/, convention isolated "
          f"to {m['canonical_path']}, grader held out, ready at scale {args.files}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
