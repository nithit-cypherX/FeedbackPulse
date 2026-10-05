---
name: repo-workflow-diagram
description: Map and explain repository workflows as evidence-backed plain-text diagrams in chat or Markdown. Use for runtime flows, CI/CD pipelines, approval processes, agent/tool workflows, operational runbooks, and relevant failure, retry, or rollback paths. Choose sequence, data-flow, or state views when they clarify the workflow. Do not use for static component architecture or UI mockups.
---

# Repository Workflow Diagram

Make a repository workflow understandable through the relationships that answer
the user's question. This skill produces plain-text diagrams in a `text` code
block, directly in chat or Markdown. No diagram toolchain or extra dependencies
are required.

## Establish the question and evidence

- Identify what the reader needs to understand, the starting event, scope, and
  relevant outcomes. Distinguish current behavior from a proposed workflow.
  Ask only when ambiguity would materially change the answer.
- Reuse relevant inspected evidence. Trace the requested path through entry
  points, callers, handlers, configuration, tests, and maintained documentation
  as needed; do not survey the whole repository by default.
- Read [the evidence contract](references/evidence-contract.md) when deriving
  repository behavior. Investigate conditions, responsibility boundaries, and
  failure or recovery paths when their omission would change the answer.
- Ground the main path in inspected evidence. Mark inferred links where they
  appear and explain material gaps; do not invent behavior to complete a graph.
  If a gap prevents a reliable answer, show the supported portion and the gap.

## Choose the view that explains the relationship

Use the question to choose the emphasis, not a compulsory diagram taxonomy:

- **Process:** actions, decisions, branches, and outcomes.
- **Handoff or sequence:** who sends what to whom, in what order, including
  relevant waiting, responses, or asynchronous work.
- **Data flow:** what enters, how it changes, where it is stored, and who uses it.
- **State change:** what event or condition moves something from one status to
  another, including relevant recovery and terminal states.

Do not substitute a list of tools or components for the requested flow. If more
than one view is useful, connect them through consistent names and identify
which step or relationship a detail view expands.

## Show enough mechanism to answer

- Name actions and their objects, meaningful states, or participants appropriate
  to the view. Preserve actual identifiers where needed; explain unfamiliar
  terms in the user's language.
- Make the meaning of each connection clear. For example,
  `Worker --stores result--> Database` says more than two component names joined
  by an unexplained arrow. Label transfers and conditions when they are not
  already clear from the endpoints; do not repeat obvious step order.
- Make the main reading path easy to follow. Attach branches to the step that
  triggers them and show their relevant outcomes or rejoin points.
- Preserve important distinctions: a call is not necessarily a data dependency
  or cause; accepted work is not necessarily completed work. Do not portray
  parallel work as serial or invent a retry limit, join, or rollback.
- Include exceptions, handoffs, waits, retries, cancellation, or rollback when
  needed to understand this workflow, not as a checklist for every diagram.
- Use no fixed number of nodes. Keep necessary intermediate transformations
  and decisions; omit incidental functions, files, and steps that add no
  explanatory value. Split a crowded flow at a meaningful boundary rather
  than compressing away its meaning.

## Write and check the text diagram

Use simple arrows, branch labels, and indentation. Boxes and aligned lanes are
optional. Prefer a narrow, top-down arrangement when long or Thai labels make
horizontal alignment fragile. Preserve meaningful wording instead of shortening
it just to fit a grid. Use consistent symbols and explain unusual ones.

Before delivery, walk the main path and material branches against the evidence.
Check arrow direction and meaning, conditions, handoffs, waits, and outcomes.
Check whether the diagram answers the original question without requiring the
reader to reconstruct missing relationships from a long explanation.

Give brief framing and explain the key relationship when useful; keep important
uncertainty visible. Do not narrate every node again below the diagram. A
readable drawing is not proof of runtime behavior or reader understanding.
Report checks actually performed, not a generic claim that the flow is verified.

Answer in chat unless documentation or an artifact is requested. Read
[the output contract](references/output-contract.md) when saving, updating, or
delivering an artifact. Do not modify production code, publish the diagram, or
expose secrets, personal data, or unnecessary sensitive details.

<!-- Design basis, not required reading on every diagram:
IHMC (https://cmap.ihmc.us/docs/theory-of-concept-maps) supports focus questions
and meaningful linking phrases; concept maps are not process flowcharts.
ASQ (https://asq.org/quality-resources/flowchart) supports scoped process mapping
and walking the process to check accuracy. The text-first adaptation is a local
design choice, not evidence of a measured productivity or comprehension gain.
-->
