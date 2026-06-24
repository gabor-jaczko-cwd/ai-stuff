# Review — Reference

## Output Templates

### PR Mode — Part 1 (Findings)

```markdown
## PR Review: #<number> — <title>
> **Author:** @<author> | **Base:** `<base>` | **CI:** <✅ passing / ❌ failing / ⚠️ unknown>
> *(Incremental review — commits since <date> only)* <!-- omit if full review -->

### 📋 Summary
<What the PR does in 2–3 sentences. In incremental mode, note what changed since last review.>

### 🔍 Findings

| # | Severity | File | Line | Issue |
|---|----------|------|------|-------|
| 1 | 🔴 Critical | `path/to/file.php` | 42 | Description. Secrets: rotate immediately. |
| 2 | 🟡 Warning  | `path/to/file.php` | 17 | Description. |
| 3 | 🔵 Nit      | `path/to/file.php` | 5  | Description. |

*In incremental mode, active findings are [NEW] only. Previously raised and resolved findings appear in the sections below.*

<!-- Omit if no unverified findings -->
### ⚠️ Unverified Findings
*These findings could not be fully validated (cross-file dependencies, deleted files, or runtime behaviour). Review manually.*

| # | Severity | File | Line | Issue |
|---|----------|------|------|-------|
| 1 | 🟡 Warning | `path/to/file.php` | 17 | <issue — could not be confirmed or dismissed> |

<!-- Incremental mode only — omit if no previously raised findings -->
### ⏳ Still open from last review
*These findings were raised in the previous review and have not been addressed. They do not affect this review's verdict.*

| # | Severity | File | Line | Issue |
|---|----------|------|------|-------|
| 1 | 🟡 Warning | `path/to/file.php` | 17 | <original issue — still present> |

<!-- Incremental mode only — omit if no resolved findings -->
### ✅ Resolved since last review

| # | Severity | File | Line | Issue |
|---|----------|------|------|-------|
| 1 | 🟡 Warning | `path/to/file.php` | 17 | <original issue — now fixed> |

### 🏁 Recommended Verdict: <✅ APPROVE | 🔄 REQUEST CHANGES | 💬 COMMENT ONLY>
<Rationale for the recommended verdict, referencing the findings above.>

---
```

### PR Mode — Part 2 (Final Review Comment)

This is the body posted to GitHub when the formal review is submitted. Render it in chat immediately after Part 1 so the user can review and edit before posting.

```markdown
<Summary of the PR and rationale for the verdict in 1–3 sentences.>

### ✅ What's good
- <Positive callout>
- <Positive callout>
<!-- Aim for at least 1–2 points for larger PRs; can omit for very small PRs with no clear positives -->

### 💡 Suggestions (non-blocking)
- <Optional improvement>
<!-- Omit this section entirely if there are no suggestions -->
```

### Branch Mode — Single Report

```markdown
## Branch Review: `<branch>` → `<base>`
> **Author(s):** <authors> | **Commits:** <count>

### 📋 Summary
<What the branch does in 2–3 sentences.>

### 🔍 Findings

| # | Severity | File | Line | Issue |
|---|----------|------|------|-------|
| 1 | 🔴 Critical | `path/to/file.php` | 42 | Description. Secrets: rotate immediately. |
| 2 | 🟡 Warning  | `path/to/file.php` | 17 | Description. |
| 3 | 🔵 Nit      | `path/to/file.php` | 5  | Description. |

*No findings — branch looks clean.* <!-- use if findings table is empty -->

<!-- Omit if no unverified findings -->
### ⚠️ Unverified Findings
*These findings could not be fully validated (cross-file dependencies, deleted files, or runtime behaviour). Review manually.*

| # | Severity | File | Line | Issue |
|---|----------|------|------|-------|
| 1 | 🟡 Warning | `path/to/file.php` | 17 | <issue — could not be confirmed or dismissed> |

### 🏁 Verdict: <✅ READY TO MERGE | 🔄 NEEDS WORK | 💬 LOOKS OK>
<Rationale for the verdict, referencing the findings above.>

### 💡 Suggestions / Further Considerations
- <Forward-looking idea, new feature, performance optimisation, tech choice, or architectural improvement>
<!-- Omit this section if there is genuinely nothing to add -->
```

---

## Coherence Subagent Prompt Template

Use this template when spawning the cross-group coherence subagent in Step 5. Fill in the bracketed sections from the orchestrator's context.

