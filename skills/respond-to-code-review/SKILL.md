---
name: respond-to-code-review
description: Respond to pull request code review comments by investigating, validating, planning, and implementing fixes. Use when user wants to address review comments, respond to a PR review, resolve reviewer feedback, or mentions "code review", "review comments", or "PR feedback".
---

# Respond to Code Review

## Quick Start

Run this skill after receiving review comments on a pull request. It will triage all unresolved comments, validate each one, build a plan, and implement fixes incrementally.

## Workflow

### 1. Find the Pull Request

- Identify the current branch: `git branch --show-current`
- Find the open PR for this branch on GitHub
- Retrieve all unresolved review comments

### 2. Triage Comments

For each unresolved comment:

- **Categorise**: bug fix / style / design / question / nit
- **Prioritise**: blocker > major > minor > nit
- **Validate**: determine if the concern is legitimate given the codebase context

If a comment is ambiguous, use the `grill-me` skill to clarify intent before proceeding.

### 3. Build a Plan

Produce a prioritised action list:

```
## Review Response Plan

### Blockers
- [ ] Comment #<id> (@<reviewer>): <summary> → <proposed fix>

### Major
- [ ] Comment #<id> (@<reviewer>): <summary> → <proposed fix>

### Minor / Nits
- [ ] Comment #<id> (@<reviewer>): <summary> → <proposed fix>

### Rejected (with reason)
- Comment #<id>: <reason for not acting>
```

Include a **reply message** for each comment — whether actioning it or declining it.

Present the plan to the user and wait for approval before implementing.

### 4. Implement

Work through the plan top-down (blockers first):

- Make code changes
- Stage and commit after each logical group: `git add -p && git commit -m "review: <summary>"`
- Do **not** push or post any replies yet

### 5. Test & Validate

Before touching GitHub, pause and prompt the user to verify the changes:

- Suggest a test command if one is detectable from the repo (e.g. `make test`, `php artisan test`, `npm test`)
- Otherwise prompt: _"Please run your tests and check the diff. Reply 'approved' when happy, or describe any issues."_
- If the user reports a problem, return to Step 4 to fix and re-commit
- Only continue to Step 6 once the user has explicitly approved

### 6. Edit Replies

Write a temporary reply file at `/tmp/review-replies.md` with the following structure — one entry per actioned or declined comment:

```markdown
# Review Replies
<!-- Edit 'reply' text freely. Set skip: true to skip posting a comment. -->

## 1. Comment #<id> (@<reviewer>)

> <original comment text quoted here>

skip: false

reply: |
  <proposed reply text here>

---

## 2. Comment #<id> (@<reviewer>)

> <original comment text quoted here>

skip: false

reply: |
  <proposed reply text here>

---
```

Then prompt: _"Reply file written to `/tmp/review-replies.md`. Edit the reply text and set `skip: true` for any comment you want to skip. Reply 'approved' when ready."_

Wait for the user to approve before continuing.

### 7. Push & Post

After both Step 5 and Step 6 are approved:

1. `git push` to publish the commits
2. Read back `/tmp/review-replies.md` and for each entry:
   - If `skip: true` — leave the comment unresolved, do not post a reply
   - Otherwise — post the (edited) reply on GitHub against the original review comment and mark it resolved
3. Delete `/tmp/review-replies.md`

### 8. Mark Resolved

Verify that all non-skipped comments are marked resolved on GitHub. Report a summary to the user:

- ✅ Actioned & replied: `<n>` comments
- ⏭️ Skipped (left unresolved): `<n>` comments

## Rules

- Never push commits until the user has passed the Test & Validate gate (Step 5)
- Never post replies until the user has approved the reply file (Step 6)
- Never mark a comment resolved without either implementing a fix or posting a clear decline reply
- Keep commits small and scoped to the comment being addressed
- Do not rewrite unrelated code while addressing review comments
- If a fix introduces risk, note it in the reply and flag to the user
- `/tmp/review-replies.md` must never be staged or committed
