# Project Context

This skill is portable. It resolves each project's tooling and conventions at runtime, so the global skill and agents never hardcode project specifics. A project contributes only its profile; it does not copy the skill or agents.

## Resolution order (Step 0)

1. The project's `CLAUDE.md` (auto-loaded by Claude Code) for high-level conventions.
2. A project profile at `.claude/build.md`, if present. This is preferred: explicit and stable.
3. Detection from the project: `composer.json`, `package.json` scripts, `Makefile` or `justfile` targets, CI config. Confirm detected commands with the user before relying on them.

If nothing is found and detection is ambiguous, ask the user for the test and format commands, then offer to write a profile.

## What the profile provides

- `test_command` — how to run the test and eval suite.
- `format_command` — how to format changed files, with any "never run bare" caveats.
- `lint_command` / `typecheck_command` — optional.
- test layout — where tests live and the framework and pattern.
- conventions — language and framework rules crewman must follow.
- guardrails — hard rules, for example files that must never be touched.
- plan location — where plans are written (default `docs/plans`).
- tracker — which issue tracker holds the tickets/steps for this project (matches whatever `to-tickets`/`wayfinder` already resolved via `docs/agents/issue-tracker.md`; `build` does not maintain its own separate tracker config).

## Profile template — `.claude/build.md`

```markdown
---
project: [name]
test_command: [e.g. npm test | pytest -q | ./gradlew test]
format_command: [e.g. prettier -w . | black .]
lint_command: [optional]
plan_location: docs/plans
---

## Conventions
[Language, framework and structural rules crewman must follow.]

## Test layout
[Where tests live; framework and pattern.]

## Guardrails
[Hard rules: files never to touch, commands never to run bare, required reviewers, etc.]
```

`inspector` always runs `code-review`'s Standards + Spec axes, and `crewman` always leans on `tdd`/`run` where they apply — neither is project-configurable.

## How agents receive it

foreman loads the profile once and injects the relevant values into each crewman/inspector payload. crewman should be told the exact test and format commands and the conventions that apply to its step; it should not rediscover them. Keep the injected context minimal and step-relevant.

## Portability rule

If a step's instructions and the resolved project context disagree, the project context wins for tooling (commands, paths, frameworks) and the plan wins for scope. When neither resolves a question, escalate rather than assume.
