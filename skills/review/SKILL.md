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
- If found with `status: in_progress` → ask: _"Found a saved review from \<date\> with N findings. Continue or start fresh?"_
- If continue: load findings and skip already-reviewed files
- If start fresh: overwrite the save file

**PR mode only — fallback incremental detection:**
- If no save file exists, check GitHub for a prior review by this agent (enables incremental mode)

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

In PR incremental mode, label each finding as **[NEW]** or **[PREVIOUSLY RAISED]**.

**Finalize save file:** set `status: completed` in the frontmatter.

### 5. Post-Review Actions

**PR mode only** — after rendering the report, ask:
1. _"Post these as inline GitHub review comments? (y/n)"_ — if yes, post findings via `pull_request_review_write`
2. _"Submit the verdict (`APPROVE` / `REQUEST CHANGES` / `COMMENT`) to GitHub? (y/n)"_ — if yes, submit the formal review

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

Markdown with YAML frontmatter:

```markdown
---
type: pr | branch
branch: feature/my-work        # branch mode
base: origin/master             # branch mode
pr_number: 42                   # PR mode
repo: org/repo                  # PR mode
started: 2026-05-13T10:30:00
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
```

### Auto-save behaviour

- **Created** at the start of step 3 (Review) with `status: in_progress`
- **Updated** after each file is reviewed: new findings appended, file added to `files_reviewed`
- **Finalized** at end of step 4: `status: completed`, full report replaces the body

### Continue behaviour

- On startup, check `./tmp/` for a matching save file with `status: in_progress`
- If found: show the user what's been reviewed so far and ask to continue or start fresh
- If continuing: load `files_reviewed` and `excluded_commits`, skip those files, resume review
- Save files with `status: completed` are ignored for continuation (but kept for reference)

---

## Rules

- Secrets findings always sorted to top of the findings table, always 🔴 Critical
- Do not review commits the user has excluded as boilerplate/generated
- Auto-save after each file reviewed — never lose progress
- **PR mode only:**
  - Never post to GitHub without explicit user confirmation
  - If CI checks are failing, verdict is forced to `REQUEST CHANGES` (GitHub Actions only — see [REFERENCE.md](REFERENCE.md))
  - In incremental mode, do not re-raise findings already marked resolved
- **Branch mode only:**
  - Use only local `git` commands — no GitHub API calls
  - Run `git fetch` before resolving remote branches
  - No posting to GitHub — report is chat-only

