# Loop Protocol

How the root session and foreman drive one step from selection to done, and how phases close. The root is the persistent session (interactive or background) that stays alive for the whole plan; foreman is a subagent it spawns fresh at each reset point; crewman and inspector are subagents foreman spawns per step. Tooling (test and format commands) comes from the resolved project context.

## Roles

- **Root** (persistent, thin): spawns a fresh `foreman` at each reset point, waits for its report, spawns the next one. Never touches code, the tracker, or `.build-state.json` directly.
- **Foreman** (subagent, spawned fresh per reset point): selects work, delegates, polls status, counts cycles, escalates. Never edits code, never reads review content, never commits.
- **Crewman** (subagent): the only code modifier. Implements one step, writes and runs its evals with the project's commands, reports back.
- **Inspector** (subagent, scoped-write): verifies a step against acceptance criteria and evals — Standards + Spec axes, scoped to the step — commits on approve, and posts status/feedback to `.build-state.json`.

## Step lifecycle

```
pending -> in_progress -> in_review -> done
              ^                |
              |___ changes ____|        (up to cycle_cap)
                                 -> escalated   (cap exceeded or blocker)
```

1. **Select.** Foreman queries the tracker (or `.build-state.json`, if freshly synced) for the next unblocked step (all `depends_on` closed/done). Sets it `in_progress`.
2. **Dispatch to crewman.** Foreman spawns `crewman` with the build payload (below) — step id and pointers only. Independent unblocked steps may be dispatched together if they don't touch overlapping files.
3. **Dispatch to inspector.** On crewman's report, foreman sets the step `in_review` and spawns `inspector` with the review payload. Foreman does not read or evaluate crewman's report itself; inspector's Spec axis is the only check.
4. **Resolve.** Inspector reviews, and on `APPROVE` commits the step and writes the result to `.build-state.json` directly. On `CHANGES_REQUESTED`, inspector writes the numbered feedback to `.build-state.json` and leaves the step `in_progress`. Either way, foreman learns the outcome by polling `.build-state.json` — never by reading inspector's report content.
5. **Loop or advance.** On `CHANGES_REQUESTED`, foreman re-dispatches crewman with just the step id (crewman reads the feedback itself) and returns to step 2, counting the cycle. On `APPROVE`, foreman marks the step `done` and moves to the next unblocked step; inspector has already committed and synced the tracker.
6. **Cap.** If a step's crewman/inspector cycle count exceeds `cycle_cap` (default 3) still unresolved, foreman sets it `escalated` (tracker + cache) and stops, reporting to the root.

The commit invariant: a step is marked `done` only in the same update that records its commit SHA. Inspector commits in the same action as its APPROVE, and foreman never treats a step as done without a recorded commit. A `done` step with no commit is a bug in inspector's run, not a finished step.

## Handoff payloads

Keep payloads tight. Pass references by path/ticket-id, not by pasting whole files, and never pass review content as text — it lives in `.build-state.json` and the receiving agent reads it there.

**Build payload (foreman to crewman):**

- Step id, and its ticket (or step file, if spec-planned).
- On a re-dispatch after `CHANGES_REQUESTED`: just the step id — crewman reads the feedback from `.build-state.json` itself.
- The project's test command and format command, and the conventions that apply to this step.
- Whether this step touches rendered UI (triggers the browser-verification eval).
- Any interface or contract decisions from earlier phases (from the tracker's prior ticket comments or `.build-state.json`, not a bespoke state file foreman carries in its own context).

**crewman report (crewman to foreman):** step id, changed files, evals written and the test-command result, browser-check result if applicable, how each acceptance criterion is met, deviations and risks. Aim 1,000 to 2,000 tokens. Foreman passes it to inspector by reference (the diff, the step id) without reading or summarizing it.

**Review payload (foreman to inspector):**

- The step's ticket (acceptance criteria) and the diff for the step.
- A pointer to crewman's report (inspector reads it directly; foreman doesn't relay its content).
- The project's documented standards sources, exactly as `code-review` would gather them for a normal invocation, plus any `scratch_paths` from the resolved project profile.

