#!/usr/bin/env python3
"""PostToolUse (matcher: Task) hook for the `build` skill.

Fires right after an `inspector` subagent call returns, and if the verdict
looks like APPROVE, reminds foreman to commit and sync the tracker/cache
before moving on -- inspector's own instructions already say this, but the
reminder is a cheap nudge against it getting lost under context pressure.
Inert whenever no .build-state.json exists in the project.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import find_cache_files, read_stdin_json  # noqa: E402


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
    if not find_cache_files():
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

    sys.stderr.write(
        "build-review-commit-reminder: inspector returned APPROVE. Per loop-protocol.md, "
        "commit this step's changes now, post the SHA and verdict to the tracker, and update "
        ".build-state.json -- before dispatching the next step or ending your turn.\n"
    )
    return 2  # PostToolUse exit 2 surfaces stderr to the driving agent without undoing the tool call


if __name__ == "__main__":
    sys.exit(main())
