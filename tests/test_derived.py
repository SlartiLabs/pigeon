"""Lever 2: the optional ``state.derived`` reasoning-residue field (schema 1.2).

Covers the contract (carries through build/validate, additive superset over 1.1,
no-op 1.1->1.2 migration), the per-slice meter, and the soft budget warning.
"""

from __future__ import annotations

from pigeon import SCHEMA_VERSION
from pigeon import handoff as ho
from pigeon import tokens as tk

_DERIVED = {
    "ruled_out": [{"path": "src/marshmallow/utils.py", "reason": "no validator base class there"}],
    "constraint_found": ["Slug regex must reject leading/trailing hyphens"],
    "next_action": "wire Slug into fields.__all__",
    "open_questions": ["should empty string be valid?"],
    "rationale": "mirror Email, the closest existing convention",
}


def test_build_handoff_carries_derived_and_validates(repo):
    h = ho.build_handoff(
        sid="s1", frm="plan", to="implement", done=["explored"], doing="implement",
        artifacts=["repo://src/marshmallow/validate.py"], derived=_DERIVED,
    )
    assert h["state"]["derived"] == _DERIVED
    assert h["schema_version"] == SCHEMA_VERSION == "1.2"
    ho.validate_handoff(h, repo)  # no raise


def test_derived_omitted_when_empty(repo):
    h = ho.build_handoff(sid="s1", frm="a", to="b", done=[], doing="x")
    assert "derived" not in h["state"]
    ho.validate_handoff(h, repo)


def test_a_1_1_handoff_still_validates_under_1_2(repo):
    """1.2 is a pure superset: a handoff that predates derived still passes."""
    h = ho.build_handoff(sid="s1", frm="a", to="b", done=[], doing="x",
                         artifacts=["repo://AGENTS.md"], schema_version="1.1")
    assert "derived" not in h["state"]
    ho.validate_handoff(h, repo)  # older minor accepted by the gate + structure


def test_migration_1_1_to_1_2_is_a_no_op(repo):
    h = ho.build_handoff(sid="s1", frm="a", to="b", done=["d"], doing="x",
                         artifacts=["repo://AGENTS.md"], schema_version="1.1")
    up = ho.upgrade_handoff(h)
    assert up["schema_version"] == SCHEMA_VERSION
    # only the version string changed; the carried state is identical
    assert {k: v for k, v in up.items() if k != "schema_version"} == \
           {k: v for k, v in h.items() if k != "schema_version"}
    ho.validate_handoff(up, repo)


def test_schema_rejects_unknown_derived_key(repo):
    h = ho.build_handoff(sid="s1", frm="a", to="b", done=[], doing="x",
                         derived={"made_up": "nope"})
    try:
        ho.validate_handoff(h, repo)
    except ho.HandoffValidationError:
        return
    raise AssertionError("expected additionalProperties:false to reject 'made_up'")


def test_components_meter_counts_derived(repo):
    h = ho.build_handoff(sid="s1", frm="a", to="b", done=[], doing="x", derived=_DERIVED)
    ev = tk.account_handoff(repo, h, record_event=False)
    assert ev["components"]["derived"] > 0
    # a handoff with no derived reads 0 on the meter
    bare = ho.build_handoff(sid="s1", frm="a", to="b", done=[], doing="x")
    assert tk.account_handoff(repo, bare, record_event=False)["components"]["derived"] == 0


def test_soft_budget_flag_and_status(repo):
    repo.coordinate_cfg["derived_token_budget"] = 5  # force the residue over budget
    h = ho.build_handoff(sid="s1", frm="a", to="b", done=[], doing="x", derived=_DERIVED)

    ev = tk.account_handoff(repo, h, record_event=False)
    assert ev["derived_over_budget"] is True

    status = tk.derived_budget_status(repo, h)
    assert status is not None
    tokens_used, budget = status
    assert tokens_used > budget == 5


def test_under_budget_does_not_flag(repo):
    repo.coordinate_cfg["derived_token_budget"] = 400  # the default; _DERIVED is small
    h = ho.build_handoff(sid="s1", frm="a", to="b", done=[], doing="x", derived=_DERIVED)
    ev = tk.account_handoff(repo, h, record_event=False)
    assert ev["derived_over_budget"] is False
    assert tk.derived_budget_status(repo, h) is None


def test_account_scaffold_counts_and_records(repo):
    """The scaffold kind counts re-emitted per-spawn prompt text (overhead, not a saving)."""
    ev = tk.account_scaffold(
        repo, prompt_text="You are sub-agent 'plan' in pigeon session 's1'. Do only the doing step.",
        kind_detail="claude", sid="s1", record_event=False,
    )
    assert ev["kind"] == "scaffold"
    assert ev["actual_tokens"] > 0
    assert ev["baseline_tokens"] == 0 and ev["saved_tokens"] == 0  # overhead, never a saving
    assert ev["detail"] == "claude"

    # recorded events surface under the 'scaffold' kind in the summary
    tk.account_scaffold(repo, prompt_text="hello world", kind_detail="agy", sid="s1")
    assert "scaffold" in tk.summarize(repo)["by_kind"]
