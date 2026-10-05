<!--
Use only when creating an overview that does not already exist. Follow the host's
instructions and the plan-and-track-work skill. Save outside .agents, normally
as docs/work/PROJECT_PLAN.md; existing project conventions take precedence.
Replace placeholders with supported information and remove this setup comment.
Use the user's language. Omit unused fields/sections; mark material unknowns.
Do not copy another project's populated plan or create future phase files early.
Resolve links relative to the saved file. Dates are update metadata, not proof.
-->

# {{PROJECT_NAME}} - Work Plan

Updated: {{DATE}}

## Goal and scope basis

- Intended outcome: {{WHAT_THE_USER_SHOULD_BE_ABLE_TO_DO_OR_UNDERSTAND}}
- Requirement/context source: {{LINK_TO_EXISTING_BRIEF_SPEC_OR_DECISION}}
- Project acceptance: {{OBSERVABLE_OVERALL_SUCCESS_CRITERIA}}
- Scope and authority: {{CURRENTLY_AUTHORIZED_WORK_AND_MATERIAL_PENDING_APPROVAL}}
- Out of scope: {{RELEVANT_EXCLUSIONS}}

<!-- This file owns phase-level planning, not the product specification or detailed
     task evidence. Future work can be proposed without being authorized. -->

## Phases

<!-- Repeat rows for real outcomes; do not invent a fixed phase count. Preserve
     existing IDs. For future phases without a plan, say "not expanded yet" instead
     of linking to a nonexistent file. An inline plan can link to its heading. -->

| ID | Outcome and phase acceptance | Depends on | Status | Implementation plan |
| --- | --- | --- | --- | --- |
| {{PHASE_ID}} | {{BOUNDED_RESULT_AND_HOW_IT_IS_ACCEPTED}} | {{DEPENDENCY_OR_NONE}} | {{ACTUAL_STATUS}} | {{PLAN_LINK_INLINE_ANCHOR_OR_NOT_EXPANDED_YET}} |

<!-- Status: use existing project meanings, or planned / in_progress / blocked /
     done / deferred. Phase status summarizes the phase plan's acceptance evidence;
     it is not a duplicate task checklist. An approved plan is not completed work. -->

## Current focus and next action

- Current phase(s): {{ID_AND_LINK_OR_NONE}}
- Next action: {{NEXT_IN_SCOPE_ACTION_OR_PENDING_DECISION}}
- Blocker or material uncertainty: {{CONDITION_AND_HOW_TO_RESOLVE_IT_IF_ANY}}

<!-- For a small phase, insert the useful outcome, task/verification, and handoff
     portions of phase-plan.template.md below and link its stable heading above.
     For a separate phase plan, keep task details and handoff there, not here. -->

## Material plan changes

<!-- Optional: only scope, ordering, or decision changes needed for continuity.
     This is not a per-session task log. Preserve supersession and open requirements. -->

- {{DATE_OR_DECISION_REF}}: {{WHAT_CHANGED_WHY_AND_WHICH_PHASES_ARE_AFFECTED}}
