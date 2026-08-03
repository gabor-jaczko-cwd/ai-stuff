---
name: build
description: Drive a large, multi-phase feature to completion with an unattended (or lightly attended) agent loop — foreman coordinates, crewman is the only one that writes code, inspector gates every step before it can be committed. Reserved for work too big or too long-running to hand-hold; everyday ticket work stays on wayfinder/to-spec/to-tickets/implement/code-review. Use when the user wants a feature built end to end across many steps without reviewing each one personally, or explicitly asks to "run build" / "build this plan".
argument-hint: "A to-spec doc, a to-tickets breakdown, or nothing to plan from the current conversation"
---

# Build

Turn a spec or an existing ticket breakdown into a phased, dependency-aware plan, then drive it to completion through a foreman/crewman/inspector loop with eval-based sign-off at every step and phase.

**This is not the everyday path.** For normal ticket-sized work, use `implement` directly against a `to-tickets` breakdown — one agent, one session, tdd + typecheck + tests + `/code-review` + commit. Reach for `build` specifically when the work is too large or too long-running to watch step by step: many phases, real risk of drifting off-course unattended, or a build you want to kick off and check back on rather than babysit.

## When to use

- A feature is big enough that `implement` in one session won't hold it, and you want it driven across a context-reset-safe loop instead of you manually re-invoking `implement` per ticket.
- You want hard sign-off (evals + independent review + recorded commit) enforced by hooks, not just prose discipline — because nobody's watching every step.
- Trigger phrases: "build this out end to end", "run build on this plan", "drive this to completion".

## Relationship to the rest of the pack

`build` deliberately reuses what already works rather than reinventing it:

- **Planning input is flexible** — from a `to-spec` document (decomposed itself) or an existing `to-tickets` breakdown (tickets become steps, blocking edges become `depends_on`). Decided per case.
- **State lives on the tracker**, not a bespoke local file — consistent with `wayfinder`. See `references/plan-structure.md`.
- **inspector reuses `code-review`'s two-axis machinery**, scoped to one step's diff instead of a whole branch.
- **crewman leans on `tdd`** for test-first discipline and the `run` skill for UI verification (see `references/evals.md`).
- **At plan close, foreman runs a final whole-branch `/code-review`** over the entire commit range — catches cross-phase drift no per-step gate would. See `references/loop-protocol.md`.

## Step 0 — Load project context

This skill hardcodes no build, test or format commands. Before planning or executing, resolve the project's tooling (full detail in `references/project-context.md`):

1. Read the project's `CLAUDE.md` if present.
2. If a project profile exists at `.claude/build.md`, load it.
3. Otherwise detect tooling (`composer.json`, `package.json` scripts, `Makefile`/`justfile`, CI config) and confirm with the user before relying on it. Offer to write a profile so future runs are turnkey.

Carry the resolved values through planning and into every crewman/inspector payload.

## Modes

- `plan` — generate the plan only, then stop for review.
- `execute` — run an existing plan to completion.
- `plan-then-execute` — default. Generate the plan, then begin execution. Pauses after planning for sign-off unless autonomy is `auto`.

State the mode when invoked.

## Mode A — Generate the plan

1. Read the spec (from `to-spec`) or the ticket breakdown (from `to-tickets`), whichever was supplied. Extract scope, out-of-scope, acceptance criteria, and dependencies.
2. Decompose into phases (sequenced groups) and steps (single, independently buildable units — if the input was tickets, one ticket per step). Keep each step small enough for one crewman pass.
3. Build the dependency graph (`depends_on` per step). If the input was a `to-tickets` breakdown, its blocking edges *are* the graph — don't re-derive it.
4. Define evals for every phase and step up front (see `references/evals.md`). No step is done until its evals pass — this includes a browser-verification eval for any step that touches rendered UI.
5. **Tag checkpoint phases now.** For any phase you or the user judge risky enough to warrant a pause before it runs — not the orchestrator's live self-judgment, decided here at plan-approval time — mark it `checkpoint: true` in its phase README (see `references/plan-structure.md`). This is in addition to autonomy's own pause behavior.
6. Write the plan to `[plan_location]/[feature-slug]/` (default `docs/plans/`) using the templates in `references/plan-structure.md` (PLAN.md, per-phase README, per-step files). There is no STATE.md — progress lives on the tracker (see below).
7. Summarise the plan and the critical path. If the mode is `plan`, or autonomy requires it, stop here for review.

