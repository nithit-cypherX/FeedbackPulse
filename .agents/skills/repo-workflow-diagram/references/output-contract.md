# Workflow Output Contract

## Text diagram delivery

Answer in chat with a plain-text diagram inside a fenced `text` code block.
Give enough framing to identify the question and scope. Keep supporting evidence
and material limitations nearby; do not repeat the entire flow in prose.

Use simple connectors and meaningful labels rather than decorative frames.
For example, this illustrative structure distinguishes a decision's outcomes;
it is not repository evidence or a mandatory template:

```text
Receive request
  |
Validate required fields
  |-- missing --> Return validation error (end)
  `-- present --> Continue processing
```

Choose a different arrangement when handoffs, data transformations, or state
changes answer the question better. Avoid wide layouts that depend on fragile
spacing. Keep labels in the user's language, preserving needed identifiers.

## Requested documentation

- Follow the repository's existing documentation conventions and reuse a
  relevant document instead of creating a parallel set of records.
- For a new standalone text workflow document, a single Markdown file can hold
  the question, diagram, focused evidence, and important unknowns.
- If no convention exists, `docs/workflows/<workflow-slug>.md` is a suggested
  location, not a directory to create for an ordinary chat answer.
- Name the workflow for the question or process. When updating, preserve useful
  names, anchors, and references; keep supporting notes consistent with edits.
- Keep the diagram and its notes together; create companion files only when
  requested or needed for traceability.
- Preserve existing artifacts and supporting evidence unless the requested
  change includes updating or removing them.

## Completion

Check that the final diagram answers the requested question, preserves the
important relationships, and matches its evidence notes. Distinguish a source
walkthrough from execution testing; report only the checks actually performed.
For a saved document, also check the code block and local references.

ASCII art is not automatically accessible because it consists of text.
Provide an accompanying explanation of its meaning, proportionate to the
diagram and reader, without making spatial alignment the only way to obtain
the essential information. [W3C's ASCII-art guidance](https://www.w3.org/WAI/WCAG22/Techniques/html/H86)
supports providing a text alternative; this is an adaptation of that concern
to chat and Markdown, not a claim of WCAG conformance.
