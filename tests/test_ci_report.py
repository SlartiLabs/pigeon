"""ci_report: structured, fail-closed CI verdict (Tier B4)."""

from __future__ import annotations

from pigeon import ci_report as ci

_JUNIT_GREEN = """<?xml version="1.0"?>
<testsuites><testsuite tests="2">
  <testcase classname="t" name="a"/>
  <testcase classname="t" name="b"/>
</testsuite></testsuites>"""

_JUNIT_RED = """<?xml version="1.0"?>
<testsuites><testsuite tests="2">
  <testcase classname="tests.test_resolve" name="test_fence">
    <failure message="AssertionError: escaped">trace</failure>
  </testcase>
  <testcase classname="t" name="ok"/>
</testsuite></testsuites>"""


# --- fail-closed on crash / missing output (the load-bearing property) ---

def test_missing_junit_is_error_not_pass(tmp_path):
    r = ci.parse_pytest_junit(tmp_path / "nope.xml")
    assert r["status"] == "error"


def test_unparseable_junit_is_error(tmp_path):
    p = tmp_path / "bad.xml"
    p.write_text("not xml <<<", encoding="utf-8")
    assert ci.parse_pytest_junit(p)["status"] == "error"


def test_pyrefly_nonzero_without_parseable_errors_is_error():
    # a crash: pyrefly failed but emitted nothing we can attribute
    assert ci.parse_pyrefly(2, "Segmentation fault")["status"] == "error"


def test_verdict_error_dominates(tmp_path):
    v = ci.build_verdict("abc", {
        "pytest": {"status": "pass", "failures": []},
        "pyrefly": {"status": "error", "failures": []},
    })
    assert v["status"] == "error"          # one errored check -> whole verdict errors


# --- green => empty, red => expected id ---

def test_green_junit_pass_no_failures(tmp_path):
    p = tmp_path / "g.xml"
    p.write_text(_JUNIT_GREEN, encoding="utf-8")
    r = ci.parse_pytest_junit(p)
    assert r["status"] == "pass" and r["failures"] == []


def test_red_junit_yields_failure_id(tmp_path):
    p = tmp_path / "r.xml"
    p.write_text(_JUNIT_RED, encoding="utf-8")
    r = ci.parse_pytest_junit(p)
    assert r["status"] == "fail"
    assert any(f["id"] == "tests.test_resolve::test_fence" for f in r["failures"])


def test_pyrefly_clean_is_pass():
    assert ci.parse_pyrefly(0, "")["status"] == "pass"


# --- human-gate invariant blocks auto-merge ---

def test_can_auto_merge_only_when_green_and_no_gate():
    green = ci.build_verdict("c", {"pytest": {"status": "pass", "failures": []}})
    assert ci.can_auto_merge(green) is True

    failed = ci.build_verdict("c", {"pytest": {"status": "fail", "failures": [
        {"id": "x", "human_gate_required": False}]}})
    assert ci.can_auto_merge(failed) is False

    gated = ci.build_verdict("c", {"pytest": {"status": "pass", "failures": [
        {"id": "s1", "human_gate_required": True}]}})
    # even 'pass' cannot auto-merge if a failure is flagged human-gate-required
    assert gated["status"] == "pass"
    assert ci.can_auto_merge(gated) is False


def test_write_verdict_lands_under_pigeon_ci(tmp_path):
    v = ci.build_verdict("c0ffee", {"pytest": {"status": "pass", "failures": []}})
    path = ci.write_verdict(v, tmp_path)
    assert path == tmp_path / "ci" / "verdict.json"
    assert '"status": "pass"' in path.read_text("utf-8")
