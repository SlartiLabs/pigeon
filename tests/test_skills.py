"""Skill projection: canonical playbooks -> runtime-native subagent files."""

from __future__ import annotations

from pathlib import Path

from pigeon import skills
from pigeon.config import load_config
from pigeon.skills import parse_playbook, playbooks, project_skills


def _mk_repo(tmp_path: Path, config_yaml: str = ""):
    """Minimal pigeon-native repo (.pigeon/) with optional config snippet."""
    pigeon = tmp_path / ".pigeon"
    pigeon.mkdir(exist_ok=True)
    if config_yaml:
        (pigeon / "config.yaml").write_text(config_yaml, encoding="utf-8")
    return load_config(tmp_path)


def _playbook(repo, name="security-audit", body="You are a security reviewer.",
              extra_meta=""):
    d = repo.root / ".agentctx" / "memory" / "playbooks"
    d.mkdir(parents=True, exist_ok=True)
    page = d / f"{name}.md"
    page.write_text(
        f"---\nname: {name}\ndescription: Adversarial review.\n{extra_meta}---\n\n{body}\n",
        encoding="utf-8")
    return page


def test_projects_claude_agent_file(repo):
    _playbook(repo)
    out = skills.project_skills(repo)
    assert out["written"] == [".claude/agents/security-audit.md"]
    text = (repo.root / ".claude" / "agents" / "security-audit.md").read_text(encoding="utf-8")
    assert text.startswith("---\nname: security-audit\n")
    assert "description: Adversarial review." in text
    assert skills.GEN_MARKER in text
    assert "source: .agentctx/memory/playbooks/security-audit.md" in text
    assert "You are a security reviewer." in text


def test_tools_frontmatter_carries_over(repo):
    _playbook(repo, extra_meta="tools: Read, Grep\n")
    skills.project_skills(repo)
    text = (repo.root / ".claude" / "agents" / "security-audit.md").read_text(encoding="utf-8")
    assert "tools: Read, Grep" in text


def test_pages_without_name_are_not_projected(repo):
    d = repo.root / ".agentctx" / "memory" / "playbooks"
    d.mkdir(parents=True, exist_ok=True)
    (d / "README.md").write_text("# Playbooks\n\nJust prose, no frontmatter.\n",
                                 encoding="utf-8")
    out = skills.project_skills(repo)
    assert out["written"] == [] and out["playbooks"] == 0


def test_handwritten_agent_files_never_clobbered(repo):
    _playbook(repo)
    target = repo.root / ".claude" / "agents" / "security-audit.md"
    target.parent.mkdir(parents=True)
    target.write_text("my precious hand-written agent\n", encoding="utf-8")
    out = skills.project_skills(repo)
    assert out["written"] == []
    assert any("hand-written" in s for s in out["skipped"])
    assert target.read_text(encoding="utf-8") == "my precious hand-written agent\n"


def test_reprojection_updates_generated_files(repo):
    page = _playbook(repo, body="v1 instructions.")
    skills.project_skills(repo)
    page.write_text(page.read_text(encoding="utf-8").replace("v1", "v2"), encoding="utf-8")
    skills.project_skills(repo)
    text = (repo.root / ".claude" / "agents" / "security-audit.md").read_text(encoding="utf-8")
    assert "v2 instructions." in text


def test_frontmatter_tolerates_trailing_whitespace_and_yaml_end(repo):
    d = repo.root / ".agentctx" / "memory" / "playbooks"
    d.mkdir(parents=True, exist_ok=True)
    (d / "spaced.md").write_text(
        "--- \nname: spaced\ndescription: d.\n... \nBody here.\n", encoding="utf-8")
    pages = skills.playbooks(repo)
    assert [p["name"] for p in pages] == ["spaced"]
    assert pages[0]["body"] == "Body here."


# ===========================================================================
# F1 — Memory-page typing: record_type + loud resolution
# ===========================================================================

def test_parse_playbook_reads_record_type(tmp_path: Path) -> None:
    """Each valid record_type value is parsed from frontmatter."""
    for rt in ("skill", "playbook", "decision", "reference"):
        page = tmp_path / f"{rt}.md"
        page.write_text(
            f"---\nname: test-{rt}\nrecord_type: {rt}\n---\nBody.\n", encoding="utf-8"
        )
        result = parse_playbook(page)
        assert result is not None
        assert result["meta"]["record_type"] == rt


