# agents

Custom Claude Code subagents used by the `build` skill (see `../SKILL.md`), bundled directly under this skill since nothing else in this repo uses them. Unlike the skills in this repo, these are Claude-Code-native subagent definitions (`tools:`/`model:`/`color:` frontmatter) rather than the pack's usual cross-provider skill format (there's no `openai.yaml` here) — kept that way deliberately for now; see `build`'s own notes if that ever needs revisiting.

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
