# Context Management

Keep every layer's context small by construction, not by discipline within a long-lived session. Three things do this: subagent isolation, foreman's own thin tool surface, and resetting foreman between reset points instead of asking it to self-compact.

## Why this changed

The old design ran foreman continuously in the main session for an entire plan and relied on it to "discard detailed history" between steps. In practice that doesn't work: a session's context can't actually be shrunk mid-conversation, so "discard" was aspirational, and a foreman with `Bash`/`Read`/`Edit` available used them — real build sessions showed foreman running hundreds of `grep`/`sed`/`docker exec` calls and full test-suite re-runs directly, none of which a "compact between steps" instruction ever removed once it was in context. The fix isn't better discipline inside one long session; it's not letting that much ever accumulate in the first place.

## Subagent isolation (unchanged in spirit)

Crewman and inspector run in their own context windows and return only distilled results — crewman's 1,000–2,000 token report, inspector's verdict. None of their detailed exploration or raw tool output ever enters foreman's context, and as of this version, most of what they produce doesn't even pass *through* foreman — inspector writes its verdict and feedback straight to `.build-state.json`; foreman polls status, not content.

## Foreman's own footprint is bounded by its tool list

Foreman's tools are `Task`, `TodoWrite`, and `Read`/`Write` hook-scoped to exactly `PLAN.md` and `.build-state.json`. It cannot `grep` the codebase, cannot run the test suite itself, cannot open arbitrary files. Its context grows by roughly: one dispatch call plus one short status poll per step, not by whatever raw exploration it might otherwise be tempted to do. This is what keeps a foreman generation's context small regardless of how many steps it drives, and it's enforced by the harness (the tools genuinely aren't offered), not by prose telling it to behave.

## Resets instead of self-compaction

Foreman cannot clear its own context (`/clear` is a harness-level action, not something an agent can invoke on itself) and is not asked to try. Instead, it's spawned fresh by the root at each reset point (see `agents/foreman.md` and `loop-protocol.md`) — a `checkpoint: true` phase, autonomy `checkpoint`, an escalation, or any point it would otherwise sit idle waiting on something outside the plan. Reset cadence is tied to where a gap already exists, not a fixed step count: a well-behaved, tool-restricted foreman doesn't need a reset every few steps just to stay small, but resetting before a gap caps how much context is ever exposed to a stale prompt-cache entry (long idle gaps risk a cache miss being rebilled at the more expensive cache-write rate — see the profile's `test_command` latency as a rough guide to how long a step-to-step gap actually is on this project).

Each new foreman generation starts from: `PLAN.md`, the current phase's README, and a fresh read of `.build-state.json`/the tracker for status. Nothing carries forward as remembered prose — if the next generation needs to know something, it's either already on the tracker/cache or re-derivable by reading the code, never something the previous generation has to have "remembered to mention" in a handoff message.

## What to keep versus discard

- **Keep:** the plan documents (`PLAN.md`, phase READMEs), `.build-state.json` as the record of per-step status and review content, awareness of which tickets are done/in-flight (queryable on demand — don't pre-load all of them).
- **Discard:** raw tool output (foreman has no tools that produce much of it), resolved back-and-forth, superseded attempts, full file contents, and any prose restating what `.build-state.json` or the tracker already says.

## The root's own footprint

The root session (persistent for the whole plan) does even less per cycle than foreman: spawn a foreman generation, wait, receive its short report, spawn the next one. It never reads code, the diff, or review content — so its own context grows by roughly one short report per reset point for the life of the plan, not per step. This is what makes "stay alive for the whole plan" safe for the root even though it wasn't safe for the old, unrestricted foreman.
