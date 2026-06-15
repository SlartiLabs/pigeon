"""Property / contract tests for DAG scheduler invariants and telemetry parsers.

DD Risk 1/4 — these tests harden the contracts CI enforces:
  1. DAG scheduler: "no task starts before its needs exit 0"
     → for every task T and every dependency D of T, wave_index(D) < wave_index(T)
  2. DAG scheduler: "cyclic graphs are rejected" by load_tasks
  3. Telemetry parsers: claude usage:{*_tokens} shape contract
  4. Telemetry parsers: opencode tokens:{total,input,...}+cost shape contract
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Any

import pytest
import yaml

from pigeon import coordinate as co


# ================================================================= helpers
def _tasks_from_adj(adj: dict[str, list[str]]) -> list[dict[str, Any]]:
    """Build a task list from an adjacency dict {id: [dep_ids]}."""
    return [
        {"id": tid, "doing": f"do {tid}", "runner": "py",
         **({"needs": deps} if deps else {})}
        for tid, deps in adj.items()
    ]


def _wave_index(waves: list[list[str]], task_id: str) -> int:
    for i, wave in enumerate(waves):
        if task_id in wave:
            return i
    raise KeyError(f"{task_id!r} not in any wave")


# =========================================================== DAG invariant 1
# "No task starts before its needs exit 0"
# Structural claim: for every task T and every dep D of T,
# wave_index(D) < wave_index(T).
# We test this over many parametrized topologies.

_DAG_TOPOLOGIES = [
    # (label, adjacency dict {id: [needs]})
    ("linear_3", {"a": [], "b": ["a"], "c": ["b"]}),
    ("diamond", {"a": [], "b": ["a"], "c": ["a"], "d": ["b", "c"]}),
    ("parallel_then_join", {"x": [], "y": [], "z": ["x", "y"]}),
    ("two_chains", {"a": [], "b": ["a"], "p": [], "q": ["p"]}),
    ("star_in", {"root": [], "b": ["root"], "c": ["root"], "d": ["root"]}),
    ("star_out", {"a": [], "b": [], "c": [], "join": ["a", "b", "c"]}),
    ("single_task", {"solo": []}),
    ("v_shape", {"a": [], "b": [], "c": ["a", "b"]}),
    ("w_shape", {"a": [], "b": [], "c": ["a"], "d": ["b"], "e": ["c", "d"]}),
    ("long_chain", {"n0": [], "n1": ["n0"], "n2": ["n1"], "n3": ["n2"], "n4": ["n3"]}),
    ("forest_3", {"a": [], "b": ["a"], "p": [], "q": ["p"], "x": []}),
    ("wide_then_deep",
     {"r": [], "a": ["r"], "b": ["r"], "c": ["r"], "d": ["a", "b"], "e": ["d", "c"]}),
]


@pytest.mark.parametrize("label,adj", _DAG_TOPOLOGIES, ids=[t[0] for t in _DAG_TOPOLOGIES])
def test_waves_ordering_invariant(label, adj):
    """The ordering invariant: every dependency is placed in an earlier wave.

    This is the structural representation of "no task starts before its needs
    exit 0". If this holds for compute_waves(), the scheduler can safely run
    all tasks in wave N after wave N-1 exits 0 — the contract is met.
    """
    tasks = _tasks_from_adj(adj)
    waves = co.compute_waves(tasks)

    # All tasks appear in exactly one wave
    placed = sorted(tid for wave in waves for tid in wave)
    assert placed == sorted(adj), f"[{label}] not all tasks placed in waves"

    # The ordering invariant
    for task in tasks:
        t_wave = _wave_index(waves, task["id"])
        for dep_id in task.get("needs") or []:
            d_wave = _wave_index(waves, dep_id)
            assert d_wave < t_wave, (
                f"[{label}] invariant violation: task {task['id']!r} is in wave "
                f"{t_wave} but its dependency {dep_id!r} is in wave {d_wave} "
                f"(must be strictly earlier). waves={waves}"
            )


@pytest.mark.parametrize("label,adj", _DAG_TOPOLOGIES, ids=[t[0] for t in _DAG_TOPOLOGIES])
def test_waves_root_tasks_in_first_wave(label, adj):
    """Tasks with no dependencies must be in wave 0 (they block nothing)."""
    tasks = _tasks_from_adj(adj)
    waves = co.compute_waves(tasks)
    roots = [tid for tid, deps in adj.items() if not deps]
    wave_0 = set(waves[0])
    for root in roots:
        assert root in wave_0, (
            f"[{label}] root task {root!r} (no deps) should be in wave 0 "
            f"but waves[0]={waves[0]}"
        )


@pytest.mark.parametrize("label,adj", _DAG_TOPOLOGIES, ids=[t[0] for t in _DAG_TOPOLOGIES])
def test_waves_no_empty_waves(label, adj):
    """compute_waves must never produce an empty wave (defensively)."""
    tasks = _tasks_from_adj(adj)
    waves = co.compute_waves(tasks)
    for i, wave in enumerate(waves):
        assert wave, f"[{label}] wave {i} is empty — waves={waves}"


# =========================================================== DAG invariant 2
# "Cyclic graphs are rejected"
# load_tasks must raise ValueError mentioning "cycle" for any cyclic graph.

def _write_tasks_yaml(tmp_path: Path, spec: dict) -> Path:
    path = tmp_path / "tasks.yaml"
    path.write_text(yaml.safe_dump(spec), encoding="utf-8")
    return path


_CYCLE_CASES: list[tuple[str, list[dict[str, Any]]]] = [
    ("self_dep", [
        {"id": "a", "doing": "x", "runner": "py", "needs": ["a"]},
    ]),
    ("two_cycle", [
        {"id": "a", "doing": "x", "runner": "py", "needs": ["b"]},
        {"id": "b", "doing": "y", "runner": "py", "needs": ["a"]},
    ]),
    ("three_cycle", [
        {"id": "a", "doing": "x", "runner": "py", "needs": ["c"]},
        {"id": "b", "doing": "y", "runner": "py", "needs": ["a"]},
        {"id": "c", "doing": "z", "runner": "py", "needs": ["b"]},
    ]),
    ("cycle_with_free_task", [
        {"id": "free", "doing": "ok", "runner": "py"},
        {"id": "a", "doing": "x", "runner": "py", "needs": ["b"]},
        {"id": "b", "doing": "y", "runner": "py", "needs": ["a"]},
    ]),
    ("longer_cycle", [
        {"id": "a", "doing": "x", "runner": "py", "needs": ["d"]},
        {"id": "b", "doing": "y", "runner": "py", "needs": ["a"]},
        {"id": "c", "doing": "z", "runner": "py", "needs": ["b"]},
        {"id": "d", "doing": "w", "runner": "py", "needs": ["c"]},
    ]),
]


@pytest.mark.parametrize("label,tasks", _CYCLE_CASES, ids=[c[0] for c in _CYCLE_CASES])
def test_cycle_rejected_by_load_tasks(tmp_path, label, tasks):
    """load_tasks must reject any cyclic dependency graph with ValueError.

    Self-dependencies, 2-cycles, 3-cycles, longer cycles, and cycles mixed with
    free tasks are all rejected. The error message mentions 'cycle'.
    """
    spec = {"sid": f"cycle-{label}", "tasks": tasks}
    path = _write_tasks_yaml(tmp_path, spec)
    with pytest.raises(ValueError, match="cycle|itself"):
        co.load_tasks(path, default_runner="py")


@pytest.mark.parametrize("label,adj", [
    (lbl, adj) for lbl, adj in _DAG_TOPOLOGIES if len(adj) > 1
], ids=[t[0] for t in _DAG_TOPOLOGIES if len(t[1]) > 1])
def test_acyclic_dag_accepted_by_load_tasks(tmp_path, label, adj):
    """Valid acyclic DAGs must load without error (negative cycle test)."""
    tasks = _tasks_from_adj(adj)
    spec = {"sid": f"ok-{label}", "tasks": tasks}
    path = _write_tasks_yaml(tmp_path, spec)
    result = co.load_tasks(path, default_runner="py")
    assert result["sid"] == f"ok-{label}"
    assert len(result["tasks"]) == len(adj)


# =========================================================== Telemetry contracts
# Small captured JSON fixtures — each is a verbatim or minimal representative
# sample from the actual CLI output shapes the parsers must handle.

# ---- Claude `usage:{*_tokens}` shape ----------------------------------------
# claude -p --output-format json emits a single JSON document with a `usage`
# object whose keys all end in `_tokens`.

_CLAUDE_FIXTURES: list[tuple[str, str, int, float | None]] = [
    # (label, json_text, expected_total_tokens, expected_cost_usd_or_None)
    (
        "basic",
        '{"type":"result","num_turns":1,'
        '"usage":{"input_tokens":100,"output_tokens":50},'
        '"total_cost_usd":0.005}',
        150, 0.005,
    ),
    (
        "with_cache",
        '{"type":"result","num_turns":4,"total_cost_usd":0.0123,'
        '"usage":{"input_tokens":100,"output_tokens":50,'
        '"cache_creation_input_tokens":5,"cache_read_input_tokens":25}}',
        180, 0.0123,
    ),
    (
        "only_input_output",
        '{"usage":{"input_tokens":7,"output_tokens":3},"total_cost_usd":0.01}',
        10, 0.01,
    ),
    (
        "large_context",
        '{"type":"result","total_cost_usd":1.5,'
        '"usage":{"input_tokens":50000,"output_tokens":3000,'
        '"cache_read_input_tokens":12000}}',
        65000, 1.5,
    ),
    (
        "no_cost_field",
        '{"usage":{"input_tokens":20,"output_tokens":10}}',
        30, None,
    ),
    (
        "ndjson_last_line",
        '{"type":"system","system":"claude"}\nplain log line\n'
        '{"usage":{"input_tokens":40,"output_tokens":20},"total_cost_usd":0.002}',
        60, 0.002,
    ),
]


@pytest.mark.parametrize(
    "label,text,expected_total,expected_cost",
    _CLAUDE_FIXTURES,
    ids=[f[0] for f in _CLAUDE_FIXTURES],
)
def test_claude_usage_parser_contract(label, text, expected_total, expected_cost):
    """Contract: _extract_telemetry correctly parses claude usage:{*_tokens} fixtures.

    Invariants that always hold when a usage object is present:
    - result is not None
    - total_tokens equals the sum of all *_tokens keys in usage
    - usage dict is preserved verbatim in the output
    - total_cost_usd is present only when the source JSON contains it
    """
    result = co._extract_telemetry(text)
    assert result is not None, f"[{label}] parser returned None; expected telemetry"
    assert result["total_tokens"] == expected_total, (
        f"[{label}] total_tokens={result['total_tokens']} != {expected_total}"
    )
    assert "usage" in result, f"[{label}] 'usage' key missing from result"
    if expected_cost is not None:
        assert abs(result["total_cost_usd"] - expected_cost) < 1e-9, (
            f"[{label}] total_cost_usd={result.get('total_cost_usd')} != {expected_cost}"
        )
    else:
        assert "total_cost_usd" not in result, (
            f"[{label}] unexpected total_cost_usd={result.get('total_cost_usd')}"
        )


# Structural invariant: sum of *_tokens keys equals reported total
@pytest.mark.parametrize(
    "label,text,expected_total,_cost",
    _CLAUDE_FIXTURES,
    ids=[f[0] for f in _CLAUDE_FIXTURES],
)
def test_claude_usage_total_equals_sum_of_token_fields(label, text, expected_total, _cost):
    """total_tokens must equal the sum of every *_tokens key in usage."""
    result = co._extract_telemetry(text)
    assert result is not None
    usage = result["usage"]
    computed = sum(
        int(v) for k, v in usage.items()
        if k.endswith("_tokens") and isinstance(v, (int, float))
    )
    assert computed == result["total_tokens"], (
        f"[{label}] sum of *_tokens keys ({computed}) != total_tokens "
        f"({result['total_tokens']}); usage={usage}"
    )


# ---- opencode `tokens:{total,input,...}+cost` shape -------------------------
# opencode run --format json emits NDJSON; its assistant message carries
# `tokens:{total,input,output,reasoning,cache:{read,write}}` + `cost`.

_OPENCODE_FIXTURES: list[tuple[str, str, int, float | None, str | None]] = [
    # (label, ndjson_text, expected_total, expected_cost, expected_model_or_None)
    (
        "deepseek_free",
        json.dumps({
            "role": "assistant",
            "modelID": "deepseek-v4-flash-free",
            "tokens": {
                "total": 38509, "input": 38483, "output": 2, "reasoning": 24,
                "cache": {"read": 0, "write": 0},
            },
            "cost": 0,
        }),
        38509, 0.0, "deepseek-v4-flash-free",
    ),
    (
        "nvidia_paid",
        json.dumps({
            "role": "assistant",
            "providerID": "nvidia",
            "tokens": {
                "total": 51815, "input": 51727, "output": 88, "reasoning": 0,
                "cache": {"read": 0, "write": 0},
            },
            "cost": 0.0260835,
        }),
        51815, 0.0260835, None,
    ),
    (
        "no_total_sum_components",
        '{"tokens":{"input":100,"output":50,"reasoning":0,"cache":{"read":10,"write":0}}}',
        160, None, None,
    ),
    (
        "wrapped_in_ndjson_stream",
        "\n".join([
            '{"type":"step_start"}',
            json.dumps({
                "role": "assistant",
                "modelID": "claude-sonnet-4-6",
                "tokens": {"total": 1000, "input": 900, "output": 100, "reasoning": 0,
                           "cache": {"read": 0, "write": 0}},
                "cost": 0.05,
            }),
        ]),
        1000, 0.05, "claude-sonnet-4-6",
    ),
    (
        "nested_in_event_envelope",
        json.dumps({
            "type": "message",
            "data": {
                "role": "assistant",
                "tokens": {"total": 500, "input": 450, "output": 50, "reasoning": 0,
                           "cache": {"read": 0, "write": 0}},
                "cost": 0.025,
            },
        }),
        500, 0.025, None,
    ),
    (
        "with_cache_tokens",
        json.dumps({
            "role": "assistant",
            "tokens": {
                "total": 200, "input": 100, "output": 50, "reasoning": 10,
                "cache": {"read": 30, "write": 10},
            },
            "cost": 0.001,
        }),
        200, 0.001, None,
    ),
]


@pytest.mark.parametrize(
    "label,text,expected_total,expected_cost,expected_model",
    _OPENCODE_FIXTURES,
    ids=[f[0] for f in _OPENCODE_FIXTURES],
)
def test_opencode_tokens_parser_contract(label, text, expected_total, expected_cost, expected_model):
    """Contract: _extract_telemetry correctly parses opencode tokens:{...}+cost fixtures.

    Invariants that always hold for the opencode shape:
    - result is not None
    - total_tokens > 0
    - 'usage' key present (holds the raw tokens dict for metrics)
    - total_cost_usd present only when cost field is in the source
    - model extracted from modelID when present
    """
    result = co._extract_telemetry(text)
    assert result is not None, f"[{label}] parser returned None; expected telemetry"
    assert result["total_tokens"] == expected_total, (
        f"[{label}] total_tokens={result['total_tokens']} != {expected_total}"
    )
    assert "usage" in result, f"[{label}] 'usage' key missing from result"
    assert result["total_tokens"] > 0, f"[{label}] total_tokens must be > 0 for a valid event"
    if expected_cost is not None:
        assert abs(result.get("total_cost_usd", float("nan")) - expected_cost) < 1e-9, (
            f"[{label}] total_cost_usd={result.get('total_cost_usd')} != {expected_cost}"
        )
    if expected_model is not None:
        assert result.get("model") == expected_model, (
            f"[{label}] model={result.get('model')!r} != {expected_model!r}"
        )


# ---- Zero-total events are not measurements --------------------------------
_ZERO_EVENTS: list[tuple[str, str]] = [
    ("opencode_zero_total", '{"type":"step_start","tokens":{"total":0,"input":0}}'),
    ("opencode_zero_all",
     '{"tokens":{"total":0,"input":0,"output":0,"reasoning":0,"cache":{"read":0,"write":0}}}'),
    ("plain_text", "hello world"),
    ("no_usage_no_tokens", '{"type":"system","data":"ok"}'),
    ("empty_string", ""),
]


@pytest.mark.parametrize("label,text", _ZERO_EVENTS, ids=[e[0] for e in _ZERO_EVENTS])
def test_telemetry_returns_none_for_unmeasurable_output(label, text):
    """Events with no measurable usage (zero total, plain text, no usage block)
    must return None — a confident zero beats a silent miscount."""
    assert co._extract_telemetry(text) is None, (
        f"[{label}] expected None but got a result"
    )


# ---- Parser structural invariants (cross-shape) ----------------------------
_ALL_VALID_FIXTURES = (
    [(lbl, text) for lbl, text, *_ in _CLAUDE_FIXTURES]
    + [(lbl, text) for lbl, text, *_ in _OPENCODE_FIXTURES]
)


@pytest.mark.parametrize("label,text", _ALL_VALID_FIXTURES,
                         ids=[f[0] for f in _ALL_VALID_FIXTURES])
def test_telemetry_result_invariants(label, text):
    """Structural invariants that hold for every valid telemetry result,
    regardless of the parser branch (claude or opencode):
    - total_tokens is a positive integer
    - usage key is a non-empty dict
    - no unexpected keys sneak in (contract is stable)
    """
    result = co._extract_telemetry(text)
    assert result is not None, f"[{label}] parser returned None for a valid fixture"
    assert isinstance(result["total_tokens"], int), (
        f"[{label}] total_tokens must be int, got {type(result['total_tokens'])}"
    )
    assert result["total_tokens"] > 0, f"[{label}] total_tokens must be > 0"
    assert isinstance(result["usage"], dict), f"[{label}] usage must be a dict"
    assert result["usage"], f"[{label}] usage must be non-empty"
    # No unknown top-level keys
    allowed = {"total_tokens", "usage", "total_cost_usd", "duration_ms",
               "num_turns", "model"}
    unknown = set(result) - allowed
    assert not unknown, f"[{label}] unexpected keys in result: {unknown}"
