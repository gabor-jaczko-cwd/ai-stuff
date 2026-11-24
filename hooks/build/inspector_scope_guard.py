#!/usr/bin/env python3
"""PreToolUse hook (matcher: Write|Edit|Bash) for the `build` skill.

inspector legitimately needs Bash (running evals, docker exec, throwaway
verification probes) and Write/Edit (committing, syncing .build-state.json
and its append-only .build-state.log.jsonl sidecar, its own agent-memory,
scratch verification artifacts) -- unlike foreman, its
tools can't just be withheld. This hook is the actual enforcement of the
allowlist described in agents/inspector.md: real source/test files stay off
limits at the tool level, not just by instruction.

Registered in inspector's own frontmatter (agents/inspector.md), so Claude
Code only runs it while an inspector subagent is running. It still checks
agent_type == "inspector" and the presence of an active build plan, and is a
no-op otherwise.

This is a best-effort static guard, not a sandbox -- it pattern-matches
shell commands, which can't be parsed with full fidelity. It exists to
close the specific bypass real build sessions were observed using
(`sed -i` editing files directly, shell output-redirection into real repo
files) rather than to guarantee no clever command could ever get past it.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import agent_type, is_under, log_path_for, parse_scratch_paths, plan_paths, read_stdin_json  # noqa: E402

ALLOWED_GIT_SUBCOMMANDS = {
    "add", "commit", "diff", "show", "status", "log", "blame", "rev-parse", "ls-files", "describe",
}
BLOCKED_BASH_WORDS = re.compile(r"\b(rm|mv|cp|truncate)\b")
SED_IN_PLACE = re.compile(r"\bsed\b[^|;&]*(-i\b|--in-place\b)")
BARE_REDIRECT = re.compile(r"(?<!\d)>{1,2}(?!&)")


def _scratchpad_ok(path):
    # OS-level scratchpad: outside any repo, structurally can't leak into a commit.
    # Heuristic match rather than an exact session path, since this hook is
    # project-agnostic and doesn't know this session's literal scratchpad dir.
    norm = path.replace(os.sep, "/")
    return norm.startswith("/tmp/") and "/scratchpad/" in norm


def write_edit_allowed(file_path, cwd):
    target = os.path.abspath(file_path)

    for _plan_md, cache_path in plan_paths(cwd):
        if target == cache_path:
            return True
        if target == log_path_for(cache_path):
            return True

    if is_under(target, os.path.join(cwd, ".claude", "agent-memory", "inspector")):
        return True

    if _scratchpad_ok(target):
        return True

    for scratch_root in parse_scratch_paths(cwd):
        if is_under(target, scratch_root):
            return True

    return False


def bash_violation(command):
    """Returns a reason string if the command should be blocked, else None."""
    for m in re.finditer(r"\bgit\s+(\S+)", command):
        sub = m.group(1)
        if sub not in ALLOWED_GIT_SUBCOMMANDS:
            return f"git {sub} is not in inspector's allowed git subcommands ({', '.join(sorted(ALLOWED_GIT_SUBCOMMANDS))})"

    if SED_IN_PLACE.search(command):
        return "sed -i / --in-place edits a file directly -- use Write for scratch artifacts, or CHANGES_REQUESTED feedback for real files"

    if BLOCKED_BASH_WORDS.search(command):
        return "rm/mv/cp/truncate are blocked outright -- inspector doesn't need them for anything in its scope"

    if BARE_REDIRECT.search(command):
        return "shell output-redirection to a file is blocked -- use the Write tool for scratch artifacts instead"

    return None


def main():
    payload = read_stdin_json()

    if agent_type(payload) != "inspector":
        return 0

    cwd = payload.get("cwd") or os.getcwd()
    if not plan_paths(cwd):
        return 0  # no active build plan in this project -- inert

    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input", {})

    if tool_name in ("Write", "Edit"):
        file_path = tool_input.get("file_path")
        if file_path and not write_edit_allowed(file_path, cwd):
            sys.stderr.write(
                "build-inspector-scope-guard: blocked. inspector's Write/Edit is scoped to "
                ".build-state.json, its .build-state.log.jsonl sidecar, "
                ".claude/agent-memory/inspector/**, the OS scratchpad, and "
                "this project's declared scratch_paths -- see agents/inspector.md. "
                f"Requested: {file_path}. Real source/test changes belong in CHANGES_REQUESTED "
                "feedback for crewman, not a direct edit.\n"
            )
            return 2

    elif tool_name == "Bash":
        command = tool_input.get("command", "")
        reason = bash_violation(command)
        if reason:
            sys.stderr.write(
                f"build-inspector-scope-guard: blocked ({reason}). "
                "inspector may run git add/git commit and read-only git/inspection commands; "
                "everything else that mutates the repo is out of scope -- see agents/inspector.md.\n"
            )
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
