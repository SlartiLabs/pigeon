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
from urllib.parse import urlsplit, urlunsplit

import yaml

from .config import Config
from .skills import GEN_MARKER

# Argument tokens that signal a secret is being passed on an MCP server's
# command line (e.g. ["--api-key", "sk-…"]). Matched case-insensitively.
_SECRET_ARG_RE = re.compile(
    r"(?i)(token|secret|api[_-]?key|password|passwd|pwd|auth|credential|bearer)"
)


def _redact_url(url: Any) -> tuple[str | None, bool]:
    """Strip userinfo and query from an MCP URL; report if either was present.

    A connection string may carry credentials in the userinfo
    (``postgres://user:pass@host``) or a query token (``?token=sk-…``). Both are
    secrets that must never reach ``catalog.json`` (§6). Returns
    ``(safe_url, had_secret)``; an unparseable URL is dropped (``None``) rather
    than risk leaking an embedded credential.
    """
    if not url or not isinstance(url, str):
        return (url if isinstance(url, str) else None), False
    try:
        parts = urlsplit(url)
    except ValueError:
        return None, True
    had_secret = bool(parts.username or parts.password or parts.query)
    if not had_secret:
        return url, False
    netloc = parts.hostname or ""
    if parts.port:
        netloc = f"{netloc}:{parts.port}"
    return urlunsplit((parts.scheme, netloc, parts.path, "", "")), True


