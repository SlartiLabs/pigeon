"""Tests for the heuristic router (Track B, rung B2)."""

import pytest

from pigeon.coordinate import router

AVAIL = ["opus", "sonnet", "mimo", "oc-mimo", "nv-nano"]  # strong, mid, cheap, cheap, cheap


def test_classify_role_by_id_and_doing():
    assert router.classify_role({"id": "architect", "doing": "plan the work"}) == "planner"
    assert router.classify_role({"id": "impl", "doing": "implement settle()"}) == "worker"
    assert router.classify_role({"id": "reviewer", "doing": "review the diff"}) == "verifier"
    # verifier wins over planner when both cues present ("review the plan")
    assert router.classify_role({"id": "r", "doing": "review the plan"}) == "verifier"
    # a bare doing-task defaults to worker
    assert router.classify_role({"id": "x", "doing": "produce output"}) == "worker"


def test_tier_of_defaults():
    assert router.tier_of("opus") == "strong"
    assert router.tier_of("sonnet") == "mid"
    assert router.tier_of("mimo") == "cheap"
    assert router.tier_of("oc-mimo") == "cheap"   # opencode-routed free
    assert router.tier_of("nv-nano") == "cheap"
    assert router.tier_of("some-unknown") == "mid"


def test_static_policy_keeps_declared_runner():
    tasks = [{"id": "a", "runner": "sonnet"}, {"id": "b", "runner": "opus"}]
    assert router.route(tasks, "static", AVAIL) == {"a": "sonnet", "b": "opus"}


def test_cost_aware_routes_by_role():
    tasks = [
        {"id": "architect", "runner": "sonnet", "doing": "design the api"},
        {"id": "impl", "runner": "sonnet", "doing": "implement it"},
        {"id": "review", "runner": "sonnet", "doing": "verify correctness"},
    ]
    got = router.route(tasks, "cost-aware", AVAIL)
    assert got["architect"] == "opus"      # planner -> strong
    assert router.tier_of(got["impl"]) == "cheap"   # worker -> cheap
    assert got["review"] == "opus"         # verifier -> strong


def test_route_degrades_when_tier_absent():
    # no strong runner available -> planner/verifier degrade to mid
    tasks = [{"id": "review", "runner": "sonnet", "doing": "verify"}]
    got = router.route(tasks, "cost-aware", ["sonnet", "mimo"])
    assert got["review"] == "sonnet"       # strong absent -> mid


def test_unknown_policy_raises():
    with pytest.raises(ValueError):
        router.route([{"id": "a", "runner": "sonnet"}], "nope", AVAIL)


def test_apply_mutates_spec_runners():
    spec = {"sid": "s", "tasks": [
        {"id": "impl", "runner": "sonnet", "doing": "implement"},
        {"id": "gate", "runner": "sonnet", "doing": "review"},
    ]}
    router.apply(spec, "cost-aware", AVAIL)
    runners = {t["id"]: t["runner"] for t in spec["tasks"]}
    assert router.tier_of(runners["impl"]) == "cheap"
    assert runners["gate"] == "opus"


def test_explain_reports_from_to():
    tasks = [{"id": "impl", "runner": "sonnet", "doing": "implement"}]
    rows = router.explain(tasks, "cost-aware", AVAIL)
    assert rows[0]["task"] == "impl" and rows[0]["role"] == "worker"
    assert rows[0]["from"] == "sonnet" and router.tier_of(rows[0]["to"]) == "cheap"
