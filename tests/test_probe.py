"""probe: runner qualification harness (workstream 3)."""

from __future__ import annotations

import json
import sys

import yaml

from pigeon import probe as pr
from pigeon.config import Config, load_config

# Fake runners (no external CLI): a {prompt} placeholder is filled by the probe.
_OK = [sys.executable, "-c", "print('PIGEON_OK')"]
_JUNK = [sys.executable, "-c", "print('hello there')"]
_FAIL = [sys.executable, "-c", "import sys; sys.exit(1)"]
_HANG = [sys.executable, "-c", "import time; time.sleep(10)"]
_TRUSTED = ["claude", "-p", "{prompt}", "--model", "sonnet"]


def _cfg(repo: Config, runners: dict) -> Config:
    (repo.root / ".git").mkdir(exist_ok=True)
    (repo.root / ".agentctx" / "config.yaml").write_text(
        yaml.safe_dump({"coordinate": {"runners": {}}}), encoding="utf-8")
    cfg = load_config(repo.root)
    # Fully REPLACE the deep-merged default runners so the probe sees only the
    # fakes (otherwise it would spawn the real claude/opencode/... runners).
    cfg.data["coordinate"]["runners"] = runners
    return cfg


# --- unit: pure classification + helpers ---

def test_classify_matrix():
    assert pr.classify(0, "x PIGEON_OK y", 1.0, timed_out=False, soft_s=30)[0] == "ok"
    assert pr.classify(0, "PIGEON_OK", 45.0, timed_out=False, soft_s=30)[0] == "slow"
    assert pr.classify(0, "nope", 1.0, timed_out=False, soft_s=30)[0] == "protocol_fail"
    assert pr.classify(1, "boom", 1.0, timed_out=False, soft_s=30)[0] == "dead"
    assert pr.classify(0, "", 9.0, timed_out=True, soft_s=30)[0] == "dead"


def test_build_probe_cmd_substitutes_prompt():
    cmd = pr.build_probe_cmd(["x", "{prompt}", "y"], "HELLO")
    assert cmd == ["x", "HELLO", "y"]


def test_is_free_excludes_trusted():
    assert pr._is_free([sys.executable, "-c", "..."]) is True
    assert pr._is_free(_TRUSTED) is False
    assert pr._is_free(["timeout", "-k", "30", "900", "agy", "-p", "{prompt}"]) is False


def test_model_of():
    assert pr._model_of(["opencode", "run", "-m", "x/y-free", "{prompt}"]) == "x/y-free"
    assert pr._model_of(["claude", "-p", "{prompt}"]) == ""


# --- integration: real subprocess fake runners ---

def test_probe_classifies_each_runner(repo):
    cfg = _cfg(repo, {"good": _OK, "junk": _JUNK, "broken": _FAIL})
    recs = {r["runner"]: r for r in pr.probe(cfg, timeout_s=10, soft_s=30)}
    assert recs["good"]["verdict"] == "ok"
    assert recs["junk"]["verdict"] == "protocol_fail"
    assert recs["broken"]["verdict"] == "dead"


def test_probe_timeout_is_dead(repo):
    cfg = _cfg(repo, {"hang": _HANG})
    [rec] = pr.probe(cfg, timeout_s=1, soft_s=30)
    assert rec["verdict"] == "dead"
    assert "timed out" in rec["note"]


def test_probe_sorts_worst_first(repo):
    cfg = _cfg(repo, {"good": _OK, "broken": _FAIL})
    recs = pr.probe(cfg, timeout_s=10, soft_s=30)
    assert [r["verdict"] for r in recs] == ["dead", "ok"]


def test_free_only_skips_trusted(repo):
    cfg = _cfg(repo, {"good": _OK, "paid": _TRUSTED})
    names = {r["runner"] for r in pr.probe(cfg, free_only=True, timeout_s=10)}
    assert names == {"good"}          # the trusted runner is skipped (not spawned)


def test_write_probe_lands_in_contract_dir(repo):
    cfg = _cfg(repo, {"good": _OK})
    recs = pr.probe(cfg, timeout_s=10)
    path = pr.write_probe(recs, cfg)
    assert path == cfg.contract_dir / "probe.json"
    assert json.loads(path.read_text("utf-8"))[0]["runner"] == "good"


def test_cli_probe_runs(repo):
    from pigeon.cli import main
    _cfg(repo, {"good": _OK, "broken": _FAIL})
    assert main(["--root", str(repo.root), "probe", "--timeout", "10"]) == 0
    assert (repo.root / ".agentctx" / "probe.json").exists()
