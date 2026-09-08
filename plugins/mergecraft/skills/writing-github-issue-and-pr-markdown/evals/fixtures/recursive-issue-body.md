# Recursive release-check Issue body

Field: Issue body.

Create a new body for an Issue that tracks three release checks. Use a `## Checks` heading followed by an ordered list. The second item contains a nested unordered list with two independently actionable checks. Its second nested item contains a blockquote explaining that a missing checksum blocks promotion. After the list, add a `<details>` container whose summary is `Operator note` and whose body is one paragraph explaining that promotion and installation remain separate decisions.

The opening paragraph explains that all three checks bind the same candidate, and it intentionally contains a visible hard break between the candidate-identity sentence and the sentence naming the operator decision. Use an explicit HTML break for that author-intended break.

No line-width policy applies. Use LF and no terminal newline. Do not create or edit an Issue.
