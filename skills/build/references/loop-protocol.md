# Loop Protocol

How foreman drives one step from selection to done, and how phases close. foreman runs in the main session; crewman and inspector are subagents spawned with the Task tool. Tooling (test and format commands) comes from the resolved project context.

## Roles

- **foreman** (main session): selects work, delegates, gates sign-off, compacts. Never edits code.
- **crewman** (subagent): the only code modifier. Implements one step, writes and runs its evals with the project's commands, reports back.
- **inspector** (subagent, read-only): verifies a step against acceptance criteria and evals by running `code-review`'s Standards + Spec axes scoped to the step, then folds both into one verdict.

## Step lifecycle

```
pending -> in_progress -> in_review -> done
              ^                |
              |___ changes ____|        (up to cycle_cap)
                                 -> escalated   (cap exceeded or blocker)
```

1. **Select.** Query the tracker (or the cache, if freshly synced) for the next unblocked step (all `depends_on` closed/done). Set it `in_progress`: claim its ticket the way `wayfinder` claims a frontier ticket.
2. **Dispatch to crewman.** Spawn `crewman` with the build payload (below). Independent unblocked steps may be dispatched together if they don't touch overlapping files.
3. **Conformance check (sign-off one).** On crewman's report, confirm each acceptance criterion is addressed and the evals ran and passed — including the browser-verification eval if the step touches UI. If not, return to crewman with specific notes (counts against the cycle cap).
4. **Review (sign-off two).** Set the step `in_review` (ticket state + cache). Spawn `inspector` with the review payload.
5. **Resolve.** APPROVE with evals passing moves to the commit gate below. CHANGES_REQUESTED posts the numbered feedback as a ticket comment and hands it to crewman, returning to step 2 for this step.
6. **Commit (mandatory, before status flips to done).** Stage and commit exactly this step's changed files, message referencing the step/ticket id, e.g. `feat(2.1): add rate-limit middleware`. One commit per step — never batch several approved steps into one commit, and never commit on crewman's report alone (only after inspector's APPROVE). Post the SHA as a ticket comment, close/transition the ticket, write both to `.build-state.json`, then mark the step `done`.
7. **Cap.** If the crewman/inspector exchange for a step exceeds `cycle_cap` (default 3) still unresolved, set `escalated` (ticket + cache), write the open feedback as a ticket comment, and stop for a human.

A `Stop` hook (`build-commit-guard.py`) enforces step 6 deterministically: it blocks foreman's turn from ending if `.build-state.json` shows any step `done` with no commit recorded. Treat that block as a bug in your own execution, not a false positive — go back and commit and sync.

## Handoff payloads

Keep payloads tight. Pass references by path/ticket-id, not by pasting whole files.

**Build payload (foreman to crewman):**

- Step id, and its ticket (or step file, if spec-planned).
- Acceptance criteria and eval spec.
- The project's test command and format command, and the conventions that apply to this step.
- Whether this step touches rendered UI (triggers the browser-verification eval).
- Any interface or contract decisions from earlier phases (from the tracker's prior ticket comments, not a bespoke state file).

**crewman report (crewman to foreman):** step id, changed files, evals written and the test-command result, browser-check result if applicable, how each acceptance criterion is met, deviations and risks. Aim 1,000 to 2,000 tokens.

**Review payload (foreman to inspector):**

- The step's ticket (acceptance criteria) and the diff for the step.
- crewman's report.
- The project's documented standards sources, exactly as `code-review` would gather them for a normal invocation.

**inspector verdict (inspector to foreman):** APPROVE (one-line justification, plus any non-blocking suggestions from either axis marked optional) or CHANGES_REQUESTED (numbered, file-specific, severity-ordered items, each tagged `[standards]` or `[spec]` so crewman knows which axis flagged it).

### How inspector runs the two axes

Spawn the same Standards + Spec parallel sub-agent pattern `code-review` uses, but scoped down:

- **Standards sub-agent:** same brief as `code-review`'s (documented repo standards + the Fowler smell baseline), but only the step's diff.
- **Spec sub-agent:** same brief as `code-review`'s, but the "spec" is this step's acceptance criteria (from its ticket or step file), not the whole feature spec.

Fold both reports into one verdict rather than presenting them side by side as `code-review` does standalone — a step gate needs one APPROVE/CHANGES_REQUESTED, not two parallel readouts.

## Sign-off gates

A step is `done` only when all four hold:

1. Evals pass (the project's test command is green for the step's evals, and the browser check passed if applicable).
2. foreman confirms the step meets its acceptance criteria.
3. inspector returns APPROVE.
4. The step's changes are committed, and the commit SHA is recorded on the tracker and in `.build-state.json`.

Never mark a step done on crewman's word alone. Never weaken an eval to pass. Never mark a step `done` before it is committed — status and the commit happen together.

Compact when a step is done (see `context-compaction.md`).

## Phase close

When every step in a phase is `done`:

1. Run the phase exit-criteria evals (phase README). If they fail, open a corrective step in the phase and continue the loop.
2. Confirm every step in the phase has a commit SHA on the tracker and in the cache. Do not proceed until it does.
3. **If this phase is tagged `checkpoint: true`, or autonomy is `checkpoint`,** stop here for the user's sign-off — do not continue past it in the same context.
4. **End the session, don't try to clear it from inside itself.** foreman has no tool to invoke `/clear` on its own running session. So its job at phase close is to stop cleanly and hand off:
   - If there are more phases, end the final message with a clearly marked **handoff prompt**: the plan path, the phase now closing, the next phase to start, and "read PLAN.md and the tracker, then continue the loop-protocol from phase N+1." Tell the user (or the process driving this session) to run `/clear` and start a fresh `foreman` with that handoff prompt.
   - If autonomy is `auto` and something outside this session is scripted to relaunch automatically, the handoff prompt is what gets fed to the next invocation. foreman never assumes it can loop itself.
5. A `PreCompact` hook (`build-precompact-check.py`) fires as a safety net whenever compaction runs while a plan is active, reminding whoever is driving the session that the tracker and cache must be current first. It does not replace the deliberate end-of-phase handoff above.

## Plan close — final coherence pass

When every phase is done and the plan's final acceptance check passes end to end:

1. Run one final `/code-review` over the **entire commit range** for this plan (fixed point = the commit before phase 1 started). This is on top of, not instead of, every step's `inspector` gate — it catches cross-step drift (divergent change, shotgun surgery, inconsistent conventions between phases) that no single-step scope would see.
2. Report the result. If it surfaces blocking findings, open a corrective step (or phase) and return to the loop rather than declaring the plan done over unresolved findings.
3. Only once this pass is clean does foreman declare the plan complete.

## Parallel dispatch

Dispatch a batch of steps only when they are mutually independent in the graph and do not touch overlapping files. If two unblocked steps are likely to edit the same file, run them in sequence to avoid conflicts.

## Failure and escalation

Escalate (set `escalated` on the tracker + cache, stop) when:

- The cycle cap is exceeded with changes still requested.
- An eval cannot be made to pass.
- A precondition is missing or wrong (e.g. the schema differs from the plan's assumption).
- The step is genuinely ambiguous.

Escalation is a clean stop with a specific question, never a guess.

## Definition of done

- **Step:** evals pass, conformance confirmed, inspector approved, commit recorded.
- **Phase:** all steps done and phase exit evals pass.
- **Plan:** all phases done, the final whole-branch `/code-review` pass is clean, and the spec's acceptance criteria are met end to end.
