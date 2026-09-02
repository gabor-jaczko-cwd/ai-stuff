#!/usr/bin/env python3
"""PostToolUse (matcher: Task) hook for the `build` skill.

inspector now commits and syncs .build-state.json itself, atomically with its
own APPROVE -- there's no longer a separate foreman action to remind about.
What's left is a sanity check: if an inspector dispatch's own response text
looks like APPROVE but .build-state.json still shows a step marked done with
no commit recorded, that's a real bug in inspector's own execution (it said
APPROVE without actually completing the write), not something advisory.
Surfaces it immediately rather than waiting for the Stop hook to catch it.
Inert whenever no .build-state.json exists in the project.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import find_cache_files, load_cache, read_stdin_json, unsynced_done_steps  # noqa: E402


def _extract_text(value):
    """tool_input/tool_response shapes vary; pull out anything string-like."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        parts = []
        for v in value.values():
            parts.append(_extract_text(v))
        return "\n".join(p for p in parts if p)
    if isinstance(value, list):
        return "\n".join(_extract_text(v) for v in value)
    return ""


def looks_like_inspector_call(tool_input):
    text = _extract_text(tool_input).lower()
    return "inspector" in text


def verdict_of(tool_response):
    text = _extract_text(tool_response)
    if "CHANGES_REQUESTED" in text:
        return "CHANGES_REQUESTED"
    if "APPROVE" in text:
        return "APPROVE"
    return None


def main():
    cache_files = find_cache_files()
    if not cache_files:
        return 0  # no active build plan in this project -- inert

    payload = read_stdin_json()
    if payload.get("tool_name") != "Task":
        return 0

    tool_input = payload.get("tool_input", {})
    if not looks_like_inspector_call(tool_input):
        return 0

    verdict = verdict_of(payload.get("tool_response", {}))
    if verdict != "APPROVE":
        return 0

    violations = []
    for path in cache_files:
        cache = load_cache(path)
        if cache is None:
            continue
        bad = unsynced_done_steps(cache)
        if bad:
            violations.append((cache.get("feature", os.path.dirname(path)), bad))

    if not violations:
        return 0  # inspector's APPROVE was genuinely followed through -- nothing to say

    lines = [
        "build-review-commit-reminder: inspector's dispatch looked like APPROVE, but "
        ".build-state.json still shows a done step with no commit recorded. Per "
        "agents/inspector.md, inspector commits atomically with its own APPROVE -- this "
        "means that write didn't actually complete. Do not treat the step as done; "
        "re-check inspector's own execution before moving on.",
    ]
    for feature, bad in violations:
        lines.append(f"  - {feature}: unsynced done step(s): {', '.join(bad)}")

    sys.stderr.write("\n".join(lines) + "\n")
    return 2  # PostToolUse exit 2 surfaces stderr to the driving agent without undoing the tool call


if __name__ == "__main__":
    sys.exit(main())
