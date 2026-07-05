"""Tests for the routing-decision log (Track B, rung B1)."""

from pigeon import coordinate as co
from pigeon.coordinate import routing


def _mk(runner, turns, cost, status="exited", **extra):
    t = {"runner": runner, "status": status,
         "telemetry": {"num_turns": turns, "total_cost_usd": cost}}
    t.update(extra)
    return t


def test_build_records_decision_and_outcome_fields():
    recs = routing.build_records("r1", "s", {
        "a": _mk("sonnet", 10, 0.4),
        "b": _mk("sonnet", 12, 0.5, needs=["a"]),
    }, depth={"a": 0, "b": 1}, carried={"b": True})
    assert len(recs) == 2
    b = next(r for r in recs if r["task"] == "b")
    assert b["runner"] == "sonnet" and b["num_deps"] == 1 and b["depth"] == 1
    assert b["carried_residue"] is True
    assert b["num_turns"] == 12 and b["cost_usd"] == 0.5


def test_records_carry_role_and_summarize_groups_by_role():
    recs = routing.build_records("r", "s", {
        "architect": _mk("sonnet", 10, 0.4, doing="design the api"),
        "impl": _mk("sonnet", 12, 0.5, doing="implement it"),
    }, {"architect": 0, "impl": 1}, {})
    roles = {r["task"]: r["role"] for r in recs}
    assert roles["architect"] == "planner" and roles["impl"] == "worker"
    assert set(routing.summarize(recs)["roles"]) == {"planner", "worker"}


def test_summarize_flags_small_free_vs_paid_cost_gap():
    # a $0.00 free-arm run vs a small paid run must register as a cost signal,
    # not get swallowed by a flat floor (the `min(costs) or 1` bug).
    recs = routing.build_records("r1", "s", {"w": _mk("oc-mimo", 10, 0.0, doing="implement")}, {"w": 0}, {})
    recs += routing.build_records("r2", "s", {"w": _mk("sonnet", 10, 0.03, doing="implement")}, {"w": 0}, {})
    s = routing.summarize(recs)
    assert s["varied_roles"] == 1 and s["signal_roles"] == 1


def test_summarize_no_variation():
    recs = routing.build_records("r1", "s",
                                 {"a": _mk("sonnet", 10, 0.4)}, {"a": 0}, {})
    s = routing.summarize(recs)
    assert s["varied_roles"] == 0 and "NO routing variation" in s["verdict"]


def test_summarize_detects_signal():
    recs = routing.build_records("r1", "s", {"a": _mk("sonnet", 10, 0.4)}, {"a": 0}, {})
    recs += routing.build_records("r2", "s", {"a": _mk("opus", 25, 1.2)}, {"a": 0}, {})
    s = routing.summarize(recs)
    assert s["varied_roles"] == 1 and s["signal_roles"] == 1
    assert "worth testing" in s["verdict"]


def test_summarize_variation_without_signal():
    recs = routing.build_records("r1", "s", {"a": _mk("sonnet", 10, 0.40)}, {"a": 0}, {})
    recs += routing.build_records("r2", "s", {"a": _mk("opus", 10, 0.41)}, {"a": 0}, {})
    s = routing.summarize(recs)
    assert s["varied_roles"] == 1 and s["signal_roles"] == 0
    assert "did not differ materially" in s["verdict"]


def test_summarize_empty():
    s = routing.summarize([])
    assert s["task_records"] == 0 and "empty log" in s["verdict"]


def test_append_and_load_roundtrip(tmp_path):
    p = tmp_path / "routing_log.jsonl"
    recs = routing.build_records("r1", "s", {"a": _mk("x", 3, 0.1)}, {"a": 0}, {})
    routing.append_log(p, recs)
    routing.append_log(p, recs)
    assert len(routing.load_log(p)) == 2
    assert routing.load_log(p)[0]["task"] == "a"


def test_records_from_manifest_transitive_depth():
    man = {"run_id": "r1", "sid": "s", "tasks": {
        "a": {"runner": "sonnet", "status": "exited"},
        "b": {"runner": "sonnet", "needs": ["a"], "status": "exited"},
        "c": {"runner": "opus", "needs": ["b"], "status": "exited"},
    }}
    depths = {r["task"]: r["depth"] for r in routing.records_from_manifest(man)}
    assert depths == {"a": 0, "b": 1, "c": 2}


def _recorder(repo, sid, tasks):
    return co.RunRecorder(repo, sid, tasks, tasks_file="t.yaml", parallel_limit=1,
                          skip_permissions=False, dry_run=False, telemetry=False,
                          isolated_env=None, depth=0)


def test_recorder_writes_routing_log_on_finish(repo):
    rec = _recorder(repo, "run1", [{"id": "a", "runner": "sonnet"},
                                   {"id": "b", "runner": "sonnet", "needs": ["a"]}])
    rec.task("a", status="exited", telemetry={"num_turns": 8, "total_cost_usd": 0.3})
    rec.task("b", status="exited", telemetry={"num_turns": 11, "total_cost_usd": 0.5})
    rec.finish("completed", summary={"ok": 2, "failed": 0, "skipped": 0, "total": 2})

    log = repo.coordinate_routing_log
    assert log.exists(), "finish() must append per-task routing records"
    recs = routing.load_log(log)
    assert {r["task"] for r in recs} == {"a", "b"}
    b = next(r for r in recs if r["task"] == "b")
    assert b["runner"] == "sonnet" and b["depth"] == 1 and b["num_turns"] == 11
    # single runner per role -> probe reports no variation
    assert routing.summarize(recs)["varied_roles"] == 0
