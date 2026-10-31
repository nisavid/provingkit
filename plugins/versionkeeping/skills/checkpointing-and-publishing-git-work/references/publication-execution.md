# Publication Planning And Execution

Use the planner and executor from the loaded plugin root. Never rely on a
machine-local installation path:

- `skills/checkpointing-and-publishing-git-work/scripts/plan_git_publication.py`
- `skills/checkpointing-and-publishing-git-work/scripts/execute_git_publication.py`
- `skills/checkpointing-and-publishing-git-work/scripts/plan_git_remote_ref_deletion.py`
- `skills/checkpointing-and-publishing-git-work/scripts/execute_git_remote_ref_deletion.py`

## Planner Effects And States

The planner is not a read-only command. It may fetch bounded remote objects and
create target-local refs under `refs/versionkeeping/publication/`. It preserves
`FETCH_HEAD`, removes only the exact refs it reserved, and may leave fetched
objects in the repository object store.

Follow only `blocked`, `needs_reconciliation`, `ready`, or `verified`. Never
infer around a gate. Missing authorization for any SHA in `target_only_shas`
alone yields `needs_reconciliation`; another concurrent gate yields `blocked`.
The ordinary publication planner and executor never delete a remote ref.

## Default-Branch Policy Gate

Publication request schema version 2 includes one closed
`default_branch_policy` field:

```json
null
```

or:

```json
{
  "ref": "refs/heads/main",
  "direct_push_permitted": true
}
```

Use the object only for a separately verified repository policy/protection
decision. Its `ref` must be the exact full ref reported as the push endpoint's
symbolic default branch, and `direct_push_permitted` must be boolean. An
ordinary non-default destination may use `null`. The observed default branch
is blocked when the field is absent, false, or ref-mismatched; this does not
blanket-ban a branch named `main` when the endpoint reports another default or
when verified policy explicitly permits the direct push.

The planner fails closed if the endpoint's symbolic default branch is
unavailable or malformed. It records that ref in `destination.default_branch_ref`
and includes it in `destination.config_digest`. The executor re-observes the
same endpoint after validating the target lease and immediately before push
actuation, and blocks if the default branch changed.

Git does not provide a lease for symbolic `HEAD`, so the endpoint can still
change its default branch after that final observation and before it processes
the push. The executor closes every observable pre-actuation interval but
cannot turn symbolic `HEAD` into an atomic compare-and-swap condition.
Server-enforced repository policy/protection is the hard guarantee for direct
default-branch pushes; this client-side gate detects observed drift and never
substitutes for that enforcement.

## Trusted Plan Handoff

Capture the complete `ready` JSON file as exact reviewed plan bytes. Separately
capture its SHA-256 digest in trusted review state; the digest must not be read
from the plan or from mutable metadata beside it. Invoke the executor with both
the plan file and `--reviewed-plan-sha256 sha256:<64-lowercase-hex>`. It verifies
the digest before JSON decoding or repository access. Any byte change requires
a fresh planner run and review; never recompute the trusted digest for an edited
plan.

Invoke the executor only after publication authority is bound as `SKILL.md`
describes (Bind Publication Authority).

The executor then requires the current destination remote, full ref, endpoint
fingerprint, default-branch ref, config digest, expected lease, and immutable
source SHA to match.
It resolves the current push URL without printing it and binds an ephemeral
config-env remote alias to the captured endpoint string. A normal configured
remote name is discovery metadata, not a publication actuator.

## Authenticated HTTPS Boundary

Ordinary publication uses the `host-compatible` Git configuration profile by
default. It inherits the effective host Git configuration and credential
helpers visible to the harness, while retaining endpoint, ref, lease, prompt,
and post-push verification gates. This weaker, harness-trusting profile is
outside the guarded authenticated HTTPS contract; that distinction is a route
boundary, not an assertion that it provides hardened isolation. When the
publication needs no ambient executable Git configuration, one trusted
provider, and a fail-closed provider boundary, set
`VERSIONKEEPING_GIT_CONFIG_PROFILE=hardened` before planning and keep it
selected through execution. That profile clears global and system
configuration and permits only the validated platform provider described
below. The selected profile is included in the reviewed destination
configuration digest; changing it requires a fresh plan and review.

On POSIX, the host-compatible profile also trusts the host-supplied interpreter,
fixed `/usr/bin/git` and `/usr/bin/ssh`, and filesystem root namespace without
requiring UID 0. It selects neither executable from ambient `PATH` or repository
configuration. Executable targets must be regular, executable, free of
redirection and group/other write permission, and outside the candidate
repository. Their ancestor modes and identities remain checked. The operation
binds the selected paths and rechecks their identities before and after Git
execution, including credential preflight. Observable replacement blocks
further execution; a failure after push begins retains the unknown-outcome
contract below. These checks detect drift but do not independently authenticate
the host or rule out concurrent same-user mutation. The hardened profile keeps
its root-owned executable requirements and never falls back to ordinary trust.
Windows retains its existing registration and ACL requirements.

