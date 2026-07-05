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


def test_full_roster_is_tiered_explicitly():
    assert router.tier_of("opus") == "strong"
    for r in ("sonnet", "codex", "agy"):
        assert router.tier_of(r) == "mid"
    for r in ("mimo", "oc-mimo", "oc-north", "oc-nemotron", "oc-nex",
              "nv-nano", "nv-minimax", "nv-mixtral", "nv-mistral-large"):
        assert router.tier_of(r) == "cheap", r


def test_cheap_tier_round_robins_across_free_arm():
    tasks = [{"id": f"w{i}", "runner": "sonnet", "doing": "implement it"} for i in range(3)]
    free = ["oc-mimo", "oc-north", "nv-nano"]  # three cheap runners
    got = router.route(tasks, "cost-aware", free)
    # three worker tasks spread across three distinct free runners (load spreading)
    assert len(set(got.values())) == 3
    assert all(router.tier_of(v) == "cheap" for v in got.values())


def test_static_policy_keeps_declared_runner():
    tasks = [{"id": "a", "runner": "sonnet"}, {"id": "b", "runner": "opus"}]
    assert router.route(tasks, "static", AVAIL) == {"a": "sonnet", "b": "opus"}


def test_cost_aware_keeps_reasoning_mid_offloads_workers():
    tasks = [
        {"id": "architect", "runner": "sonnet", "doing": "design the api"},
        {"id": "impl", "runner": "sonnet", "doing": "implement it"},
        {"id": "review", "runner": "sonnet", "doing": "verify correctness"},
    ]
    got = router.route(tasks, "cost-aware", AVAIL)
    # cost-aware must NOT upgrade reasoning to strong (that would cost more than static)
    assert router.tier_of(got["architect"]) == "mid"   # planner stays mid (sonnet)
    assert router.tier_of(got["impl"]) == "cheap"       # worker -> free arm
    assert router.tier_of(got["review"]) == "mid"       # verifier stays mid


def test_quality_first_upgrades_reasoning_to_strong():
    tasks = [
        {"id": "architect", "runner": "sonnet", "doing": "design the api"},
        {"id": "review", "runner": "sonnet", "doing": "verify correctness"},
    ]
    got = router.route(tasks, "quality-first", AVAIL)
    assert got["architect"] == "opus" and got["review"] == "opus"


def test_route_degrades_when_tier_absent():
    # no strong runner available -> planner/verifier degrade to mid
    tasks = [{"id": "review", "runner": "sonnet", "doing": "verify"}]
    got = router.route(tasks, "cost-aware", ["sonnet", "mimo"])
    assert got["review"] == "sonnet"       # strong absent -> mid


def test_unknown_policy_raises():
    with pytest.raises(ValueError):
        router.route([{"id": "a", "runner": "sonnet"}], "nope", AVAIL)


def test_route_rejects_task_without_id():
    # a hand-edited spec via `pigeon route` must get a clear ValueError, not a raw KeyError
    with pytest.raises(ValueError):
        router.route([{"runner": "sonnet"}], "cost-aware", AVAIL)


def test_parse_routing_prefers_real_answer_over_echoed_example():
    # prompted_prompt embeds an example {"architect":"sonnet","impl":"oc-mimo"}; a model that
    # echoes it after answering must not have the example override its real decision.
    text = 'example: {"architect": "sonnet", "impl": "oc-mimo"}\nmy answer: {"a": "opus", "b": "sonnet"}'
    assert router.parse_routing(text, ["a", "b"], ["opus", "sonnet"]) == {"a": "opus", "b": "sonnet"}


def test_apply_mutates_spec_runners():
    spec = {"sid": "s", "tasks": [
        {"id": "impl", "runner": "sonnet", "doing": "implement"},
        {"id": "gate", "runner": "sonnet", "doing": "review"},
    ]}
    router.apply(spec, "cost-aware", AVAIL)
    runners = {t["id"]: t["runner"] for t in spec["tasks"]}
    assert router.tier_of(runners["impl"]) == "cheap"
    assert router.tier_of(runners["gate"]) == "mid"   # cost-aware verifier stays mid


def test_prompted_prompt_lists_tasks_and_runners():
    tasks = [{"id": "architect", "doing": "design"}, {"id": "impl", "doing": "implement"}]
    p = router.prompted_prompt(tasks, AVAIL)
    assert "architect" in p and "impl" in p
    assert "opus" in p and "free arm" in p
    assert "JSON" in p


def test_prompted_prompt_includes_history_when_given():
    p = router.prompted_prompt([{"id": "a", "doing": "x"}], AVAIL,
                               history_summary="impl: oc-mimo 2/5 pass; sonnet 5/5 pass")
    assert "routing history" in p and "oc-mimo 2/5" in p


def test_parse_routing_keeps_only_known_task_and_runner():
    text = '{"architect": "opus", "impl": "oc-mimo", "ghost": "sonnet", "impl2": "no-such"}'
    got = router.parse_routing(text, ["architect", "impl", "impl2"], AVAIL)
    assert got == {"architect": "opus", "impl": "oc-mimo"}  # ghost task + bad runner dropped


def test_parse_routing_from_noisy_prose():
    text = 'Sure! Here is my routing:\n{"a": "sonnet"}\nHope that helps.'
    assert router.parse_routing(text, ["a"], AVAIL) == {"a": "sonnet"}


def test_parse_routing_empty_on_garbage():
    assert router.parse_routing("no json here", ["a"], AVAIL) == {}


def test_explain_reports_from_to():
    tasks = [{"id": "impl", "runner": "sonnet", "doing": "implement"}]
    rows = router.explain(tasks, "cost-aware", AVAIL)
    assert rows[0]["task"] == "impl" and rows[0]["role"] == "worker"
    assert rows[0]["from"] == "sonnet" and router.tier_of(rows[0]["to"]) == "cheap"
