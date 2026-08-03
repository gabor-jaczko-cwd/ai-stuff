# agents

Custom Claude Code subagents used by the `build` skill (see `../SKILL.md`), bundled directly under this skill since nothing else in this repo uses them. Unlike the skills in this repo, these are Claude-Code-native subagent definitions (`tools:`/`model:`/`color:` frontmatter) rather than the pack's usual cross-provider skill format (there's no `openai.yaml` here) — kept that way deliberately for now; see `build`'s own notes if that ever needs revisiting.

- `foreman.md` — opus, orchestrates the build loop, commits, never edits code.
- `crewman.md` — sonnet, the only one that edits code, implements one step at a time.
- `inspector.md` — opus, read-only, gates each step via `code-review`'s Standards + Spec axes.

## Install

Symlink each file into `~/.claude/agents/`:

```bash
mkdir -p ~/.claude/agents
ln -s ../../.agents/skills/build/agents/foreman.md   ~/.claude/agents/foreman.md
ln -s ../../.agents/skills/build/agents/crewman.md   ~/.claude/agents/crewman.md
ln -s ../../.agents/skills/build/agents/inspector.md ~/.claude/agents/inspector.md
```
