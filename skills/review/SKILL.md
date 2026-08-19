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

**`use-cwd` opt-in (either mode):** the skill also detects, from free-text intent (no fixed keyword — phrases like "you can use the current working environment", "use the CWD", "you're allowed to use the local environment" all count), whether the user has granted permission to operate directly in the current working directory instead of a disposable worktree. See Step 3.

## Workflow

### 1. Determine Scope

**Parse the input** to identify PR vs Branch mode and extract identifiers:
- **PR mode:** parse `owner`, `repo`, `pull_number` from the PR reference
- **Branch mode:** always a full review — skip the rest of this step

**PR mode — incremental detection (do this before fetching anything else):**
1. Check for a local save file (`./tmp/review-pr-<number>.md`) — incremental if found
2. If no save file: check GitHub for a prior review submitted by this agent on the PR — incremental if found
3. **If incremental:** fetch all inline review comments from the previous review and record their `comment_id` → finding mapping (file + line + excerpt), so resolved findings can be replied to later

### 2. Gather Context

**Project context discovery (both modes):**
- Load `CLAUDE.md` and `README.md` from the repo root if present — these are always injected verbatim into every subagent
- Parse both files for references to:
  - Tech stack documentation or design docs
  - Area-specific reviewer agents (`.claude/agents/*.md`)
  - Project-specific skill files (`.claude/skills/*/SKILL.md`)
  - Any other linked conventions or architecture docs
- Collect the paths of all referenced files — **do not load them**; subagents will read whichever ones are relevant to their group on demand

**PR mode:**
- Fetch PR metadata: title, description, base branch, author, CI status

**Branch mode:**
- Resolve the **branch**: if provided use it, otherwise `git rev-parse --abbrev-ref HEAD`
- Resolve the **base**: if `against <base>` provided use it, otherwise `origin/master`
- Run `git fetch` to ensure remote refs are up to date
- Extract metadata: author(s), commit count (see [REFERENCE.md](REFERENCE.md) for git commands)

**Ticket & acceptance-criteria discovery (both modes):**
- Extract a ticket-key-shaped token (e.g. `PROJ-123`) from the PR title, PR description, or branch name (Branch mode: the branch name and/or recent commit messages)
- If found, search available MCP tools via `ToolSearch` for a matching issue-tracker capability (Jira, Linear, GitHub Issues, etc.) and fetch the ticket
- If the ticket has children/sub-issues (an epic with child stories/bugs, a parent issue with sub-issues, etc.), fetch and check each child too, one level deep — same mechanism, no tracker-specific naming
- Compare the diff against each ticket's description/acceptance criteria and classify per ticket: **covered**, **partially covered**, or **not covered**
- If no ticket-shaped token is found, no matching tracker tool is reachable, or the fetch fails: skip this check entirely and omit it from the report — this is best-effort and must never block the review on an inability to verify

### 3. Set Up Review Environment

Determine whether subagents will operate against a disposable **read-only worktree** (default) or the **current working directory** (`use-cwd`, opt-in — detected per Quick Start above). This is a per-invocation signal only; never carry it over from a prior review.

**If `use-cwd` was requested:**
1. Run `git status`. If the working directory has *any* uncommitted changes (tracked or untracked), **abort the review immediately** with a clear error telling the user to commit or stash and re-run. Do not fall back to the worktree path silently, and do not do any other setup work first.
2. If clean:
   - **Branch mode:** fetch and `git checkout <branch>` directly in the working directory
   - **PR mode:** `git fetch origin pull/<number>/head:<local-ref>` then `git checkout <local-ref>` (same-repo branches only — this skill does not special-case fork PRs)
3. Do **not** restore the previously-checked-out branch after the review finishes — leave the working directory on the reviewed branch, since the user explicitly opted into using it live.
4. Subagents read directly from the working directory (no worktree exists in this mode). This is also the only mode where the coherence subagent may execute tests/tooling (Step 5).

