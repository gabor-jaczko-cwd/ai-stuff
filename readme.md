# My AI Tools

A collection of AI agent skills and tools for use with GitHub Copilot, Claude, and similar coding assistants. These are skills I've picked up, adapted, or written myself. To use a skill, copy the relevant folder under `skills/` into `~/.agents/skills/` (or `{project-root}/.claude/skills/`).

## Skills

| Skill | Description | Source |
|---|---|---|
| [ask-matt](skills/ask-matt/SKILL.md) | Routes you to whichever skill or flow fits your current situation. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| [batch-grill-me](skills/batch-grill-me/SKILL.md) | Interviews you on every open question at once, round by round, instead of one at a time. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| [claude-handoff](skills/claude-handoff/SKILL.md) | Hands the current conversation off to a fresh background agent that picks up immediately. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| [code-review](skills/code-review/SKILL.md) | Reviews a diff along two axes — Standards and Spec — via parallel sub-agents, reported side by side. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| [codebase-design](skills/codebase-design/SKILL.md) | Shared vocabulary for designing deep modules and finding deepening opportunities. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| [design-an-interface](skills/design-an-interface/SKILL.md) | Generates several radically different interface designs for a module via parallel sub-agents. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| [diagnosing-bugs](skills/diagnosing-bugs/SKILL.md) | Disciplined debug loop for hard bugs and performance regressions. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| [domain-modeling](skills/domain-modeling/SKILL.md) | Builds and sharpens a project's domain terminology and architectural decisions. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| [find-skills](skills/find-skills/SKILL.md) | Helps discover and install agent skills that match what you're trying to do. | [vercel-labs/skills](https://github.com/vercel-labs/skills) |
| [grill-me](skills/grill-me/SKILL.md) | Relentlessly interviews you about a plan or design until it's sharp. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| [grill-with-docs](skills/grill-with-docs/SKILL.md) | Like `grill-me`, but also produces ADRs and a glossary as it goes. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| [grilling](skills/grilling/SKILL.md) | Relentlessly interviews you about a plan, decision, or idea. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| [handoff](skills/handoff/SKILL.md) | Compacts the current conversation into a handoff document for another agent. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| [implement](skills/implement/SKILL.md) | Implements a piece of work from a spec or set of tickets (tdd + typecheck + tests + code-review + commit). | [mattpocock/skills](https://github.com/mattpocock/skills) |
| [improve-codebase-architecture](skills/improve-codebase-architecture/SKILL.md) | Scans a codebase for deepening opportunities and presents them as a visual HTML report. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| [loop-me](skills/loop-me/SKILL.md) | Grills you about specs for the recurring workflows you want to build. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| [prototype](skills/prototype/SKILL.md) | Builds a throwaway prototype to answer a design question. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| [qa](skills/qa/SKILL.md) | Interactive QA session — report bugs conversationally, the agent files the GitHub issues. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| [research](skills/research/SKILL.md) | Investigates a question against primary sources and writes up the findings. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| [resolving-merge-conflicts](skills/resolving-merge-conflicts/SKILL.md) | Resolves an in-progress git merge/rebase conflict. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| [respond-to-code-review](skills/respond-to-code-review/SKILL.md) | Investigates, plans, and implements fixes for pull request review comments. | &mdash; |
| [review](skills/review/SKILL.md) | Reviews GitHub PRs or local branches with structured, severity-rated findings. | &mdash; |
| [setup-matt-pocock-skills](skills/setup-matt-pocock-skills/SKILL.md) | One-time repo setup — issue tracker, triage labels, domain doc layout — for the rest of this pack. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| [tdd](skills/tdd/SKILL.md) | Test-driven development with a red-green-refactor loop. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| [teach](skills/teach/SKILL.md) | Teaches the user a new skill or concept within the workspace. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| [to-questionnaire](skills/to-questionnaire/SKILL.md) | Turns a decision you can't fully answer into a questionnaire for someone else to fill in. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| [to-spec](skills/to-spec/SKILL.md) | Turns the current conversation into a spec and publishes it to the issue tracker. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| [to-tickets](skills/to-tickets/SKILL.md) | Breaks a plan or spec into tracer-bullet tickets with blocking edges, published to the tracker. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| [triage](skills/triage/SKILL.md) | Moves issues and external PRs through a state machine of triage roles. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| [wayfinder](skills/wayfinder/SKILL.md) | Charts a huge chunk of work as a shared map of decision tickets, resolved one at a time. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| [wizard](skills/wizard/SKILL.md) | Generates an interactive bash wizard that walks a human through a manual setup or migration procedure. | [mattpocock/skills](https://github.com/mattpocock/skills) |
| [writing-great-skills](skills/writing-great-skills/SKILL.md) | Reference for writing and editing skills well. | [mattpocock/skills](https://github.com/mattpocock/skills) |
