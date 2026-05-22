---
name: review
description: Review GitHub pull requests or local git branches with structured findings, severity ratings, parallel subagent review+triage, and optional GitHub posting. Use when user says "review PR", "review branch", pastes a GitHub PR URL, or asks for a code review.
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

**Project context discovery (both modes):**
- Load `CLAUDE.md` and `README.md` from the repo root if present
- Parse both files for references to:
  - Tech stack documentation or design docs
  - Area-specific reviewer agents (`.claude/agents/*.md`)
  - Project-specific skill files (`.claude/skills/*/SKILL.md`)
  - Any other linked conventions or architecture docs
- Load all referenced files as additional context
- Build a **project context bundle** — this will be injected verbatim into every subagent prompt

**PR mode:**
- Parse `owner`, `repo`, `pull_number` from the PR reference
- Fetch PR metadata: title, description, base branch, author, CI status
- Check for prior review by this agent on GitHub (enables incremental mode — see below)

**Branch mode:**
- Resolve the **branch**: if provided use it, otherwise `git rev-parse --abbrev-ref HEAD`
- Resolve the **base**: if `against <base>` provided use it, otherwise `origin/master`
- Run `git fetch` to ensure remote refs are up to date
- Extract metadata: author(s), commit count (see [REFERENCE.md](REFERENCE.md) for git commands)

**PR mode only — incremental detection:**
- If no save file exists, check GitHub for a prior review by this agent
- In incremental mode: fetch all inline review comments from the previous review and record their `comment_id` → finding mapping (file + line + excerpt), so resolved findings can be replied to later

### 2. Assess Scope

- Fetch/list the commits:
  - **PR mode:** fetch commit list via GitHub API
  - **Branch mode:** `git --no-pager log <base>..<branch> --oneline`
- Group commits by type: feature, fix, refactor, boilerplate/generated/reformatted (see [REFERENCE.md](REFERENCE.md))
- Get the diff:
  - **PR mode:** fetch via GitHub API
  - **Branch mode:** `git --no-pager diff <base>...<branch>`
- **Group changed files into logical slices** using your judgement:
  - Group files that are closely related: a service + its callers + its tests, a controller + its form request + its policy, a model + its migration + its factory
  - Each group should be coherent enough for a subagent to detect cross-file issues within it
  - Aim for 2–8 files per group; large standalone files may warrant their own group
  - Boilerplate/generated/reformatted files that will be skipped need not be grouped
- **If diff exceeds ~500 changed lines:** present the commit groups and proposed file grouping to the user and ask if any commits or groups should be excluded before proceeding
- **In incremental mode (PR mode):** only include commits pushed after the last review

### 3. Spawn Review+Triage Subagents

For each logical group, spawn a **review+triage subagent** using the Agent tool (see **Subagent Prompt Template** in [REFERENCE.md](REFERENCE.md)).

**Inject into each subagent's prompt:**
- The full **project context bundle** (CLAUDE.md, README.md, all discovered docs and agent files)
- The **group's file list** and their diffs
- The **full diff stat** (so the subagent knows what else changed outside its group)
- The optional `focus:` hint if provided
- **In incremental mode:** prior findings for files in this group, with their `comment_id`s

**Spawn all group subagents in parallel.** Collect findings as each completes.

Each subagent will:
1. Review the changed files in its group against the core checklist and injected project context — generating candidate findings with recommended severity
2. Triage each candidate: read the full relevant file(s) to confirm or dismiss, and set final severity
3. Return three lists: **confirmed findings**, **dismissed findings** (with reason), and **unverified findings** (cross-file or unreadable — cannot be confirmed or dismissed)

**In incremental mode:** subagents also check whether previously raised findings in their group have been addressed, labelling them `[RESOLVED]` if so.

### 4. Cross-Group Coherence Pass

After all subagents complete, merge all confirmed and unverified findings. Then review the merged results alongside the full diff stat for issues that span groups:
- Type, interface, or contract changes in one group affecting callers in another
- Shared config or constants changed in one group with downstream effects in another
- Patterns that appear acceptable in isolation but indicate a systemic problem across groups

Add any cross-group findings directly to the confirmed findings list.

### 5. Produce Report

**PR mode** — render both parts from [REFERENCE.md](REFERENCE.md):
1. **Part 1 — Findings**: PR header, summary, findings table, unverified findings section (if any)
2. **Part 2 — Final Review Comment**: verdict + rationale, "What's good", "Suggestions"

**Branch mode** — render the single report from [REFERENCE.md](REFERENCE.md):
1. Header, summary, findings table, unverified findings section (if any)
2. Verdict + rationale
3. Suggestions / Further Considerations

**Determine verdict:**

