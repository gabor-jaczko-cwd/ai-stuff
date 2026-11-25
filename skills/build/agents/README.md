# agents

Claude Code subagents used by the `build` skill (see `../SKILL.md`).

- `foreman.md` — sonnet, orchestrates the build loop: dispatches crewman and inspector by step id and polls `.build-state.json`. Writes only `PLAN.md` and `.build-state.json`; never edits code or commits.
- `crewman.md` — sonnet, the only one that edits code, implements one step at a time. Never commits.
- `inspector.md` — opus, reviews each step via `code-review`'s Standards + Spec axes, commits on APPROVE and records the verdict in `.build-state.json`. Never edits source or test files.

## Install

The dotfiles script `run_after_40-link-claude-agents.sh` symlinks each file into `~/.claude/agents/` on every `chezmoi apply`. To do it by hand:

```bash
mkdir -p ~/.claude/agents
ln -sfn ~/.agents/skills/build/agents/foreman.md   ~/.claude/agents/foreman.md
ln -sfn ~/.agents/skills/build/agents/crewman.md   ~/.claude/agents/crewman.md
ln -sfn ~/.agents/skills/build/agents/inspector.md ~/.claude/agents/inspector.md
```
