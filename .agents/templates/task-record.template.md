<!--
Usage guidance (remove this comment when creating a task record):

- Use only when handoff, continuity, or auditability needs a durable record.
  For a small, self-contained task, a concise chat handoff can suffice.
- Reuse an existing issue, task document, or decision record when it already
  serves this purpose; do not create a parallel tracking system.
- Follow active project instructions. This template supports the shared protocol
  at .agents/protocols/evidence-and-verification.md (relative to the project root);
  it does not activate that protocol or grant authority to perform work.
- Keep only useful fields. Replace placeholders with known facts; mark material
  unknowns or pending decisions explicitly rather than inventing details.
  Remove irrelevant fields or sections instead of filling them with boilerplate.
- Link to relevant code, source passages, results, and existing records. Use
  repository-relative locations or stable identifiers; do not paste full logs,
  sensitive data, or the protocol itself. Use a table only when multiple mappings
  are clearer that way.
- Update at meaningful decisions or handoffs, not after every tool call. On
  resumption, check whether the recorded scope, inputs, and results still apply.
  A record of an earlier pass is not proof for a changed artifact.
- Copy this unfilled template between projects, not another project's task data.
-->

# {{TASK_TITLE}}

Updated: {{DATE}}

## Outcome and boundaries

- Goal: {{REQUESTED_OUTCOME}}
- Acceptance criteria: {{OBSERVABLE_RESULTS_THAT_DEFINE_SUCCESS}}
- Scope and authorization: {{PERMITTED_WORK_AND_EXPLICIT_EXCLUSIONS}}
- Must preserve: {{IMPORTANT_CONSTRAINTS_OR_EXISTING_DECISIONS}}

## Evidence and decisions

- Evidence: {{KEY_OBSERVATION_OR_SOURCE_FINDING_WITH_LOCATION_AND_RELEVANT_LIMITS}}
- Agent inference / assumption: {{MATERIAL_INTERPRETATION_OR_ADAPTATION_AND_HOW_TO_CHECK_IT}}
- Decision: {{CHOICE_AND_BRIEF_REASON; APPROVAL_OR_DELEGATED_AUTHORITY_REFERENCE; OTHERWISE_PENDING}}

## Work and verification

<!-- Repeat the following block only for distinct requirements that need tracking.
     Expected results must come from a requirement or defensible reference,
     not merely from what the current implementation returns. -->

- Requirement: {{ACCEPTANCE_CRITERION_AND_EXPECTED_BEHAVIOR}}
  - Work: {{PROPOSED_OR_ACTUAL_CHANGE_OR_DELIVERABLE_AND_LOCATION}}
  - Verification: {{CHECK_OR_SOURCE_COMPARISON; ACTUAL_RESULT_AND_EVIDENCE; OR_NOT_RUN_AND_WHY}}
  - Coverage / gaps: {{WHAT_THIS_CHECK_ESTABLISHES_AND_WHAT_REMAINS_UNVERIFIED}}

Checked state, when relevant: {{CODE_DATA_OR_CONFIG_VERSION_AND_EXECUTION_CONDITIONS}}

## Handoff

- Current state: {{COMPLETED_PORTION_AND_REMAINING_REQUIRED_WORK}}
- Open issues / decisions: {{MATERIAL_GAP_RISK_OR_PENDING_CHOICE_AND_REQUIRED_INPUT}}
- Next action: {{NEXT_IN_SCOPE_STEP_OR_NONE_IF_COMPLETE}}

<!-- Approval, implementation, and successful verification are different facts.
     Do not mark the whole task complete while required work or checks remain.
     Keep optional follow-ups separate from required work. -->
