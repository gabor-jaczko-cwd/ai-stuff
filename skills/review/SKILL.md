---
name: review
description: Review GitHub pull requests or local git branches with structured findings, severity ratings, auto-saved progress, and optional GitHub posting. Use when user says "review PR", "review branch", pastes a GitHub PR URL, or asks for a code review.
---

# Review

## Quick Start

The skill auto-detects **PR mode** or **Branch mode** from the input:

**PR mode:**
- `review PR #42`
- `review https://github.com/org/repo/pull/42`
- `review PR #42 focus: security`

**Branch mode:**
- `review branch` — current branch vs `origin/master`
- `review branch feature/my-work` — named branch vs `origin/master`
- `review branch feature/my-work against main` — explicit base
- `review branch focus: security`

## Workflow

### 1. Gather Context

**PR mode:**
- Parse `owner`, `repo`, `pull_number` from the PR reference
- Fetch PR metadata: title, description, base branch, author, CI status
- Check for `CLAUDE.md` at the repo root — load it as project conventions context

**Branch mode:**
- Resolve the **branch**: if provided use it, otherwise `git rev-parse --abbrev-ref HEAD`
- Resolve the **base**: if `against <base>` provided use it, otherwise `origin/master`
- Run `git fetch` to ensure remote refs are up to date
- Extract metadata: author(s), commit count (see [REFERENCE.md](REFERENCE.md) for git commands)
- Check for `CLAUDE.md` at the repo root — load it as project conventions context

**Both modes — check for saved review:**
- Look for an existing save file in `./tmp/` (see _Save/Continue_ below)
- If found with `status: in_progress` → ask: _"Found an in-progress review from \<date\> with N findings. Continue or start fresh?"_
  - If continue: load findings and skip already-reviewed files
  - If start fresh: discard the in-progress content, reset frontmatter, and start fresh (any previously archived completed reviews in the file are preserved)
- If found with `status: completed` → proceed with the new review; the previous completed review will be archived in the file when finalized (see _Save/Continue_ below)

**PR mode only — fallback incremental detection:**
- If no save file exists, check GitHub for a prior review by this agent (enables incremental mode)
- In incremental mode: fetch all inline review comments from the previous review and record their `comment_id` → finding mapping (file + line + excerpt), so resolved findings can be replied to in step 5

### 2. Assess Scope

- Fetch/list the commits:
  - **PR mode:** fetch commit list via GitHub API
  - **Branch mode:** `git --no-pager log <base>..<branch> --oneline`
- Group commits by type: feature, fix, refactor, boilerplate/generated/reformatted (see [REFERENCE.md](REFERENCE.md))
- Get the diff:
  - **PR mode:** fetch via GitHub API
  - **Branch mode:** `git --no-pager diff <base>...<branch>`
- If diff exceeds ~500 changed lines, present the commit groups and ask the user if any should be excluded before proceeding
- In **incremental mode** (PR mode, prior GitHub review): only load commits pushed *after* the last review

### 3. Review

Work through the diff applying the core checklist (see [REFERENCE.md](REFERENCE.md)):
- Correctness & logic
- Security (including secrets scan — sort any 🔴 secrets findings to top of table)
- Test coverage
- Project conventions (from `CLAUDE.md` if present)
- Naming & readability
- Missing migrations, N+1 queries, performance

Apply an optional `focus:` hint to go deeper on a specific area.

**In incremental mode — check for resolved findings:** For each previously raised finding, inspect the new diff to determine whether the concern has been addressed (the code at that location was changed to fix the issue, or the flagged pattern no longer exists). Label resolved findings `[RESOLVED]` and record their previous `comment_id` if available.

**Auto-save:** after reviewing each file, update the save file with new findings and mark the file as reviewed (see _Save/Continue_ below).

### 4. Produce Report

**PR mode** — render both parts from [REFERENCE.md](REFERENCE.md):
1. **Part 1 — Findings**: PR header, summary, findings table
2. **Part 2 — Final Review Comment**: verdict + rationale, "What's good", "Suggestions" — the body to post to GitHub

**Branch mode** — render the single report from [REFERENCE.md](REFERENCE.md):
1. Header, summary, findings table
2. Verdict + rationale
3. Suggestions / Further Considerations

**Determine verdict:**

| Condition | PR mode | Branch mode |
|-----------|---------|-------------|
| No blockers | ✅ APPROVE | ✅ READY TO MERGE |
| 🔴 Critical findings (or CI failing in PR mode, or secrets detected) | 🔄 REQUEST CHANGES | 🔄 NEEDS WORK |
| Observations only, no hard blockers | 💬 COMMENT ONLY | 💬 LOOKS OK |

In PR incremental mode, label each finding as **[NEW]**, **[PREVIOUSLY RAISED]**, or **[RESOLVED]**. Render `[RESOLVED]` findings in a separate **"✅ Resolved since last review"** section below the main findings table — do not include them as active findings or let them affect the verdict.

**Finalize save file:** set `status: completed` in the frontmatter and prepend the completed report to the file (see _Save/Continue — Finalization_ below).

### 5. Post-Review Actions

**PR mode only** — after rendering the report, enter a loop:

1. Ask: _"Post to GitHub, or make changes first?"_
   - **Make changes:** the user may edit the save file directly, or ask for changes in chat (apply them to both the chat display and the save file). Then repeat from step 1.
   - **Post to GitHub:** proceed below.

2. Re-read the save file as the authoritative source for findings and the final comment.

