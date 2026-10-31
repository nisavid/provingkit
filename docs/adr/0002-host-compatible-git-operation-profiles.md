# ADR 0002: Host-compatible Git operation profiles

## Status

Accepted

## Decision

Versionkeeping's ordinary publication operations inherit the effective host Git
configuration and credential providers available to the harness. The harness
owns whether that host state is visible; Versionkeeping owns operation
invariants such as the reviewed endpoint, full destination ref, exact lease,
noninteractive execution, and post-operation verification.

Ordinary POSIX runtime selection trusts the host-supplied interpreter, fixed
system Git and SSH executables, and filesystem root namespace without
requiring numeric UID 0. It still rejects redirected, nonregular,
nonexecutable, group- or world-writable executable paths and paths controlled
by the candidate repository. It binds the selected path identities per
operation and rechecks them before and after execution. Those observations
detect visible drift; they do not prove host provenance or eliminate races.
The host, interpreter, and same-user concurrent mutation remain outside this
ordinary assurance boundary.

This runtime policy is separate from Git configuration policy. Worktree
creation and ordinary candidate inspection retain their closed configuration
contracts. Ordinary publication retains its host-compatible configuration
contract. Existing Windows registration and ACL requirements are unchanged.

Versionkeeping also provides an explicit hardened profile for workflows that
need closed configuration, trusted executable ancestry, and a restricted
credential provider set. The hardened profile is never selected implicitly by
ordinary publication and must be bound into planning and execution so a
profile change invalidates the reviewed plan.

Hardened publication retains the stronger root-owned POSIX executable ancestry
and platform-provider checks, with no fallback to ordinary host trust. A host
that cannot satisfy them may support ordinary publication while hardened
publication remains unavailable.

When the selected profile cannot access the required host configuration,
credential provider, or harness capability, the operation returns a typed
diagnostic naming the missing capability and the supported operator or
harness-side remedy. It does not require an unrelated daemon or secret cache to
be prepared outside the operation without explaining that profile choice.

## Rationale

The previous publication path unconditionally discarded global and system Git
configuration, cleared every ambient credential helper, and required a
pre-existing Linux `git-credential-cache` entry. That was a valid hardened
implementation, but it was presented as ordinary publication and had no
profile selector or guided capability diagnosis. It therefore broke the
expected host-compatible default for users whose normal Git path uses a
persistent store, a keyring, or a `gh` helper.

The hardened profile remains useful when repository configuration, hooks, or
ambient process state are treated as hostile. Keeping it explicit preserves
those protections without making an invisible host setup prerequisite part of
the default workflow.

## Consequences

The profile is part of the reviewed publication identity. Planner and executor
must use the same selected profile, and a change invalidates the plan. Tests
must cover both host-compatible inheritance and hardened isolation. Other
Provingkit transports should adopt the same capability vocabulary rather than
silently choosing one environment policy.

For ordinary local publication endpoints, only the filesystem root's owner
is accepted on host trust. The existing directory type, mode, symlink,
current-user endpoint ownership, link-count, and intermediate-ancestor checks
remain. Arbitrary foreign-owned ancestors and foreign-owned temporary roots
receive no exemption. Native Cloud qualification uses owned workspace paths.
