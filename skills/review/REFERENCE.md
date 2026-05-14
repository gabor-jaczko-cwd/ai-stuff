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

*Findings labelled [NEW] / [PREVIOUSLY RAISED] in incremental mode.*

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
<!-- This section can be omitted for very small PRs with no clear positives, but aim to include at least 1–2 points for larger PRs to encourage good practices. -->

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

### 🏁 Verdict: <✅ READY TO MERGE | 🔄 NEEDS WORK | 💬 LOOKS OK>
<Rationale for the verdict, referencing the findings above.>

### 💡 Suggestions / Further Considerations
- <Forward-looking idea, new feature, performance optimisation, tech choice, or architectural improvement>
- <Another idea>
<!-- Omit this section if there is genuinely nothing to add -->
```

---

## Severity Levels

| Icon | Label | Meaning | Effect on Verdict |
|------|-------|---------|-------------------|
| 🔴 | Critical | Must fix before merge (bugs, security, secrets, broken tests) | Forces `REQUEST CHANGES` / `NEEDS WORK` |
| 🟡 | Warning | Should fix (code smell, missing test, perf issue) | Nudges toward `REQUEST CHANGES` / `NEEDS WORK` |
| 🔵 | Nit | Optional improvement (style, naming preference) | No effect |

---

## Core Review Checklist

### Correctness & Logic
- [ ] Does the code do what the PR description / commit messages indicate?
- [ ] Are edge cases handled (nulls, empty collections, race conditions)?
- [ ] Are exceptions caught appropriately?

### Security
- [ ] No secrets, credentials, or tokens committed (API keys, passwords, `.env` values)
- [ ] No SQL injection vectors (raw queries without binding)
- [ ] No mass-assignment vulnerabilities (`$fillable` / `$guarded` correct)
- [ ] No unauthenticated routes exposing sensitive data
- [ ] File uploads validated (type, size, storage path)

### Test Coverage
- [ ] Happy path covered
- [ ] Edge cases and validation covered
- [ ] Authorization tested (403 for unauthorised users)
- [ ] No new feature without a test

### Project Conventions (from CLAUDE.md)
- [ ] Livewire 2 patterns used (`wire:model`, `$this->emit()`, `$listeners`)
- [ ] Bootstrap 5 only (no Bootstrap 4 classes, no inline styles)
- [ ] No jQuery, no Vue
- [ ] New views use `main-bs5.blade.php` layout
- [ ] Vite used (not `webpack.mix.js`)
- [ ] Auth0 patterns followed
- [ ] No Spire/ShipsDNA references (deprecated)

### Database
- [ ] Migrations present for schema changes
- [ ] No N+1 queries (eager loading where needed)
- [ ] PostGIS used correctly for spatial queries

### Naming & Readability
- [ ] Method and variable names are clear and consistent
- [ ] No dead code or commented-out blocks left in
- [ ] No unnecessary complexity

---

## CI Status (PR mode only)

The skill fetches PR check runs via the GitHub API and displays their status in the PR summary header.

> ⚠️ **Note:** CI status checking requires GitHub Actions. If the project uses an **external CI provider** (e.g. Jenkins, CircleCI) that does not report status checks back to GitHub, the CI field will show `⚠️ unknown` and the skill cannot factor CI results into the verdict. This will be resolved once the project migrates its CI pipeline to GitHub Actions.

---

## Commit Group Types

When grouping commits by type, use these categories:

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

