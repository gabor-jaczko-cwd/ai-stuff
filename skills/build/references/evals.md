# Evals

Evals are the objective sign-off for every step and phase. They are defined during planning and are the gate the loop cannot bypass. Automated types run with the project's own test command; the browser-verification type does not.

## Principle

No step is `done` until its evals pass, and no phase closes until its exit evals pass. Evals encode the spec's acceptance criteria as checks — automated where possible, visually verified where not — so "done" means demonstrably correct, not "looks right on paper".

## Eval types

- **Unit:** a function, class or rule in isolation.
- **Integration / feature:** a full workflow, request or component interaction.
- **Data-integrity assertions:** for steps that generate or transform data, assert invariants directly (counts, relationships, sums, ranges).
- **Acceptance-criteria checks:** one test per Given / When / Then in the step.
- **Performance checks (where relevant):** assert a batch completes, or an operation stays within a bound, for volume-sensitive steps.
- **Browser verification (UI steps only):** for any step that changes rendered UI, this is required in addition to the automated types above — automated evals alone are not sufficient sign-off for a UI-facing step. crewman launches the app (via the `run` skill if the project has one, otherwise whatever the project profile's guardrails specify) and visually checks the golden path plus the step's stated UI acceptance criteria before reporting. Record what was checked and what it looked like in the crewman report; inspector's Spec axis checks this account against the acceptance criteria the same way it checks any other claim.

Use the project's test framework and layout (from the project context) for the automated types.

## Defining an eval in a step

In the step's eval spec (ticket body, or step file if spec-planned), for each eval give: the type, the file it lives in (project test layout), what it asserts, and the pass threshold. For a browser-verification eval, give the golden path to exercise instead of a file/assertion. Keep it concrete enough that crewman writes or performs the check without further questions.

Example eval spec:

```
- type: unit
  file: [project test dir]/AllocationTest
  asserts: generated shares across a group sum to exactly 100; at least one item is flagged primary.
  threshold: all assertions pass.
- type: integration
  file: [project test dir]/SeedGroupTest
  asserts: a generated group exposes one primary and internally consistent shares.
  threshold: pass.
- type: browser
  golden_path: open the group page, confirm the primary badge renders on exactly one member, confirm shares sum to 100% in the UI.
  threshold: golden path renders correctly with no console errors.
```

## Running evals

- Run automated evals with the project's test command. You may filter to a subset while iterating, but the step's full eval set must pass before sign-off.
- Format changed files with the project's format command before reporting, honouring any "never run bare" caveats in the profile.
- crewman writes and runs the evals and performs the browser check. inspector may re-run the automated evals read-only as part of its Standards/Spec review. foreman gates on the result.
- crewman decides test-first vs test-after per step — no fixed rule — but test-first, following the `tdd` skill's red-green-refactor discipline, is preferred where it applies.

## Mapping from the spec

Turn each spec acceptance criterion into at least one eval, assigned to the step that delivers it. If the plan was built from a `to-tickets` breakdown, each ticket's own acceptance criteria checklist is the source instead of re-deriving from the spec. If a criterion has no eval, the plan is incomplete: add one.

## Thresholds and gates

- **Step gate:** every eval named in the step's eval spec passes, including the browser check if applicable.
- **Phase gate:** the phase exit-criteria evals pass (often a small set of cross-step integration checks).
- **Plan gate:** the full suite passes, every spec acceptance criterion has a passing eval, and the final whole-branch `/code-review` pass (see `loop-protocol.md`) is clean.

## Anti-patterns

- Do not weaken, skip or delete an eval to make a step pass. If an eval is genuinely wrong, fix it deliberately and record why in the ticket/step file.
- Do not assert on incidental implementation detail; assert on the behaviour the criterion describes.
- Do not treat automated-green as sufficient for a UI-facing step — the browser-verification eval is not optional just because the test suite passed.
