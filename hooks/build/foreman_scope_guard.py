#!/usr/bin/env python3
"""PreToolUse hook (matcher: Read|Write) for the `build` skill.

foreman is pure orchestration and its agent definition already excludes
Bash/Grep/Edit from its tools -- those simply aren't offered, no hook needed.
Read/Write are still granted (it needs to read PLAN.md and poll/write
.build-state.json), but as general-purpose tools they aren't path-scoped by
the tools list alone. This hook is that scoping: it blocks any foreman
Read/Write call whose target isn't exactly this plan's PLAN.md or
.build-state.json.

Fires for every subagent's Read/Write calls (the matcher can't filter by
agent), but is a no-op unless agent_type == "foreman" or there's no active
build plan in this project -- inert everywhere else.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import agent_type, is_under, plan_paths, read_stdin_json  # noqa: E402


def main():
    payload = read_stdin_json()

    if agent_type(payload) != "foreman":
        return 0

    tool_name = payload.get("tool_name")
    if tool_name not in ("Read", "Write"):
        return 0

    file_path = payload.get("tool_input", {}).get("file_path")
    if not file_path:
        return 0

    cwd = payload.get("cwd") or os.getcwd()
    pairs = plan_paths(cwd)
    if not pairs:
        return 0  # no active build plan in this project -- inert

    allowed = {p for pair in pairs for p in pair}
    target = os.path.abspath(file_path)
    if target in allowed:
        return 0

    sys.stderr.write(
        "build-foreman-scope-guard: blocked. foreman may only Read/Write PLAN.md "
        "and .build-state.json for the active plan -- see agents/foreman.md. "
        f"Requested: {file_path}. If this step genuinely needs to touch other files, "
        "that belongs to crewman or inspector, not foreman.\n"
    )
    return 2  # PreToolUse exit 2 blocks the tool call


if __name__ == "__main__":
    sys.exit(main())
