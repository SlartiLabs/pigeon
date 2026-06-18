"""Telemetry usage parsing — a small plugin boundary for vendor output formats.

Each agent CLI reports token usage in its own JSON shape. Rather than bury that
knowledge inside the scheduler core, every shape is a *parser plugin*: a small
callable that, given the JSON candidates mined from a child's output, returns a
normalized ``{usage, total_tokens, ...}`` dict (or ``None`` if it does not
recognize the shape). :data:`USAGE_PARSERS` is the ordered registry the core
consults; the first parser to return a non-``None`` result wins.

Adding support for a new vendor's output format is therefore a *fixture + registry*
edit — write a parser, append it to :data:`USAGE_PARSERS`, drop a sample event
under ``tests/`` — never a change to the run loop (DD C4 / U8). The parse order
is part of the contract: claude's ``usage:{*_tokens}`` shape is tried before
opencode's ``tokens:{...}`` + ``cost`` shape, so a document carrying both reads
as claude (unchanged from the pre-split behavior).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

# A parser plugin: given the JSON candidates mined from a child's output (newest
# event first), return a normalized usage dict, or None if the shape is foreign.
UsageParser = Callable[[list[Any]], "dict[str, Any] | None"]


def _claude_usage(candidates: list[Any]) -> dict[str, Any] | None:
    """Parser plugin: claude ``-p --output-format json`` (a ``usage`` object
    whose ``*_tokens`` fields sum to the total), with optional sibling cost and
    run metadata."""
    for obj in candidates:
        usage = obj.get("usage") if isinstance(obj, dict) else None
        if isinstance(usage, dict) and usage:
            total = sum(
                int(v) for k, v in usage.items()
                if k.endswith("tokens") and isinstance(v, (int, float))
            )
            out: dict[str, Any] = {"usage": usage, "total_tokens": total}
            for key in ("total_cost_usd", "duration_ms", "num_turns", "model"):
                if key in obj:
                    out[key] = obj[key]
            return out
    return None


def _opencode_usage(obj: Any) -> dict[str, Any] | None:
    """Find an opencode usage report nested anywhere in one JSON event.

    opencode (`run --format json`) does NOT use claude's ``usage:{*_tokens}``
    shape — its assistant message carries ``tokens:{total,input,output,
    reasoning,cache:{read,write}}`` with a sibling ``cost``. The event envelope
    around that message varies, so search recursively for the ``tokens`` object
    and read ``cost`` from the same dict. Only a non-zero total counts (a
    streamed-but-empty event is not a measurement)."""
    if isinstance(obj, dict):
        tok = obj.get("tokens")
        if isinstance(tok, dict) and any(
            isinstance(tok.get(k), (int, float)) for k in ("total", "input", "output")
        ):
            total = tok.get("total")
            if not isinstance(total, (int, float)):
                cache = tok.get("cache") if isinstance(tok.get("cache"), dict) else {}
                total = sum(int(v) for v in (
                    tok.get("input", 0), tok.get("output", 0), tok.get("reasoning", 0),
                    cache.get("read", 0), cache.get("write", 0),
                ) if isinstance(v, (int, float)))
            if int(total) > 0:
                out: dict[str, Any] = {"usage": tok, "total_tokens": int(total)}
                if isinstance(obj.get("cost"), (int, float)):
                    out["total_cost_usd"] = obj["cost"]
                for key in ("modelID", "model"):
                    if obj.get(key):
                        out["model"] = obj[key]
                        break
                return out
        for v in obj.values():
            found = _opencode_usage(v)
            if found:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _opencode_usage(v)
            if found:
                return found
    return None


def _opencode_parser(candidates: list[Any]) -> dict[str, Any] | None:
    """Parser plugin: opencode's ``tokens`` object + sibling ``cost``, scanned
    last-event-first (the recursive worker is :func:`_opencode_usage`)."""
    for obj in candidates:
        oc = _opencode_usage(obj)
        if oc:
            return oc
    return None


# The plugin registry: ordered list of usage parsers tried in turn. Extend it to
# teach pigeon a new vendor's output shape — no scheduler-core edit required.
USAGE_PARSERS: list[UsageParser] = [_claude_usage, _opencode_parser]


def _candidates(text: str) -> list[Any]:
    """Mine an agent CLI's output for parseable JSON: the whole document if it
    is one, plus each NDJSON/stream-json line scanned from the last backwards
    (so the final, post-run usage event is found first)."""
    candidates: list[Any] = []
    stripped = text.strip()
    if stripped.startswith("{"):
        try:
            candidates.append(json.loads(stripped))
        except json.JSONDecodeError:
            pass
    for line in reversed(stripped.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            candidates.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return candidates


def _extract_telemetry(text: str) -> dict[str, Any] | None:
    """Mine an agent CLI's output for its final, *measured* usage report.

    Understands ``claude -p --output-format json`` (a single JSON document
    with a ``usage`` object), opencode ``run --format json`` (NDJSON events
    whose assistant message carries a ``tokens`` object + ``cost``), and
    stream-json/NDJSON variants (scanned from the last line backwards). Returns
    ``None`` when no usage report exists — plain-text output is not an error.

    The recognized shapes live in :data:`USAGE_PARSERS`; the first parser to
    claim the candidates wins, so vendor formats are added there, not here.
    """
    candidates = _candidates(text)
    for parser in USAGE_PARSERS:
        result = parser(candidates)
        if result is not None:
            return result
    return None
