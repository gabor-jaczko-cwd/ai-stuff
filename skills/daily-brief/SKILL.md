---
name: daily-brief
description: Generate and send the Daily Brief — today's calendar plus open-PR status across your configured repos — to Slack. Use when the user asks to run/send the Daily Brief, or invokes /daily-brief. Also invoked headlessly by a scheduled job every workday morning.
---

# Daily Brief

Produces one Slack message summarizing today's calendar and the state of
open pull requests across your configured repos, then sends it. Runs both
interactively (`/daily-brief`) and headlessly via a scheduled job — behave
identically either way; don't ask clarifying questions, just run the steps
below and send.

## 0. Setup (one-time)

This skill reads a local config file — `config.yaml` in this skill's own
directory — for your repos, GitHub login, and Slack details. That file is
gitignored; never commit it.

See `README.md` (next to this file) for how to create `config.yaml` and how
to set up the scheduled headless run. This section only covers what the
skill itself needs to know at runtime.

Before doing anything else, read `config.yaml` from this skill's own
directory. If it doesn't exist, stop and tell the user to complete Setup
above; don't guess at repos or IDs.

Use the **`gh` CLI** (via Bash) for all PR data, never the GitHub MCP tool.

## 1. Calendar

Call the Outlook calendar search tool:
- `query`: `*`
- `afterDateTime`: "today at midnight"
- `beforeDateTime`: "tomorrow at midnight"
- `limit`: 25 (follow `nextOffset` if present)

Drop any event with `isCancelled: true`. Sort by start time ascending.

**Always convert each event's time into `display_timezone`** (from
`config.yaml`), using the event's own returned `timeZone` as the source zone
— never render `dateTime` as-is. Convert every event's start/end in **one**
call to this skill's own `convert_tz.py` script — never by hand or by
reasoning about offsets or DST. Invoke it as `./convert_tz.py`, relative to
this skill's own directory, never by absolute path (the headless run's
permission allowlist only matches the relative form; see `README.md`):
```
./convert_tz.py <display_timezone> <dateTime_1> <timeZone_1> <dateTime_2> <timeZone_2> ...
```
Pass every event's start and end as `(dateTime, timeZone)` pairs, in a stable
order, then map the printed lines back onto their events by that order.

For each event, render one line:
`• <start>–<end> — <subject> (<attendee names>)`

- Times: use the local time from the step above. Format as `HH:MM`.
- All-day events: `All day — <subject>` instead of a time range.
- Attendee names: the API only returns email addresses. Derive a display name
  from the local-part (before `@`): split on `.`, title-case each part, join
  with a space (e.g. `jane.doe` → `Jane Doe`). Exclude the user's own
  email from the shown list. Show up to 3 names, then `+N others` if more.
- If there are no events for today: the calendar section is just `No meetings
  today.`

**If the calendar tool call fails for any reason** — including a permission
prompt that never resolves — retry up to 3 times, then move on. Never pause
the run to wait for a human to approve a permission prompt. Treat it as a
Failures-section case (see below): render the calendar section as
`⚠️ Could not fetch calendar (<short reason>) — showing PR data only.` and
continue straight on to the Pull requests section.

## 2. Pull requests

Read `repos` and `github_login` from `config.yaml`.

