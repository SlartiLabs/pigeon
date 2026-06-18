"""Guard against version drift across the project's sources of truth.

pyproject.toml is canonical; src/pigeon/__init__.py carries a fallback only for
vendored checkouts; the README must not pin a version that can drift.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _pyproject_version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text("utf-8"))
    return data["project"]["version"]


def test_init_fallback_matches_pyproject() -> None:
    pv = _pyproject_version()
    init = (ROOT / "src" / "pigeon" / "__init__.py").read_text("utf-8")
    m = re.search(r'__version__\s*=\s*"([^"]+)"', init)
    assert m, "no __version__ fallback found in src/pigeon/__init__.py"
    assert m.group(1) == pv, (
        f"version drift: __init__ fallback {m.group(1)!r} != pyproject {pv!r} — "
        "bump both, or let importlib.metadata be the only source"
    )


def test_readme_status_pins_no_version() -> None:
    """A hardcoded version in the README Status line is the recurring drift bug;
    a deliberately mismatched '(0.4)'-style pin must fail this test."""
    readme = (ROOT / "README.md").read_text("utf-8")
    status = [ln for ln in readme.splitlines() if ln.startswith("**Status:**")]
    assert status, "README has no '**Status:**' line"
    assert not re.search(r"\(\s*\d+\.\d+", status[0]), (
        f"README Status line pins a version (will drift from pyproject): {status[0]!r}"
    )
