# Context Compaction

Keep foreman's context lean so it stays coherent across a long build: subagents isolate detail, and foreman compacts at each boundary.

## Subagent isolation

crewman and inspector run in their own context windows and return only distilled summaries (the 1,000 to 2,000 token report and the verdict). Their detailed exploration and raw tool output never enter foreman's context. Prefer delegating deep work over doing it in the main session.

## Between-step compaction

At each step boundary:

1. Confirm the step is committed (see `loop-protocol.md`'s commit gate) and note the short SHA — a step is never compacted away as "done" without one.
2. Sync the tracker: post the commit SHA and inspector's verdict as ticket comments, close/transition the ticket.
3. Update `.build-state.json` to match what was just posted to the tracker — it should never drift from what the tracker says.
4. Discard the finished step's detailed message history: what the next step needs is either already on the tracker or re-derivable by reading the code, not carried forward as prose.
5. Continue the next step from a lean context: PLAN.md, the relevant phase README, and the next step's ticket/step file only.

Sync the same way at phase close and escalation, not just step completion — nothing should be true only in a message history about to be discarded.

## What to keep versus discard

- **Keep:** the plan documents (PLAN.md, phase READMEs), open escalations, awareness of which tickets are done/in-flight (queryable from the tracker on demand — don't pre-load all of them).
- **Discard:** raw tool output, resolved back-and-forth, superseded attempts, full file contents that can be re-read on demand, and any prose restating what a ticket comment already says.
