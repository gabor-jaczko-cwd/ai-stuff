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
  .build-state.json             build state: per-step status, commit SHA, live review content — see "Cache file" below. Not the record of truth; safe to gitignore.
  .build-state.log.jsonl        append-only archive of approved steps' full review content — see "Cache file" below. Gitignore this too.
```

Number phases and steps with zero-padded prefixes so they sort in intended order. Slugs are kebab-case.

## Where a step comes from

Planning input is flexible (decided per case, see the skill's Mode A):

- **From a `to-tickets` breakdown:** each ticket becomes one step. The step file is a thin pointer — id, title, `depends_on` (copied straight from the ticket's blocking edges), and a link to the ticket (its acceptance criteria and "what to build" already live there — don't duplicate them into the step file).
- **From a `to-spec` document directly:** the step file is fully self-contained (see the template below).

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
[true/false, set at plan-approval time — see the skill's Mode A step 5. If true, foreman pauses at this phase's boundary regardless of autonomy level.]
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

## Tracker as the record of truth — for ticket status, not review content

Whatever a step's ticket is (from `to-tickets`, or opened fresh if planning from a spec directly — one ticket per step, same `ready-for-agent`-style labeling `to-tickets` uses), progress is recorded there:

- On dispatch: the ticket is claimed/assigned, same convention as `wayfinder` (foreman does this).
- On commit: the commit SHA is posted as a ticket comment and the ticket is closed (or transitioned) (inspector does this, in the same action as the commit).
- A human — or a fresh `wayfinder`/`to-tickets` session — can read step status straight off the tracker, exactly as they would for any other ticket.

**What never goes to the tracker:** inspector's verdict and `CHANGES_REQUESTED` feedback. They live only in `.build-state.json` (below), never as a ticket comment, whatever the tracker.

## Cache file (`.build-state.json`) and its log (`.build-state.log.jsonl`)

The cache holds *live* review content: a step's full review content lives there only while the step is in flight. When inspector approves a step, the full content moves to an append-only sidecar log next to it, and the cache keeps only a compact pointer. Don't delete either file; see the rules below.

foreman writes `status` transitions on dispatch (`in_progress`, `in_review`); inspector writes everything else — `status: "done"`, `commit`, and the `review` field — in the same action as committing or posting `CHANGES_REQUESTED`. If the cache and the tracker's status ever disagree, the tracker wins for status/commit/ticket; there is no equivalent authority for `review`.

```json
{
  "feature": "feature-slug",
  "plan_path": "docs/plans/feature-slug",
  "steps": {
    "1.1": {
      "status": "done",
      "commit": "a1b2c3d",
      "ticket": "1234",
      "review": { "verdict": "APPROVE" }
    },
    "1.2": {
      "status": "in_progress",
      "commit": null,
      "ticket": "1235",
      "review": {
        "verdict": "CHANGES_REQUESTED",
        "feedback": [
          "[spec] Acceptance criterion 2 not met: ... (file:line)",
          "[standards] Duplicated Code: ... (file:line)"
        ]
      }
    }
  }
}
```

`.build-state.log.jsonl` is one JSON object per line, append-only, never rewritten or read back by any agent:

```jsonl
{"step": "1.1", "ts": "2026-09-17T12:00:00Z", "commit": "a1b2c3d", "verdict": "APPROVE", "notes": "one-line justification, optional suggestions"}
```

Rules:

- A step may only be written with `"status": "done"` in the same update that fills in a non-null `commit`. Never done-now-commit-later.
- **On `APPROVE`**, inspector does three things atomically: commit, append one line to `.build-state.log.jsonl` with the step id, timestamp, commit SHA, and the full verdict (justification + any non-blocking suggestions), then write the compact `review: {"verdict": "APPROVE"}` — not the full text — into `.build-state.json`, discarding any prior `CHANGES_REQUESTED` feedback for that step.
- **While a step is `in_progress`/`in_review`**, its `CHANGES_REQUESTED` feedback stays live and full in `.build-state.json`; crewman reads it there on its next dispatch. Only an `APPROVE` archives it.
- `status`, `commit`, and `ticket` can be regenerated from the tracker if the cache is lost.
- **The log cannot be regenerated.** Archived review history exists nowhere else, and the log is gitignored with no backup.

## Expressing parallelism

Parallelism is implicit in `depends_on`. Any two steps where neither is reachable from the other in the dependency graph may run at the same time. foreman uses this to dispatch a safe batch. Where two otherwise-independent steps would edit the same file, add a dependency so they run in sequence and avoid conflicts.
