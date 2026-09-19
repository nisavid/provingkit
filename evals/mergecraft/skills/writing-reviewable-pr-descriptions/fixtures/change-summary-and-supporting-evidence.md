# Retry limit change

Draft the prose following an already-valid Diff disclosure. The repository
uses Conventional Commit titles and permits a short Summary and Verification.

The changed worker now reads its retry limit from the project's existing
`retry_limit` setting instead of a hard-coded value of 3. The command-line
default and explicit command-line override are unchanged. The author ran the
18 worker tests; all passed. The integration suite was not run.

The author's relevant investigation: "I tried changing the shared default
first, but that would also change the command-line behavior. I believe keeping
the fix in the worker makes this PR easier to assess." That judgment is the
author's view, not an agreed project policy or a measured performance result.
Preserve this useful rationale in the PR's explanation. No issue relation,
deployment, release, or approval decision has been supplied.
