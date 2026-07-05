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


def _gemini_usage(obj: Any) -> dict[str, Any] | None:
    """Find a Gemini ``usageMetadata`` report nested anywhere in one JSON event.

    Gemini (the ``generateContent`` REST shape agy wraps) reports usage as
    ``usageMetadata:{promptTokenCount, candidatesTokenCount, totalTokenCount,
    cachedContentTokenCount?, thoughtsTokenCount?}`` — none of claude's
    ``usage:{*_tokens}`` nor opencode's ``tokens:{...}``. The event envelope
    around it varies (a raw REST body, or a streamed chunk), so search
    recursively for the ``usageMetadata`` object.

    ``totalTokenCount`` is authoritative when present; otherwise it is the sum of
    prompt + candidates + thoughts (``cachedContentTokenCount`` is the *cached
    subset* of the prompt, already inside ``promptTokenCount``, so it is never
    added again). Only a non-zero total counts (a streamed-but-empty chunk is not
    a measurement)."""
    if isinstance(obj, dict):
        um = obj.get("usageMetadata")
        if isinstance(um, dict) and any(
            isinstance(um.get(k), (int, float))
            for k in ("totalTokenCount", "promptTokenCount", "candidatesTokenCount")
        ):
            total = um.get("totalTokenCount")
            if not isinstance(total, (int, float)):
                total = sum(int(v) for v in (
                    um.get("promptTokenCount", 0),
                    um.get("candidatesTokenCount", 0),
                    um.get("thoughtsTokenCount", 0),
                    um.get("toolUsePromptTokenCount", 0),
                ) if isinstance(v, (int, float)))
            if int(total) > 0:
                out: dict[str, Any] = {"usage": um, "total_tokens": int(total)}
                # agy/Gemini `-p` print mode ships no cost field; USD is derived
                # downstream from the pricing snapshot, not read from the child.
                for key in ("modelVersion", "model"):
                    if obj.get(key):
                        out["model"] = obj[key]
                        break
                return out
        for v in obj.values():
            found = _gemini_usage(v)
            if found:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _gemini_usage(v)
            if found:
                return found
    return None


def _gemini_parser(candidates: list[Any]) -> dict[str, Any] | None:
    """Parser plugin: Gemini's ``usageMetadata`` object, scanned last-event-first
    (the recursive worker is :func:`_gemini_usage`). See Stage 0 of the
    limitations-closing plan: agy's ``-p`` print mode emits no structured usage
    today, so this parser is the receiving half — the moment agy (or a direct
    Gemini call) surfaces ``usageMetadata``, cost accounting is captured with no
    scheduler-core edit."""
    for obj in candidates:
        g = _gemini_usage(obj)
        if g:
            return g
    return None


# The plugin registry: ordered list of usage parsers tried in turn. Extend it to
# teach pigeon a new vendor's output shape — no scheduler-core edit required.
# Keys are disjoint across the three shapes (``usage`` / ``tokens`` /
# ``usageMetadata``), so registry order is a tie-break only, never a collision.
USAGE_PARSERS: list[UsageParser] = [_claude_usage, _opencode_parser, _gemini_parser]


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


def normalize_usage(usage: dict[str, Any] | None) -> dict[str, int]:
    """Project any vendor's raw ``usage`` object onto the four canonical fields
    Stage 0 of the limitations-closing plan requires archived for *every* trial:
    ``input_tokens``, ``output_tokens``, ``cache_creation_input_tokens``,
    ``cache_read_input_tokens``. Claude already reports these natively; opencode
    and Gemini name the same quantities differently, so a fair cross-model
    token/cache split needs one uniform projection rather than three ad-hoc reads
    at persist time.

    Conventions, chosen to match Claude's (so the fields mean the same thing
    across vendors): ``input_tokens`` is *uncached* prompt only (cache-read
    tokens are reported separately, never double-counted); reasoning/thought
    tokens are billed and counted on the output side. Unknown shapes yield all
    zeros rather than raising — a missing split is archival loss, not a crash."""
    u = usage or {}
    # Claude: native — the canonical fields are already the keys.
    if "input_tokens" in u or "output_tokens" in u:
        return {
            "input_tokens": int(u.get("input_tokens", 0) or 0),
            "output_tokens": int(u.get("output_tokens", 0) or 0),
            "cache_creation_input_tokens": int(u.get("cache_creation_input_tokens", 0) or 0),
            "cache_read_input_tokens": int(u.get("cache_read_input_tokens", 0) or 0),
        }
    # opencode: {input, output, reasoning, cache:{read, write}}
    if "input" in u or "output" in u:
        cache = u.get("cache") if isinstance(u.get("cache"), dict) else {}
        return {
            "input_tokens": int(u.get("input", 0) or 0),
            "output_tokens": int(u.get("output", 0) or 0) + int(u.get("reasoning", 0) or 0),
            "cache_creation_input_tokens": int(cache.get("write", 0) or 0),
            "cache_read_input_tokens": int(cache.get("read", 0) or 0),
        }
    # Gemini: {promptTokenCount, candidatesTokenCount, cachedContentTokenCount,
    # thoughtsTokenCount}. promptTokenCount INCLUDES the cached subset, so the
    # uncached input is prompt minus cached (mirroring Claude's split).
    if "promptTokenCount" in u or "candidatesTokenCount" in u:
        prompt = int(u.get("promptTokenCount", 0) or 0)
        cached = int(u.get("cachedContentTokenCount", 0) or 0)
        return {
            "input_tokens": max(prompt - cached, 0),
            "output_tokens": int(u.get("candidatesTokenCount", 0) or 0)
            + int(u.get("thoughtsTokenCount", 0) or 0),
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": cached,
        }
    return {
        "input_tokens": 0, "output_tokens": 0,
        "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0,
    }


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
