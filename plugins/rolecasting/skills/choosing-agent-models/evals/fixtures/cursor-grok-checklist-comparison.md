# Compare two checklists on the settled Cursor target

A Cursor peer has the source checklist, the completed checklist, and the
leader's rules for matching entries across sections. It reports missing or
changed items with their source and destination locations. This moderately
complex comparison is well understood. Differences are cheap to verify and
correct before they inform a decision. The peer must inspect both documents
and describe the differences in context, beyond a single typed text judgment. Grok high has sufficient judgment margin.

The peer has read-only access. The leader independently reviews the differences,
decides whether each is acceptable, and owns revision, verification, and
integration.

The current Cursor catalog and executor both accept `cursor-grok-4.7-high`.
A stale catalog advertises `cursor-grok-4.6-high`, but the current executor
rejects that pair. No GPT pair is available on the frozen Cursor target.
The foreign-harness invocation, scope, inputs, and non-mutation boundary are
authorized.
