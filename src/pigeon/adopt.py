"""adopt: discover and catalogue existing subagents, skills, and MCP servers.

Canonical assets (pigeon playbooks) flow OUT via ``skills.project_skills``.
This module is the inverse: it reads what the user already has in their
runtime directories (.claude/agents, .claude/skills, MCP configs) and builds
a catalog so ``coordinate`` crews can reference those assets by name.

Key invariants:
- Discovery is read-only; no user source file is ever modified.
- Pigeon-generated files (those bearing GEN_MARKER) are excluded from the
  catalog — they already came from a playbook.
- MCP ``env`` values (secrets) are never written to catalog.json; only the
  ``has_secrets`` flag is recorded.
- Nothing is usable in a crew until the name appears in ``adopt.allow``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from .config import Config
from .skills import GEN_MARKER


def provenance(path: Path) -> str:
    """Return 'pigeon-generated' or 'user-authored' for a file.

    A missing or unreadable file is treated as user-authored (safe fallback).
    """
    try:
        text = path.read_text(encoding="utf-8")
        return "pigeon-generated" if GEN_MARKER in text else "user-authored"
    except OSError:
        return "user-authored"


def parse_claude_subagent(path: Path) -> dict[str, Any] | None:
    """Parse a .claude/agents/*.md file into a subagent record.

    Returns a dict with keys: name, description, tools, body, provenance,
    kind='subagent'.  Returns None for missing/empty frontmatter, malformed
    YAML, missing 'name', or read errors.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    match = re.match(
        r"^---[ \t]*\n(.*?)\n(?:---|\.\.\.)[ \t]*\n(.*)$", text, re.DOTALL
    )
    if not match:
        return None

    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return None

    if not isinstance(meta, dict) or not meta.get("name"):
        return None

    body = match.group(2).strip()
    prov = "pigeon-generated" if GEN_MARKER in text else "user-authored"

    return {
        "name": str(meta["name"]),
        "description": str(meta.get("description", "")),
        "tools": meta.get("tools"),
        "body": body,
        "provenance": prov,
        "kind": "subagent",
    }


def parse_skill(path: Path) -> dict[str, Any] | None:
    """Parse a directory-based .claude/skills/<name>/ skill.

    Reads SKILL.md inside the directory.  Returns None if the path is not a
    directory, SKILL.md is absent or empty, or the YAML is malformed.
    """
    if not path.is_dir():
        return None
    skill_md = path / "SKILL.md"
    if not skill_md.exists():
        return None
    try:
        text = skill_md.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    if not text.strip():
        return None
    match = re.match(
        r"^---[ \t]*\n(.*?)\n(?:---|\.\.\.)[ \t]*\n(.*)$", text, re.DOTALL
    )
    if not match:
        return None
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return None
    if not isinstance(meta, dict) or not meta.get("name"):
        return None
    return {
        "name": str(meta["name"]),
        "description": str(meta.get("description", "")),
        "kind": "skill",
    }


def parse_mcp_config(path: Path) -> list[dict[str, Any]]:
    """Parse an MCP server config file.

    Handles both ``{"mcpServers": {...}}`` (~/.claude.json) and
    ``{"servers": {...}}`` (.mcp.json / .cursor/mcp.json) shapes.
    Returns [] on any error; secret env values are never included in records.
    """
    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, dict):
        return []
    servers: dict[str, Any] = data.get("mcpServers") or data.get("servers") or {}
    if not isinstance(servers, dict):
        return []
    records: list[dict[str, Any]] = []
    for name, cfg in servers.items():
        if not isinstance(cfg, dict):
            continue
        env = cfg.get("env") or {}
        records.append({
            "name": str(name),
            "kind": "mcp",
            "command": cfg.get("command"),
            "args": cfg.get("args"),
            "url": cfg.get("url"),
            "has_secrets": bool(env),
        })
    return records


def _resolve_source(path_str: str, root: Path) -> Path:
    p = Path(path_str).expanduser()
    if p.is_absolute():
        return p
    return (root / p).resolve()


def discover(config: Config) -> list[dict[str, Any]]:
    """Discover adoptable assets from configured sources.

    Sources are resolved relative to config.root for relative paths and via
    expanduser for ~ paths.  Pigeon-generated subagents (bearing GEN_MARKER)
    are excluded.  Project-scope sources should be listed before user-scope in
    the config to ensure project-wins precedence (first encounter wins).
    """
    adopt_cfg = config.data.get("adopt", {})
    sources = adopt_cfg.get("sources", {})

    entries: list[dict[str, Any]] = []
    seen: set[str] = set()

    # Subagents
    for path_str in sources.get("subagents", []):
        src = _resolve_source(path_str, config.root)
        scope = "user" if str(path_str).startswith("~") else "project"
        if not src.is_dir():
            continue
        for md_file in sorted(src.glob("*.md")):
            record = parse_claude_subagent(md_file)
            if record is None or record["provenance"] == "pigeon-generated":
                continue
            name = record["name"]
            key = f"subagent:{name}"
            if key in seen:
                continue
            seen.add(key)
            record.update({"source": str(md_file), "scope": scope})
            entries.append(record)

    # Skills
    for path_str in sources.get("skills", []):
        src = _resolve_source(path_str, config.root)
        scope = "user" if str(path_str).startswith("~") else "project"
        if not src.is_dir():
            continue
        for skill_dir in sorted(src.iterdir()):
            if not skill_dir.is_dir():
                continue
            record = parse_skill(skill_dir)
            if record is None:
                continue
            name = record["name"]
            key = f"skill:{name}"
            if key in seen:
                continue
            seen.add(key)
            record.update({"source": str(skill_dir), "scope": scope})
            entries.append(record)

    # MCP servers
    for path_str in sources.get("mcp", []):
        src = _resolve_source(path_str, config.root)
        scope = "user" if str(path_str).startswith("~") else "project"
        if not src.exists():
            continue
        for record in parse_mcp_config(src):
            name = record["name"]
            key = f"mcp:{name}"
            if key in seen:
                continue
            seen.add(key)
            record.update({"source": str(src), "scope": scope})
            entries.append(record)

    for entry in entries:
        entry["allowed"] = check_allow(entry["name"], config)

    return entries


def write_catalog(entries: list[dict[str, Any]], config: Config) -> Path:
    """Write catalog.json with secret values stripped.

    The catalog lives at <contract_dir>/adopt/catalog.json.  Subagent body
    text is omitted to keep the catalog compact.
    """
    catalog_path = config.catalog_path
    catalog_path.parent.mkdir(parents=True, exist_ok=True)

    safe: list[dict[str, Any]] = []
    for entry in entries:
        row = {k: v for k, v in entry.items() if k != "body"}
        safe.append(row)

    catalog_path.write_text(
        json.dumps(safe, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return catalog_path


def load_catalog(config: Config) -> list[dict[str, Any]]:
    """Load catalog.json; returns [] if absent or invalid."""
    catalog_path = config.catalog_path
    if not catalog_path.exists():
        return []
    try:
        data = json.loads(catalog_path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def format_catalog(catalog: list[dict[str, Any]]) -> str:
    """Format the catalog for human-readable terminal output."""
    if not catalog:
        return "No catalog assets found.\nUse `pigeon adopt --allow <name>` to enable individual assets"

    kind_counts: dict[str, int] = {}
    scope_counts: dict[str, int] = {}
    lines: list[str] = []

    for asset in sorted(catalog, key=lambda x: x.get("name", "")):
        name = asset.get("name", "?")
        kind = asset.get("kind", "unknown")
        scope = asset.get("scope", "project")
        allowed = asset.get("allowed", False)
        desc = str(asset.get("description", "")).split("\n")[0][:60]

        kind_counts[kind] = kind_counts.get(kind, 0) + 1
        scope_counts[scope] = scope_counts.get(scope, 0) + 1

        status = "allowed" if allowed else "not-allowed"
        lines.append(f"  {name:<25} {kind:<10} {scope:<7} {status:<12} {desc}")

    kind_parts = ", ".join(f"{n} {k}s" for k, n in sorted(kind_counts.items()))
    scope_parts = ", ".join(f"{n} {s}" for s, n in sorted(scope_counts.items()))
    header = f"Catalog ({kind_parts}; {scope_parts})\n"
    footer = "\nUse `pigeon adopt --allow <name>` to enable individual assets"

    return header + "\n".join(lines) + footer


def check_allow(name: str, config: Config) -> bool:
    """Return True iff name appears in adopt.allow."""
    allow_list = config.data.get("adopt", {}).get("allow") or []
    return name in allow_list


def resolve_adopted(name: str, config: Config) -> dict[str, Any] | None:
    """Return the catalog entry for name if it exists AND is allow-listed."""
    if not check_allow(name, config):
        return None
    for entry in load_catalog(config):
        if entry.get("name") == name:
            return entry
    return None


def preflight_check(names: list[str], config: Config) -> list[str]:
    """Return advisory messages for crew skill names that need action.

    A name is fine if it is allow-listed in adopt.allow.  Otherwise a warning
    is returned whether or not the name is in the catalog.
    """
    warnings: list[str] = []
    catalog_names = {e.get("name") for e in load_catalog(config)}

    for name in names:
        if check_allow(name, config):
            continue
        if name in catalog_names:
            warnings.append(
                f"crew skill {name!r} is discovered but not allow-listed — "
                "use `pigeon adopt --allow` to trust it"
            )
        else:
            warnings.append(
                f"crew skill {name!r} is neither a playbook nor a known adopted asset"
            )
    return warnings


def update_allow(names: list[str], config: Config) -> None:
    """Append names to adopt.allow in the on-disk config.yaml."""
    cfg_path = config.contract_dir / "config.yaml"
    try:
        existing: dict[str, Any] = yaml.safe_load(
            cfg_path.read_text(encoding="utf-8")
        ) if cfg_path.exists() else {}
    except yaml.YAMLError:
        existing = {}
    if not isinstance(existing, dict):
        existing = {}
    adopt_section = existing.setdefault("adopt", {})
    allow_list: list[str] = adopt_section.setdefault("allow", [])
    added = False
    for name in names:
        if name not in allow_list:
            allow_list.append(name)
            added = True
    if added:
        cfg_path.write_text(
            yaml.safe_dump(existing, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
