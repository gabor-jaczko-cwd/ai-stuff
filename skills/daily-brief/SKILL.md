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

1. Copy `config.example.yaml` (next to this file) to `config.yaml` and fill
   in:
   - `github_login` — your GitHub username
   - `repos` — list of `owner/repo` strings to track
   - `slack_user_id` — your Slack member ID (Slack profile → "Copy member ID")
   - `slack_bot_token_path` — filesystem path to a Slack bot token file
2. If you don't already have a Slack bot token: create an app at
   api.slack.com/apps, add the `chat:write` bot scope, install the app to
   your workspace, then save its Bot User OAuth Token to the path you put in
   `slack_bot_token_path` (`chmod 600` it).

Before doing anything else, read `config.yaml` from this skill's own
directory. If it doesn't exist, stop and tell the user to complete Setup
above — don't guess at repos or IDs, and don't fail deep into the run with a
confusing error.

Use the **`gh` CLI** (via Bash) for all PR data — not the GitHub MCP tool.
The MCP tool's `get_reviews`/`get_comments` methods return full review/comment
bodies with no way to ask for just the metadata, which can be large enough to
blow past the MCP tool's response-size limit on some PRs. `gh ... --json
... --jq '...'` filters server/CLI-side before the data ever reaches you, so
it never hits that ceiling. Don't mix MCP and CLI for this data — CLI only.

## 1. Calendar

Call the Outlook calendar search tool:
- `query`: `*`
- `afterDateTime`: "today at midnight"
- `beforeDateTime`: "tomorrow at midnight"
- `limit`: 25 (follow `nextOffset` if present)

Drop any event with `isCancelled: true`. Sort by start time ascending.

For each event, render one line:
`• <start>–<end> — <subject> (<attendee names>)`

- Times: use the event's own `{dateTime, timeZone}` pair as returned — do not
  reinterpret as UTC. Format as `HH:MM`.
- All-day events: `All day — <subject>` instead of a time range.
- Attendee names: the API only returns email addresses. Derive a display name
  from the local-part (before `@`): split on `.`, title-case each part, join
  with a space (e.g. `jane.doe` → `Jane Doe`). Exclude the user's own
  email from the shown list. Show up to 3 names, then `+N others` if more.
- If there are no events for today: the calendar section is just `No meetings
  today.`

**If the calendar tool call fails for any reason** — including a permission
prompt that never resolves — retry up to 3 times, then stop trying and move
on. Never pause the run to wait for a human to approve a permission prompt;
when this runs headlessly (via the scheduled job) there is no one there to
approve it, and stalling means the whole brief never gets sent. Treat it as
a Failures-section case (see below): render the calendar section as
`⚠️ Could not fetch calendar (<short reason>) — showing PR data only.` and
continue straight on to the Pull requests section. This must be the actual
behavior every run, not a judgment call — a prior run stalled asking for
approval instead of degrading gracefully, and that's the bug this rule
fixes.

## 2. Pull requests

Read `repos` and `github_login` from `config.yaml`.

For each repo, fetch everything needed in **one** `gh api graphql` call, with
a `--jq` filter that strips review/comment bodies server-side so they never
enter your context. Use a raw GraphQL query rather than `gh pr list --json`:
`gh pr list --json commits` pulls in every commit's `authors` connection
whether you ask for it or not, and on a PR list of any size that blows past
GitHub's GraphQL node-count limit (100 PRs × commits × authors can exceed
500,000 nodes). A hand-written query with `commits(last: 1)` and no `authors`
sub-selection avoids that entirely.

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

`lastCommitAt` comes from the PR's single most recent commit — no need to
reduce an array, `commits(last: 1)` already gives just that one.

`ci` reuses GitHub's own rollup (`statusCheckRollup.state` on the latest
commit) rather than aggregating individual check runs by hand.

Draft PRs are excluded entirely — `select(.isDraft == false)` drops them before
they ever reach the classification step below.

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
   - Human review(s) exist → for each human reviewer, compute their
     *standing state*: the state of their most recent `APPROVED` or
     `CHANGES_REQUESTED` review if they have one, otherwise their most
     recent `COMMENTED` review. Do NOT just take the timestamp-latest review
     regardless of state — a reviewer who approves and then leaves follow-up
     single-comment reviews (a common GitHub pattern: replying to their own
     inline threads right after approving) still reads as "Approved" in
     GitHub's own Reviewers panel; a later `COMMENTED` review from the same
     person doesn't downgrade it. Picking the raw latest-by-time review
     mislabels these as "commented by" the approver, which is wrong.
   - Let `last_review` = whichever reviewer's standing-state review is most
     recent across all reviewers, and `last_review_time` = its
     `submittedAt`. Compare against `lastCommitAt`, NOT `updatedAt` — `updatedAt`
     bumps on anything (a bot comment, a label, a reply) and doesn't mean new
     code landed, which is what actually invalidates a review. If
     `lastCommitAt` is newer than `last_review_time` (a commit landed after
     the last human look) → **Updated** bucket, marked `🆕 new commits since
     last review (<login> <state>)` from `last_review`. Otherwise →
     **Reviewed** bucket, marked from `last_review`'s state: `✅ approved by
     @<login>`, `🔴 changes requested by @<login>`, or `💬 commented by
     @<login>` (only when `COMMENTED` is that reviewer's standing state, i.e.
     they never approved or requested changes).

Render each bucket as:
```
<Bucket name> (<count>)
• <url as Slack link>|#<number>> <title>
  by @<author> · updated <relative time> · <bucket-specific marker> · <CI marker>
