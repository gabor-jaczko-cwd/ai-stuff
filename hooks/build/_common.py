"""Shared helpers for the build skill's hooks.

Every hook here is gated on the presence of a `.build-state.json` cache file
somewhere in the current project. No cache file means no active `build`
plan, and every hook here becomes a silent no-op -- this is what keeps them
inert on every other project. See
~/.agents/skills/build/references/plan-structure.md for the cache-file
format, and references/project-context.md for the profile schema
(including `scratch_paths`).
"""
import json
import os
import re

SKIP_DIRS = {".git", "node_modules", "vendor", "dist", "build", ".venv", "venv", "__pycache__"}
CACHE_FILENAME = ".build-state.json"
LOG_FILENAME = ".build-state.log.jsonl"
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


def agent_type(payload):
    """The subagent's agent_type/agent_id fields are only present when a hook fires
    inside a subagent call. Returns None for a main-session (non-subagent) tool call.
    """
    return payload.get("agent_type")


def plan_paths(cwd=None):
    """(plan_md_path, cache_path) for every active plan under cwd -- the two paths
    foreman's PLAN.md/.build-state.json allowlist is scoped to. Derived from
    find_cache_files() since .build-state.json and PLAN.md are documented siblings
    in the same plan folder (see plan-structure.md's folder layout).
    """
    pairs = []
    for cache_path in find_cache_files(cwd):
        plan_md = os.path.join(os.path.dirname(cache_path), "PLAN.md")
        pairs.append((os.path.abspath(plan_md), os.path.abspath(cache_path)))
    return pairs


def log_path_for(cache_path):
    """The append-only sidecar log path for a given .build-state.json path -- see
    plan-structure.md's Cache file section. inspector archives a step's full review
    content here on APPROVE, which is what keeps the live cache bounded over a long plan.
    """
    return os.path.join(os.path.dirname(cache_path), LOG_FILENAME)


def is_under(path, base):
    """True if abspath(path) is base itself or somewhere inside it."""
    path = os.path.abspath(path)
    base = os.path.abspath(base)
    return path == base or path.startswith(base + os.sep)


def parse_scratch_paths(cwd):
    """Read `scratch_paths:` out of .claude/local/build.md's YAML frontmatter, as a
    list of repo-relative path prefixes. Deliberately tiny/manual parser (no PyYAML
    dependency) -- only handles the simple `key:\\n  - item` list shape the profile
    template uses. Returns absolute paths, or [] if the profile or field is absent.
    Validation that each entry is actually gitignored happens once at profile-load
    time (Step 0), not here -- this just returns what the profile declares.
    """
    profile_path = os.path.join(cwd, ".claude", "local", "build.md")
    try:
        with open(profile_path, "r") as f:
            text = f.read()
    except OSError:
        return []

    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return []
    frontmatter = m.group(1)

    lines = frontmatter.splitlines()
    paths = []
    in_list = False
    for line in lines:
        if re.match(r"^scratch_paths\s*:\s*$", line):
            in_list = True
            continue
        if in_list:
            item = re.match(r"^\s*-\s*(.+?)\s*$", line)
            if item:
                paths.append(os.path.abspath(os.path.join(cwd, item.group(1).strip("\"'"))))
                continue
            in_list = False  # dedented past the list
    return paths


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
