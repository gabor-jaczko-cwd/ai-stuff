# build hooks

Backstops for the `build` skill's sign-off gates and scoping rules (see `skills/build/references/loop-protocol.md` and `skills/build/agents/*.md` in this repo). All five are gated on finding a `.build-state.json` cache file anywhere under the current project — with no active `build` plan, they're silent no-ops.

None of them is registered in `~/.claude/settings.json`. Each one is declared in the `hooks:` frontmatter of the skill or agent that needs it. Claude Code only runs it while that skill or agent is active, so it doesn't start a `python3` process on every tool call in every project:

- `commit_guard.py` is a **Stop** hook, declared in `skills/build/SKILL.md` (root session) and in `agents/foreman.md` and `agents/inspector.md` (where Claude Code runs it as **SubagentStop**). It blocks ending the turn if any step is `done` with no commit SHA recorded.
- `precompact_check.py` is a **PreCompact** hook, declared in `skills/build/SKILL.md`. It reminds whoever is driving the session to sync the tracker/cache before context is lost.
- `review_commit_reminder.py` is a **PostToolUse** hook (matcher `Agent|Task`; `Task` is the pre-2.1.63 name of the subagent tool), declared in `agents/foreman.md`, since foreman is the one that dispatches inspector. Right after an `inspector` dispatch that looked like APPROVE, it checks that the commit actually landed in `.build-state.json`.
- `foreman_scope_guard.py` is a **PreToolUse** hook (matcher `Read|Write`), declared in `agents/foreman.md`. It blocks `foreman`'s Read/Write outside exactly `PLAN.md` and `.build-state.json` for the active plan. This is the mechanical enforcement behind "foreman is pure orchestration."
- `inspector_scope_guard.py` is a **PreToolUse** hook (matcher `Write|Edit|Bash`), declared in `agents/inspector.md`. It blocks `inspector`'s Write/Edit/Bash outside its allowlist: git add/commit, `.build-state.json` and its `.build-state.log.jsonl` sidecar, its own agent-memory, the scratchpad, and this project's declared `scratch_paths`. This is the mechanical enforcement behind "inspector never touches real code directly." It's best-effort static pattern-matching, not a full sandbox.

Lifetimes, per the Claude Code hooks reference ("Hooks in skills and agents"):

- Agent frontmatter hooks run only while that subagent is running. User-level agents in `~/.claude/agents/` don't need the workspace trust prompt for them.
- Skill frontmatter hooks register when the skill is invoked and stay for the rest of the session. `/clear` and `/resume` drop them. After either one mid-build, invoke `/build` again before the root session continues the plan.

The two scope guards still check the payload's `agent_type` field. That's redundant with the frontmatter scoping, but it's cheap and keeps them safe if they're ever registered more broadly again.

## Install

Nothing to merge into `settings.json`. `run_after_40-link-claude-agents.sh` creates the symlinks the frontmatter commands rely on:

- `~/.claude/hooks/build` → `~/.agents/hooks/build` (the commands call `python3 "$HOME"/.claude/hooks/build/<script>.py`)
- `~/.claude/agents/{foreman,crewman,inspector}.md` → `~/.agents/skills/build/agents/`
- `~/.claude/skills/build` → `~/.agents/skills/build`

To check they're live, run `/hooks` in a session after invoking `/build`. The root hooks are listed with the skill as their source. The agent hooks show up only while foreman or inspector is running.

If an older setup still has these five scripts registered in `~/.claude/settings.json`, remove those entries; otherwise each hook runs twice inside a build.