On Linux, ordinary GitHub HTTPS transport can use an existing `GH_TOKEN` or,
when absent, `GITHUB_TOKEN` through the explicitly configured
`!/usr/bin/gh auth git-credential` helper. This bounded exception checks the
fixed executable's identity and the full potentially matching helper chain;
conflicting or ambiguous declarations are refused after gh is selected. A matching
path-specific declaration cannot hide a conflicting helper. The operation
seals the known helper, TLS verification, disabled redirects, and empty hooks
for each transport. Ambient HTTP overrides, other credential controls and
URL rewrites are not admitted by this token-bearing path. Other host providers
retain their existing behavior without receiving these token variables.
This route also requires no conditional-include directives, including inactive
conditions or directives reached through ordinary includes. Their selection
can differ in transport context, so the expanded key inventory is checked on
every policy validation before constructing a token-bearing environment.
Ordinary unconditional includes remain supported when their expanded contents
pass these checks. Unselected providers and deletion retain their prior include
behavior and scrubbed environment.
The exception also binds the fixed `/usr/bin/false` nonprompting fallback and
sets absolute askpass paths; helper failure cannot select a fallback from
ambient `PATH`.

Only the selected token variable reaches matching credential preflight,
`ls-remote`, `fetch`, and `push` subprocesses. Other Git calls, authorities,
SSH/local transport and hardened mode receive no new token environment.
Debug/tracing and client redirection variables remain scrubbed. Git and its
children can read the token; this is not gh-exclusive secret isolation.
The token is never persisted, printed, passed in arguments, or hashed into
the plan. The credential policy, source-variable name, helper declarations
and executable identities are bound into the reviewed configuration digest.
Token rotation under the same source name does not bind a new principal.
Execution compares that identity before any credential-bearing preflight or
transport, then independently rechecks the live default branch and lease.
Only the ordinary publication planner and executor activate this capability.
The shared remote-ref-deletion operations retain their previous scrubbed
environment and credential contract; this exception does not authorize or
enable deletion.

The harness owns helper configuration. It can select the standard helper in
a private external Git config without storing a token; preserve existing
configuration and use the same selection for planning and execution. This
operation never installs gh, writes configuration, or creates a token store.
The environment-token exception currently supports the fixed Linux path;
macOS, Windows and enterprise authorities retain their existing provider
routes and require separate qualification for such an exception.

The hardened publication profile supports noninteractive HTTPS credentials on
modern macOS, Linux, and Windows through closed platform-provider sets:

- macOS uses `git-credential-osxkeychain` from the trusted system Git exec
  directory;
- Linux uses the system Git installation's memory-only
  `git-credential-cache`; and
- Windows uses `git-credential-manager.exe` (or the allowlisted legacy
  `git-credential-manager-core.exe`) only from the selected Git for Windows
  installation, with the `wincredman` store forced through GCM's environment
  contract and at command scope.

The Linux provider and both its lexical and resolved directory ancestries must
be root-owned, non-writable by group or other, and free of shell
metacharacters; only a root-owned package symlink may redirect the helper. The
macOS candidates are limited to Git's absolute exec path and closed system
Command Line Tools locations. Each candidate and its ancestry must satisfy the
same root-owned, non-writable contract, and the trusted `/usr/bin/codesign` must
also verify Apple's exact `git-credential-osxkeychain` requirement.
On Windows, Git, SSH, the non-prompting askpass command, the shell, the closed
command path, and GCM must all resolve without redirection inside the same
machine-registered Git for Windows installation under the operating system's
machine-wide Program Files boundary. Per-user and custom-location installations
are not trusted. The executor reads machine registration and Program Files
locations instead of ambient `PATH` or directory environment variables. Paths
containing command syntax are rejected, and helper paths are escaped before
entering command-scope Git configuration. A missing, redirected, mutable, or
unsupported provider yields
`HTTPS_CREDENTIAL_PROVIDER_UNAVAILABLE` before any push attempt. A Linux
credential must already be present in Git's user-private memory cache. The
executor neither starts an interactive acquisition flow nor reads a persistent
desktop secret store whose API may request an unlock prompt; a cache miss fails
closed.