For each repo, fetch everything needed in **one** `gh api graphql` call with
this query and `--jq` filter. Never use `gh pr list --json` instead (it
exceeds GitHub's GraphQL node limit).

```
gh api graphql -f query='
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    pullRequests(states: OPEN, first: 100, orderBy: {field: UPDATED_AT, direction: DESC}) {
      nodes {
        number
        title
        url
        isDraft
        updatedAt
        createdAt
        author { login }
        assignees(first: 10) { nodes { login } }
        reviewRequests(first: 10) { nodes { requestedReviewer {
          ... on User { login }
          ... on Team { name }
        } } }
        reviews(first: 100) { nodes { author { login } state submittedAt } }
        commits(last: 1) {
          nodes {
            commit {
              committedDate
              statusCheckRollup { state }
            }
          }
        }
      }
    }
  }
}' -f owner=<owner> -f name=<repo> \
--jq '[.data.repository.pullRequests.nodes[] | select(.isDraft == false) | {
  number, title, url,
  author: .author.login,
  assignees: [.assignees.nodes[].login],
  updatedAt, createdAt,
  reviewRequests: [.reviewRequests.nodes[].requestedReviewer | (.login // .name)],
  reviews: [.reviews.nodes[] | {author: .author.login, state, submittedAt}],
  lastCommitAt: .commits.nodes[0].commit.committedDate,
  ci: (.commits.nodes[0].commit.statusCheckRollup.state as $s |
       if $s == "SUCCESS" then "passing"
       elif $s == "FAILURE" or $s == "ERROR" then "failing"
       elif $s == "PENDING" or $s == "EXPECTED" then "running"
       else "none" end)
}]'
```

If a repo's call fails or errors, note it (see Failures below) and move on —
don't abort the whole run.

**Bot filtering**: when computing "last human review", ignore reviews from bot
accounts (`copilot-pull-request-reviewer`, `github-actions`, or any login
containing "copilot" or "[bot]"). Bot reviews never count as a review for
classification or for the green/red mark.

**CI status** from the `ci` field, already aggregated by the jq filter above:
`failing` → `❌ CI failing`, `running` → `⏳ CI running`, `passing` → `✅ CI
passing`, `none` → omit the CI marker.

**Classification** (My PRs takes priority over the other two buckets):

1. **My PRs** — `author == github_login` OR `github_login` appears in
   `assignees`. Goes here regardless of review state. Show CI status and, if
   `reviewRequests` is non-empty, "review requested from N people".

2. Otherwise, look at human-authored reviews only:
   - No human review at all → **Updated** bucket, marked `🆕 no review yet`.
   - Human review(s) exist → for each human reviewer, walk their reviews in
     chronological order (oldest to newest, by `submittedAt`) and track two
     things: `standing` (starts at none) and `ever_approved` (starts at
     false). Also separately remember each reviewer's own most recent
     `COMMENTED` `submittedAt`, for the comment-only fallback below.
     - `APPROVED` or `CHANGES_REQUESTED` → `standing` = that state + its
       `submittedAt`; `ever_approved` = true.
     - `DISMISSED` → `standing` = none again (`ever_approved` stays as it
       was).
     - `COMMENTED` → never changes `standing` or `ever_approved`.
   - **If any reviewer ends with `standing` none but `ever_approved` true**
     (a later commit got their approval/changes-requested `DISMISSED`, and
     nobody has re-reviewed since) → **Updated** bucket, marked `🆕 new
     commits invalidated @<login>'s review — needs a fresh look`.
   - **Otherwise**, determine `last_review`: the reviewer with the most
     recent non-none `standing`, or — if no reviewer has one — the reviewer
     with the most recent `COMMENTED`. If neither exists → **Updated**
     bucket, marked `🆕 no review yet`.
   - **If `last_review`'s state is `APPROVED`** → **Reviewed** bucket,
     marked `✅ approved by @<login>`. Do not compare against `lastCommitAt`
     here; the `DISMISSED` check above already covers invalidated approvals.
   - **Otherwise** (`last_review`'s state is `CHANGES_REQUESTED` or
     `COMMENTED`), compare `last_review`'s `submittedAt` against
     `lastCommitAt`, NOT `updatedAt` (which bumps on any activity, not just
     new code): if `lastCommitAt`
     is newer → **Updated** bucket, marked `🆕 new commits since last review
     (<login> <state>)`; otherwise → **Reviewed** bucket, marked `🔴 changes
     requested by @<login>` or `💬 commented by @<login>` accordingly.

Render each bucket as:
```
<Bucket name> (<count>)
• <url as Slack link>|#<number>> <title>
  by @<author> · updated <relative time> · <bucket-specific marker> · <CI marker>
```
Omit a bucket entirely if it has zero PRs. If all three buckets are empty:
`No PRs need attention.`

**Added as reviewer**: `github_login` counts as added if EITHER: they appear
in the PR's `reviewRequests` (currently requested, hasn't reviewed yet), OR
they appear as an `author` in the PR's `reviews` array (already submitted a
review, any state). If either is true, render that PR's two-line entry in
Slack bold, wrapping **each line in its own `*` pair** (Slack bold does not
span a newline):
```
• *<url as Slack link>|#<number>> <title>*
  *by @<author> · updated <relative time> · <bucket-specific marker> · <CI marker>*
```
This applies in whichever bucket the PR lands in, including **My PRs**.

Do not include repo names in the PR lines.

## 3. Failures

If the calendar fetch, a repo's PR list, or a specific PR's detail calls
fail, keep going with everything else that succeeded, and add one line per
failure — `⚠️ Could not fetch calendar (<short error>) — showing PR data
only.` or `⚠️ Could not fetch PRs from <repo> (<short error>) — showing
partial results.`

Never abort the whole brief because one call failed, and never stop to wait
on a permission prompt.

## 4. Compose and send

Message template:

```
📋 Daily Brief — <Weekday, D Mon YYYY>

📅 Today's Calendar
<calendar lines, or "No meetings today.">

🔧 Pull Requests

<non-empty buckets, in order: My PRs, Updated — needs a look, Reviewed — no new activity>

<any ⚠️ failure lines>
```

**Sending**: use the dedicated Slack bot, never the `slack_send_message`
MCP tool. The bot token lives at `slack-bot-token` in this skill's own
directory — never print, log, or echo its contents.

Send with this skill's own `send_slack_message.py` script, invoked as
`./send_slack_message.py` (relative, like `convert_tz.py` above), passing
`slack_user_id` (from `config.yaml`) as its one argument and the composed
message on **stdin** via a heredoc:

```
./send_slack_message.py <slack_user_id> <<'EOF'
<the composed message>
EOF
```

The script does the DM-channel lookup and the send, and JSON-encodes the
payload itself. **Never** hand-build a JSON string for this (e.g. a
`curl -d '{"...": "..."}'` argument); always pass the raw message on stdin.

The script prints the final Slack API response as JSON and exits non-zero
on failure — check it for `"ok":true`; treat a non-zero exit or `"ok":false`
as a Failures-section case.

After sending, report back briefly (one line) that the Daily Brief was sent.
Don't restate the report in chat.
