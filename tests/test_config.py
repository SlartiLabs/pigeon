"""Tests for config hardening: D3 (vector guard), S2 (env_allowlist default),
U7 (schema validation at load)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pigeon.config import default_config, load_config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mk_repo(tmp_path: Path, yaml_text: str = "") -> Path:
    """Create a minimal legacy-contract repo with an optional config snippet."""
    actx = tmp_path / ".agentctx"
    actx.mkdir()
    if yaml_text:
        (actx / "config.yaml").write_text(yaml_text, encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# D3: vector enabled → fail at load, not mid-run
# ---------------------------------------------------------------------------

def test_vector_enabled_fails_at_load(tmp_path: Path) -> None:
    """Enabling vector raises a clear ValueError at load time (DD D3)."""
    root = _mk_repo(tmp_path, "retrieval:\n  vector:\n    enabled: true\n")
    with pytest.raises(ValueError, match="not yet implemented"):
        load_config(root)


def test_vector_disabled_loads_fine(tmp_path: Path) -> None:
    """Default (disabled) vector config loads without error."""
    root = _mk_repo(tmp_path)
    cfg = load_config(root)  # should not raise
    assert cfg.retrieval_cfg["vector"]["enabled"] is False


def test_vector_enabled_message_is_actionable(tmp_path: Path) -> None:
    """The vector-disabled error message tells the operator what to fix."""
    root = _mk_repo(tmp_path, "retrieval:\n  vector:\n    enabled: true\n")
    with pytest.raises(ValueError, match=r"retrieval\.vector\.enabled"):
        load_config(root)


# ---------------------------------------------------------------------------
# S2: env_allowlist defaults to ON (empty list, not None)
# ---------------------------------------------------------------------------

def test_env_allowlist_default_is_list() -> None:
    """env_allowlist defaults to a list (strict mode ON) not None (DD S2)."""
    al = default_config()["coordinate"]["env_allowlist"]
    assert isinstance(al, list), (
        f"env_allowlist should default to a list, got {type(al).__name__}"
    )


def test_env_allowlist_null_opts_out(tmp_path: Path) -> None:
    """Setting env_allowlist: null in config.yaml restores full inheritance."""
    root = _mk_repo(tmp_path, "coordinate:\n  env_allowlist: null\n")
    cfg = load_config(root)
    assert cfg.coordinate_cfg["env_allowlist"] is None


def test_env_allowlist_list_merges_correctly(tmp_path: Path) -> None:
    """An explicit allowlist list in config.yaml is preserved after merge."""
    root = _mk_repo(tmp_path,
                    "coordinate:\n  env_allowlist:\n    - ANTHROPIC_API_KEY\n")
    cfg = load_config(root)
    assert cfg.coordinate_cfg["env_allowlist"] == ["ANTHROPIC_API_KEY"]


def test_env_allowlist_rejects_non_string_elements(tmp_path: Path) -> None:
    """A non-string allowlist element fails at load (advisory nit) — it would
    otherwise be silently ignored during env matching."""
    root = _mk_repo(tmp_path, "coordinate:\n  env_allowlist:\n    - PATH\n    - 123\n")
    with pytest.raises(ValueError, match="only strings"):
        load_config(root)


# ---------------------------------------------------------------------------
# U7: schema validation at load
# ---------------------------------------------------------------------------

def test_max_depth_string_fails_at_load(tmp_path: Path) -> None:
    """A mistyped max_depth raises at load with a useful message (DD U7)."""
    root = _mk_repo(tmp_path,
                    "coordinate:\n  safety:\n    max_depth: 'one'\n")
    with pytest.raises(ValueError, match="max_depth"):
        load_config(root)


def test_max_depth_zero_fails_at_load(tmp_path: Path) -> None:
    """max_depth < 1 raises at load."""
    root = _mk_repo(tmp_path,
                    "coordinate:\n  safety:\n    max_depth: 0\n")
    with pytest.raises(ValueError, match="max_depth"):
        load_config(root)


def test_parallel_limit_string_fails_at_load(tmp_path: Path) -> None:
    """A mistyped parallel_limit raises at load (DD U7)."""
    root = _mk_repo(tmp_path, "coordinate:\n  parallel_limit: 'fast'\n")
    with pytest.raises(ValueError, match="parallel_limit"):
        load_config(root)


def test_allow_s3_string_fails_at_load(tmp_path: Path) -> None:
    """A YAML string for allow_s3 raises at load (DD U7)."""
    root = _mk_repo(tmp_path, "resolve:\n  allow_s3: 'yes'\n")
    with pytest.raises(ValueError, match="allow_s3"):
        load_config(root)


def test_env_allowlist_string_fails_at_load(tmp_path: Path) -> None:
    """env_allowlist must be a list or null; a bare string raises (DD U7)."""
    root = _mk_repo(tmp_path, "coordinate:\n  env_allowlist: 'PATH'\n")
    with pytest.raises(ValueError, match="env_allowlist"):
        load_config(root)


def test_bool_as_int_fails_for_bool_field(tmp_path: Path) -> None:
    """YAML integer 1 for a bool field raises (bool != int in schema) (DD U7)."""
    root = _mk_repo(tmp_path, "resolve:\n  allow_outside_root: 1\n")
    with pytest.raises(ValueError, match="allow_outside_root"):
        load_config(root)


def test_valid_config_loads_cleanly(tmp_path: Path) -> None:
    """A well-formed config loads without error (schema regression guard)."""
    root = _mk_repo(tmp_path, (
        "coordinate:\n"
        "  parallel_limit: 2\n"
        "  env_allowlist:\n"
        "    - ANTHROPIC_API_KEY\n"
        "  safety:\n"
        "    max_depth: 2\n"
    ))
    cfg = load_config(root)
    assert cfg.coordinate_cfg["parallel_limit"] == 2
    assert cfg.coordinate_cfg["env_allowlist"] == ["ANTHROPIC_API_KEY"]
    assert cfg.coordinate_cfg["safety"]["max_depth"] == 2