def _args_have_secret(args: Any) -> bool:
    """True if any command-line arg looks like it carries a secret."""
    if not isinstance(args, list):
        return False
    return any(isinstance(a, str) and _SECRET_ARG_RE.search(a) for a in args)


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
        "provenance": "pigeon-generated" if GEN_MARKER in text else "user-authored",
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
        # Secrets may hide in env, in the url (userinfo/query) or in args
        # (e.g. --api-key). Inventory only needs name/command/url + the flag, so
        # args are dropped entirely and the url is redacted before storage (§6).
        safe_url, url_secret = _redact_url(cfg.get("url"))
        records.append({
            "name": str(name),
            "kind": "mcp",
            "command": cfg.get("command"),
            "url": safe_url,
            "has_secrets": bool(env) or url_secret or _args_have_secret(cfg.get("args")),
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
        try:
            md_files = sorted(src.glob("*.md"))
        except OSError:
            continue  # unreadable source dir (e.g. PermissionError) — skip, don't crash
        for md_file in md_files:
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
        try:
            skill_dirs = sorted(src.iterdir())
        except OSError:
            continue  # unreadable source dir (e.g. PermissionError) — skip, don't crash
        for skill_dir in skill_dirs:
            if not skill_dir.is_dir():
                continue
            record = parse_skill(skill_dir)
            if record is None or record.get("provenance") == "pigeon-generated":
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


def _make_import_page(entry: dict[str, Any]) -> str:
    """Build playbook page content from a catalog entry (no GEN_MARKER).

    Frontmatter: name, description, record_type: skill.
    Body: entry['body'] if present, else empty string.
    """
    body = entry.get("body") or ""
    fm: dict[str, Any] = {
        "name": entry["name"],
        "description": entry.get("description") or "",
        "record_type": "skill",
    }
    yaml_block = yaml.dump(fm, default_flow_style=False, allow_unicode=True)
    return f"---\n{yaml_block}---\n\n{body}"


def import_asset(name: str, config: Config) -> None:
    """Copy an allow-listed catalog entry into .pigeon/memory/playbooks/<name>.md.

    Refuses with a clear exception if:
    - ``name`` is not in the catalog (KeyError)
    - ``name`` is not allow-listed (ValueError)
    - the catalog entry is an MCP record (ValueError)
    - a playbook of that name already exists (FileExistsError)

    The written page carries no GEN_MARKER, so ``refresh`` treats it as
    hand-written and never clobbers it.
    """
    catalog = load_catalog(config)
    entry = next((e for e in catalog if e.get("name") == name), None)
    if entry is None:
        raise KeyError(f"adopt: {name!r} not found in catalog")
    if not check_allow(name, config):
        raise ValueError(
            f"adopt: {name!r} is not allow-listed — "
            "use `pigeon adopt --allow` to enable it"
        )
    if entry.get("kind") == "mcp":
        raise ValueError(
            f"adopt: cannot import MCP asset {name!r} — "
            "MCP records are inventory-only, not importable"
        )
    target = config.memory_dir / "playbooks" / f"{name}.md"
    if target.exists():
        raise FileExistsError(
            f"adopt: {name!r} already exists: "
            f"{target.relative_to(config.root)}"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_make_import_page(entry), encoding="utf-8")


def update_allow(names: list[str], config: Config) -> list[str]:
    """Add names to adopt.allow in .pigeon/config.yaml; return those newly added.

    The config is human-edited and heavily commented, so this does a *targeted*
    text edit (append a fresh ``adopt:`` block, or insert into an existing
    ``allow:`` list) rather than a full safe_dump round-trip that would strip
    every comment. It refuses to proceed — rather than silently overwrite — if
    the existing config is not parseable YAML.
    """
    cfg_path = config.contract_dir / "config.yaml"
    text = cfg_path.read_text(encoding="utf-8") if cfg_path.exists() else ""
    try:
        parsed = yaml.safe_load(text) if text.strip() else {}
    except yaml.YAMLError as exc:
        raise ValueError(
            f"refusing to edit {cfg_path}: it is not valid YAML ({exc}); "
            "fix it by hand before running `pigeon adopt --allow`"
        ) from None
    if parsed is not None and not isinstance(parsed, dict):
        raise ValueError(
            f"refusing to edit {cfg_path}: its top level is not a mapping"
        )

    current: list[str] = []
    adopt_cfg = (parsed or {}).get("adopt")
    if isinstance(adopt_cfg, dict) and isinstance(adopt_cfg.get("allow"), list):
        current = [a for a in adopt_cfg["allow"] if isinstance(a, str)]
    # New names not already allowed, de-duped, order preserved.
    seen: set[str] = set(current)
    new = [n for n in names if not (n in seen or seen.add(n))]
    if not new:
        return []

    _write_allow(cfg_path, text, current, new)
    return new


def _write_allow(cfg_path: Path, text: str, current: list[str],
                 new: list[str]) -> None:
    """Comment-preserving insert of ``new`` names into adopt.allow.

    Handles the three real states of the on-disk config: no ``adopt:`` block
    (append a fresh one), ``allow: []`` (expand to a block list), and an existing
    ``allow:`` block list (insert after the last item). Any other hand-authored
    shape is left untouched and the caller is told to edit by hand — never a
    blind rewrite.
    """
    lines = text.splitlines()
    adopt_idx = next(
        (i for i, ln in enumerate(lines) if re.match(r"^adopt:\s*$", ln)), None)

    if adopt_idx is None:
        block = ["", "adopt:", "  allow:"] + [f"    - {n}" for n in current + new]
        cfg_path.write_text(
            (text.rstrip("\n") + "\n" if text.strip() else "") + "\n".join(block) + "\n",
            encoding="utf-8")
        return

    end = len(lines)
    for i in range(adopt_idx + 1, len(lines)):
        if lines[i] and not lines[i][0].isspace():
            end = i
            break

    for i in range(adopt_idx + 1, end):
        m = re.match(r"^(\s+)allow:\s*\[\s*\]\s*$", lines[i])
        if m:
            base = m.group(1)
            lines[i:i + 1] = (
                [f"{base}allow:"] + [f"{base}  - {n}" for n in current + new])
            cfg_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return

    allow_idx = next(
        (i for i in range(adopt_idx + 1, end)
         if re.match(r"^\s+allow:\s*$", lines[i])), None)
    if allow_idx is not None:
        insert_at, indent = allow_idx + 1, "    "
        for i in range(allow_idx + 1, end):
            if re.match(r"^\s+-\s", lines[i]):
                indent = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
                insert_at = i + 1
            elif lines[i].strip():
                break
        lines[insert_at:insert_at] = [f"{indent}- {n}" for n in new]
        cfg_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    raise ValueError(
        f"refusing to auto-edit the existing 'adopt:' block in {cfg_path}; "
        f"add these to adopt.allow by hand: {', '.join(new)}")
