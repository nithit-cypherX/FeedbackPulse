---
name: plan-and-track-work
description: Plan project phases, break active phases into appropriately sized tasks, and maintain shared progress and handoffs. Use for roadmaps, phased implementation plans, task decomposition, or continuing tracked work. Status-only requests remain read-only; routine standalone answers do not need planning documents.
---

# Plan and Track Work

Keep one shared project overview and enough phase-level detail for the user and
the next agent to understand what is intended, what is proven, and what comes next.
This is a planning and continuity workflow, not an autonomous execution scheduler.

## Establish the task and existing authority

- Distinguish proposing a plan, creating/updating plan files, implementing work,
  and reporting status. A proposal or status request does not authorize file edits;
  writing or approving a plan does not by itself authorize its implementation.
- Read the existing overview/roadmap and relevant phase plan first. Use the user's
  brief, maintained product documentation, and applicable decisions as the scope
  basis. Link them; do not create another product specification by copying them.
- Reuse existing filenames, IDs, issues, and records when they serve these roles.
  Do not create a second tracker or reconstruct missing history as fact. If several
  active plans conflict, establish the authoritative one before relying on it.
- Ask only about gaps that materially change scope, acceptance, or authority.
  Mark unresolved decisions explicitly; do not invent approval or implementation detail.

## Use two levels, with detail proportional to the work

- **Project overview:** owns the goal, phase outcomes/order, dependencies that
  matter, and links to implementation plans. Show phase-level status and current
  focus here so one file explains overall progress.
- **Phase implementation plan:** owns task state, acceptance evidence, relevant
  decisions, and the handoff for that phase. The overview's phase status is a
  summary of this evidence, not a competing record of task-level facts.
- **Small work:** add a task to the relevant existing phase. A small phase may
  keep its implementation plan inline in the overview, linked by a stable heading.
  A routine standalone request does not need new planning documents unless tracking
  was requested. Answer-only work does not create a phase automatically.
- **Larger or cross-session work:** use a separate plan for the relevant phase.
  Develop upcoming phases only to the level supported by current evidence; flesh
  out tasks as the phase approaches. Do not generate empty files for every future phase.
- **High consequence or uncertainty:** add the evidence, decision, failure-case,
  verification, or recovery detail needed at that boundary. Do not impose the same
  detail on every task or require a fixed number of phases or subtasks.

When creating a new overview, read [the project template](assets/project-plan.template.md).
When creating a phase plan or expanding an inline one, read
[the phase template](assets/phase-plan.template.md). Adapt and omit unused fields;
these are output templates, not documents to load on every status check.
Default new locations are `docs/work/PROJECT_PLAN.md` and
`docs/work/phases/P01-<short-name>.md`; follow existing project conventions instead
when available. Save populated plans outside `.agents`, resolve links relative to
their saved files, and copy only unfilled templates between projects.

## Decompose into outcomes, tasks, and steps

- A **phase** delivers a bounded, observable outcome. State its acceptance and
  non-goals without changing the governing requirements. A **task** contributes
  to that outcome and has a checkable result. Ordinary execution **steps** stay
  inside the task; opening a file or running a command need not become another task.
- Give tracked phases/tasks stable IDs, such as `P02` and `P02-T01`, or preserve
  the project's existing scheme. Keep IDs when reordering or renaming work.
- Cover required outcomes with tasks or explicitly unresolved future work. Show
  dependencies only when they affect execution order; don't manufacture parallelism.
- Include verification in the work that needs it; a separate final testing phase
  is not a substitute. Research may be a task or a phase when its uncertainty
  warrants it, not a compulsory stage for every change.
- Tie consequential choices to requirements, source evidence, and expected checks.
  Use the project's evidence guidance; in this bundle the
  [shared protocol](../../protocols/evidence-and-verification.md) governs requested
  research, material uncertainty, and non-trivial verification. Do not copy it into plans.
- Specify only implementation details supported by inspection or a recorded decision.
  Discover commands from the project; proposed checks are not executed results.

## Maintain truthful progress

Use the project's status vocabulary if it is clear. Otherwise use `planned`,
`in_progress`, `blocked`, `done`, and `deferred` when needed. A blocker names the
missing input/condition and the next way to resolve it. Approval is a separate
scope/decision note, not a completion status. Avoid invented progress percentages.

- Mark a task done only when its required outcome and applicable verification are
  satisfied. Work written but awaiting a required check stays incomplete; identify
  the implemented portion and gap. Mark a phase done only when its required tasks
  and phase-level acceptance are satisfied, including any required human acceptance.
- Plan-writing completion must be distinguished from implementation completion.
  A proposal can be delivered while all proposed implementation tasks remain planned.
- Do not remove requirements, weaken checks, or move required work to deferred just
  to close a phase. Record the basis of any authorized scope change or supersession;
  preserve the unresolved work and historical evidence rather than erasing it.
- Update the phase plan at meaningful progress, decisions, blockers, and handoffs,
  not after every tool call. Update the overview when phase status, scope, dependency,
  or next focus changes. Reconcile affected summaries in the same handoff when
  authorized; report a conflict instead of silently choosing the more favorable state.
- Keep concise result evidence and the checked revision/environment when relevant.
  Link maintained artifacts rather than pasting full logs. Do not create an additional
  status file, task log, task record, or phase summary when the phase plan suffices.
  Retain closed plans for history, but do not read them all on each task.

## Resume, coordinate, and stop

Read the overview and relevant phase plan, then inspect affected artifacts enough
to establish that recorded scope, decisions, and verification still apply. An old
pass does not verify changed work. Recheck affected claims, not the entire history.
For a read-only status request, explain stale/conflicting records without editing them.

Proceed with the next authorized, unblocked task; do not ask again for routine steps
already approved. Pause the affected work for an unapproved material deviation or
a required decision. Honor any explicit phase boundary; a future roadmap entry is
not permission to start it. This skill grants no commit, deployment, external write,
or delegation authority.

If multiple agents are already authorized to work concurrently, use clear task
ownership and an agreed overview updater. Re-read affected records before updating
and preserve others' changes; plain Markdown is not a locking or scheduling system.

At handoff, state the outcome, evidence and gaps, remaining required work, and next
in-scope action. A status answer alone does not change recorded status. Stop when
the requested outcome is met; do not add speculative follow-up phases.

<!-- Design basis, not extra per-task reading:
Adapted from the user's approved two-level tracking requirements and existing
evidence protocol. OpenAI's ExecPlan example supports living plans, observable
milestones, and progress tracking for complex work, not mandatory heavy plans:
https://developers.openai.com/cookbook/articles/codex_exec_plans
Anthropic's long-running web-agent experiments support incremental progress and
verified handoffs, not universal claims about this layout or other domains:
https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
The templates, statuses, and update cadence here are design choices requiring
local evaluation, not proven productivity gains or automatic cross-agent loading.
-->
