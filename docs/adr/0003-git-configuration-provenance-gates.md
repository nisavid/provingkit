# ADR 0003: Git configuration provenance gates

## Status

Accepted

## Decision

Provingkit code that reads a Git configuration key as a single value fails
closed when the key has an accidental repeat: one file defines it more than
once, or both global files, `$XDG_CONFIG_HOME/git/config` and `~/.gitconfig`,
define it directly. The repeat fails even when the values agree and even though
Git would accept the configuration and use the last value read.

Every other repeat follows Git's documented precedence. A later scope overrides
an earlier one, in the order system, global, local, worktree, and command, and
a file brought in by `include` or `includeIf` overrides the file that includes
it. These are Git's mechanisms for overriding a value, and ADR 0002 commits
ordinary operations to the effective host configuration.

A key that Git reads as a list, such as `remote.<name>.push` or
`credential.helper`, is valid configuration with any number of values,
including Git's empty-value reset where the key defines one. An operation that
needs exactly one value from a list blocks as unsupported for that operation,
not as invalid configuration. Each operation decides which keys it reads as
single values and which as lists.

A rejected repeat reports `GIT_CONFIG_DUPLICATE_DEFINITION` with the key, the
scope, and the defining files. Files are named relative to `$GIT_DIR`,
`$XDG_CONFIG_HOME`, or `~`, and values are never reported. An operation that
binds a reviewed plan includes the source file of each single value it reads in
the plan's configuration digest, so a value that moves to another file after
review blocks execution.

## Rationale

Git never treats a repeated definition as ambiguous. The last value read wins,
and Git's documentation states that both global files are read when both
exist. This gate is therefore about provenance, not ambiguity. A key defined in
both global files, or twice in one file, is the signature of configuration
nobody meant to keep: a legacy `~/.gitconfig` left beside a managed
`$XDG_CONFIG_HOME/git/config`, or a line duplicated by an edit. Values that
agree today can diverge silently when one copy changes, so agreement is not
evidence that the repeat is intended.

The earlier gate counted every definition across every scope and include. It
caught the accidental cases, but it also blocked a repository that sets
`push.default` while the global configuration sets it too, and it would have
treated an `includeIf` override, the usual way to switch identity per
directory, the same way. Both are ordinary uses of Git's override mechanisms.
The narrower boundary keeps the accidents and permits the overrides.

Once overrides are permitted, a winning value's text no longer identifies
where it came from. Binding its source file into the reviewed configuration
digest keeps a reviewed plan tied to the configuration that produced it.

## Consequences

Versionkeeping's publication planner reads `branch.<name>.pushRemote`,
`remote.pushDefault`, and `push.default` as single values under this rule. It
reads `remote.<name>.push` as a list, and several entries block as
`REMOTE_PUSH_AMBIGUOUS` because publication needs one destination ref.
`PUSH_DEFAULT_AMBIGUOUS` and `DESTINATION_REMOTE_AMBIGUOUS` now cover only real
ambiguity, such as a `simple` default without an upstream or several remotes
with no selection. A new reader of Git configuration in any member follows the
same rule and reuses its diagnostic. A host that keeps a key in both global
files must remove the stray definition; a repository or include override needs
no change.
