<!--
Read when creating/expanding a phase implementation plan. Reuse an existing plan
first. Save outside .agents, normally docs/work/phases/P01-<short-name>.md, or use
its useful sections inline for a small phase. Follow existing project conventions.
Replace placeholders with supported information and remove this setup comment.
Use the user's language. Omit unused fields; distinguish unknowns from decisions.
Retain stable IDs, keep links relative to the saved location, and do not copy
populated plans between projects. Proposed verification is never a recorded pass.
-->

# {{PHASE_ID}} - {{PHASE_OUTCOME_TITLE}}

- Overview: {{RELATIVE_LINK_TO_PROJECT_PLAN_AND_PHASE_IF_USEFUL}}
- Status: {{PLANNED_IN_PROGRESS_BLOCKED_DONE_OR_DEFERRED}}
- Updated: {{DATE}}

## Outcome and boundaries

- Result: {{WHAT_WILL_EXIST_OR_WORK_AND_WHY_IT_MATTERS}}
- Phase acceptance: {{OBSERVABLE_REQUIRED_RESULTS_AND_EXPECTED_CHECKS}}
- Scope and authorization: {{ALLOWED_WORK_AND_AUTHORITY_BASIS_OR_PENDING}}
- Must preserve / non-goals: {{RELEVANT_CONSTRAINTS_AND_EXCLUSIONS}}
- Dependency: {{REQUIRED_PREDECESSOR_OR_EXTERNAL_INPUT_IF_ANY}}

## Tasks and verification

<!-- Repeat a block per meaningful task, not every execution step. Use a compact
     table instead when it is clearer. Remove unused fields, but keep each required
     result traceable to work and a check. Include owner only for real coordination. -->

### {{TASK_ID}} - {{TASK_OUTCOME}}

- Status: {{ACTUAL_TASK_STATUS}}
- Work: {{BOUNDED_CHANGE_OR_DELIVERABLE_AND_RELEVANT_LOCATIONS}}
- Done when: {{EXPECTED_RESULT_AND_REQUIREMENT_OR_DEFENSIBLE_REFERENCE}}
- Check: {{HOW_TO_VERIFY_THE_RESULT_USING_EXISTING_TOOLS_OR_SOURCE_COMPARISON}}
- Actual result: {{NOT_RUN_OR_OBSERVED_RESULT_WITH_EVIDENCE_AND_MATERIAL_GAPS}}
- Depends on / owner: {{ONLY_WHEN_NEEDED}}

<!-- For partial work, state the completed portion and remaining check/work. Do
     not mark done until required acceptance and verification are satisfied.
     Record checked code/data/config version and environment when they affect
     applicability. Share one check across tasks by reference when appropriate. -->

## Evidence and material decisions

<!-- Optional for routine work; required detail belongs here when a consequential
     choice needs support. Link existing records rather than creating a parallel ADR.
     Separate source findings, assumptions, decisions, and approval where relevant. -->

- {{DECISION_OR_MATERIAL_UNKNOWN}}: {{EVIDENCE_OR_SOURCE_AND_RELEVANT_LIMITS}};
  {{CHOICE_OR_PENDING_STATUS_AND_BRIEF_REASON_AUTHORITY_OR_NEXT_CHECK}}

## Handoff

- Completed portion: {{WHAT_IS_SUPPORTED_BY_ACTUAL_EVIDENCE}}
- Remaining required work / blocker: {{GAP_AND_NEEDED_INPUT_OR_NONE}}
- Next action: {{NEXT_AUTHORIZED_TASK_OR_DECISION_OR_NONE_IF_COMPLETE}}
- Recheck on resumption: {{AFFECTED_STATE_OR_CLAIM_IF_MATERIAL}}

<!-- This section becomes the closure note when acceptance is satisfied; no separate
     phase summary or task record is required. Update the overview if phase status or
     next focus changed. Planning approval and implementation completion remain
     separate; do not close a phase by silently deferring its required work. -->
