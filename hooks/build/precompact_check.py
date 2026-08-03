#!/usr/bin/env python3
"""PreCompact hook for the `build` skill.

Fires before any compaction (manual or automatic) while a build plan is
active, reminding whoever is driving the session that the tracker and
.build-state.json must be current first -- compaction will proceed either
way, this is a safety-net reminder, not a hard gate (unlike commit_guard.py's
Stop-hook block). Inert whenever no .build-state.json exists in the project.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import find_cache_files, load_cache, unsynced_done_steps  # noqa: E402


def main():
    cache_files = find_cache_files()
    if not cache_files:
        return 0  # no active build plan in this project -- inert

    lines = [
        "build-precompact-check: a build plan is active in this project. Before context is "
        "compacted, make sure the tracker and .build-state.json are current for every step "
        "touched this turn (per context-compaction.md) -- once compacted, anything not synced "
        "there is gone.",
    ]

    any_unsynced = False
    for path in cache_files:
        cache = load_cache(path)
        if cache is None:
            continue
        bad = unsynced_done_steps(cache)
        if bad:
            any_unsynced = True
            feature = cache.get("feature", os.path.dirname(path))
            lines.append(f"  - {feature} ({path}): already unsynced: {', '.join(bad)} -- fix this now.")

    sys.stderr.write("\n".join(lines) + "\n")
    # Best-effort reminder only -- PreCompact has no documented hard-block semantics the way
    # Stop does, so this never tries to prevent compaction from happening. Non-zero exit here
    # is just how the message reliably surfaces in the transcript.
    return 2 if any_unsynced else 0


if __name__ == "__main__":
    sys.exit(main())
