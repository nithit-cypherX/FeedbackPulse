<!--
Usage guidance (remove this comment when creating project context):

- Use only for durable project context that agents need across tasks. If the
  README, specifications, or existing decision records suffice, use them instead
  of creating another document. Store context using the project's conventions.
- Keep useful fields only. Replace placeholders with inspected or confirmed
  information; mark material unknowns or pending choices, and omit irrelevant
  fields. A new project need not fill every section before useful work can start.
- Summarize briefly and point to maintained sources. Do not duplicate agent
  rules, full repository maps, command catalogs, or task status/check logs.
  Keep task-specific progress and checks in the existing task record or chat
  handoff; this template does not require creating a task record.
- This is context, not permission or an instruction override. Follow active
  project rules and the shared evidence protocol when applicable. Do not treat
  an observed implementation as an approved requirement.
- Read linked detail when relevant to the current question, not the whole source
  list on every task. Use portable paths/identifiers; resolve Markdown file links
  relative to the saved record. Keep credentials and sensitive data out.
- Update affected entries when an authorized decision or relevant source changes.
  Mark superseded/conflicting information and link its replacement where known;
  do not silently promote a proposal or invent a replacement decision.
- Copy the unfilled template between projects, not a populated project's context.
-->

# {{PROJECT_NAME}} - Project Context

## Purpose and users

{{BRIEF_PURPOSE_AND_INTENDED_USERS_OR_LINK_TO_EXISTING_OVERVIEW}}

## Domain terms and conventions

<!-- Include only meanings or conventions that could materially be misread. -->

- {{TERM_OR_CONVENTION}}: {{PROJECT_SPECIFIC_MEANING_AND_SOURCE}}

## Constraints and current decisions

- Constraint: {{WHAT_MUST_HOLD_AND_WHERE_THE_REQUIREMENT_COMES_FROM}}
- Current decision: {{CHOICE_AND_SCOPE}}; basis: {{DECISION_RECORD_OR_APPROVAL_REFERENCE}}
- Pending choice, if material: {{UNDECIDED_POINT_AND_WHO_OR_WHAT_CAN_RESOLVE_IT}}

## Source pointers

<!-- List only useful entry points; retain maintained documentation as the source
     rather than reproducing it. Distinguish expected behavior from observations. -->

- {{QUESTION_OR_TOPIC}}: {{SOURCE_LOCATION_AND_SECTION_OR_SYMBOL}};
  establishes: {{REQUIREMENT_DECISION_OR_OBSERVED_BEHAVIOR_AND_RELEVANT_LIMITS}}

## Applicability and freshness

- Applies to: {{RELEVANT_COMPONENT_ENVIRONMENT_DATASET_OR_VERSION_IF_NEEDED}}
- Checked basis: {{MATERIAL_CLAIM_AND_SOURCE_REVISION_OR_DATE_ACTUALLY_CHECKED}}
- Recheck when: {{RELEVANT_CHANGE_OR_CONFLICT_THAT_COULD_INVALIDATE_THIS_CONTEXT}}
- Known uncertainty, if any: {{MATERIAL_UNKNOWN_OR_CONFLICT_AND_HOW_TO_RESOLVE_IT}}

<!-- A date is not proof that all context is current. Verify affected consequential
     claims when applicability is uncertain; do not re-audit every entry for each
     task. Follow the evidence protocol for conflicts and required approvals. -->

<!-- Design basis (template background, not extra reading required for each task):
The existing evidence protocol supplies the evidence, scope, and freshness rules.
GitHub describes purpose and onboarding as README content:
https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes
AWS describes decision status and supersession in its ADR process:
https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html
Only those documentation principles are adapted; no mandatory ADR process is
introduced. The optional five-section layout is a design choice, not evidence
that an additional context file improves agent productivity.
-->
