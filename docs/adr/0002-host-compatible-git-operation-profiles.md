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

The shared POSIX guard retains every lexical and resolved ancestor, including
the filesystem root. Directory observations compare device, inode, type/mode,
UID, and GID; other entries retain their full metadata tuples, and resolved
targets are compared separately. Unrelated directory-entry activity therefore
does not invalidate the selected executable or an equivalent new binding.
Removing directory size, link count, mtime, and ctime deliberately narrows
drift detection: ctime can also record metadata changes or intervening changes
whose final represented state matches. These snapshots do not establish ACL
or extended-security-metadata continuity, uninterrupted identity, or absence
of intervening mutation; inode reuse and path-check/use races remain possible.
POSIX mode is not a portable ACL fingerprint.

This shared identity rule applies to ordinary publication, selected Linux
GitHub credential providers, worktree execution, and both host-compatible and
hardened Graphite execution. Hardened Graphite retains its stronger root-owned
selection without fallback, but its shared guard's timestamp/history
observations narrow too. Hardened POSIX Versionkeeping retains its existing
root-owned selector without adding shared-guard bindings.

Windows publication in both profiles analogously compares directory device,
inode, and type/mode, while retaining full six-field file identities. Its
registration, owner, ACL, and path-redirection admission checks remain separate
and unchanged; stat mode does not represent Windows ACL permissions, nor is
ctime a portable security-change counter. Neither platform's directory tuple
asserts ACL continuity. Native platform checks are required for platform
qualification; Linux tests of Windows identity logic establish only that logic.

The ordinary Linux GitHub HTTPS route has a bounded exception for existing
environment-backed gh credentials. It selects only the fixed, identity-checked
`/usr/bin/gh auth git-credential` helper and inherits only `GH_TOKEN`, or
`GITHUB_TOKEN` when the former is absent, for matching credential preflight and
transport. It does not put a token in stored configuration, arguments, plans,
or logs. Git and its children receive the token; no exclusive-secret-isolation
claim is made. Nonmatching operations and hardened mode retain the scrubbed
environment. Helper ambiguity, HTTP/auth overrides and URL rewriting block
the token-bearing route. The nonsecret policy/provider/source-name identity is
part of the reviewed configuration digest and is compared before any
credential-bearing transport. Plans recording the previous directory-identity
representation require fresh planning and review; no compatibility bypass
accepts their old digest. A fixed, identity-checked nonprompting fallback
prevents ambient PATH from selecting an askpass process. Only the ordinary
publication planner and executor activate the exception; the separate
remote-ref-deletion contract remains unchanged. Other platforms and enterprise
authorities need their own qualified provider binding.
The selected environment-token route excludes conditional-include directives,
even inactive ones and those reached through ordinary includes. The expanded
key inventory is checked before every token-bearing call; unconditional
includes remain admissible if their expanded contents satisfy the route's
other checks. This restriction does not change unselected provider or deletion
configuration behavior.

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