## Mode B — Execute the plan

Execution runs the **foreman** protocol in the main session, because it must be able to spawn crewman and inspector with the Task tool, and a subagent cannot reliably spawn further subagents. Load the `foreman` agent and follow it.

The loop, per step (full detail in `references/loop-protocol.md`):

1. foreman selects the next unblocked step (all `depends_on` done, per the tracker or PLAN.md).
2. It hands **crewman** one step plus only the context it needs, including the project's test/format commands and applicable conventions.
3. crewman implements the step, writes/runs its evals (test-first preferred, its call), does a browser check if the step touches UI, and returns a concise report.
4. foreman checks the report against the step's acceptance criteria (sign-off one: plan conformance).
5. **inspector** reviews the diff and eval results — Standards + Spec, scoped to this step — and returns APPROVE or CHANGES_REQUESTED. On changes, feedback returns to crewman and steps 3–5 repeat, up to the cycle cap.
6. On APPROVE, foreman commits the step's changes itself (message references the step/ticket id), records the SHA on the tracker (ticket comment/transition) **and** in the local cache file, then marks the step done. Never before all four sign-off gates hold (see `references/loop-protocol.md`).

At each step boundary foreman compacts context (see `references/context-compaction.md`): commits, syncs the tracker and cache, then continues from a lean context of PLAN.md plus the tracker plus the next step. At each phase boundary — and at every `checkpoint: true` phase — it ends its turn with a handoff prompt rather than attempting to clear its own context; no tool lets an agent invoke `/clear` on itself.

When every phase is done, foreman runs one final `/code-review` over the whole commit range before declaring the plan complete.

Two hooks backstop the parts prose alone can't guarantee, gated on the local cache file's presence so they're inert on every other project:

- `build-commit-guard.py` (Stop) — blocks foreman's turn from ending if the cache shows any step `done` with no commit recorded.
- `build-review-commit-reminder.py` (PostToolUse:Task) — fires right after `inspector` returns APPROVE, reminding foreman to commit and sync before moving on.
- `build-precompact-check.py` (PreCompact) — fires before any compaction while a plan is active, reminding whoever is driving the session that the tracker and cache must be current first.

## Agents

Definitions live in `agents/` alongside this file (`agents/README.md` has install instructions — symlink each into `~/.claude/agents/`):

- **foreman** (Opus) — runs in the main session; owns the plan, dependency graph, sign-off gates, commits and compaction. Read-only on source code; never edits it.
- **crewman** (Sonnet) — the only agent that modifies the codebase. Implements one step at a time, writes and runs its evals, reports back. Never commits.
- **inspector** (Opus) — read-only; verifies each step via `code-review`'s Standards + Spec axes, scoped to the step. Never commits.

## Autonomy and guardrails

- `auto` — run to completion, escalating only on blockers.
- `review-plan` (default) — approve the plan once, then run phase-to-phase autonomously, except: pause at every `checkpoint: true` phase, and always pause on a real blocker (cycle cap exceeded, unfixable eval, missing precondition, genuine ambiguity) regardless of autonomy level.
- `checkpoint` — also pause at every phase boundary, not just tagged ones.

Guardrails:

- Per-step cycle cap (default 3). Exceeding it escalates with the open feedback.
- crewman is the only agent permitted to modify the codebase. Only foreman commits, and only after inspector's APPROVE.
- Never bypass or weaken an eval to force a step to "done". Never mark a step done without a recorded commit — the `build-commit-guard.py` hook enforces this.
- Always honour the project profile's guardrails (a required format command, files that must never be touched).

## Output rules

- Planning artifacts go under the project's plan location (default `docs/plans/[feature-slug]/`).
- Step/phase progress lives on the tracker; the local cache file (`references/plan-structure.md`) exists only so the hooks can check fast and offline — it is not the record of truth and is safe to gitignore.

## References

Load these only when the task needs them (progressive disclosure):

- `references/project-context.md` — how project tooling and conventions are resolved, and the profile schema.
- `references/plan-structure.md` — plan folder layout, file templates, tracker-state mapping, and the cache-file format.
- `references/loop-protocol.md` — the foreman/crewman/inspector state machine, handoff payloads, sign-off gates, failure handling.
- `references/evals.md` — eval types (including browser verification), how to define them per phase and step, and pass thresholds.
- `references/context-compaction.md` — what to keep and discard between phases, and the progress-note format.