In the hardened profile, the executor installs an empty command-scope `credential.helper` to clear
all ambient helpers, rejects every repository or worktree `credential.*`
setting for HTTPS execution, and then appends only the validated platform
helper. Every repository or worktree `http.*` setting is rejected so transport,
proxy, redirect, TLS, header, cookie, and client-certificate behavior cannot be
changed below the reviewed endpoint. Credential lookup retains Git's standard
authority-level matching so existing host-scoped credentials remain usable. A
closed askpass command,
`GIT_TERMINAL_PROMPT=0`, and `GCM_INTERACTIVE=never` remain in force. Before
helper activation, ambient `SSL_CERT_FILE`, `SSL_CERT_DIR`, and `GIT_SSL_*`
variables are also removed. This prevents a narrower Git configuration or
process environment from weakening TLS beneath the authenticated endpoint.
Rejected setting values are never read into diagnostics.

Credential-provider response bytes remain between Git and the system helper.
The executor sends credential-preflight stdout and stderr to the null device
and decides availability only from the return code; it never receives or
inspects provider response bytes. Credential bytes never enter arguments,
diagnostics, plans, receipts, or repository configuration. SSH and
ancestry-guarded local endpoints do not enable a credential helper and retain
their existing contracts.

Ordinary local endpoint ancestry exempts only the filesystem root's owner
from the ownership check. It retains directory mode and symlink checks,
current-user endpoint ownership, regular-file link-count checks, and the
ownership checks on intermediate ancestors. A foreign-owned writable temporary
root is not admitted through this exemption; use an owned workspace path.
Hardened local endpoint ancestry retains its existing root/current-user owner
requirements throughout.

## Terminal Remote-Ref Deletion

Remote-ref deletion is a separate planner and executor surface owned by this
skill. It is not an ordinary publication update and must not be supplied to
`execute_git_publication.py`. It is outside this guarded authenticated HTTPS
claim and must establish any credential/profile claim under its own contract.
Before planning, the deletion request requires a
verified merge outcome plus explicit repository and operator authorization. Each
authorization repeats and exactly binds the remote, full `refs/heads/...` ref,
and `expected_target_sha`; the verified merged source SHA must equal that
expected target SHA.

The deletion planner captures the exact remote/ref, endpoint fingerprint, and
configuration digest. It returns terminal `verified` when the exact ref is
already absent. Otherwise it returns `ready` only if that exact ref resolves to
the expected target SHA. Capture complete `ready` JSON as exact reviewed plan
bytes and separately retain its SHA-256 digest. Invoke
`execute_git_remote_ref_deletion.py` with
`--reviewed-plan-sha256 sha256:<64-lowercase-hex>`; it validates the digest
before parsing or repository access.

The executor rechecks configuration and endpoint identity, probes the exact ref,
and treats absence as terminal verified. It deletes only `:<full-ref>` using the
exact `--force-with-lease=<full-ref>:<expected-target-sha>` lease, with one
endpoint-bound attempt and no blind retry. It then verifies that the exact ref
is absent. A moved, ambiguous, malformed, unauthorized, or drifted request
blocks before actuation. Any timeout or failure after deletion actuation begins
returns `POST_DELETION_STATE_UNKNOWN` with `deletion_attempted: true`; re-probe
the captured endpoint and ref before deciding whether another reviewed plan is
safe.

## Transport And Push Boundary

All planner and executor Git subprocesses scrub ambient repository, index,
object, config, SSH, credential, and editor routing; disable prompts; close
stdin; and use a bounded timeout. Every transport command overrides
`core.hooksPath` with a controlled empty directory, so ambient Git hooks cannot
observe endpoint or credential-bearing environment data. A timeout before push
actuation is a deterministic gate. A timeout after push actuation begins has an
unknown remote outcome. Neither is retried automatically.

Execute one immutable source SHA, one explicit nonempty
`<source_sha>:<full-ref>` branch-update refspec, the exact existing or absent
`--force-with-lease`, options before `--`, no followed tags, and submodule mode
`check`. Never use a deletion refspec, mutable `HEAD`, bare, `--all`, `--mirror`,
a wildcard, multiple refspecs, or unconditional force.

The executor performs one push with no blind retry, then re-probes the same
captured endpoint and full ref. Completion requires terminal `verified`
evidence for the immutable source SHA.

If an unexpected failure occurs after the push begins, return
`POST_PUSH_STATE_UNKNOWN` with `push_attempted: true`, the expected SHA, exact
ref, endpoint fingerprint, and safe re-probe instruction. Never expose the raw
exception or retry. A typed blocked execution exits 1; malformed input exits 2;
an internal failure before a possible push exits 3, so automation cannot
mistake an implementation failure for an ordinary publication gate.