```
You are a code review coordinator. You have received findings from multiple review subagents, each of which reviewed a separate group of changed files. Your job is to produce the final, cross-group-validated finding set.

## Diff Files

The full diff stat is at: [PATH TO stat.diff]
Per-group diff files: [LIST group-N.diff paths with their group name]

Read any of these files freely when you need to validate or resolve a finding.

## Findings by Group

[FOR EACH GROUP, INSERT:]
### Group: [GROUP NAME — list of files]

**Confirmed:**
[confirmed findings table]

**Dismissed:**
[dismissed findings table with reasons]

**Unverified:**
[unverified findings table — include the "why unverified" reason from the subagent]

---

## Instructions

### Primary job — false-positive reduction

Review the confirmed findings across all groups. Dismiss any finding that is contradicted by another group's diff or findings:
- A change flagged in one group whose callers were already updated in another group
- A concern about missing handling that another group's files already provide
- A finding dismissed by one subagent that another group's diff confirms was correctly dismissed

Also review dismissed findings for wrongful dismissals: a finding dismissed by one subagent may be valid in light of another group's diff (e.g. the interface change one group dismissed is genuinely unhandled in another group's callers).

### Resolve unverified findings

For each unverified finding, read the other group's diff file(s) needed to validate it. Decide: **CONFIRM**, **DISMISS** (with reason), or **STILL UNVERIFIED** (the required context is not in any diff file — runtime behaviour, deleted file, external dependency). Only findings you cannot resolve with the available diffs remain unverified in the output.

### Secondary job — new cross-group findings

Identify genuine issues that span groups and were not caught by any subagent:
- Contract or type changes in one group with unupdated callers in another
- Shared config or constants changed with downstream effects not reflected elsewhere
- A pattern acceptable in isolation that reveals a systemic problem across groups

### Output

**CONFIRMED FINDINGS** (surviving + resolved-unverified confirmed + any new cross-group findings)
| # | Severity | File | Line | Issue |
|---|----------|------|------|-------|
| ... |

**DISMISSED FINDINGS** (original dismissals + newly dismissed + resolved-unverified dismissed, each with reason)
| # | File | Line | Reason for dismissal |
|---|------|------|----------------------|
| ... |

**UNVERIFIED FINDINGS** (only findings that could not be resolved with the available diffs)
| # | Severity | File | Line | Issue | Why unverified |
|---|----------|------|------|-------|----------------|
| ... |

If a section is empty, write "None."
```

---

## Subagent Prompt Template

Use this template when spawning a review+triage subagent for a logical file group. Fill in the bracketed sections from the orchestrator's context.

