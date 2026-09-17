# Destination Commit Policy

Establish the destination's commit policy before the first commit in a thread.
Read its `CONTRIBUTING.md` or equivalent contribution guidance, including linked
commit rules. If none exists, establish the policy from repository instructions,
commit checks, and applicable maintainer policy. Record the source and the DCO
requirement in the task evidence. Reuse that established policy during the
thread while the repository and policy remain unchanged; no per-commit reread
is needed. An installed DCO app alone proves neither a contribution requirement
nor merge enforcement; documented policy still applies
without a required status check. Resolve conflicting or unavailable policy
before the affected commit instead of assuming DCO is absent.

If no DCO requirement exists, continue without DCO deliberation. This procedure
adds no sign-off requirement to that repository.

## When DCO is required

Read the destination's certificate and license terms. A Developer Certificate
of Origin (DCO) sign-off is the named contributor's attestation; the agent acts
under the authorized contributor identity, not an invented agent identity.

- For ordinary original work authored or assisted by the agent for the
  repository, use the authorized contributor's sign-off with minimal deliberation
  and no redundant confirmation when the task's authority and evidence support
  the certificate. Agent-assisted generation alone is not uncertainty. Apply
  `git commit --signoff` with that verified committer identity, or the
  destination's prescribed equivalent. Existing uncertainty about submission
  rights takes the next branch.
- Concrete employer ownership, third-party copying, imported material, generated
  artifacts with external licensing obligations, or other provenance uncertainty
  requires checking whether the signer can truthfully certify
  submission under the destination license. Creation, modification, or bot
  identity alone does not establish those rights. Preserve original authors,
  existing trailers, bot contribution records, and license provenance. A
  justified additional sign-off certifies only the named signer's own role.
  Never add the operator's sign-off as another contributor's attestation.
- When the evidence does not establish truthful certification, ask the operator
  if the thread permits escalation. State the affected work, the missing rights
  or policy evidence, and what would allow the commit to proceed. A confirmation
  must establish that basis; permission to continue does not make a false
  attestation true. If escalation is unavailable, retain the affected work uncommitted
  and report the gate, or complete the task through a rights-clear implementation
  within existing authority or a destination-defined alternative whose
  requirements are satisfied. Preserve the original contribution records when
  replacing affected work; certify only the supported replacement. Continue
  independent work when separable. No stopping constraint authorizes an unsupported sign-off, silently
  bypassing required checks, or rewriting third-party history to make DCO green.

Verify the resulting commit's sign-off trailer and identity against the
established policy and preserve contribution records during amend, rebase, or
integration. Reassess when the destination, policy, signer, or selected work
changes; the first-commit check is not blanket authorization for later imports.

DCO attestation is separate from cryptographic commit signing, license
compliance, code review, and release authority. These remain independent gates.
