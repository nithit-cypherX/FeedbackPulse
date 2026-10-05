---
name: explain-work
description: Explain the purpose, behavior changes, decisions, trade-offs, and verification behind work an agent performed or proposed. Use for requests to explain a fix, implementation, configuration change, document edit, analysis, diff, or deliverable. Ground explanations in the actual task and available artifacts; general lessons about a concept are a separate task.
---

# Explain Work

Help the user understand a specific piece of work and assess what it accomplishes,
why it fits their goal, and what the evidence establishes. This skill works
independently of other skills or tools.

For Thai explanations, read the reference that fits the requested depth:

- A focused answer or follow-up: [Thai writing examples](references/thai-examples.md).
- A connected multi-section explanation, article, or substantial rewrite:
  [Whole-explanation example](references/thai-connected-explanation.md).

Reuse a reference already read and unchanged in the current context. These show
wording and connections, not project facts, mandatory headings, or target length.
Do not expand a short question to fit the longer example.

## Establish the work and evidence

- Identify the user's question, the work it concerns, and relevant constraints.
  Distinguish proposed, partially completed, and completed work from what has
  actually been verified.
- Reuse task context, inspected artifacts, and recorded results while they remain
  relevant. Inspect missing or stale evidence at the scope needed to answer.
  For code, this can include the diff, affected behavior and callers, and tests;
  for configuration, values and consumers; for documents, the brief, source
  material, and revisions. Do not force a software-testing model onto other work.
- Attribute changes correctly, preserving the distinction between agent work
  and unrelated user changes.
- Explanation permits relevant inspection, not additional edits, deployment,
  publication, or other external actions. Report a discovered defect; fix it
  only when the ongoing task already authorizes that work.

## Answer the question, not every possible reporting category

Lead with the requested answer and enough context to identify the work. Say
whether it is proposed or done when that could be unclear, and connect it to the
user's goal. Do not recap the entire project to explain one change.

- Connect the relevant problem, change, and resulting behavior so the reader
  does not have to infer why separate details belong together. Group by purpose,
  not by file, tool call, or the order in which the agent worked. For a longer
  explanation, follow the work or decision through its consequences; introduce
  fields, tools, and terms when they help the reader follow that same thread.
  Do not substitute a sequence of definitions for an explanation of the work.
- For bug fixes, connect the symptom, triggering condition, cause, and fix.
  Distinguish a reproduced cause from a plausible diagnosis.
- Use a concrete before-and-after example when it clarifies the change.
  Do not invent a missing baseline or turn an example into an unrelated lesson.
- Explain reasons through actual requirements and constraints, such as
  compatibility, existing conventions, transaction boundaries, or scope.
  Include alternatives and trade-offs only when they help assess this work.
- Give the evidence and remaining limitations needed to evaluate the answer.
  A routine explanation is not an exhaustive audit or activity log.

These are content-selection rules, not required headings. If the user asks about
one decision or detail, answer that point instead of producing a full handoff.

## Keep reasons, results, and time honest

- Use recorded reasons when available. Otherwise, explain observable effects
  and label inferred rationale; do not invent historical intent, an internal
  thought process, or alternatives the author supposedly rejected.
- Distinguish measured improvement, expected improvement, and untested claims.
  Keep focused source or artifact pointers near consequential claims instead
  of appending a file inventory.
- Report only checks actually run, their results, and what they establish.
  Distinguish existing tests from new regression tests; claim a regression
  failed before the fix only if that failure was observed.
- A passing build or unit test does not prove all runtime, integration,
  concurrency, deployment, or usability properties. State missing or stale
  verification when material, and separate proposed checks from completed ones.
  For non-code work, use relevant checks such as source accuracy, requirement
  coverage, consistency, calculations, or visual inspection.
- When historical status could be mistaken for current status, state its date
  or task/version scope. Preserve what was true then; point to a verified later
  update if available, or say current status is unknown. Do not rewrite history
  to imply that later work was already complete at the earlier time.

## Make the explanation easy to follow

Use the user's language and demonstrated knowledge. Describe concrete actions
and effects, explain unfamiliar terms in context, and use consistent names.
Teach only the principles needed to understand this work unless a broader
lesson is requested.

Keep the main answer understandable without opening every supporting detail.
Keep a limitation beside the claim it qualifies, especially when it changes how
a result should be read. Separate optional commands, audit trails, and document
revision history unless they answer the user's question. Open with the work,
not commentary about how this explanation is organized. Do not repeat the same
qualification in every section; qualify each distinct claim where needed.
A requested walkthrough can be detailed; do not impose a fixed length, set of
headings, or number of sections.

Answer in chat unless a separate artifact is requested. Use lists, tables, code,
or a diagram only when they clarify the question. Do not require diagrams,
collapsible sections, report files, or teaching exercises.

If the user is confused, re-establish which work or proposal is being discussed
and repair the unclear connection instead of introducing unrelated examples
or adding a generic lesson.

Before sending, remove tangents, duplicate explanations, and a recap that only
repeats the answer. Replace vague improvement claims with supported changes in
behavior, or remove them; do not invent outcomes or measurements. Check that
connectors express an actual relationship between ideas. Natural language does
not require jokes, exaggerated praise, or invented personal experience.
Check that the wording does not claim more than the evidence supports, then
stop once the requested question has been answered.
