"""Adopt: discover & catalogue existing subagents, skills, and MCP servers.

Tests define the API contract for ``pigeon.adopt``.
Each test validates one behaviour from adopt.md §8.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from pigeon.config import Config, load_config
from pigeon import adopt
from pigeon.skills import GEN_MARKER


# ---------------------------------------------------------------------------
# Helpers — filesystem scaffolding (all under tmp_path, no real ~/.claude)
# ---------------------------------------------------------------------------

def _mk_repo(tmp_path: Path, config_yaml: str = "") -> Config:
    """Minimal pigeon-native repo with an optional config snippet."""
    pigeon = tmp_path / ".pigeon"
    pigeon.mkdir()
    if config_yaml:
        (pigeon / "config.yaml").write_text(config_yaml, encoding="utf-8")
    return load_config(tmp_path)


def _write_subagent(path: Path, name: str, body: str = "You are helpful.",
                    *, marker: bool = False) -> None:
    """Write a Claude subagent .md file with frontmatter."""
    path.parent.mkdir(parents=True, exist_ok=True)
    marker_line = f"\n{GEN_MARKER}\n" if marker else "\n"
    path.write_text(
        f"---\nname: {name}\ndescription: A test agent.\n---\n"
        f"{marker_line}{body}\n",
        encoding="utf-8",
    )


def _write_skill_dir(base: Path, name: str,
                     description: str = "A test skill.") -> Path:
    """Write a .claude/skills/<name>/SKILL.md directory-based skill."""
    skill_dir = base / ".claude" / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\nBody.\n",
        encoding="utf-8",
    )
    return skill_dir


def _write_mcp_json(path: Path, data: dict[str, Any]) -> None:
    """Write an MCP config file (e.g. .mcp.json or ~/.claude.json)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


# ===========================================================================
# 1. Parse unit tests — each source format incl. malformed / empty
# ===========================================================================

