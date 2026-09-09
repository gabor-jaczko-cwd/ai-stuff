# Long-running commands (full suite / full CI runs)

Some eval and verification commands — a full test suite, a full local CI gate, a full browser
suite — routinely run well past the Bash tool's own foreground timeout (max 10 minutes), sometimes
30-90+ minutes on a real project. crewman and inspector both only have `Bash` for this (no
`Monitor`, no `ScheduleWakeup`, no `TaskOutput`) — and, structurally, a nested Task-dispatched
subagent cannot reliably receive the "background job finished" notification a top-level root
session gets from the Bash tool's own `run_in_background`. **Do not rely on that notification
arriving.** This page is the one correct pattern for waiting out a command that will outlive a
single foreground call — read it before improvising your own.

## The bug this page exists to prevent

A real production run produced eight permanently-stuck background shells, each written as some
variant of:

```bash
while pgrep -f "coral ci" >/dev/null; do sleep 5; done; echo CI_DONE
```

This is broken in a way that is not obvious until it happens: `pgrep -f PATTERN` matches against
the **full command line of every process**, including the polling loop's own wrapper process —
and that wrapper's command line contains the exact string it's grepping for, because the shell
literally embeds the pattern in its own invocation. The loop matches itself, forever. The real
`./coral ci` had already finished; the loop never noticed and never exited. Root only found these
by manually walking `ps -ef` for `sleep` children and reading each parent's full command line —
that should never be necessary.

A second, independent bug in the same incident: at least one loop was an unbounded `while`/`until`
with no max-iteration ceiling and no timeout of its own — so even a *correctly*-written exit
condition that was simply wrong for some other reason would still spin forever rather than fail
loudly.

## The canonical safe pattern

Never determine "is the command still running" by searching the process table for a string. Write
an explicit completion marker to the command's own output file instead, and poll for the marker,
not for a process disappearing.

**1. Launch, with the marker baked into the same background job** (use the Bash tool's own
`run_in_background: true` so the harness tracks it too, not a bare trailing `&`):

```bash
{ ./coral ci; echo "EXIT_CODE=$?"; } > /tmp/<scratchpad>/coral_ci.log 2>&1
```
(`run_in_background: true` on this call.)

**2. Poll for the marker in a separate, later, plain foreground Bash call** — bounded by that
call's own timeout, which is fine:

```bash
until grep -q '^EXIT_CODE=' /tmp/<scratchpad>/coral_ci.log 2>/dev/null; do sleep 15; done
tail -80 /tmp/<scratchpad>/coral_ci.log
```

If this single foreground poll call times out before the marker appears — expected for a
90-minute suite — just issue the identical call again. Each individual call is safely bounded;
repeating it across several tool calls is the normal, expected way to wait out a long run. This is
different from, and safe where, the broken pattern above was not: there is no long-lived detached
process anywhere, so there is nothing left running if you stop polling (you simply haven't read
the result yet — the real command keeps running to completion regardless).

**3. Never re-derive a PID or a "still running" signal by grepping for a description string.** If
you truly need a liveness check rather than a marker (rare — prefer the marker), capture the PID
directly at spawn time (`$!`, immediately after backgrounding) and check that exact PID with
`kill -0 "$PID"` — never `pgrep -f "<text that also appears in your own checking command>"`. Even
this is weaker than the marker pattern (a recycled PID can produce a false positive), so treat it
as a fallback, not the default.

## When you don't need any of this

Anything that reliably finishes in a couple of minutes — a single test file, a filtered subset —
just run in the foreground, plainly, with no polling machinery at all. Reserve the pattern above
for genuinely long commands (full suite, full CI, full browser run). Don't background a command
just because it *might* be slow; background it because you've already seen it take longer than a
single foreground call can wait.

## If you abandon a background job

If a background run stops mattering before it finishes (superseded by a later run, the step's
scope changed under you), say so plainly in your report rather than silently walking away from it
— foreman/inspector/root should know a background process may still be executing so it isn't
mistaken for stuck state later, and so it can be killed if it's pointless to let finish.

## A killed poll call tells you nothing about the real command

In the same incident, root eventually killed the stuck loops directly (there was no other way to
clear them). At least one agent's very next action, immediately after its blocking wait call
returned with a kill/error status, was to treat that as if the underlying long-running command had
itself just finished or failed, and resume acting on that basis — it hadn't; only the polling
wrapper died. With the broken pattern above this ambiguity is real, because the loop and the real
command were tangled into the same lifecycle. With the marker pattern above it structurally cannot
happen: the real command runs as its own independent backgrounded process, decoupled from whatever
poll call is currently reading its output file. If a foreground poll call you issued ever comes
back killed, errored, or otherwise abnormal, that is a statement about the poll call — check the
output file directly for the real marker before concluding anything about whether the actual
command succeeded, failed, or is still running.
