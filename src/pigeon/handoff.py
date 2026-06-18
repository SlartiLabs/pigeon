"""Handoff contract: build, validate, serialize, append.

A handoff is a JSON message carrying sparse state deltas plus pointers. It is
validated against ``.pigeon/handoff.schema.json`` (JSON Schema draft 2020-12)
**on receipt**, and appended to ``.pigeon/handoffs/`` as ``<sid>-<n>.json``.
Logs are append-only; handoffs are never rewritten in place.

The ``schema_version`` field is not merely recorded — it **gates** compatibility
(see the COMPATIBILITY POLICY below). Every receive path rejects a handoff this
pigeon cannot read; :func:`upgrade_handoff` (``pigeon migrate``) carries an
older one forward.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from . import SCHEMA_VERSION
from .config import Config

_FILENAME_RE = re.compile(r"^(?P<sid>.+)-(?P<n>\d+)\.json$")


class HandoffValidationError(ValueError):
    """A handoff failed schema validation. Message lists every violation."""


class HandoffCompatibilityError(HandoffValidationError):
    """A handoff's ``schema_version`` is incompatible with this pigeon.

    A subclass of :class:`HandoffValidationError` so existing receive paths that
    catch validation failures keep catching this one — an incompatible version
    *is* a kind of invalid handoff, just diagnosed against the contract version
    rather than the JSON structure.
    """


class HandoffMigrationError(ValueError):
    """A handoff could not be carried forward to the requested schema version."""


# --- COMPATIBILITY POLICY (the contract's versioning rule) -----------------
#
# ``schema_version`` is a two-part ``MAJOR.MINOR`` string. The running pigeon
# advertises the version it speaks as ``pigeon.SCHEMA_VERSION``. A received
# handoff is *compatible* — and therefore accepted — iff:
#
#     * its MAJOR equals the current MAJOR, **and**
#     * its MINOR is <= the current MINOR.
#
# Case by case:
#   - Same major, older-or-equal minor -> ACCEPT. Minor bumps are strictly
#     additive (new optional fields), so the current schema is a superset and
#     validates an older handoff unchanged. This keeps deployed producers
#     working after pigeon gains a field (e.g. 1.0 handoffs under a 1.1 reader).
#   - Same major, NEWER minor          -> REJECT. The handoff came from a newer
#     pigeon that may use fields this one does not know; upgrade pigeon.
#   - Different major                  -> REJECT. A major bump is a breaking
#     change (fields removed/renamed/re-defined); run ``pigeon migrate`` to
#     carry the handoff forward.
#
# The gate is enforced in :func:`validate_handoff`, so every receive path
# (:func:`load_handoff`, ``pigeon handoff --validate``, coordinate's on-receipt
# validation) rejects an incompatible handoff with a clear, actionable error.

_VERSION_RE = re.compile(r"^(\d+)\.(\d+)$")


def parse_schema_version(version: str) -> tuple[int, int]:
    """Parse a ``MAJOR.MINOR`` schema version into an ``(int, int)`` tuple."""
    match = _VERSION_RE.match(version or "")
    if not match:
        raise HandoffMigrationError(
            f"malformed schema_version {version!r}; expected MAJOR.MINOR"
        )
    return int(match.group(1)), int(match.group(2))


def is_compatible(version: str, *, current: str = SCHEMA_VERSION) -> bool:
    """True iff a handoff at ``version`` is readable by ``current`` pigeon.

    Same major and an equal-or-older minor — see the COMPATIBILITY POLICY above.
    """
    try:
        maj, minor = parse_schema_version(version)
        cur_maj, cur_minor = parse_schema_version(current)
    except HandoffMigrationError:
        return False
    return maj == cur_maj and minor <= cur_minor


def check_compatibility(handoff: dict[str, Any], *, current: str = SCHEMA_VERSION) -> None:
    """Raise :class:`HandoffCompatibilityError` if the handoff can't be read here."""
    version = handoff.get("schema_version")
    if isinstance(version, str) and is_compatible(version, current=current):
        return
    shown = version if isinstance(version, str) else repr(version)
    too_new = False
    if isinstance(version, str):
        try:
            too_new = parse_schema_version(version) > parse_schema_version(current)
        except HandoffMigrationError:
            too_new = False
    remedy = (
        f"upgrade pigeon to read schema {shown}"
        if too_new
        else f"run `pigeon migrate <file>` to carry it forward to {current}"
    )
    raise HandoffCompatibilityError(
        f"incompatible handoff: schema_version {shown} cannot be read by pigeon "
        f"{current} ({remedy}). Policy: same major, minor <= current."
    )


def _migrate_1_0_to_1_1(handoff: dict[str, Any]) -> dict[str, Any]:
    """1.0 -> 1.1: the optional ``crew`` field was added; no existing field
    changes shape, so the data carries forward untouched (the caller bumps the
    recorded version)."""
    return dict(handoff)


# Ordered, stepwise migrations: source version -> (next version, transform).
# Each step carries a handoff across exactly one version boundary; the chain is
# walked until the target is reached, so a future bump only adds one entry here.
_MIGRATIONS: dict[str, tuple[str, Callable[[dict[str, Any]], dict[str, Any]]]] = {
    "1.0": ("1.1", _migrate_1_0_to_1_1),
}


