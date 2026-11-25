---
name: build
description: Drive a large, multi-phase feature to completion with an unattended (or lightly attended) agent loop — a persistent root session spawns foreman fresh at each reset point, foreman coordinates, crewman is the only one that writes code, inspector verifies and commits every step. Reserved for work too big or too long-running to hand-hold; everyday ticket work stays on wayfinder/to-spec/to-tickets/implement/code-review. Use when the user wants a feature built end to end across many steps without reviewing each one personally, or explicitly asks to "run build" / "build this plan".
argument-hint: "A to-spec doc, a to-tickets breakdown, or nothing to plan from the current conversation"
---

# Build

Turn a spec or an existing ticket breakdown into a phased, dependency-aware plan, then drive it to completion through a root/foreman/crewman/inspector loop with eval-based sign-off at every step and phase.

**This is not the everyday path.** For normal ticket-sized work, use `implement` directly against a `to-tickets` breakdown — one agent, one session, tdd + typecheck + tests + `/code-review` + commit. Reach for `build` specifically when the work is too large or too long-running to watch step by step: many phases, real risk of drifting off-course unattended, or a build you want to kick off and check back on rather than babysit.

## When to use

- A feature is big enough that `implement` in one session won't hold it, and you want it driven across a context-reset-safe loop instead of you manually re-invoking `implement` per ticket.
- You want hard sign-off (evals + independent review + recorded commit) on every step, because nobody's watching every step.
- Trigger phrases: "build this out end to end", "run build on this plan", "drive this to completion".

## Relationship to the rest of the pack

`build` builds on the rest of the pack:

- **Planning input is flexible** — from a `to-spec` document (decomposed itself) or an existing `to-tickets` breakdown (tickets become steps, blocking edges become `depends_on`). Decided per case.
- **State lives on the tracker for status, and in `.build-state.json` for live review content** — approved steps' full review content is archived to a `.build-state.log.jsonl` sidecar; see `references/plan-structure.md` for the exact split. Ticket claim/close/SHA still goes through the tracker as `wayfinder` does; verdicts and `CHANGES_REQUESTED` feedback are local-only, regardless of tracker.
- **inspector reuses `code-review`'s two-axis machinery**, scoped to one step's diff instead of a whole branch — and also runs the whole-branch pass at plan close (see below).
- **crewman leans on `tdd`** for test-first discipline and the `run` skill for UI verification (see `references/evals.md`).
- **At plan close, inspector runs a final whole-branch `/code-review`** over the entire commit range. See `references/loop-protocol.md`.

## Step 0 — Load project context

This skill hardcodes no build, test or format commands. Before planning or executing, resolve the project's tooling (full detail in `references/project-context.md`):

1. Read the project's `CLAUDE.md` if present.
2. If a project profile exists at `.claude/local/build.md`, load it.
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
5. **Tag checkpoint phases now.** For any phase you or the user judge risky enough to warrant a pause before it runs, mark it `checkpoint: true` in its phase README (see `references/plan-structure.md`). Decide this here, not at run time. It is in addition to autonomy's own pause behavior.
6. Write the plan to `[plan_location]/[feature-slug]/` (default `docs/plans/`) using the templates in `references/plan-structure.md` (PLAN.md, per-phase README, per-step files). There is no STATE.md — progress lives on the tracker (see below).
7. Summarise the plan and the critical path. If the mode is `plan`, or autonomy requires it, stop here for review.

## Mode B — Execute the plan

Execution runs across three layers, not one continuous session:

- **Root** — the session you're already in (interactive or background). It stays alive for the whole plan but does almost nothing itself: at each reset point it spawns a fresh **foreman** subagent, waits, and spawns the next one when foreman reports back. It never touches code, the tracker, or `.build-state.json` directly.
- **Foreman** — spawned fresh by the root at each reset point (a `checkpoint: true` phase, an escalation, or any point it would otherwise sit idle). Pure orchestration: selects the next unblocked step, dispatches crewman and inspector by step id, polls `.build-state.json` for outcomes. Never chains its own successor.
- **crewman / inspector** — spawned per step by foreman. Inspector also verifies conformance, commits, and posts status/feedback to `.build-state.json` itself.

The loop, per step (full detail in `references/loop-protocol.md`):

