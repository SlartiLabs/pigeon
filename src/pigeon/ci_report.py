"""ci_report: normalize CI tool results into one structured, fail-closed verdict.

The self-remediation loop's reader is an agent, not a human — prose logs are a
lossy channel between "CI knows what's wrong" and "the fixer acts on it". This
emits ``.pigeon/ci/verdict.json``: a typed pass/fail/error per check plus failure
records the fixer consumes by pointer.

FAIL-CLOSED is the load-bearing property: a crashed, missing, or unparseable
check is ``error`` — never a silent ``pass``. A self-fix loop that reads a
crashed check as green is the catastrophic failure this exists to prevent.

Repair hints are opportunistic: pyrefly codes map to useful hints, an arbitrary
pytest assertion does not, so the ``human_gate_required`` flag and any hint are
per-failure and never assumed universal.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"


def parse_pytest_junit(path: Path | None) -> dict[str, Any]:
    """Parse a pytest ``--junitxml`` report. Fail-closed: a missing or
    unparseable report is ``error``, not ``pass``."""
    if path is None or not Path(path).exists():
        return {"status": "error", "failures": [],
                "note": f"no pytest junit report at {path}"}
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        return {"status": "error", "failures": [],
                "note": f"unparseable pytest junit: {exc}"}
    failures: list[dict[str, Any]] = []
    for ts in root.iter("testsuite"):
        for tc in ts.iter("testcase"):
            node = tc.find("failure")
            if node is None:
                node = tc.find("error")
            if node is None:
                continue
            tid = f"{tc.get('classname', '')}::{tc.get('name', '')}".strip(":")
            failures.append({
                "id": tid or "pytest:unknown",
                "check": "pytest",
                "location": {"test": tid},
                "category": "test",
                "message": (node.get("message") or "")[:300],
                "human_gate_required": False,
            })
    return {"status": "pass" if not failures else "fail", "failures": failures}


_PYREFLY_ERR = re.compile(r"^\s*ERROR\s+(.+)$", re.MULTILINE)


def parse_pyrefly(exit_code: int | None, output: str) -> dict[str, Any]:
    """Parse pyrefly text output. Fail-closed: a non-zero exit with no parseable
    errors is ``error`` (something broke that we can't attribute)."""
    if exit_code is None:
        return {"status": "error", "failures": [], "note": "pyrefly did not run"}
    if exit_code == 0:
        return {"status": "pass", "failures": []}
    errs = _PYREFLY_ERR.findall(output or "")
    failures = [{
        "id": f"pyrefly:{i}", "check": "pyrefly", "location": {},
        "category": "type", "message": e.strip()[:300],
        "human_gate_required": False,
    } for i, e in enumerate(errs)]
    # nonzero exit but nothing parsed -> error (crash), not a clean fail
    return {"status": "fail" if failures else "error", "failures": failures}


def build_verdict(commit: str, checks: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Combine per-check results into one verdict.

    Status precedence is ``error`` > ``fail`` > ``pass`` (a single errored check
    makes the whole verdict ``error`` — fail-closed at the aggregate too)."""
    statuses = {name: c.get("status", "error") for name, c in checks.items()}
    failures = [f for c in checks.values() for f in c.get("failures", [])]
    if not statuses or any(s == "error" for s in statuses.values()):
        overall = "error"
    elif any(s == "fail" for s in statuses.values()):
        overall = "fail"
    else:
        overall = "pass"
    return {
        "schema_version": SCHEMA_VERSION,
        "commit": commit,
        "status": overall,
        "checks": statuses,
        "failures": failures,
    }


def can_auto_merge(verdict: dict[str, Any]) -> bool:
    """The invariant the loop must honor: only a fully-green verdict with NO
    human-gated failure may auto-merge."""
    if verdict.get("status") != "pass":
        return False
    return not any(f.get("human_gate_required") for f in verdict.get("failures", []))


def write_verdict(verdict: dict[str, Any], out_dir: Path) -> Path:
    path = Path(out_dir) / "ci" / "verdict.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(verdict, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    """CI entrypoint: read tool artifacts, write verdict.json, exit fail-closed
    (0 only when the verdict is ``pass``)."""
    import argparse

    ap = argparse.ArgumentParser(prog="pigeon-ci-report")
    ap.add_argument("--commit", default="")
    ap.add_argument("--junit", type=Path, default=None,
                    help="pytest --junitxml report path")
    ap.add_argument("--pyrefly-exit", type=int, default=None)
    ap.add_argument("--pyrefly-log", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=Path(".pigeon"))
    args = ap.parse_args(argv)

    pyrefly_out = ""
    if args.pyrefly_log and args.pyrefly_log.exists():
        pyrefly_out = args.pyrefly_log.read_text(encoding="utf-8", errors="replace")
    checks = {
        "pytest": parse_pytest_junit(args.junit),
        "pyrefly": parse_pyrefly(args.pyrefly_exit, pyrefly_out),
    }
    verdict = build_verdict(args.commit, checks)
    path = write_verdict(verdict, args.out)
    print(f"ci-report: {verdict['status']} -> {path}")
    return 0 if verdict["status"] == "pass" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