**Otherwise (default):**
1. Resolve the source ref to a commit SHA (`git rev-parse <branch>`, or the PR head SHA)
2. In PR mode, fetch the PR head explicitly if not already done: `git fetch origin pull/<number>/head:<local-ref>`
3. If a worktree already exists at the target path from a stale/interrupted prior review, remove it first (`git worktree remove --force`)
4. Create a **detached** worktree at that SHA: `git worktree add --detach ./tmp/review-worktrees/<pr-number|branch-name> <sha>` — detached so it never conflicts with a branch checked out elsewhere (including the main worktree)
5. **If `git worktree add` fails for any reason, abort the review** with the underlying git error. Do not fall back to reading from the ambient working directory — that reintroduces the exact unreliable-checkout problem this step exists to fix.
6. This worktree is shared **read-only** by every subagent spawned in Steps 4–5. Base-branch file content (e.g. to inspect a deleted or renamed file) is read via `git show <base-ref>:<path>` — no second worktree is created.
7. Tear down the worktree (`git worktree remove`) once Step 6's report has been produced, including on early-exit paths (e.g. the user cancels after the large-diff prompt in Step 4).

Record which mode was used (worktree vs. live CWD) — it is surfaced in the report header in Step 6.

### 4. Assess Scope

**a) Classify commits** — determines what to review (skip decision):
- Fetch/list the commits:
  - **PR mode:** fetch commit list via GitHub API — **in incremental mode, only commits pushed after the last review**
  - **Branch mode:** `git --no-pager log <base>..<branch> --oneline`
- Classify each commit by type: feature, fix, refactor, boilerplate/generated/reformatted (see [REFERENCE.md](REFERENCE.md))
- Boilerplate/generated/reformatted commits are candidates for exclusion — confirm with the user if large

**b) Get the diff** — one fetch/call covering only the commits being reviewed:
- **PR mode:** fetch via GitHub API
- **Branch mode:** `git --no-pager diff <base>...<branch>`
- **If diff exceeds ~500 changed lines:** present the commit classification and changed file list to the user and ask if any commits should be excluded before proceeding

**c) Group changed files for subagents** — independent of commit classification; a single commit can span multiple groups, and multiple commits often touch the same files:
- Group files that are closely related by domain: a service + its callers + its tests, a controller + its form request + its policy, a model + its migration + its factory
- Each group should be coherent enough for a subagent to detect cross-file issues within it
- Aim for 2–8 files per group; large standalone files may warrant their own group
- Files from excluded commits need not be grouped

**d) Write diffs to temp files** under `./tmp/review-<pr-number|branch-name>/`:
- `stat.diff` — the full diff stat summary
- `group-1.diff`, `group-2.diff`, … — one file per logical group, containing only the diffs for that group's files
- Pass each subagent its group's file path; the orchestrator does not hold diff content in context after this point

### 5. Spawn Review+Triage Subagents

For each logical group, spawn a **review+triage subagent** using the Agent tool (see **Subagent Prompt Template** in [REFERENCE.md](REFERENCE.md)).

**Inject into each subagent's prompt:**
- **CLAUDE.md** and **README.md** verbatim (always)
- A **list of available context docs** (paths only — the subagent reads whichever are relevant)
- The **group's file list**
- The path to the group's diff file (`./tmp/review-.../group-N.diff`) and the stat file (`./tmp/review-.../stat.diff`)
- The **absolute path to the worktree root** (or a note that the working directory is being used directly, in `use-cwd` mode) — this is where full-file content lives for triage
- The resolved **base ref** (for `git show <base-ref>:<path>` lookups, e.g. deleted/renamed files)
- The optional `focus:` hint if provided
- **In incremental mode:** prior findings for files in this group, with their `comment_id`s

**Spawn all group subagents in parallel.** Collect all three lists (confirmed, dismissed, unverified) as each completes. **In incremental mode:** extract any `[PREVIOUSLY RAISED]` findings from the confirmed list and hold them separately — they will be reattached after the coherence pass and must not be sent to the coherence subagent.

