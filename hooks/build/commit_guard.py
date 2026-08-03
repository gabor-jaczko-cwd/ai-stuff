#!/usr/bin/env python3
"""Stop hook for the `build` skill.

Blocks foreman from ending its turn if `.build-state.json` shows any step
marked `done` with no commit SHA recorded -- the hard backstop for the
loop-protocol's commit gate (a step may only be `done` in the same update
that fills in its commit). Inert (exit 0, no output) whenever no
.build-state.json exists in the project, which is the case for every
project not currently running a `build` plan.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import find_cache_files, load_cache, read_stdin_json, unsynced_done_steps  # noqa: E402


def main():
    payload = read_stdin_json()

    # Claude Code sets stop_hook_active when a Stop hook already blocked once
    # in this turn cycle -- never block a second time in the same cycle, or
    # a genuinely stuck step turns into an infinite loop.
    if payload.get("stop_hook_active"):
        return 0

    cache_files = find_cache_files()
    if not cache_files:
        return 0  # no active build plan in this project -- inert

    violations = []
    for path in cache_files:
        cache = load_cache(path)
        if cache is None:
            continue
        bad = unsynced_done_steps(cache)
        if bad:
            feature = cache.get("feature", os.path.dirname(path))
            violations.append((feature, path, bad))

    if not violations:
        return 0

    lines = [
        "build-commit-guard: cannot end this turn -- a step is marked done with no commit recorded.",
        "This violates the build skill's sign-off gate (loop-protocol.md): a step is only done",
        "in the same update that records its commit SHA on the tracker and in the cache. Go back,",
        "commit the step's changes, sync the tracker, and update .build-state.json before stopping.",
        "",
    ]
    for feature, path, bad in violations:
        lines.append(f"  - {feature} ({path}): unsynced done step(s): {', '.join(bad)}")

    sys.stderr.write("\n".join(lines) + "\n")
    return 2  # exit code 2 on a Stop hook blocks the turn from ending


if __name__ == "__main__":
    sys.exit(main())