1. foreman selects the next unblocked step (all `depends_on` done, per the tracker or `PLAN.md`).
2. It hands **crewman** one step plus only the context it needs, including the project's test/format commands and applicable conventions.
3. crewman implements the step, writes/runs its evals (test-first preferred, its call), does a browser check if the step touches UI, and returns a concise report.
4. foreman dispatches **inspector** with the step and a pointer to crewman's report; it does not read or judge the report itself.
5. **inspector** reviews the diff and eval results — Standards + Spec, scoped to this step, with the Spec axis covering acceptance-criteria conformance — and either commits (on APPROVE) or writes numbered feedback (on CHANGES_REQUESTED) directly to `.build-state.json`. On changes, foreman re-dispatches crewman by step id only — crewman reads the feedback itself — and steps 3–5 repeat, up to the cycle cap.
6. foreman learns the outcome by polling `.build-state.json`, never by reading inspector's report content. On APPROVE, the commit and tracker sync already happened inside inspector's dispatch.

At each reset point, foreman ends its turn and reports to the root, which spawns the next foreman.

When every phase is done, foreman dispatches inspector to run one final `/code-review` over the whole commit range before declaring the plan complete.

Rules the loop depends on:

- Foreman writes only `PLAN.md` and `.build-state.json`. It reads only what its instructions name: the plan files, `.build-state.json`, this skill's `references/*`, the project's `CLAUDE.md` and `.claude/local/build.md`, and its own agent memory.
- Inspector writes only `.build-state.json`, `.build-state.log.jsonl`, its agent memory, the session scratchpad and the project's `scratch_paths`. It never edits source or test files, and runs no git command that changes history or the branch. `git add` and `git commit` for its own step are allowed.
- A step is marked `done` only in the same update that records its commit SHA. Inspector commits in the same action as its APPROVE, and foreman never treats a step as done without a recorded commit.
- Before any compaction, bring the tracker and `.build-state.json` up to date for every step touched.

## Agents

Definitions live in `agents/` alongside this file (`agents/README.md` has install instructions — symlink each into `~/.claude/agents/`):

- **foreman** (Sonnet) — spawned fresh per reset point, not the main session. Pure orchestration: dispatches, polls, escalates. Tool-restricted to `Task`, `TodoWrite`, `Read` and `Write`, and writes only `PLAN.md`/`.build-state.json` — no `Bash`, `Grep`, or `Edit`.
- **crewman** (Sonnet) — the only agent that modifies the codebase. Implements one step at a time, writes and runs its evals, reports back. Never commits.
- **inspector** (Opus) — verifies each step via `code-review`'s Standards + Spec axes, scoped to the step, commits on APPROVE, and posts status/feedback to `.build-state.json`. Writes only that, plus scratch verification artifacts — never source or test files.

## Autonomy and guardrails

- `auto` — run to completion, escalating only on blockers.
- `review-plan` (default) — approve the plan once, then run phase-to-phase autonomously, except: pause at every `checkpoint: true` phase, and always pause on a real blocker (cycle cap exceeded, unfixable eval, missing precondition, genuine ambiguity) regardless of autonomy level.
- `checkpoint` — also pause at every phase boundary, not just tagged ones.

Guardrails:

- Per-step cycle cap (default 3). Exceeding it escalates with the open feedback.
- crewman is the only agent permitted to modify real source/test files. Only inspector commits, and only as part of its own APPROVE.
- Never bypass or weaken an eval to force a step to "done". Never mark a step done without a recorded commit.
- Always honour the project profile's guardrails (a required format command, files that must never be touched) and, symmetrically, never grant `scratch_paths` beyond what the profile declares and validates against that project's own `.gitignore`.

## Output rules

- Planning artifacts go under the project's plan location (default `docs/plans/[feature-slug]/`).
- Step/phase status lives on the tracker; `.build-state.json` (`references/plan-structure.md`) carries live review content — in-flight `CHANGES_REQUESTED` feedback, and a compact `{"verdict": "APPROVE"}` pointer for done steps. Full review history for approved steps is archived to a sibling `.build-state.log.jsonl` when inspector approves. Both files are gitignored; don't delete either.

## References

Load these only when the task needs them (progressive disclosure):

- `references/project-context.md` — how project tooling and conventions are resolved, the profile schema, and `scratch_paths` validation.
- `references/plan-structure.md` — plan folder layout, file templates, tracker-state mapping, and the cache-file format.
- `references/loop-protocol.md` — the root/foreman/crewman/inspector state machine, handoff payloads, sign-off gates, failure handling.
- `references/evals.md` — eval types (including browser verification), how to define them per phase and step, and pass thresholds.
- `references/long-running-commands.md` — how crewman/inspector wait out a full test/CI/browser suite that outlives a single foreground Bash call.