Each subagent will:
1. Review the changed files in its group against the core checklist and injected project context — generating candidate findings with recommended severity
2. Triage each candidate: read the full relevant file(s) — from the worktree/working directory, including files owned by another group — to confirm or dismiss, and set final severity. Subagents may report a finding on any file they read, not only their own group's; the coherence pass (Step 6) dedupes across groups.
3. Return three lists: **confirmed findings**, **dismissed findings** (with reason), and **unverified findings** — the only remaining unverified reason is runtime behaviour that cannot be confirmed without executing code, which group subagents never do (see Step 6). When flagging a finding this way, suggest a candidate test/command that could resolve it.

**In incremental mode:** subagents also check whether previously raised findings in their group have been addressed, labelling them `[RESOLVED]` if so.

### 6. Cross-Group Coherence Pass

**If there is only one group and `use-cwd` is not active (or no group returned a runtime-behaviour unverified finding), skip this step** — use the subagent's output directly as the authoritative finding set and proceed to Step 7.

**Otherwise, spawn a coherence subagent** (see **Coherence Subagent Prompt Template** in [REFERENCE.md](REFERENCE.md)) — even with only one group, if `use-cwd` is active and that group returned runtime-behaviour unverified findings, spawn it scoped solely to attempting execution on those.

**Inject into the subagent's prompt:**
- All confirmed (`[NEW]` only), unverified, and dismissed findings from every group (labelled by group)
- The full diff stat
- The worktree/working-directory path and base ref (same as Step 5)
- Whether `use-cwd` is active

**Only if `use-cwd` is active:** the coherence subagent may run the project's existing tests or static-analysis tooling to resolve runtime-behaviour unverified findings (e.g. `./coral test <path>`, `./coral pint --dirty`) — never arbitrary or destructive commands, and never against a finding outside the diff's scope. This is the **only** point in the whole workflow where code is executed; group subagents in Step 5 never execute anything, since they run concurrently against a shared live environment and could contend with each other (test DB, ports, etc.).

The subagent returns a final confirmed list, an updated dismissed list (with cross-group reasons), and any new cross-group findings. Reattach the held `[PREVIOUSLY RAISED]` findings to the confirmed list after receiving the coherence subagent's output. Use the combined result as the authoritative finding set for the report.

### 7. Produce Report

**PR mode** — render both parts from [REFERENCE.md](REFERENCE.md):
1. **Part 1 — Findings**: PR header (including the **Verification** line — read-only worktree vs. live working directory with tests executed), summary, **Acceptance Criteria section (if a ticket was found and checked in Step 2)**, findings table, unverified findings section (if any)
2. **Part 2 — Final Review Comment**: verdict + rationale, "What's good", "Suggestions"

**Branch mode** — render the single report from [REFERENCE.md](REFERENCE.md):
1. Header (including the **Verification** line), summary, **Acceptance Criteria section (if a ticket was found and checked in Step 2)**, findings table, unverified findings section (if any)
2. Verdict + rationale
3. Suggestions / Further Considerations

**Determine verdict:**

