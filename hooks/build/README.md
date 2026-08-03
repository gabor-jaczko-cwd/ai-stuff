# build hooks

Backstops for the `build` skill's sign-off gates (see `skills/build/references/loop-protocol.md` in this repo). All three are gated on finding a `.build-state.json` cache file anywhere under the current project — with no active `build` plan, they're silent no-ops.

- `commit_guard.py` — **Stop** hook. Blocks ending the turn if any step is `done` with no commit SHA recorded.
- `review_commit_reminder.py` — **PostToolUse** hook (matcher `Task`). Reminds `foreman` to commit right after `inspector` returns APPROVE.
- `precompact_check.py` — **PreCompact** hook. Reminds whoever is driving the session to sync the tracker/cache before context is lost.

## Install

Symlink this directory into `~/.claude/hooks/build`:

```bash
mkdir -p ~/.claude/hooks
ln -s ../../.agents/hooks/build ~/.claude/hooks/build
```

Then merge the following into the top-level `"hooks"` key of `~/.claude/settings.json` (merge the arrays — don't overwrite any existing hooks for the same event, e.g. an existing `PreToolUse` entry):

```json
{
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