```
Omit a bucket entirely if it has zero PRs. If all three buckets are empty:
`No PRs need attention.`

**Added as reviewer**: this is the same set of people GitHub's PR UI shows
under "Reviewers" — everyone ever requested, whether or not they've reviewed
yet. `github_login` counts as added if EITHER: they appear in the PR's
`reviewRequests` (currently requested, hasn't reviewed yet), OR they appear
as an `author` in the PR's `reviews` array (already submitted a review,
any state — approved, changes requested, or just commented). Checking only
`reviewRequests` misses everyone who already reviewed, since GitHub drops a
person from `reviewRequests` once their review is submitted. If either is
true, render that PR's two-line entry in Slack bold. Slack's mrkdwn bold does
NOT span a newline — a single `*...*` pair wrapped around both lines renders
as literal asterisks, not bold (verified empirically: bold on one line works,
bold "across\nlines" does not). Instead, wrap **each line in its own `*`
pair**:
```
• *<url as Slack link>|#<number>> <title>*
  *by @<author> · updated <relative time> · <bucket-specific marker> · <CI marker>*
```
This applies in whichever bucket the PR lands in, including **My PRs**.

Do not include repo names in the PR lines — the link is enough.

## 3. Failures

If the calendar fetch, a repo's PR list, or a specific PR's detail calls
fail, keep going with everything else that succeeded, and add one line per
failure — `⚠️ Could not fetch calendar (<short error>) — showing PR data
only.` or `⚠️ Could not fetch PRs from <repo> (<short error>) — showing
partial results.`

Never abort the whole brief, and never stop to wait on a permission prompt,
because one call failed — this runs headlessly with no one to approve
anything, so any stall here means the brief silently never gets sent.

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

**Sending**: use a dedicated Slack bot (not the `slack_send_message` MCP
tool). The MCP connector authenticates with the user's own personal OAuth
token, so every message it sends — DM or channel, self-mentioned or not —
is posted *as the user*, and Slack never push-notifies you for your own
messages. A bot token is a distinct identity, so a bot-to-user DM notifies
normally. Read the bot token from the path in `config.yaml`'s
`slack_bot_token_path` — never print, log, or echo its contents.

Run these as **two separate Bash calls** (the Bash tool doesn't persist shell
variables between calls — each is a fresh shell, so a token/channel-id saved
in one call is gone by the next). Call 1 (substitute `slack_bot_token_path`
and `slack_user_id` from `config.yaml`):

```
curl -s -X POST https://slack.com/api/conversations.open \
  -H "Authorization: Bearer $(cat <slack_bot_token_path>)" \
  -H "Content-Type: application/json" \
  -d '{"users":"<slack_user_id>"}'
```

Read the DM channel ID out of that response's `channel.id` field yourself
(it's in the tool output you just saw), then use it as a literal value in
call 2 — don't try to carry it via a shell variable:

```
curl -s -X POST https://slack.com/api/chat.postMessage \
  -H "Authorization: Bearer $(cat <slack_bot_token_path>)" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d '{"channel":"<channel id from call 1>","text":"<the composed message>"}'
```

`conversations.open` is idempotent — calling it every run just returns the
existing DM channel with the user, so there's no need to persist the channel
ID anywhere across runs either. Check each response's `"ok"` field; if
`false`, treat it as a Failures-section case (see below) rather than
silently doing nothing. Escape the message text as valid JSON (quotes,
newlines) when building the `-d` payload.

After sending, report back briefly (one line) that the Daily Brief was sent.
Don't restate the whole report back to the user in chat if this was invoked
interactively — the Slack message is the deliverable.