def test_decision_page_not_projected(tmp_path: Path) -> None:
    """A page with record_type: decision is parsed but not projected."""
    cfg = _mk_repo(tmp_path)
    playbooks_dir = cfg.memory_dir / "playbooks"
    playbooks_dir.mkdir(parents=True)
    (playbooks_dir / "decisions.md").write_text(
        "---\nname: my-decision\nrecord_type: decision\n---\nWe chose X.\n",
        encoding="utf-8",
    )
    (playbooks_dir / "my-skill.md").write_text(
        "---\nname: my-skill\nrecord_type: skill\n---\nDo stuff.\n",
        encoding="utf-8",
    )

    # playbooks() lists both pages
    all_pages = playbooks(cfg)
    names = {p["name"] for p in all_pages}
    assert "my-decision" in names
    assert "my-skill" in names

    # project_skills only writes the skill
    result = project_skills(cfg)
    written_names = {Path(p).stem for p in result["written"]}
    assert "my-skill" in written_names
    assert "my-decision" not in written_names


def test_unknown_record_type_raises(tmp_path: Path) -> None:
    """An unknown record_type value raises ValueError at project time."""
    import pytest
    cfg = _mk_repo(tmp_path)
    playbooks_dir = cfg.memory_dir / "playbooks"
    playbooks_dir.mkdir(parents=True)
    page = playbooks_dir / "weird.md"
    page.write_text(
        "---\nname: weird-page\nrecord_type: banana\n---\nBody.\n",
        encoding="utf-8",
    )

    # parse_playbook raises directly
    with pytest.raises(ValueError, match="record_type"):
        parse_playbook(page)


def test_absent_record_type_defaults_to_skill(tmp_path: Path) -> None:
    """A page without record_type is projected as a skill (back-compat)."""
    cfg = _mk_repo(tmp_path)
    playbooks_dir = cfg.memory_dir / "playbooks"
    playbooks_dir.mkdir(parents=True)
    (playbooks_dir / "legacy.md").write_text(
        "---\nname: legacy-skill\n---\nOld-style page.\n", encoding="utf-8"
    )

    result = project_skills(cfg)
    written_names = {Path(p).stem for p in result["written"]}
    assert "legacy-skill" in written_names


# ----------------------------------------------------- cross-runtime (P1.5)

_OPENCODE_TARGET = ("skills:\n  targets:\n"
                    "    claude: .claude/agents\n    opencode: .opencode/agent\n")


def _write_page(cfg, name="security-audit", body="You are a security reviewer.",
                meta="description: Adversarial review.\n"):
    d = cfg.memory_dir / "playbooks"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.md").write_text(
        f"---\nname: {name}\n{meta}---\n\n{body}\n", encoding="utf-8")


def test_render_opencode_format():
    """opencode render: description + mode:subagent frontmatter, marker, body;
    name (filename-derived) and tools (vocab mismatch) are NOT in frontmatter."""
    page = {"name": "scout",
            "meta": {"description": "Recon specialist.", "tools": "Read, Grep"},
            "body": "You are a scout.",
            "source": ".pigeon/memory/playbooks/scout.md"}
    out = skills._render_opencode(page)
    assert out.startswith("---\ndescription: Recon specialist.\n")
    assert "mode: subagent" in out
    assert skills.GEN_MARKER in out
    assert "You are a scout." in out
    front = out.split("---", 2)[1]
    assert "name:" not in front     # opencode takes the name from the filename
    assert "tools:" not in out      # Claude tools vocab not projected to opencode


def test_projects_opencode_agent_file(tmp_path):
    cfg = _mk_repo(tmp_path, _OPENCODE_TARGET)
    _write_page(cfg)
    out = skills.project_skills(cfg)
    oc = cfg.root / ".opencode" / "agent" / "security-audit.md"
    assert str(oc.relative_to(cfg.root)) in out["written"]
    text = oc.read_text(encoding="utf-8")
    assert "mode: subagent" in text and "description: Adversarial review." in text
    assert skills.GEN_MARKER in text and "You are a security reviewer." in text
    # the one page projects to BOTH runtimes
    assert (cfg.root / ".claude" / "agents" / "security-audit.md").exists()


def test_opencode_handwritten_never_clobbered(tmp_path):
    cfg = _mk_repo(tmp_path, _OPENCODE_TARGET)
    _write_page(cfg)
    oc = cfg.root / ".opencode" / "agent"
    oc.mkdir(parents=True, exist_ok=True)
    (oc / "security-audit.md").write_text("hand-written, no marker\n", encoding="utf-8")
    out = skills.project_skills(cfg)
    assert (oc / "security-audit.md").read_text("utf-8") == "hand-written, no marker\n"
    assert any("left alone" in s for s in out["skipped"])


def test_unknown_runtime_target_skipped(tmp_path):
    cfg = _mk_repo(tmp_path, "skills:\n  targets:\n    nonesuch: .nonesuch/agent\n")
    _write_page(cfg)
    out = skills.project_skills(cfg)
    assert any("nonesuch" in s and "no renderer" in s for s in out["skipped"])
