# Workflow Evidence Contract

Use this contract when deriving a workflow from repository evidence. A diagram
based only on a supplied description must be identified as such, not presented
as independently verified implementation behavior.

## Match evidence to the claim

- Inspect reachable code together with relevant configuration, feature flags,
  deployment context, and callers. A function's existence does not establish
  that the active workflow uses it.
- Tests describe behavior under their setup. Reading a test is not running it;
  a passing result covers only the conditions actually exercised.
- Maintained documentation and decisions can establish intended behavior.
  Investigate conflicts with implementation rather than silently choosing one.
- Distinguish source inspection, observed execution, and deployed behavior.
  Name the relevant version, environment, or date when it affects interpretation.
  Do not present a proposed or historical workflow as the current one.

Evidence relevance depends on the question, not a universal source ranking.
Resolve material conflicts where practical; disclose those that remain.

## Facts and gaps

- **Confirmed:** directly supported within the inspected source or observed
  execution's scope. State that basis; this is not a blanket runtime guarantee.
- **Inferred:** plausible from available evidence, but the relationship is not
  established across the relevant path.
- **Conflicting:** relevant evidence disagrees and the discrepancy is unresolved.
- **Unknown:** the available evidence does not establish the behavior.

Use these distinctions without requiring a status label on every node. Keep
the main path supported; mark uncertain links in place with clear wording such
as "(inferred)" or "(unknown)". If a missing link is essential, show the gap
rather than drawing a confirmed connection through it. An unknown route is not
a terminal outcome, and lack of evidence does not prove that a path is absent.

## Proportionate evidence notes

Put focused source pointers and material limitations below the diagram or in
the same document. Point to the relevant path and symbol, passage, configuration,
or execution result; use line numbers when practical and follow the host's link
conventions. Do not paste large excerpts or attach a repository file inventory.

Use an existing evidence record when appropriate. Create a separate record only
when requested or when traceability genuinely needs one and inline notes or
existing records are insufficient. No default `evidence.md`, table, or checklist
is required.

Keep notes aligned with the final flow. Identify important assumptions,
conflicts, and missing verification; distinguish suggested checks from checks
actually performed. A plausible graph or valid syntax alone
does not establish causality, blast radius, or correct implementation.
Keep sensitive information out of diagrams and supporting notes.
