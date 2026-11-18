# Context
This training guide explains a fixture. Only the labels `Setup:` and `Observation:` must remain verbatim; the prose after them may be edited while preserving the facts. The words inside the quotation and its enclosing quotation marks are verbatim; the prose introducing it may be edited. The quoted sentence is an example of boilerplate for readers to recognize. The CLI flag in the code block is literal. The two parallel numbered instructions are intentionally repeated for a two-console exercise. The author observed the fixture exit 1; nothing was run in production.

# Draft
## Reset exercise
It's worth noting that this is a fixture exercise.

Setup: a stub closes the connection after the first request.
Observation: the fixture exits 1.

The specimen says, "That said, this is where reliability matters."

```sh
export-tool --retry-limit 3
```

1. In console A, run the command.
2. In console B, run the command.

That's the power of testing.