```
You are a code reviewer. Your job is to review a specific group of changed files, then immediately triage your own findings.

## Project Context

[INSERT FULL PROJECT CONTEXT BUNDLE HERE — CLAUDE.md, README.md, and all discovered docs/agent files verbatim]

## Your Group

You are responsible for the following files:
[LIST FILES IN THIS GROUP]

## Diffs

Your group's diff is at: [PATH TO group-N.diff]
The full diff stat is at: [PATH TO stat.diff]

Read both files before starting your review. The diff stat shows what changed outside your group so you have context on the broader scope of the PR.

[IN INCREMENTAL MODE: INSERT]
## Prior Findings for Your Group
The following findings were raised in the previous review for files in your group.
Check whether each has been addressed in the new diff.
[LIST PRIOR FINDINGS WITH comment_id, file, line, excerpt]

## Focus
[INSERT focus: hint if provided, otherwise omit this section]

---

## Instructions

### Pass 1 — Review

Review the diffs above using the core checklist below. Consider the full project context when evaluating each file. Generate candidate findings — cast a wide net, you will triage them next.

If a **Focus** hint is provided: apply extra depth and scrutiny to that area, but do not suppress findings outside it — a Critical bug found outside the focus area must still be reported.

For each candidate finding record:
- File path and line number (if applicable)
- Recommended severity (🔴 Critical / 🟡 Warning / 🔵 Nit)
- Description of the issue

In incremental mode: for each prior finding, check whether the concern has been addressed. Label addressed ones [RESOLVED].

### Pass 2 — Triage

For each candidate finding:
1. Read the **full file** (not just the diff) for the file containing the finding
2. Read any related files needed to validate the finding — you may freely read files in your group and unchanged files not assigned to any group (base classes, interfaces, shared utilities). Do **not** read files assigned to another group; that is their subagent's responsibility.
3. Decide: **CONFIRM**, **DISMISS** (with reason), or **UNVERIFIED** (validation requires a file assigned to another group, a deleted file, or runtime behaviour you cannot observe)
4. Set the **final severity** (may differ from recommended)

Be strict: dismiss findings where reading the full context shows the code is correct. Only confirm findings where there is a clear, demonstrable issue.

### Output

Return three structured sections:

**CONFIRMED FINDINGS**
| # | Severity | File | Line | Issue |
|---|----------|------|------|-------|
| ... |

**DISMISSED FINDINGS**
| # | File | Line | Reason for dismissal |
|---|------|------|----------------------|
| ... |

**UNVERIFIED FINDINGS**
| # | Severity | File | Line | Issue | Why unverified |
|---|----------|------|------|-------|----------------|
| ... |

[IN INCREMENTAL MODE ALSO RETURN:]
**RESOLVED FINDINGS**
| # | comment_id | File | Line | Original issue |
|---|------------|------|------|----------------|
| ... |

If a section is empty, write "None."

---

## Core Review Checklist

### Correctness & Logic
- [ ] Does the code do what the PR description / commit messages indicate?
- [ ] Are edge cases handled (nulls, empty collections, race conditions)?
- [ ] Are exceptions caught appropriately?

### Security
- [ ] No secrets, credentials, or tokens committed (API keys, passwords, `.env` values)
- [ ] No SQL injection vectors (raw queries without binding)
- [ ] No mass-assignment vulnerabilities
- [ ] No unauthenticated routes exposing sensitive data
- [ ] File uploads validated (type, size, storage path)

### Test Coverage
- [ ] Happy path covered
- [ ] Edge cases and validation covered
- [ ] Authorization tested (403 for unauthorised users)
- [ ] No new feature without a test

### Project Conventions
- [ ] Patterns and conventions from the injected project context (CLAUDE.md, loaded agent/skill files) are followed
- [ ] No violations of documented architectural decisions

### Database
- [ ] Migrations present for schema changes
- [ ] No N+1 queries (eager loading where needed)
- [ ] Indexes present for new frequently-queried columns

### Naming & Readability
- [ ] Method and variable names are clear and consistent
- [ ] No dead code or commented-out blocks left in
- [ ] No unnecessary complexity
- [ ] No debug statements left in (e.g. `dd()`, `console.log`, `var_dump`, `print_r`)
```

---

## Severity Levels

| Icon | Label | Meaning | Effect on Verdict |
|------|-------|---------|-------------------|
| 🔴 | Critical | Must fix before merge (bugs, security, secrets, broken tests) | Forces `REQUEST CHANGES` / `NEEDS WORK` |
| 🟡 | Warning | Should fix — requires a demonstrable negative consequence (a bug that can occur, a security gap, a measurable perf hit) | Nudges toward `REQUEST CHANGES` / `NEEDS WORK` |
| 🔵 | Nit | Optional improvement (style, naming preference, structure with no functional impact) | No effect |

---

## CI Status (PR mode only)

The skill fetches PR check runs via the GitHub API and displays their status in the PR summary header.

> ⚠️ **Note:** CI status checking requires GitHub Actions. If the project uses an **external CI provider** (e.g. Jenkins, CircleCI) that does not report status checks back to GitHub, the CI field will show `⚠️ unknown` and the skill cannot factor CI results into the verdict.

---

## Commit Group Types

| Type | Examples | Reviewable? |
|------|----------|-------------|
| Feature / Fix | New logic, bug fixes | ✅ Yes |
| Refactor | Restructured code, no behaviour change | ✅ Yes |
| Boilerplate | Scaffolded files, generated code | ⚠️ Ask user |
| Reformatted | `pint`, `prettier`, whitespace-only | ❌ Skip by default |
| Generated | Migration stubs, compiled assets | ❌ Skip by default |

---

## Git Commands Reference (Branch mode)

```bash
# Detect current branch
git rev-parse --abbrev-ref HEAD

# Fetch remote refs
git fetch

# List commits on branch vs base
git --no-pager log <base>..<branch> --oneline

# Count commits
git rev-list --count <base>..<branch>

# Get authors
git --no-pager log <base>..<branch> --format="%an" | sort -u

# Full diff
git --no-pager diff <base>...<branch>

# Stat summary
git --no-pager diff --stat <base>...<branch>
```
