"""Shared helpers for the build skill's hooks.

All three hooks (commit-guard, review-commit-reminder, precompact-check) are
gated on the presence of a `.build-state.json` cache file somewhere in the
current project. No cache file means no active `build` plan, and every hook
here becomes a silent no-op -- this is what keeps them inert on every other
project. See ~/.agents/skills/build/references/plan-structure.md for the
cache-file format and the tracker-is-the-record-of-truth rationale.
"""
import json
import os

SKIP_DIRS = {".git", "node_modules", "vendor", "dist", "build", ".venv", "venv", "__pycache__"}
CACHE_FILENAME = ".build-state.json"
MAX_DEPTH = 6


def _walk_bounded(root):
    root = os.path.abspath(root)
    base_depth = root.rstrip(os.sep).count(os.sep)
    for dirpath, dirnames, filenames in os.walk(root):
        depth = dirpath.rstrip(os.sep).count(os.sep) - base_depth
        if depth >= MAX_DEPTH:
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".") or d == ".claude"]
        if CACHE_FILENAME in filenames:
            yield os.path.join(dirpath, CACHE_FILENAME)


def find_cache_files(cwd=None):
    """Return paths to every .build-state.json under cwd (bounded, defensive)."""
    cwd = cwd or os.getcwd()
    found = []
    try:
        for path in _walk_bounded(cwd):
            found.append(path)
    except OSError:
        pass
    return found


def load_cache(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def read_stdin_json():
    import sys

    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return {}
        return json.loads(raw)
    except Exception:
        return {}


def unsynced_done_steps(cache):
    """Steps marked done with no commit recorded -- the exact violation the commit-guard blocks on."""
    if not cache or not isinstance(cache, dict):
        return []
    steps = cache.get("steps", {})
    if not isinstance(steps, dict):
        return []
    bad = []
    for step_id, info in steps.items():
        if not isinstance(info, dict):
            continue
        if info.get("status") == "done" and not info.get("commit"):
            bad.append(step_id)
    return bad