| Condition | PR mode | Branch mode |
|-----------|---------|-------------|
| No blockers | ✅ APPROVE | ✅ READY TO MERGE |
| 🔴 Critical findings (or CI failing in PR mode, or secrets detected) | 🔄 REQUEST CHANGES | 🔄 NEEDS WORK |
| Observations only, no hard blockers | 💬 COMMENT ONLY | 💬 LOOKS OK |

In PR incremental mode, label each finding as **[NEW]**, **[PREVIOUSLY RAISED]**, or **[RESOLVED]**. Render `[RESOLVED]` findings in a separate **"✅ Resolved since last review"** section — do not include them as active findings or let them affect the verdict.

**Write the save file** with `status: completed` (see _Save/Continue_ below).

### 6. Post-Review Actions

**PR mode only** — after rendering the report, enter a loop:

1. Ask: _"Post to GitHub, or make changes first?"_
   - **Make changes:** the user may edit the save file directly, or ask for changes in chat (apply them to both the chat display and the save file). Then repeat from step 1.
   - **Post to GitHub:** proceed below.

2. Re-read the save file as the authoritative source for findings and the final comment.

3. Extract the verdict (APPROVE / REQUEST_CHANGES / COMMENT) from Part 2 of the save file.

4. **If verdict is APPROVE:**
   - Build the final comment body:
     - If there are any findings, prepend a **"Findings"** section listing all of them (same table format)
     - Follow with the full Part 2 content
   - Submit the review directly with the final comment body and verdict.
   - Show a completion summary: number of findings in the final comment.

5. **If verdict is REQUEST_CHANGES or COMMENT:**
   - Partition findings into **inline findings** (have file path + line number) and **remaining findings** (all others)
   - Build the final comment body:
     - If there are remaining findings, prepend a **"Remaining Findings"** section
     - Follow with the full Part 2 content
   - Post the review:
     - **If there are inline findings:** create a pending review, post each as an inline comment, then submit with the final comment body and verdict
     - **If no inline findings:** submit directly
   - **Incremental mode — resolve addressed threads:** for each `[RESOLVED]` finding with a recorded `comment_id`, post a reply `"✅ Addressed."` to that thread
   - Show a completion summary: inline comments posted, remaining findings in final comment, resolved threads replied to. List any failures.

**Branch mode** — no post-review actions. Report is chat-only.

---

## Save/Continue

### Save file location

Save files are written to `./tmp/` in the project root (already gitignored).

| Mode | Filename | Example |
|------|----------|---------|
| PR | `review-pr-<number>.md` | `./tmp/review-pr-42.md` |
| Branch | `review-branch-<name>.md` | `./tmp/review-branch-feature--my-work.md` |

Branch names: replace `/` with `--` in the filename.

### Save file format

```markdown
---
type: pr | branch
branch: feature/my-work        # branch mode
base: origin/master             # branch mode
pr_number: 42                   # PR mode
repo: org/repo                  # PR mode
started: 2026-05-14T09:00:00
status: completed
excluded_commits:
  - abc1234
---
## Review: `feature/my-work` → `origin/master`
...completed review content...

---

<!-- reviewed: 2026-05-13T10:30:00 -->
...previous completed review content...
```

### Behaviour

- The save file is **only written on completion** (no in-progress saves)
- If a completed save file already exists when a new review starts: proceed with the new review; the previous completed review will be archived on finalization
- No resume from partial runs — if a session is interrupted, start a fresh review

### Finalization

When writing the save file at the end of step 5:

1. Set `status: completed` and `started` to the current review's timestamp
2. Check whether the file contains a previously completed review
3. If yes: prepend the new completed report above a `---` separator, add `<!-- reviewed: <previous started timestamp> -->` before the old content
4. If no: write the completed report as the file body

The result is always: **frontmatter → latest completed review → `---` → `<!-- reviewed: ... -->` → older reviews (newest-first)**

---

## Rules

- Secrets findings always sorted to top of the findings table, always 🔴 Critical
- Do not review commits the user has excluded as boilerplate/generated
- **PR mode only:**
  - Never post to GitHub without the user explicitly choosing "Post to GitHub" in step 6
  - If CI checks are failing, verdict is forced to `REQUEST CHANGES` (GitHub Actions only — see [REFERENCE.md](REFERENCE.md))
  - In incremental mode, do not re-raise findings already marked resolved
  - In incremental mode, actively check whether previously raised findings have been fixed; label them `[RESOLVED]` and reply to their inline comment threads after posting
- **Branch mode only:**
  - Use only local `git` commands — no GitHub API calls
  - Run `git fetch` before resolving remote branches
  - No posting to GitHub — report is chat-only