class TestParseSubagent:
    """Parse Claude subagent frontmatter from .claude/agents/*.md."""

    def test_valid_frontmatter_extracts_name_and_body(self, tmp_path: Path) -> None:
        f = tmp_path / "agents" / "reviewer.md"
        _write_subagent(f, "reviewer", "You review code.")
        record = adopt.parse_claude_subagent(f)
        assert record is not None
        assert record["name"] == "reviewer"
        assert record["description"] == "A test agent."
        assert "You review code." in record["body"]

    def test_missing_frontmatter_returns_none(self, tmp_path: Path) -> None:
        f = tmp_path / "agents" / "bad.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("Just prose, no YAML frontmatter.\n", encoding="utf-8")
        assert adopt.parse_claude_subagent(f) is None

    def test_empty_file_returns_none(self, tmp_path: Path) -> None:
        f = tmp_path / "agents" / "empty.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("", encoding="utf-8")
        assert adopt.parse_claude_subagent(f) is None

    def test_broken_yaml_returns_none(self, tmp_path: Path) -> None:
        f = tmp_path / "agents" / "borked.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("---\nname: {{bad yaml\n---\n\nBody.\n", encoding="utf-8")
        assert adopt.parse_claude_subagent(f) is None

    def test_missing_name_key_returns_none(self, tmp_path: Path) -> None:
        f = tmp_path / "agents" / "noname.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("---\ndescription: Has no name.\n---\n\nBody.\n",
                     encoding="utf-8")
        assert adopt.parse_claude_subagent(f) is None


class TestParseSkill:
    """Parse .claude/skills/* definitions."""

    def test_directory_based_skill(self, tmp_path: Path) -> None:
        _write_skill_dir(tmp_path, "code-review", "Reviews code.")
        base = tmp_path / ".claude"
        record = adopt.parse_skill(base / "skills" / "code-review")
        assert record is not None
        assert record["name"] == "code-review"
        assert record["description"] == "Reviews code."

    def test_missing_skill_md_returns_none(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / ".claude" / "skills" / "orphan"
        skill_dir.mkdir(parents=True, exist_ok=True)
        assert adopt.parse_skill(skill_dir) is None

    def test_empty_skill_md_returns_none(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / ".claude" / "skills" / "empty-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("", encoding="utf-8")
        assert adopt.parse_skill(skill_dir) is None

    def test_nonexistent_path_returns_none(self, tmp_path: Path) -> None:
        assert adopt.parse_skill(tmp_path / "nope") is None


class TestParseMcp:
    """Parse MCP server config files (~/.claude.json, .mcp.json, etc.)."""

    def test_claude_json_servers(self, tmp_path: Path) -> None:
        cfg = tmp_path / ".claude.json"
        _write_mcp_json(cfg, {
            "mcpServers": {
                "my-server": {"command": "node", "args": ["mcp.js"]},
            }
        })
        records = adopt.parse_mcp_config(cfg)
        assert len(records) == 1
        assert records[0]["name"] == "my-server"
        assert records[0]["kind"] == "mcp"

    def test_mcp_json_format(self, tmp_path: Path) -> None:
        cfg = tmp_path / ".mcp.json"
        _write_mcp_json(cfg, {
            "servers": {
                "tool-a": {"url": "http://localhost:3000/mcp"},
            }
        })
        records = adopt.parse_mcp_config(cfg)
        assert len(records) == 1
        assert records[0]["name"] == "tool-a"

    def test_empty_servers_object(self, tmp_path: Path) -> None:
        cfg = tmp_path / ".mcp.json"
        _write_mcp_json(cfg, {"servers": {}})
        records = adopt.parse_mcp_config(cfg)
        assert records == []

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        assert adopt.parse_mcp_config(tmp_path / "nope.json") == []

    def test_malformed_json_returns_empty(self, tmp_path: Path) -> None:
        cfg = tmp_path / "bad.json"
        cfg.write_text("{not valid json", encoding="utf-8")
        assert adopt.parse_mcp_config(cfg) == []


# ===========================================================================
# 2. Provenance — GEN_MARKER distinguishes pigeon-generated from user-authored
# ===========================================================================

class TestProvenance:
    """Provenance detection via GEN_MARKER."""

    def test_marked_file_is_pigeon_generated(self, tmp_path: Path) -> None:
        f = tmp_path / "agents" / "auto.md"
        _write_subagent(f, "auto", marker=True)
        assert adopt.provenance(f) == "pigeon-generated"

    def test_unmarked_file_is_user_authored(self, tmp_path: Path) -> None:
        f = tmp_path / "agents" / "mine.md"
        _write_subagent(f, "mine", marker=False)
        assert adopt.provenance(f) == "user-authored"

    def test_nonexistent_file_is_user_authored(self, tmp_path: Path) -> None:
        """A missing file defaults to user-authored (safe fallback)."""
        assert adopt.provenance(tmp_path / "nope.md") == "user-authored"

    def test_pigeon_generated_excluded_from_catalog(self, tmp_path: Path) -> None:
        """Round-trip: refresh writes a marked file; adopt skips it."""
        cfg = _mk_repo(tmp_path, (
            "skills:\n"
            "  targets:\n"
            "    claude: .claude/agents\n"
        ))
        pb_dir = tmp_path / ".pigeon" / "memory" / "playbooks"
        pb_dir.mkdir(parents=True)
        (pb_dir / "sec.md").write_text(
            "---\nname: security-audit\ndescription: Reviews.\n---\n\nBody.\n",
            encoding="utf-8",
        )
        from pigeon import skills
        skills.project_skills(cfg)
        # The generated file must be excluded from adoption
        entries = adopt.discover(cfg)
        names = [e["name"] for e in entries]
        assert "security-audit" not in names

    def test_user_authored_is_adoptable(self, tmp_path: Path) -> None:
        """An unmarked .claude/agents file appears in the catalog."""
        cfg = _mk_repo(tmp_path)
        _write_subagent(
            tmp_path / ".claude" / "agents" / "my-agent.md",
            "my-agent",
            marker=False,
        )
        entries = adopt.discover(cfg)
        names = [e["name"] for e in entries]
        assert "my-agent" in names


# ===========================================================================
# 3. Allow-gate — unlisted names trip preflight; allow-listing clears it
# ===========================================================================

class TestAllowGate:
    """Allow-gate: names must be in adopt.allow to be usable in crews."""

    def test_unlisted_name_triggers_preflight_warning(self, tmp_path: Path) -> None:
        cfg = _mk_repo(tmp_path)
        _write_subagent(
            tmp_path / ".claude" / "agents" / "x.md", "x", marker=False
        )
        entries = adopt.discover(cfg)
        adopt.write_catalog(entries, cfg)
        warnings = adopt.preflight_check(["x"], cfg)
        assert any("x" in w for w in warnings)

    def test_allow_listed_name_passes_preflight(self, tmp_path: Path) -> None:
        cfg = _mk_repo(tmp_path, "adopt:\n  allow:\n    - x\n")
        _write_subagent(
            tmp_path / ".claude" / "agents" / "x.md", "x", marker=False
        )
        entries = adopt.discover(cfg)
        adopt.write_catalog(entries, cfg)
        warnings = adopt.preflight_check(["x"], cfg)
        assert warnings == []

    def test_nonexistent_name_also_warns(self, tmp_path: Path) -> None:
        """Referencing a name that doesn't exist at all also warns."""
        cfg = _mk_repo(tmp_path)
        warnings = adopt.preflight_check(["ghost"], cfg)
        assert any("ghost" in w for w in warnings)

    def test_default_allow_is_empty(self, tmp_path: Path) -> None:
        """Nothing is usable until explicitly allow-listed."""
        cfg = _mk_repo(tmp_path)
        assert adopt.check_allow("anything", cfg) is False


# ===========================================================================
# 4. Non-destruction — adopt + refresh never modify user sources
# ===========================================================================

class TestNonDestruction:
    """adopt + refresh in any order never modifies a user source file
    and never overwrites an unmarked target."""

    def test_adopt_does_not_modify_source_subagent(self, tmp_path: Path) -> None:
        cfg = _mk_repo(tmp_path)
        f = tmp_path / ".claude" / "agents" / "mine.md"
        _write_subagent(f, "mine", marker=False)
        original = f.read_text(encoding="utf-8")
        adopt.discover(cfg)
        adopt.write_catalog(adopt.discover(cfg), cfg)
        assert f.read_text(encoding="utf-8") == original

    def test_adopt_does_not_modify_source_skill(self, tmp_path: Path) -> None:
        cfg = _mk_repo(tmp_path)
        _write_skill_dir(tmp_path, "solo")
        skill_md = tmp_path / ".claude" / "skills" / "solo" / "SKILL.md"
        original = skill_md.read_text(encoding="utf-8")
        adopt.discover(cfg)
        assert skill_md.read_text(encoding="utf-8") == original

    def test_refresh_then_adopt_preserves_handwritten(self, tmp_path: Path) -> None:
        """refresh projects a generated file; adopt must not touch the
        handwritten sibling."""
        cfg = _mk_repo(tmp_path, (
            "skills:\n"
            "  targets:\n"
            "    claude: .claude/agents\n"
        ))
        hw = tmp_path / ".claude" / "agents" / "hand.md"
        _write_subagent(hw, "hand", marker=False)
        hw_original = hw.read_text(encoding="utf-8")
        pb_dir = tmp_path / ".pigeon" / "memory" / "playbooks"
        pb_dir.mkdir(parents=True)
        (pb_dir / "auto.md").write_text(
            "---\nname: auto-agent\ndescription: Auto.\n---\n\nBody.\n",
            encoding="utf-8",
        )
        from pigeon import skills
        skills.project_skills(cfg)
        adopt.discover(cfg)
        assert hw.read_text(encoding="utf-8") == hw_original

    def test_adopt_then_refresh_preserves_handwritten(self, tmp_path: Path) -> None:
        """adopt first, then refresh — handwritten target still untouched."""
        cfg = _mk_repo(tmp_path, (
            "skills:\n"
            "  targets:\n"
            "    claude: .claude/agents\n"
        ))
        hw = tmp_path / ".claude" / "agents" / "hand.md"
        _write_subagent(hw, "hand", marker=False)
        hw_original = hw.read_text(encoding="utf-8")
        pb_dir = tmp_path / ".pigeon" / "memory" / "playbooks"
        pb_dir.mkdir(parents=True)
        (pb_dir / "auto.md").write_text(
            "---\nname: auto-agent\ndescription: Auto.\n---\n\nBody.\n",
            encoding="utf-8",
        )
        adopt.discover(cfg)
        from pigeon import skills
        skills.project_skills(cfg)
        assert hw.read_text(encoding="utf-8") == hw_original

    def test_adopt_never_clobbers_unmarked_target(self, tmp_path: Path) -> None:
        """A generated file (with marker) CAN be overwritten; an unmarked
        file MUST NOT be, even if the name matches a playbook."""
        cfg = _mk_repo(tmp_path, (
            "skills:\n"
            "  targets:\n"
            "    claude: .claude/agents\n"
        ))
        hw = tmp_path / ".claude" / "agents" / "security-audit.md"
        _write_subagent(hw, "security-audit", marker=False)
        hw_original = hw.read_text(encoding="utf-8")
        pb_dir = tmp_path / ".pigeon" / "memory" / "playbooks"
        pb_dir.mkdir(parents=True)
        (pb_dir / "security-audit.md").write_text(
            "---\nname: security-audit\ndescription: Reviews.\n---\n\nBody.\n",
            encoding="utf-8",
        )
        from pigeon import skills
        skills.project_skills(cfg)
        assert hw.read_text(encoding="utf-8") == hw_original


# ===========================================================================
# 5. MCP secrets — secret values never land in catalog.json
# ===========================================================================

class TestMcpSecretScrubbing:
    """Secret values (API keys, tokens) are never written to catalog.json."""

    def test_api_key_not_in_catalog(self, tmp_path: Path) -> None:
        cfg = _mk_repo(tmp_path)
        mcp_path = tmp_path / ".mcp.json"
        _write_mcp_json(mcp_path, {
            "servers": {
                "data-src": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-fetch"],
                    "env": {
                        "API_KEY": "sk-super-secret-12345",
                    },
                },
            },
        })
        entries = adopt.discover(cfg)
        adopt.write_catalog(entries, cfg)
        catalog_text = (
            tmp_path / ".pigeon" / "adopt" / "catalog.json"
        ).read_text(encoding="utf-8")
        assert "sk-super-secret-12345" not in catalog_text
        data = json.loads(catalog_text)
        ds = [e for e in data if e["name"] == "data-src"]
        assert len(ds) == 1
        assert ds[0].get("has_secrets") is True

    def test_token_not_in_catalog(self, tmp_path: Path) -> None:
        # Use a custom config so .claude.json is in the MCP sources
        cfg = _mk_repo(tmp_path, (
            "adopt:\n"
            "  sources:\n"
            "    mcp: ['.claude.json']\n"
        ))
        mcp_path = tmp_path / ".claude.json"
        _write_mcp_json(mcp_path, {
            "mcpServers": {
                "slack-bot": {
                    "command": "node",
                    "args": ["slack.js"],
                    "env": {
                        "SLACK_TOKEN": "xoxb-FAKE-TOKEN-12345",
                    },
                },
            },
        })
        entries = adopt.discover(cfg)
        adopt.write_catalog(entries, cfg)
        catalog_text = (
            tmp_path / ".pigeon" / "adopt" / "catalog.json"
        ).read_text(encoding="utf-8")
        assert "xoxb-FAKE-TOKEN-12345" not in catalog_text
        data = json.loads(catalog_text)
        sb = [e for e in data if e["name"] == "slack-bot"]
        assert len(sb) == 1
        assert sb[0].get("has_secrets") is True

    def test_no_env_means_no_secrets_flag(self, tmp_path: Path) -> None:
        cfg = _mk_repo(tmp_path)
        mcp_path = tmp_path / ".mcp.json"
        _write_mcp_json(mcp_path, {
            "servers": {
                "local-tool": {
                    "command": "python",
                    "args": ["-m", "my_mcp"],
                },
            },
        })
        entries = adopt.discover(cfg)
        adopt.write_catalog(entries, cfg)
        data = json.loads(
            (tmp_path / ".pigeon" / "adopt" / "catalog.json").read_text(
                encoding="utf-8"
            )
        )
        lt = [e for e in data if e["name"] == "local-tool"]
        assert len(lt) == 1
        assert lt[0].get("has_secrets") is False


# ===========================================================================
# Gate regression tests (run adopt-gate-2 findings A–E)
# ===========================================================================

class TestMcpUrlAndArgSecrets:
    """Gate blocker A: secrets in url / args must not reach the catalog."""

    def _catalog(self, tmp_path: Path) -> list[dict[str, Any]]:
        cfg = _mk_repo(tmp_path)
        adopt.write_catalog(adopt.discover(cfg), cfg)
        return json.loads(
            (tmp_path / ".pigeon" / "adopt" / "catalog.json").read_text("utf-8"))

    def test_url_userinfo_redacted(self, tmp_path: Path) -> None:
        _write_mcp_json(tmp_path / ".mcp.json", {"servers": {
            "db": {"url": "postgres://user:s3cret@db.example.com:5432/app"}}})
        db = [e for e in self._catalog(tmp_path) if e["name"] == "db"][0]
        assert "s3cret" not in json.dumps(db)
        assert db["url"] == "postgres://db.example.com:5432/app"
        assert db["has_secrets"] is True

    def test_url_query_token_redacted(self, tmp_path: Path) -> None:
        _write_mcp_json(tmp_path / ".mcp.json", {"servers": {
            "remote": {"url": "https://host/mcp?token=sk-abc123"}}})
        r = [e for e in self._catalog(tmp_path) if e["name"] == "remote"][0]
        assert "sk-abc123" not in json.dumps(r)
        assert r["url"] == "https://host/mcp"
        assert r["has_secrets"] is True

    def test_secret_in_args_sets_flag_and_args_dropped(self, tmp_path: Path) -> None:
        _write_mcp_json(tmp_path / ".mcp.json", {"servers": {
            "svc": {"command": "npx", "args": ["server", "--api-key", "sk-xyz"]}}})
        svc = [e for e in self._catalog(tmp_path) if e["name"] == "svc"][0]
        assert "sk-xyz" not in json.dumps(svc)   # the value must not be stored
        assert "args" not in svc                  # args are not a catalog field
        assert svc["has_secrets"] is True

    def test_plain_url_kept_no_secret(self, tmp_path: Path) -> None:
        _write_mcp_json(tmp_path / ".mcp.json", {"servers": {
            "plain": {"url": "https://host/mcp"}}})
        p = [e for e in self._catalog(tmp_path) if e["name"] == "plain"][0]
        assert p["url"] == "https://host/mcp"
        assert p["has_secrets"] is False


class TestUpdateAllowSafety:
    """Gate blocker B: --allow must not wipe or de-comment config.yaml."""

    _CONFIG = (
        "# my hand-written config — keep this comment\n"
        "tokens:\n"
        "  encoding: cl100k_base   # inline comment\n"
    )

    def test_appends_fresh_block_preserving_comments(self, tmp_path: Path) -> None:
        cfg = _mk_repo(tmp_path, self._CONFIG)
        added = adopt.update_allow(["code-reviewer"], cfg)
        assert added == ["code-reviewer"]
        text = (tmp_path / ".pigeon" / "config.yaml").read_text("utf-8")
        assert "keep this comment" in text and "inline comment" in text
        reloaded = load_config(tmp_path)
        assert reloaded.data["adopt"]["allow"] == ["code-reviewer"]

    def test_second_call_inserts_into_existing_block(self, tmp_path: Path) -> None:
        cfg = _mk_repo(tmp_path, self._CONFIG)
        adopt.update_allow(["first"], cfg)
        added = adopt.update_allow(["second"], load_config(tmp_path))
        assert added == ["second"]
        text = (tmp_path / ".pigeon" / "config.yaml").read_text("utf-8")
        assert "keep this comment" in text
        assert load_config(tmp_path).data["adopt"]["allow"] == ["first", "second"]

    def test_expands_inline_empty_allow(self, tmp_path: Path) -> None:
        cfg = _mk_repo(tmp_path, self._CONFIG + "adopt:\n  allow: []\n")
        adopt.update_allow(["x"], cfg)
        assert load_config(tmp_path).data["adopt"]["allow"] == ["x"]
        assert "keep this comment" in (
            tmp_path / ".pigeon" / "config.yaml").read_text("utf-8")

    def test_idempotent_no_duplicate(self, tmp_path: Path) -> None:
        cfg = _mk_repo(tmp_path, self._CONFIG)
        adopt.update_allow(["dup"], cfg)
        assert adopt.update_allow(["dup"], load_config(tmp_path)) == []
        assert load_config(tmp_path).data["adopt"]["allow"] == ["dup"]

    def test_refuses_malformed_config_without_wiping(self, tmp_path: Path) -> None:
        cfg = _mk_repo(tmp_path, self._CONFIG)
        broken = "adopt: [unterminated\n:::not yaml:::\n"
        cfg_path = tmp_path / ".pigeon" / "config.yaml"
        cfg_path.write_text(broken, encoding="utf-8")
        with pytest.raises(ValueError):
            adopt.update_allow(["x"], cfg)
        assert cfg_path.read_text("utf-8") == broken   # untouched, not wiped


class TestGeneratedSkillExcluded:
    """Gate finding C: GEN_MARKER'd skills are excluded like subagents."""

    def test_generated_skill_not_catalogued(self, tmp_path: Path) -> None:
        d = _write_skill_dir(tmp_path, "gen-skill")
        sm = d / "SKILL.md"
        sm.write_text(sm.read_text("utf-8") + f"\n{GEN_MARKER}\n", encoding="utf-8")
        cfg = _mk_repo(tmp_path)
        names = {e["name"] for e in adopt.discover(cfg)}
        assert "gen-skill" not in names

    def test_user_skill_still_catalogued(self, tmp_path: Path) -> None:
        _write_skill_dir(tmp_path, "user-skill")
        cfg = _mk_repo(tmp_path)
        assert "user-skill" in {e["name"] for e in adopt.discover(cfg)}


class TestDiscoverRobustness:
    """Gate finding D: an unreadable source dir must not crash discovery."""

    @pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses chmod perms")
    def test_unreadable_source_dir_is_skipped(self, tmp_path: Path) -> None:
        _write_subagent(tmp_path / ".claude" / "agents" / "ok.md", "ok")
        skills = tmp_path / ".claude" / "skills"
        skills.mkdir(parents=True)
        skills.chmod(0o000)
        try:
            if os.access(skills, os.R_OK):
                pytest.skip("chmod did not restrict access in this environment")
            cfg = _mk_repo(tmp_path)
            names = {e["name"] for e in adopt.discover(cfg)}  # must not raise
            assert "ok" in names
        finally:
            skills.chmod(0o755)


class TestAdoptAllowSchema:
    """Gate finding E: adopt.allow is type-checked at load."""

    def test_non_list_allow_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            _mk_repo(tmp_path, "adopt:\n  allow: not-a-list\n")

    def test_non_string_items_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            _mk_repo(tmp_path, "adopt:\n  allow: [1, 2]\n")


# ===========================================================================
# F2 — import_asset: copies allow-listed catalog entries to playbooks/
# ===========================================================================

from pigeon.skills import playbooks, project_skills


class TestImportAsset:
    """import_asset writes an unmarked playbook page from the catalog."""

    def _catalog_entry(self, name: str, kind: str = "subagent", *,
                       allowed: bool = True, scope: str = "user",
                       source: str | None = None) -> dict:
        e = {"name": name, "kind": kind, "allowed": allowed, "scope": scope}
        if source is not None:
            e["source"] = str(source)
        return e

    def _write_catalog(self, cfg, entries: list) -> None:
        cfg.adopt_dir.mkdir(parents=True, exist_ok=True)
        (cfg.adopt_dir / "catalog.json").write_text(
            json.dumps(entries), encoding="utf-8"
        )

    def test_import_writes_unmarked_page(self, tmp_path: Path) -> None:
        """Importing an allow-listed asset writes a playbook page without GEN_MARKER,
        carrying the asset's real body (B1 regression)."""
        from pigeon.adopt import import_asset

        cfg = _mk_repo(tmp_path, "adopt:\n  allow:\n    - my-agent\n")
        src = tmp_path / ".claude" / "agents" / "my-agent.md"
        _write_subagent(src, "my-agent", body="You are a careful reviewer.")
        self._write_catalog(cfg, [self._catalog_entry("my-agent", source=src)])

        import_asset("my-agent", cfg)

        page = cfg.memory_dir / "playbooks" / "my-agent.md"
        assert page.exists()

        content = page.read_text(encoding="utf-8")
        assert GEN_MARKER not in content
        assert "record_type: skill" in content
        # B1: the asset's body is carried, not lost
        assert "You are a careful reviewer." in content
        # and the imported page is itself a valid, projectable playbook
        names = {p["name"] for p in playbooks(cfg)}
        assert "my-agent" in names
        assert any(p["name"] == "my-agent" and p["body"].strip()
                   for p in playbooks(cfg))

    def test_reimport_refuses(self, tmp_path: Path) -> None:
        """Re-importing a name that already has a playbook page raises FileExistsError."""
        from pigeon.adopt import import_asset

        cfg = _mk_repo(tmp_path, "adopt:\n  allow:\n    - my-agent\n")
        self._write_catalog(cfg, [self._catalog_entry("my-agent")])

        # Pre-create the playbook
        playbooks_dir = cfg.memory_dir / "playbooks"
        playbooks_dir.mkdir(parents=True)
        (playbooks_dir / "my-agent.md").write_text(
            "---\nname: my-agent\n---\nExisting.\n", encoding="utf-8"
        )

        with pytest.raises(FileExistsError, match="already exists"):
            import_asset("my-agent", cfg)

    def test_import_unallowlisted_refuses(self, tmp_path: Path) -> None:
        """Importing a name not in adopt.allow raises ValueError."""
        from pigeon.adopt import import_asset

        cfg = _mk_repo(tmp_path)  # allow list is empty
        self._write_catalog(cfg, [self._catalog_entry("my-agent", allowed=False)])

        with pytest.raises(ValueError, match="not allow-listed"):
            import_asset("my-agent", cfg)

    def test_import_unknown_name_refuses(self, tmp_path: Path) -> None:
        """Importing a name not in the catalog raises KeyError."""
        from pigeon.adopt import import_asset

        cfg = _mk_repo(tmp_path)
        self._write_catalog(cfg, [])

        with pytest.raises(KeyError, match="not found"):
            import_asset("nonexistent", cfg)

    def test_import_mcp_name_refuses(self, tmp_path: Path) -> None:
        """Importing an MCP-kind asset raises ValueError."""
        from pigeon.adopt import import_asset

        cfg = _mk_repo(tmp_path, "adopt:\n  allow:\n    - my-mcp\n")
        self._write_catalog(cfg, [self._catalog_entry("my-mcp", kind="mcp")])

        with pytest.raises(ValueError, match="MCP"):
            import_asset("my-mcp", cfg)

    def test_refresh_preserves_imported_page(self, tmp_path: Path) -> None:
        """Running project_skills after import does not overwrite the imported page."""
        from pigeon.adopt import import_asset

        cfg = _mk_repo(tmp_path, "adopt:\n  allow:\n    - my-agent\n")
        src = tmp_path / ".claude" / "agents" / "my-agent.md"
        _write_subagent(src, "my-agent", body="You are a careful reviewer.")
        self._write_catalog(cfg, [self._catalog_entry("my-agent", source=src)])

        import_asset("my-agent", cfg)
        page = cfg.memory_dir / "playbooks" / "my-agent.md"
        original_content = page.read_text(encoding="utf-8")

        project_skills(cfg)

        assert page.read_text(encoding="utf-8") == original_content


    def test_cli_import_end_to_end(self, tmp_path: Path) -> None:
        """`pigeon adopt --import` writes the page (B2) and refuses unknown with exit 2."""
        from pigeon.cli import main

        cfg = _mk_repo(tmp_path, "adopt:\n  allow:\n    - my-agent\n")
        src = tmp_path / ".claude" / "agents" / "my-agent.md"
        _write_subagent(src, "my-agent", body="You are a careful reviewer.")
        self._write_catalog(cfg, [self._catalog_entry("my-agent", source=src)])

        assert main(["--root", str(tmp_path), "adopt", "--import", "my-agent"]) == 0
        page = cfg.memory_dir / "playbooks" / "my-agent.md"
        assert page.exists() and "You are a careful reviewer." in page.read_text("utf-8")
        # an unknown name refuses with exit 2 (not an uncaught traceback)
        assert main(["--root", str(tmp_path), "adopt", "--import", "ghost"]) == 2


# ===========================================================================
# F3 — crew_skill_warnings de-noising
# ===========================================================================

class TestCrewSkillWarnings:
    """crew_skill_warnings deduplicates and respects assume_known_skills."""

    def test_duplicate_refs_collapse_to_one_warning(self, tmp_path: Path) -> None:
        """Multiple references to the same unknown skill produce only one warning."""
        from pigeon.coordinate import crew_skill_warnings

        cfg = _mk_repo(tmp_path)
        spec = {
            "tasks": [
                {"id": "t1", "crew": {"skills": ["mystery-skill"]}},
                {"id": "t2", "crew": {"skills": ["mystery-skill"]}},
                {"id": "t3", "crew": {"subagents": [{"role": "r", "skill": "mystery-skill"}]}},
            ]
        }

        warnings = crew_skill_warnings(cfg, spec)
        mystery_warnings = [w for w in warnings if "mystery-skill" in w]
        assert len(mystery_warnings) == 1

    def test_assume_known_skills_silent(self, tmp_path: Path) -> None:
        """A skill in coordinate.assume_known_skills produces no warning."""
        from pigeon.coordinate import crew_skill_warnings

        cfg = _mk_repo(
            tmp_path,
            "coordinate:\n  assume_known_skills:\n    - code-architect-python\n"
        )
        spec = {
            "tasks": [
                {"id": "t1", "crew": {"skills": ["code-architect-python"]}},
            ]
        }

        warnings = crew_skill_warnings(cfg, spec)
        assert not any("code-architect-python" in w for w in warnings)

    def test_imported_skill_silent(self, tmp_path: Path) -> None:
        """A skill that was imported via F2 is recognized and produces no warning."""
        from pigeon.coordinate import crew_skill_warnings
        from pigeon.adopt import import_asset

        cfg = _mk_repo(tmp_path, "adopt:\n  allow:\n    - my-agent\n")
        src = tmp_path / ".claude" / "agents" / "my-agent.md"
        _write_subagent(src, "my-agent", body="You are a careful reviewer.")
        cfg.adopt_dir.mkdir(parents=True, exist_ok=True)
        (cfg.adopt_dir / "catalog.json").write_text(
            json.dumps([{"name": "my-agent", "kind": "subagent", "allowed": True,
                         "scope": "user", "source": str(src)}]),
            encoding="utf-8",
        )

        import_asset("my-agent", cfg)

        spec = {
            "tasks": [
                {"id": "t1", "crew": {"skills": ["my-agent"]}},
            ]
        }

        warnings = crew_skill_warnings(cfg, spec)
        assert not any("my-agent" in w for w in warnings)

    def test_unknown_name_warns_once(self, tmp_path: Path) -> None:
        """A name that is not a playbook, not imported, and not in assume_known warns."""
        from pigeon.coordinate import crew_skill_warnings

        cfg = _mk_repo(tmp_path)
        spec = {
            "tasks": [
                {"id": "t1", "crew": {"skills": ["totally-unknown"]}},
            ]
        }

        warnings = crew_skill_warnings(cfg, spec)
        unknown_warnings = [w for w in warnings if "totally-unknown" in w]
        assert len(unknown_warnings) == 1


# ===========================================================================
# Deep .claude/skills parsing + agents<->adopt cross-reference
# ===========================================================================

def test_parse_skill_deep_captures_body_tools_resources(tmp_path: Path) -> None:
    from pigeon.adopt import parse_skill

    d = tmp_path / ".claude" / "skills" / "data-tools"
    (d / "scripts").mkdir(parents=True)
    (d / "SKILL.md").write_text(
        "---\nname: data-tools\ndescription: Wrangle data.\ntools: [Read, Bash]\n---\n\n"
        "You wrangle data.\n", encoding="utf-8")
    (d / "scripts" / "run.py").write_text("print('hi')\n", encoding="utf-8")
    (d / "reference.md").write_text("# notes\n", encoding="utf-8")

    rec = parse_skill(d)
    assert rec["name"] == "data-tools"
    assert rec["body"] == "You wrangle data."
    assert rec["tools"] == ["Read", "Bash"]
    assert set(rec["resources"]) == {"scripts/run.py", "reference.md"}


def test_format_catalog_cross_references_agents(tmp_path: Path) -> None:
    from pigeon.adopt import format_catalog
    out = format_catalog([{"name": "x", "kind": "skill", "scope": "user",
                           "allowed": False, "description": "d"}])
    assert "pigeon agents" in out


def test_format_agents_cross_references_adopt() -> None:
    from pigeon import agents
    recs = [{"name": "claude", "found": True, "version": "1", "cost": "paid",
             "runner_template": None, "configured": False, "note": "n"}]
    out = agents.format_agents(recs, adopt_summary={"subagent": 3, "skill": 2})
    assert "adopted assets" in out and "pigeon adopt" in out
    # no summary -> no cross-ref line (back-compat)
    assert "adopted assets" not in agents.format_agents(recs)
