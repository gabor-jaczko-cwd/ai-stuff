# My AI Tools

A collection of AI agent skills and tools for use with GitHub Copilot, Claude, and similar coding assistants. These are skills I've picked up, adapted, or written myself. To use a skill, copy the relevant folder under `skills/` into `~/.agents/skills/` (or `{project-root}/.claude/skills/`).

## Skills

| Skill | Description | Source                                                      |
|---|---|-------------------------------------------------------------|
| [caveman](skills/caveman/SKILL.md) | Ultra-compressed communication mode — cuts token usage ~75% by dropping filler while keeping full technical accuracy. | [mattpocock/skills](https://github.com/mattpocock/skills)   |
| [diagnose](skills/diagnose/SKILL.md) | Disciplined debug loop: reproduce → minimise → hypothesise → instrument → fix → regression-test. | [mattpocock/skills](https://github.com/mattpocock/skills)   |
| [find-skills](skills/find-skills/SKILL.md) | Helps discover and install agent skills when you ask "is there a skill that can…". | [vercel-labs/skills](https://github.com/vercel-labs/skills) |
| [grill-me](skills/grill-me/SKILL.md) | Relentlessly interviews you about a plan or design until all open questions are resolved. | [mattpocock/skills](https://github.com/mattpocock/skills)   |
| [grill-with-docs](skills/grill-with-docs/SKILL.md) | Like `grill-me`, but challenges your plan against the project's existing domain model and ADRs. | [mattpocock/skills](https://github.com/mattpocock/skills)   |
| [improve-codebase-architecture](skills/improve-codebase-architecture/SKILL.md) | Finds deepening and refactoring opportunities to make a codebase more testable and AI-navigable. | [mattpocock/skills](https://github.com/mattpocock/skills)   |
| [respond-to-code-review](skills/respond-to-code-review/SKILL.md) | Investigates, plans, and implements fixes for pull request review comments. | &mdash; |
| [review](skills/review/SKILL.md) | Reviews GitHub PRs or local branches with structured findings, severity ratings, and optional GitHub posting. | &mdash; |
| [setup-matt-pocock-skills](skills/setup-matt-pocock-skills/SKILL.md) | Bootstraps `AGENTS.md`/`CLAUDE.md` and `docs/agents/` so project-aware skills know the issue tracker, labels, and domain docs. | [mattpocock/skills](https://github.com/mattpocock/skills)   |
| [tdd](skills/tdd/SKILL.md) | Test-driven development with a red-green-refactor loop and integration test support. | [mattpocock/skills](https://github.com/mattpocock/skills)   |
| [to-issues](skills/to-issues/SKILL.md) | Breaks a plan, spec, or PRD into independently-grabbable issues on the project issue tracker. | [mattpocock/skills](https://github.com/mattpocock/skills)   |
| [to-prd](skills/to-prd/SKILL.md) | Turns conversation context into a PRD and publishes it to the project issue tracker. | [mattpocock/skills](https://github.com/mattpocock/skills)   |
| [triage](skills/triage/SKILL.md) | Triages issues through a state-machine workflow (create → review → ready → in-progress). | [mattpocock/skills](https://github.com/mattpocock/skills)   |
| [write-a-skill](skills/write-a-skill/SKILL.md) | Creates new agent skills with proper structure, progressive disclosure, and bundled resources. | [mattpocock/skills](https://github.com/mattpocock/skills)   |
| [zoom-out](skills/zoom-out/SKILL.md) | Gives a broader, higher-level perspective on unfamiliar code or a section you need context for. | [mattpocock/skills](https://github.com/mattpocock/skills)   |

