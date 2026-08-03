# Plan Structure

The plan for a feature lives under `docs/plans/[feature-slug]/`: the dependency graph and per-step criteria as originally decided. **Live progress does not live here** — see "Tracker as the record of truth" below.

## Folder layout

```
docs/plans/[feature-slug]/
  PLAN.md                       overview, goal, phase list, dependency graph, critical path
  phases/
    01-[phase-slug]/
      README.md                 phase goal, steps, entry/exit criteria, checkpoint flag
      01-[step-slug].md          a single buildable step (see "Step files" below)
      02-[step-slug].md
    02-[phase-slug]/
      README.md
      01-[step-slug].md
  .build-state.json             hook-only cache — see "Cache file" below. Not the record of truth; safe to gitignore.
```

Number phases and steps with zero-padded prefixes so they sort in intended order. Slugs are kebab-case.

## Where a step comes from

Planning input is flexible (decided per case, see the skill's Mode A):

- **From a `to-tickets` breakdown:** each ticket becomes one step. The step file is a thin pointer — id, title, `depends_on` (copied straight from the ticket's blocking edges), and a link to the ticket (its acceptance criteria and "what to build" already live there — don't duplicate them into the step file).
- **From a `to-spec` document directly:** the step file is fully self-contained (see the template below), because there's no ticket to point at yet.

Either way, a step carries the same identity (`[phase].[step]`, e.g. `2.1`) and the same `depends_on` semantics.

## Statuses

Every step and phase carries one status: `pending`, `blocked`, `in_progress`, `in_review`, `done`, `escalated`. `blocked` means a `depends_on` is not yet `done`. Status is **not** stored in PLAN.md or the phase README — query it live from the tracker (the linked ticket's state) or from the cache file for a fast/offline check. Static planning files only change when scope changes, never as a side effect of progress.

## PLAN.md template

```markdown
---
feature: [feature name]
slug: [feature-slug]
source: [path to the to-spec doc, or a query/label describing the to-tickets breakdown this groups]
created: [YYYY-MM-DD]
autonomy: review-plan        # auto | review-plan | checkpoint
cycle_cap: 3
---

# [Feature name] — Build Plan

## Goal
[One paragraph: the outcome, tied to the spec.]

## Phases
| # | Phase | Goal | Depends on | Checkpoint |
|---|-------|------|------------|------------|
| 1 | [slug] | [one line] | - | no |
| 2 | [slug] | [one line] | 1 | yes |

## Dependency graph
[Step-level graph. List each step id and its depends_on. Steps with no path between them may run in parallel.]

    1.1 -> (none)
    1.2 -> 1.1
    2.1 -> 1.1, 1.2
    2.2 -> 1.2

## Critical path
[The longest dependency chain, so the bottleneck is visible.]

## Out of scope
[Carried from the spec, restated so the loop does not drift.]
```

Step ids are `[phase].[step]`, for example `2.1`.

## Phase README template

```markdown
# Phase [n] — [phase name]

## Goal
[Measurable outcome for the phase.]

## Steps
| id | step | ticket | depends_on |
|----|------|--------|-----------|
| [n].1 | [slug] | [tracker ref, or "—" if planned from spec] | - |
| [n].2 | [slug] | [tracker ref] | [n].1 |

## Entry criteria
[What must be true before this phase starts.]

## Exit criteria (phase eval gate)
[The phase-level evals that must pass before the phase is done. See evals.md.]

## Checkpoint
[true/false, set at plan-approval time — see the skill's Mode A step 5. If true, foreman pauses at this phase's boundary regardless of autonomy level. Not something foreman re-judges live.]
```

## Step file template (spec-planned steps only)

Skip this file entirely when the step is ticket-backed — link the ticket from the phase README instead.

```markdown
---
id: [phase].[step]
title: [short imperative title]
phase: [n]
depends_on: [list of step ids, or empty]
agent: crewman
---

## Goal
[What this step delivers, in one or two sentences.]

## Context
[Only what crewman needs: files to touch, patterns to follow, doc references.]

## Acceptance criteria
[Given / When / Then, drawn from the spec. These are what inspector checks against.]

## Eval spec
[The evals to write and run for this step: type, what they assert, pass threshold. See evals.md.]

## Out of scope
[Explicitly what this step must not touch.]
```

## Tracker as the record of truth

Whatever a step's ticket is (from `to-tickets`, or opened fresh if planning from a spec directly — one ticket per step, same `ready-for-agent`-style labeling `to-tickets` uses), foreman records progress there, not in a local file:

- On dispatch: the ticket is claimed/assigned, same convention as `wayfinder`.
- On inspector's verdict: post the verdict (APPROVE or CHANGES_REQUESTED with the numbered list) as a ticket comment.
- On commit: post the commit SHA as a ticket comment and close (or transition) the ticket.
- A human — or a fresh `wayfinder`/`to-tickets` session — can read progress straight off the tracker, exactly as they would for any other ticket, with no plan-folder-specific knowledge required.

## Cache file (`.build-state.json`)

A thin, disposable, hook-only cache — never read by a human, never the source of truth. It exists purely so `build-commit-guard.py` can check "any step done without a commit?" fast and offline instead of hitting the tracker API on every `Stop`. foreman writes it in the same update where it syncs the tracker; if the two ever disagree, the tracker wins and the cache gets overwritten from it.

```json
{
  "feature": "feature-slug",
  "plan_path": "docs/plans/feature-slug",
  "steps": {
    "1.1": { "status": "done", "commit": "a1b2c3d", "ticket": "1234" },
    "1.2": { "status": "in_review", "commit": null, "ticket": "1235" }
  }
}
```

Rules:

- A step may only be written with `"status": "done"` in the same update that fills in a non-null `commit`. Never done-now-commit-later.
- Safe to delete at any time — foreman regenerates it from the tracker on next read if it's missing. Add it to `.gitignore`.
- Its presence anywhere under `docs/plans/*/.build-state.json` in the repo is exactly the gate the hooks use to decide whether they're inert. No cache file means no active `build` plan, and the hooks no-op.

## Expressing parallelism

Parallelism is implicit in `depends_on`. Any two steps where neither is reachable from the other in the dependency graph may run at the same time. foreman uses this to dispatch a safe batch. Where two otherwise-independent steps would edit the same file, add a dependency so they run in sequence and avoid conflicts.
