# Long-running commands (full suite / full CI runs)

Some eval and verification commands — a full test suite, a full local CI gate, a full browser
suite — run past the Bash tool's foreground timeout (max 10 minutes), sometimes 30-90+ minutes.
crewman and inspector only have `Bash` for this (no `Monitor`, `ScheduleWakeup` or `TaskOutput`),
and a nested subagent cannot rely on the "background job finished" notification arriving. Use the
pattern below; do not improvise your own.

## Never poll the process table

Never decide whether a command is still running by searching for a string, e.g.
`while pgrep -f "coral ci" >/dev/null; do sleep 5; done` — `pgrep -f` matches the polling loop's
own command line, so it never exits. Poll for a completion marker instead.

## The pattern

**1. Launch, with the marker in the same background job** (the Bash tool's
`run_in_background: true`, not a bare trailing `&`):

```bash
{ ./coral ci; echo "EXIT_CODE=$?"; } > /tmp/<scratchpad>/coral_ci.log 2>&1
```

**2. Poll for the marker in a separate, later, plain foreground Bash call:**

```bash
until grep -q '^EXIT_CODE=' /tmp/<scratchpad>/coral_ci.log 2>/dev/null; do sleep 15; done
tail -80 /tmp/<scratchpad>/coral_ci.log
```

If this call times out before the marker appears, issue the identical call again. Repeating it
across several tool calls is the normal way to wait out a long run.

**3. If you need a liveness check** (rare — prefer the marker), capture the PID at spawn time
(`$!`, immediately after backgrounding) and check that exact PID with `kill -0 "$PID"`. Never
`pgrep -f`.

## When you don't need any of this

Run anything that reliably finishes in a couple of minutes (a single test file, a filtered subset)
in the foreground, with no polling. Background a command only once you've seen it outlive a single
foreground call.

## If you abandon a background job

If a background run stops mattering before it finishes (superseded by a later run, the step's
scope changed), say so in your report, so it can be killed if pointless.

## A killed poll call tells you nothing about the real command

If a poll call comes back killed, errored or otherwise abnormal, check the output file for the
marker before concluding whether the real command succeeded, failed or is still running.