**Inspector's output:** written directly to `.build-state.json`, not returned as text foreman relays onward — `APPROVE` (commit SHA, one-line justification, optional non-blocking suggestions — the full text goes to the `.build-state.log.jsonl` sidecar, only a compact `{"verdict": "APPROVE"}` stays in the live cache) or `CHANGES_REQUESTED` (numbered, file-specific, severity-ordered items, each tagged `[standards]` or `[spec]`, kept live in the cache while the step is in flight). See `plan-structure.md` for the exact schema.

### How inspector runs the two axes

Spawn the same Standards + Spec parallel sub-agent pattern `code-review` uses, but scoped down:

- **Standards sub-agent:** same brief as `code-review`'s (documented repo standards + the Fowler smell baseline), but only the step's diff.
- **Spec sub-agent:** same brief as `code-review`'s, but the "spec" is this step's acceptance criteria (from its ticket or step file), not the whole feature spec. Every crewman report, even an obviously incomplete one, goes through this full review.

Fold both reports into one APPROVE/CHANGES_REQUESTED verdict.

## Sign-off gates

A step is `done` only when all of these hold, and inspector is the one who makes them all true in a single action on approve:

1. Evals pass (the project's test command is green for the step's evals, and the browser check passed if applicable).
2. Inspector's Spec axis confirms the step meets its acceptance criteria.
3. Inspector returns `APPROVE`.
4. The step's changes are committed by inspector, with the SHA recorded in `.build-state.json` (and on the tracker, per `plan-structure.md`).

Foreman never marks a step done on crewman's word alone, never weakens an eval to pass, and never marks a step `done` itself — it only observes that inspector already did, via `.build-state.json`.

## Reset points

Foreman is a fresh subagent per reset point. Reset points are where a natural gap already exists, not a step count:

- Every `checkpoint: true` phase, or whenever autonomy is `checkpoint`.
- Every escalation.
- Any point foreman would otherwise sit idle waiting on something outside the plan.

At a reset point, foreman ends its turn and reports to the root: what closed, what's next, and any open state — the root then spawns the next foreman generation. Foreman never spawns its own successor; every new foreman generation comes from the root.

## Phase close

When every step in a phase is `done`:

1. Foreman confirms the phase exit-criteria evals (phase README) have been run and passed — inspector runs these as part of its normal review scope; foreman only checks the recorded result. If they fail, open a corrective step in the phase and continue the loop.
2. Confirm every step in the phase has a commit SHA recorded on the tracker and in `.build-state.json`.
3. **If this phase is tagged `checkpoint: true`, or autonomy is `checkpoint`,** this is a reset point — foreman reports to the root and stops.
4. **Otherwise**, if there's an immediately-unblocked next step in the next phase, foreman continues without a reset. If not (a genuine gap), foreman reports to the root as a reset point rather than sitting idle.

## Plan close — final coherence pass

When every phase is done and the plan's final acceptance check passes end to end:

1. Foreman dispatches **inspector** to run one final `/code-review` over the **entire commit range** for this plan (fixed point = the commit before phase 1 started), on top of every step's per-step review. It looks for cross-step drift: divergent change, shotgun surgery, inconsistent conventions between phases.
2. Inspector reports the result. If it surfaces blocking findings, foreman opens a corrective step (or phase) and returns to the loop rather than declaring the plan done over unresolved findings.
3. Only once this pass is clean does foreman report the plan complete to the root.

## Parallel dispatch

Dispatch a batch of steps only when they are mutually independent in the graph and do not touch overlapping files. If two unblocked steps are likely to edit the same file, run them in sequence to avoid conflicts.

## Failure and escalation

Escalate (set `escalated` on the tracker + cache, stop, report to the root) when:

- The cycle cap is exceeded with changes still requested.
- An eval cannot be made to pass.
- A precondition is missing or wrong (e.g. the schema differs from the plan's assumption).
- The step is genuinely ambiguous.

Escalation is a clean stop with a specific question, never a guess.

## Definition of done

- **Step:** evals pass, inspector's Spec axis confirms acceptance criteria, inspector approved, commit recorded (all four, done atomically by inspector on approve).
- **Phase:** all steps done and phase exit evals pass.
- **Plan:** all phases done, inspector's final whole-branch review is clean, and the spec's acceptance criteria are met end to end.