def upgrade_handoff(handoff: dict[str, Any], *, to: str = SCHEMA_VERSION) -> dict[str, Any]:
    """Carry a handoff forward to schema version ``to`` (default: current).

    Walks the registered migration chain one step at a time. Returns a new dict;
    the input is not mutated. Raises :class:`HandoffMigrationError` when the
    handoff has no usable version, is newer than ``to`` (no downgrades), or no
    migration path reaches ``to``.
    """
    if not isinstance(handoff, dict):
        raise HandoffMigrationError(
            f"handoff must be a JSON object, got {type(handoff).__name__!r}"
        )
    version = handoff.get("schema_version")
    if not isinstance(version, str):
        raise HandoffMigrationError("handoff has no schema_version to migrate from")
    src = parse_schema_version(version)
    target = parse_schema_version(to)
    if src == target:
        return dict(handoff)
    if src > target:
        raise HandoffMigrationError(
            f"cannot downgrade handoff {version} -> {to}; upgrade pigeon instead"
        )
    migrated = dict(handoff)
    seen: set[str] = set()
    while migrated["schema_version"] != to:
        cur = migrated["schema_version"]
        if cur in seen:  # guard a malformed (cyclic) registry rather than spin
            raise HandoffMigrationError(f"cyclic migration chain at {cur}")
        seen.add(cur)
        step = _MIGRATIONS.get(cur)
        if step is None:
            raise HandoffMigrationError(f"no migration path from {cur} to {to}")
        next_version, transform = step
        migrated = transform(migrated)
        migrated["schema_version"] = next_version  # the chain owns version bookkeeping
    return migrated


def build_handoff(
    *,
    sid: str,
    frm: str,
    to: str,
    done: list[str],
    doing: str,
    artifacts: list[str] | None = None,
    decisions: dict[str, Any] | None = None,
    rag: dict[str, Any] | None = None,
    constraints: dict[str, Any] | None = None,
    crew: dict[str, Any] | None = None,
    context_ref: str | None = None,
    salvaged_upstream: list[str] | None = None,
    schema_version: str = SCHEMA_VERSION,
) -> dict[str, Any]:
    """Construct a handoff dict. Optional fields are omitted when empty."""
    state: dict[str, Any] = {"done": list(done), "doing": doing}
    if artifacts:
        state["artifacts"] = list(artifacts)
    if decisions:
        state["decisions"] = dict(decisions)
    if salvaged_upstream:
        state["salvaged_upstream"] = list(salvaged_upstream)
    handoff: dict[str, Any] = {
        "schema_version": schema_version,
        "sid": sid,
        "from": frm,
        "to": to,
        "state": state,
    }
    if rag:
        handoff["rag"] = dict(rag)
    if constraints:
        handoff["constraints"] = dict(constraints)
    if crew:
        handoff["crew"] = dict(crew)
    if context_ref is not None:
        handoff["context_ref"] = context_ref
    return handoff


def load_schema(config: Config) -> dict[str, Any]:
    path = config.handoff_schema
    if not path.is_file():
        raise FileNotFoundError(f"Handoff schema not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def validate_handoff(
    handoff: dict[str, Any],
    config: Config,
    schema: dict[str, Any] | None = None,
) -> None:
    """Validate a handoff: structure first, then the compatibility gate.

    Raises :class:`HandoffValidationError` with a clear, full message on a
    structural violation, or :class:`HandoffCompatibilityError` (a subclass) if
    the structure is fine but ``schema_version`` is one this pigeon cannot read.
    """
    schema = schema if schema is not None else load_schema(config)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(handoff), key=lambda e: list(e.absolute_path))
    if errors:
        lines = []
        for err in errors:
            loc = "/".join(str(p) for p in err.absolute_path) or "<root>"
            lines.append(f"  - at {loc}: {err.message}")
        raise HandoffValidationError(
            "Invalid handoff (" + str(len(errors)) + " error(s)):\n" + "\n".join(lines)
        )
    # Structure is sound (so schema_version is present and well-formed); now
    # gate on the contract version it declares.
    check_compatibility(handoff)


def serialize_handoff(handoff: dict[str, Any]) -> str:
    """Canonical JSON for a handoff (sorted keys, trailing newline)."""
    return json.dumps(handoff, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _next_index(handoffs_dir: Path, sid: str) -> int:
    if not handoffs_dir.is_dir():
        return 1
    highest = 0
    for child in handoffs_dir.iterdir():
        match = _FILENAME_RE.match(child.name)
        if match and match.group("sid") == sid:
            highest = max(highest, int(match.group("n")))
    return highest + 1


def next_handoff_path(config: Config, sid: str) -> Path:
    """Next append-only path ``<sid>-<n>.json`` for a session."""
    return config.handoffs_dir / f"{sid}-{_next_index(config.handoffs_dir, sid)}.json"


def claim_path(directory: Path, name_for: Callable[[int], str]) -> Path:
    """Atomically claim the next free numbered file (no TOCTOU).

    ``name_for(n)`` -> filename for attempt ``n``. The file is created with
    O_CREAT|O_EXCL, so two concurrent writers can never claim the same slot —
    the loser just moves to the next index. Returns the claimed (empty) path.
    """
    directory.mkdir(parents=True, exist_ok=True)
    n = 1
    while True:
        candidate = directory / name_for(n)
        if not candidate.exists():
            try:
                os.close(os.open(candidate, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
                return candidate
            except FileExistsError:
                pass  # raced: another writer claimed it between checks
        n += 1


def write_handoff(
    handoff: dict[str, Any],
    config: Config,
    *,
    validate: bool = True,
) -> Path:
    """Validate (by default) then append the handoff. Returns the written path."""
    if validate:
        validate_handoff(handoff, config)
    start = _next_index(config.handoffs_dir, handoff["sid"])
    path = claim_path(config.handoffs_dir,
                      lambda n, s=handoff["sid"], b=start: f"{s}-{b + n - 1}.json")
    path.write_text(serialize_handoff(handoff), encoding="utf-8")
    return path


def load_handoff(path: Path | str, config: Config, *, validate: bool = True) -> dict[str, Any]:
    """Load a handoff from disk, validating on receipt by default."""
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    if validate:
        validate_handoff(obj, config)
    return obj
