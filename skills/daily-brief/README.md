# Daily Brief — setup

This skill sends a daily Slack DM summarizing today's calendar and the state
of your open pull requests. It can be run interactively (`/daily-brief`) or
on a schedule. This doc covers both.

## 1. Configure

1. Copy `config.example.yaml` (next to this file) to `config.yaml` — it's
   gitignored, never commit it — and fill in:
   - `github_login` — your GitHub username
   - `repos` — list of `owner/repo` strings to track
   - `slack_user_id` — your Slack member ID (Slack profile → "Copy member ID")
   - `display_timezone` — IANA timezone name to render calendar times in
     (e.g. `Europe/London`)
2. If you don't already have a Slack bot token: create an app at
   api.slack.com/apps, add the `chat:write` bot scope, install the app to
   your workspace, then save its Bot User OAuth Token as a file named
   `slack-bot-token` **directly in this skill's own directory** (next to
   `SKILL.md`), and `chmod 600` it. It's gitignored by filename, same as
   `config.yaml` — never commit it.
3. Test it interactively first: run `/daily-brief` and confirm the Slack DM
   arrives correctly before moving on to scheduling it.

## 2. Schedule a headless run

The skill is designed to run unattended (see `SKILL.md`'s failure-handling
rules — it never stalls waiting for a human). To do that, invoke `claude` in
print mode (`-p`) with a scoped permission grant, so nothing prompts.

**You must `cd` into this skill's own directory first** (wherever `claude`
resolves this skill's files from — typically your `~/.claude/skills/
daily-brief`). Every path below — `config.yaml`, `convert_tz.py`,
`send_slack_message.py`, `slack-bot-token` — is granted as a path *relative*
to that directory, not an absolute path, and that only resolves correctly
if the shell's working directory matches it when `claude` starts:

```
cd <path to this skill's own directory> && claude -p "/daily-brief" \
  --permission-mode default \
  --allowedTools \
    "Read(./config.yaml)" \
    "mcp__claude_ai_Microsoft_365__outlook_calendar_search" \
    "Bash(./convert_tz.py *)" \
    "Bash(gh api graphql *)" \
    "Bash(./send_slack_message.py *)"
```

That's the whole allowlist — five entries, no wildcarded shell interpreter,
no `--add-dir`, no credential path baked into the command. Notes:

- `--permission-mode default` is real manual mode — nothing outside
  `--allowedTools` is auto-approved. This is deliberately *not* `auto` or
  `--dangerously-skip-permissions`: the allowlist is scoped to exactly what
  this skill's current steps call, so anything else (a future change to the
  skill, a bug, a prompt-injection attempt from calendar/PR content) fails
  closed instead of being silently approved.
- `convert_tz.py` and `send_slack_message.py` are fixed scripts that ship
  with this skill (see `SKILL.md`) — the allow rules grant running *those
  specific files* with varying arguments/stdin, never arbitrary code. There
  is deliberately no `Bash(python3 -c *)`-style rule anywhere: that would
  match *any* Python source passed inline, which is a much bigger grant than
  this skill actually needs.
- Both scripts and the bot token live inside the skill directory precisely
  so everything the headless run touches sits under one working directory —
  no `--add-dir` needed, because the sandbox's default filesystem access
  already covers it.
- `Bash(gh api graphql *)` is the one broader entry left — inherent to using
  the `gh` CLI for PR data; the query text itself is fixed in `SKILL.md`,
  only the target repo (from your own `config.yaml`) varies per call.

### Gotchas (found by testing this exact command)

- **Working directory is what makes the relative rules work — and it's the
  `PWD` environment variable that matters, not just the OS-level working
  directory.** A shell's `cd` sets both, which is why the crontab form above
  (`cd ... && claude ...`, run through a shell) works with `WorkingDirectory`
  never mentioned at all. systemd's `WorkingDirectory=` directive only sets
  the OS-level cwd — it does *not* set `PWD`, since that's normally a
  shell's job — and without `PWD` set, every relative allow rule silently
  stops matching and you're back to interactive approval prompts (which
  never resolve headlessly — see `SKILL.md`'s calendar-fetch failure
  handling for what happens then). Confirmed by testing: `WorkingDirectory=`
  alone fails with the `config.yaml` read denied; adding the matching
  `Environment=PWD=...` line (as in the example below) fixes it. If you
  invoke `claude -p` any other way, make sure whatever you use actually sets
  `PWD` to this skill's own directory, not just the process's cwd.
- **No log file by design.** This setup doesn't redirect output anywhere —
  the Slack message arriving is the signal that it worked. If a morning's
  brief doesn't show up, debug by running the command above manually.
- **Binary paths.** Cron and systemd both run with a minimal `PATH`. Run
  `which claude` and use its absolute path in your crontab/service file if
  it isn't reliably on `PATH` in that context (`gh` and `python3` are
  invoked by the skill itself, not by the command line below, so they only
  need to be on `PATH` inside whatever shell Claude runs them in — usually
  fine, but worth checking with `which gh python3` too).

### Option A — crontab

```
crontab -e
```

Add (weekdays at 09:00 local time — adjust as needed):

```cron
0 9 * * 1-5 cd <path to this skill's own directory> && /usr/bin/claude -p "/daily-brief" --permission-mode default --allowedTools "Read(./config.yaml)" "mcp__claude_ai_Microsoft_365__outlook_calendar_search" "Bash(./convert_tz.py *)" "Bash(gh api graphql *)" "Bash(./send_slack_message.py *)"
```

### Option B — systemd user timer

`~/.config/systemd/user/daily-brief.service`:

```ini
[Unit]
Description=Daily Brief

[Service]
Type=oneshot
WorkingDirectory=<path to this skill's own directory>
Environment=PWD=<path to this skill's own directory, same value as above>
ExecStart=/usr/bin/claude -p "/daily-brief" --permission-mode default --allowedTools "Read(./config.yaml)" "mcp__claude_ai_Microsoft_365__outlook_calendar_search" "Bash(./convert_tz.py *)" "Bash(gh api graphql *)" "Bash(./send_slack_message.py *)"
```

`~/.config/systemd/user/daily-brief.timer`:

```ini
[Unit]
Description=Run Daily Brief weekdays at 09:00

[Timer]
OnCalendar=Mon..Fri 09:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable it:

```
systemctl --user daemon-reload
systemctl --user enable --now daily-brief.timer
```

User systemd units normally stop running once you log out. To let the timer
fire while you're logged out (overnight, etc.), enable lingering once:

```
loginctl enable-linger $USER
```

Check `Linger=yes` afterward with `loginctl show-user $USER -p Linger`.

## 3. Not a fit for `CronCreate`

If you're running this from inside an interactive Claude Code session with
access to a `CronCreate` tool, don't use it for this: those jobs are
session-only (they die when the session ends) and auto-expire after 7 days
regardless. Use crontab or systemd as above for anything persistent.
