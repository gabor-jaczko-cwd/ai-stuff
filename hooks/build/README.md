# build hooks

Backstops for the `build` skill's sign-off gates and scoping rules (see `skills/build/references/loop-protocol.md` and `skills/build/agents/*.md` in this repo). All five are gated on finding a `.build-state.json` cache file anywhere under the current project — with no active `build` plan, they're silent no-ops.

- `commit_guard.py` — **Stop** hook. Blocks ending the turn if any step is `done` with no commit SHA recorded.
- `review_commit_reminder.py` — **PostToolUse** hook (matcher `Task`). Sanity-checks, right after an `inspector` dispatch that looked like APPROVE, that the commit actually landed in `.build-state.json`.
- `precompact_check.py` — **PreCompact** hook. Reminds whoever is driving the session to sync the tracker/cache before context is lost.
- `foreman_scope_guard.py` — **PreToolUse** hook (matcher `Read|Write`). Blocks `foreman`'s Read/Write outside exactly `PLAN.md` and `.build-state.json` for the active plan — the mechanical enforcement behind "foreman is pure orchestration."
- `inspector_scope_guard.py` — **PreToolUse** hook (matcher `Write|Edit|Bash`). Blocks `inspector`'s Write/Edit/Bash outside its allowlist (git add/commit, `.build-state.json` and its `.build-state.log.jsonl` sidecar, its own agent-memory, the scratchpad, and this project's declared `scratch_paths`) — the mechanical enforcement behind "inspector never touches real code directly." Best-effort static pattern-matching, not a full sandbox.

The last two rely on the hook payload's `agent_type` field, which the harness only populates inside a subagent call — see the `hooks` doc's "common input fields." They're no-ops for any tool call that isn't actually running as `foreman`/`inspector`.

## Install

Symlink this directory into `~/.claude/hooks/build`:

```bash
mkdir -p ~/.claude/hooks
ln -s ../../.agents/hooks/build ~/.claude/hooks/build
```

Then merge the following into the top-level `"hooks"` key of `~/.claude/settings.json` (merge the arrays — don't overwrite any existing hooks for the same event, e.g. an existing `PreToolUse` entry):

```json
{
  "PreToolUse": [
    {
      "matcher": "Read|Write",
      "hooks": [
        { "type": "command", "command": "python3 ~/.claude/hooks/build/foreman_scope_guard.py" }
      ]
    },
    {
      "matcher": "Write|Edit|Bash",
      "hooks": [
        { "type": "command", "command": "python3 ~/.claude/hooks/build/inspector_scope_guard.py" }
      ]
    }
  ],
  "PostToolUse": [
    {
      "matcher": "Task",
      "hooks": [
        { "type": "command", "command": "python3 ~/.claude/hooks/build/review_commit_reminder.py" }
      ]
    }
  ],
  "Stop": [
    {
      "hooks": [
        { "type": "command", "command": "python3 ~/.claude/hooks/build/commit_guard.py" }
      ]
    }
  ],
  "PreCompact": [
    {
      "hooks": [
        { "type": "command", "command": "python3 ~/.claude/hooks/build/precompact_check.py" }
      ]
    }
  ]
}
```

`settings.json` itself is not tracked in this repo (it mixes this machine's unrelated personal config with the hook wiring) — only this fragment is, so it can be merged in by hand or by a setup script on any machine that wants the `build` skill.