| Condition | PR mode | Branch mode |
|-----------|---------|-------------|
| No blockers | ✅ APPROVE | ✅ READY TO MERGE |
| 🔴 Critical findings (or CI failing in PR mode, secrets detected, or a checked ticket's acceptance criteria are not fully met) | 🔄 REQUEST CHANGES | 🔄 NEEDS WORK |
| Observations only, no hard blockers | 💬 COMMENT ONLY | 💬 LOOKS OK |

In PR incremental mode, label each finding as **[NEW]**, **[PREVIOUSLY RAISED]**, or **[RESOLVED]**:
- **[NEW]** findings go in the active findings table and affect the verdict normally.
- **[PREVIOUSLY RAISED]** findings are moved to a separate **"⏳ Still open from last review"** section and do **not** affect the verdict — the previous review already set that expectation.
- **[RESOLVED]** findings go in a separate **"✅ Resolved since last review"** section and do not affect the verdict.

**Write the save file** with `status: completed` (see _Save/Continue_ below).

**Tear down the review environment now** (worktree removal, per Step 3) — nothing after this point needs file access.

### 8. Post-Review Actions

**PR mode only** — after rendering the report, enter a loop:

1. Ask: _"Post to GitHub, or make changes first?"_
   - **Make changes:** the user may edit the save file directly, or ask for changes in chat (apply them to both the chat display and the save file). Then repeat from the top of this step.
   - **Post to GitHub:** proceed below.

2. Re-read the save file to pick up any edits the user made between review and posting — findings pruned, language softened, verdict changed.

3. Extract the verdict (APPROVE / REQUEST_CHANGES / COMMENT) from Part 2 of the save file.

4. **Build the final comment body (all verdicts):**
   - If there are any findings, prepend a **"Findings"** section listing all of them (same table format)
   - Follow with the full Part 2 content

5. **Post the review:**
   - **If verdict is REQUEST_CHANGES or COMMENT and there are inline findings** (file path + line number): create a pending review, post each as an inline comment for **[NEW] findings only** — never post a new inline comment for `[PREVIOUSLY RAISED]` findings, as their thread already exists on the PR. Then submit with the final comment body and verdict.
   - **Otherwise:** submit directly with the final comment body and verdict
   - **Incremental mode — resolve addressed threads:** for each `[RESOLVED]` finding with a recorded `comment_id`, post a reply `"✅ Addressed."` to that thread
   - Show a completion summary: inline comments posted (if any), findings in final comment, resolved threads replied to. List any failures.

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

When writing the save file at the end of step 7:

1. Set `status: completed` and `started` to the current review's timestamp
2. Check whether the file contains a previously completed review
3. If yes: prepend the new completed report above a `---` separator, add `<!-- reviewed: <previous started timestamp> -->` before the old content
4. If no: write the completed report as the file body

The result is always: **frontmatter → latest completed review → `---` → `<!-- reviewed: ... -->` → older reviews (newest-first)**

---

## Rules

- Secrets findings always sorted to top of the findings table, always 🔴 Critical
- Do not review commits the user has excluded as boilerplate/generated
- **Ticket & acceptance criteria (both modes):**
  - Best-effort only — never delay or block the review because a ticket lookup failed, timed out, or no ticket-shaped token was found
  - Only children/sub-issues one level deep are checked automatically; deeper hierarchies are out of scope
  - Unmet acceptance criteria affect the verdict the same way a 🔴 Critical finding does — see the verdict table in Step 7
- **Review environment (both modes):**
  - Default to a disposable, detached, **read-only** worktree — never read from the ambient working directory unless `use-cwd` was explicitly granted
  - `use-cwd` aborts the entire review immediately if the working directory is not clean — never auto-stash, never auto-commit, never silently fall back to the worktree path
  - If `git worktree add` fails, abort with the error — never silently fall back to reading from the ambient working directory
  - Code execution (tests, static analysis) only ever happens in the coherence/execution-pass subagent, and only when `use-cwd` is active — group subagents in Step 5 never execute anything
  - The worktree never persists between reviews — tear it down once the report is produced
- **PR mode only:**
  - Never post to GitHub without the user explicitly choosing "Post to GitHub" in step 8
  - If CI checks are failing, verdict is forced to `REQUEST CHANGES` (GitHub Actions only — see [REFERENCE.md](REFERENCE.md))
  - In incremental mode, do not re-raise findings already marked resolved
  - In incremental mode, actively check whether previously raised findings have been fixed; label them `[RESOLVED]` and reply to their inline comment threads after posting
- **Branch mode only:**
  - Use only local `git` commands — no GitHub API calls
  - Run `git fetch` before resolving remote branches
  - No posting to GitHub — report is chat-only
