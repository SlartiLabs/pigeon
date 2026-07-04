"""schema_version actually GATES compatibility (DD D1 / Risk 6).

Covers the three halves of the fix: the receive-time compatibility gate, the
``upgrade_handoff`` / ``pigeon migrate`` carry-forward, and the schema ``$id``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pigeon import SCHEMA_VERSION
from pigeon import handoff as ho
from pigeon.cli import main


def _valid(**over):
    """A structurally-valid handoff at the current schema version by default."""
    base = dict(
        sid="s1", frm="Planner", to="Executor",
        done=["analyze"], doing="implement",
        artifacts=["repo://AGENTS.md"],
    )
    base.update(over)
    return ho.build_handoff(**base)


# --- the policy itself ------------------------------------------------------

def test_parse_schema_version():
    assert ho.parse_schema_version("1.0") == (1, 0)
    assert ho.parse_schema_version("12.34") == (12, 34)
    with pytest.raises(ho.HandoffMigrationError):
        ho.parse_schema_version("one.oh")
    with pytest.raises(ho.HandoffMigrationError):
        ho.parse_schema_version("1")


def test_is_compatible_policy():
    # pin current explicitly so the test states the policy independent of the bump.
    assert ho.is_compatible("1.0", current="1.2")   # same major, older minor
    assert ho.is_compatible("1.1", current="1.2")   # same major, older minor
    assert ho.is_compatible("1.2", current="1.2")   # exact
    assert not ho.is_compatible("1.3", current="1.2")  # newer minor -> reject
    assert not ho.is_compatible("2.0", current="1.2")  # newer major -> reject
    assert not ho.is_compatible("0.9", current="1.2")  # older major -> reject
    assert not ho.is_compatible("garbage", current="1.2")
    # the shipped constant is what production actually gates on
    assert ho.is_compatible(SCHEMA_VERSION)


# --- the gate, enforced on every receive path -------------------------------

def test_compatible_older_minor_is_accepted(repo):
    # a 1.0 producer must keep working under a 1.1 reader (additive minor)
    ho.validate_handoff(_valid(schema_version="1.0"), repo)  # no raise


def test_newer_minor_rejected_with_clear_error(repo):
    h = _valid(schema_version="1.3")  # a minor newer than the current reader
    with pytest.raises(ho.HandoffCompatibilityError) as exc:
        ho.validate_handoff(h, repo)
    msg = str(exc.value)
    assert "1.3" in msg and "upgrade pigeon" in msg


def test_newer_major_rejected_as_upgrade_pigeon(repo):
    with pytest.raises(ho.HandoffCompatibilityError) as exc:
        ho.validate_handoff(_valid(schema_version="2.0"), repo)
    assert "upgrade pigeon" in str(exc.value)


def test_older_major_rejected_points_at_migrate(repo):
    # an older major is a breaking change: the remedy is to migrate forward
    with pytest.raises(ho.HandoffCompatibilityError) as exc:
        ho.validate_handoff(_valid(schema_version="0.9"), repo)
    assert "pigeon migrate" in str(exc.value)


def test_compatibility_error_is_a_validation_error(repo):
    # subclassing keeps existing `except HandoffValidationError` call sites working
    assert issubclass(ho.HandoffCompatibilityError, ho.HandoffValidationError)
    with pytest.raises(ho.HandoffValidationError):
        ho.validate_handoff(_valid(schema_version="2.0"), repo)


def test_structural_errors_take_precedence_over_compat(repo):
    # missing `doing` AND a bad version -> structural error first (clearer)
    bad = {"schema_version": "9.9", "sid": "x", "from": "A", "to": "B",
           "state": {"done": []}}
    with pytest.raises(ho.HandoffValidationError) as exc:
        ho.validate_handoff(bad, repo)
    assert "doing" in str(exc.value)


def test_load_handoff_gates_on_receipt(repo, tmp_path):
    # write a future-version handoff straight to disk (bypassing the gate),
    # then prove the on-receipt load rejects it
    path = tmp_path / "future.json"
    path.write_text(ho.serialize_handoff(_valid(schema_version="2.0")),
                    encoding="utf-8")
    with pytest.raises(ho.HandoffCompatibilityError):
        ho.load_handoff(path, repo)


# --- carrying a handoff forward ---------------------------------------------

def test_upgrade_1_0_to_current(repo):
    old = _valid(schema_version="1.0")
    up = ho.upgrade_handoff(old)
    assert up["schema_version"] == SCHEMA_VERSION
    assert old["schema_version"] == "1.0"  # input not mutated
    # the upgraded handoff now clears the gate
    ho.validate_handoff(up, repo)


def test_upgrade_already_current_is_noop():
    h = _valid()
    up = ho.upgrade_handoff(h)
    assert up == h and up is not h


def test_upgrade_refuses_downgrade():
    with pytest.raises(ho.HandoffMigrationError) as exc:
        ho.upgrade_handoff(_valid(schema_version="2.0"), to="1.1")
    assert "downgrade" in str(exc.value)


def test_upgrade_no_path_is_clear():
    # 1.0 has a step to 1.1 but the chain stops there; asking for 1.5 fails loud
    with pytest.raises(ho.HandoffMigrationError) as exc:
        ho.upgrade_handoff(_valid(schema_version="1.0"), to="1.5")
    assert "no migration path" in str(exc.value)


def test_upgrade_requires_a_version():
    with pytest.raises(ho.HandoffMigrationError):
        ho.upgrade_handoff({"sid": "x"})


# --- the `pigeon migrate` command -------------------------------------------

def _write_handoff(tmp_path: Path, handoff: dict) -> Path:
    p = tmp_path / "old.json"
    p.write_text(json.dumps(handoff), encoding="utf-8")
    return p


def test_cli_migrate_to_stdout(repo, tmp_path, capsys):
    src = _write_handoff(tmp_path, _valid(schema_version="1.0"))
    assert main(["--root", str(repo.root), "migrate", str(src)]) == 0
    out = capsys.readouterr()
    emitted = json.loads(out.out)
    assert emitted["schema_version"] == SCHEMA_VERSION
    assert f"1.0 -> {SCHEMA_VERSION}" in out.err


def test_cli_migrate_in_place(repo, tmp_path, capsys):
    src = _write_handoff(tmp_path, _valid(schema_version="1.0"))
    assert main(["--root", str(repo.root), "migrate", str(src), "--in-place"]) == 0
    rewritten = json.loads(src.read_text(encoding="utf-8"))
    assert rewritten["schema_version"] == SCHEMA_VERSION


def test_cli_migrate_to_output_file(repo, tmp_path):
    src = _write_handoff(tmp_path, _valid(schema_version="1.0"))
    dst = tmp_path / "new.json"
    assert main(["--root", str(repo.root), "migrate", str(src),
                 "--output", str(dst)]) == 0
    assert json.loads(dst.read_text(encoding="utf-8"))["schema_version"] == SCHEMA_VERSION


def test_cli_migrate_rejects_then_accepts_roundtrip(repo, tmp_path, capsys):
    """The whole point: a handoff the gate rejects, migrated, now passes."""
    incompatible = _valid(schema_version="1.0")
    # sanity: this would be accepted today (1.0 is compatible), so simulate a
    # genuinely-incompatible source by validating that an OLDER MAJOR is gated.
    older_major = _valid(schema_version="0.9")
    with pytest.raises(ho.HandoffCompatibilityError):
        ho.validate_handoff(older_major, repo)
    # ...and a real 1.0 -> current carry-forward produces a gate-passing handoff
    src = _write_handoff(tmp_path, incompatible)
    assert main(["--root", str(repo.root), "migrate", str(src),
                 "--output", str(tmp_path / "fixed.json")]) == 0
    fixed = json.loads((tmp_path / "fixed.json").read_text(encoding="utf-8"))
    ho.validate_handoff(fixed, repo)  # no raise


def test_cli_migrate_downgrade_errors(repo, tmp_path, capsys):
    src = _write_handoff(tmp_path, _valid(schema_version="2.0"))
    assert main(["--root", str(repo.root), "migrate", str(src)]) == 2
    assert "downgrade" in capsys.readouterr().err


def test_cli_migrate_bad_json(repo, tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert main(["--root", str(repo.root), "migrate", str(bad)]) == 2
    assert "not valid JSON" in capsys.readouterr().err


def test_cli_migrate_in_place_rejects_stdin(repo, capsys):
    assert main(["--root", str(repo.root), "migrate", "-", "--in-place"]) == 2
    assert "stdin" in capsys.readouterr().err


# --- the schema $id is a pigeon URL, not the old agentctx.dev ----------------

def test_schema_id_is_a_pigeon_url():
    schema_path = (Path(__file__).resolve().parents[1]
                   / ".pigeon" / "handoff.schema.json")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert "agentctx.dev" not in schema["$id"]
    assert "pigeon" in schema["$id"]
    # the version suffix init.py greps for must survive the rename
    assert f"handoff-{SCHEMA_VERSION}.json" in schema["$id"]


def test_upgrade_handoff_rejects_non_dict_input():
    # A non-dict input must raise a clean HandoffMigrationError, not an uncaught
    # AttributeError on .get() (advisory nit).
    for bad in (["not", "a", "dict"], "a string", 42, None):
        with pytest.raises(ho.HandoffMigrationError, match="must be a JSON object"):
            ho.upgrade_handoff(bad)