3. Extract the verdict (APPROVE / REQUEST_CHANGES / COMMENT) from Part 2 of the save file.

4. **If verdict is APPROVE:**
   - Build the final comment body:
     - If there are any findings, prepend a **"Findings"** section listing all of them (same table format as the findings table)
     - Follow with the full Part 2 content (verdict + rationale, "What's good", "Suggestions")
   - Submit the review directly with the final comment body and verdict (no inline comments).
   - Show a completion summary: number of findings in the final comment.

5. **If verdict is REQUEST_CHANGES or COMMENT:**
   - Partition findings into:
     - **Inline findings** — have both a file path and a line number → will be posted as inline review comments
     - **Remaining findings** — all others → will appear in the final comment
   - Build the final comment body:
     - If there are remaining findings, prepend a **"Remaining Findings"** section listing them (same table format as the findings table)
     - Follow with the full Part 2 content (verdict + rationale, "What's good", "Suggestions")
   - Post the review:
     - **If there are inline findings:** create a pending review via `pull_request_review_write`, post each inline finding as a comment on that pending review via `add_comment_to_pending_review` (if any fail, continue with the rest), then submit the pending review with the final comment body and verdict.
     - **If there are no inline findings:** submit the review directly with the final comment body and verdict.
   - **Incremental mode — resolve addressed threads:** after submitting the review, for each `[RESOLVED]` finding that has a recorded `comment_id` from the previous review, post a reply via `add_reply_to_pull_request_comment` with the body `"✅ Addressed."`. If any replies fail, continue with the rest.
   - Show a completion summary: number of inline comments posted, number of remaining findings in the final comment, number of resolved threads replied to. If any inline comments or resolution replies failed, list them.

**Branch mode** — no post-review actions. Report is chat-only.

---

## Save/Continue

### Save file location

Save files are written to `./tmp/` in the project root (already gitignored).

| Mode | Filename | Example |
|------|----------|---------|
| PR | `review-pr-<number>.md` | `./tmp/review-pr-42.md` |
| Branch | `review-branch-<name>.md` | `./tmp/review-branch-feature--my-work.md` |

Branch names: replace `/` with `--` in the filename. The real branch name is stored in frontmatter.

### Save file format

A single YAML frontmatter block is at the very top of the file, always reflecting the **latest** review. Below it, the current review body is written. Any previously completed reviews are archived below a `---` separator, each preceded by an HTML comment timestamp.

```markdown
---
type: pr | branch
branch: feature/my-work        # branch mode
base: origin/master             # branch mode
pr_number: 42                   # PR mode
repo: org/repo                  # PR mode
started: 2026-05-14T09:00:00
status: in_progress | completed
files_reviewed:
  - app/Models/User.php
  - app/Services/FooService.php
excluded_commits:
  - abc1234
---
## Review: `feature/my-work` → `origin/master`
> **Author(s):** Jacek | **Commits:** 12

### 🔍 Findings (in progress)

| # | Severity | File | Line | Issue |
|---|----------|------|------|-------|
| 1 | 🟡 Warning | `app/Models/User.php` | 42 | Missing eager load... |

---

<!-- reviewed: 2026-05-13T10:30:00 -->
## Review: `feature/my-work` → `origin/master`
> **Author(s):** Jacek | **Commits:** 8

### 🔍 Findings

...previous completed review content...
```

### Auto-save behaviour

- **Created** at the start of step 3 (Review) with `status: in_progress`
- **Updated** after each file is reviewed: new findings appended, file added to `files_reviewed`
- **Finalized** at end of step 4 (see _Finalization_ below)

### Finalization

When finalizing a review at the end of step 4:

1. Set `status: completed` in the frontmatter and update `started` to reflect the current review's timestamp
2. Check whether the file contains a previously completed review (a `---` separator followed by a `<!-- reviewed: ... -->` block, **or** a completed review body from a prior run)
3. If a previous completed review exists in the file: prepend the new completed report above a `---` separator, then add `<!-- reviewed: <previous started timestamp> -->` before the old content
4. If no previous completed review exists: write the completed report as the file body (standard finalization)

The result is always: **frontmatter → latest completed review → `---` → `<!-- reviewed: ... -->` → older reviews (newest-first)**

### Continue behaviour

- On startup, check `./tmp/` for a matching save file
- If found with `status: in_progress`: show the user what's been reviewed so far and ask to continue or start fresh
  - If continuing: load `files_reviewed` and `excluded_commits`, skip those files, resume review
  - If start fresh: discard the in-progress frontmatter and review body; preserve any archived completed reviews already in the file; begin a new review
- If found with `status: completed`: proceed with a new review; the previous completed review will be archived on finalization

---

## Rules

- Secrets findings always sorted to top of the findings table, always 🔴 Critical
- Do not review commits the user has excluded as boilerplate/generated
- Auto-save after each file reviewed — never lose progress
- **PR mode only:**
  - Never post to GitHub without the user explicitly choosing "Post to GitHub" in step 5
  - If CI checks are failing, verdict is forced to `REQUEST CHANGES` (GitHub Actions only — see [REFERENCE.md](REFERENCE.md))
  - In incremental mode, do not re-raise findings already marked resolved
  - In incremental mode, actively check whether previously raised findings have been fixed; label them `[RESOLVED]` and reply to their inline comment threads after posting
- **Branch mode only:**
  - Use only local `git` commands — no GitHub API calls
  - Run `git fetch` before resolving remote branches
  - No posting to GitHub — report is chat-only

