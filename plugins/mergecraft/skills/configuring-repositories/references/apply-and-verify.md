# Apply a bounded change and verify its effect

Use this sequence proportionally to the actual effect. Native APIs, CLIs,
connectors, and maintained declarative writers are execution surfaces; this
guide does not introduce a second configuration manager.

1. **Bind the target and intent.** Establish the repository's actual identity,
   owner, visibility, desired behavior, authorized changes, applicable policy,
   and maintained writer. Read the controls that affect the result, including
   inherited policy and the acting user's bypass/access. For creation, verify
   the intended owner and name availability through an authorized surface; a
   private 404 alone does not establish that the name is free.
2. **Prepare the useful change.** Read current primary documentation and
   observe target capabilities for unfamiliar settings. Select only owned
   fields or maintained source changes and retain the current preimage needed
   to preserve unrelated state. Establish checks/actors/allowance before
   selecting controls that depend on them. Resolve consequential missing
   authority or intent using a concrete proposal.
3. **Validate before dependent effects.** Use the owning source validators,
   meaningful tests, and independent review required by the task or policy.
   Confirm check producers and relevant event/path coverage before requiring
   their results. Create generated source or a supported workflow before
   depending on it; a definition on disk is not a hosted result. Avoid exposing
   secrets in commands, evidence, logs, or user-facing output.
4. **Reobserve and apply.** Compare current owned and relevant dependency state
   with the prepared preimage immediately before mutation. Preserve concurrent
   unrelated changes; replan when drift changes the result. Use the smallest
   supported operation once through the maintained owner. If the provider
   lacks conditional writes, retain that race limitation and perform an
   immediate full relevant readback; a reread cannot undo a lost update.
5. **Reconcile the outcome.** Record what the provider actually accepted and
   the effective resulting state. A verified existing value is a successful
   no-op. Permission denial, unsupported plan, or uneditable inherited policy
   needs an explicit outcome and useful next route. A timeout or ambiguous
   response after a possible write is unknown until reobserved; do not blindly
   replay it or guess a rollback. Retain confirmed successes when a later
   step fails, and reassess the remaining dependencies.
6. **Demonstrate the claimed behavior.** Select the smallest useful observation
   matching the claim. Settings readback establishes stored configuration;
   effective-policy evidence establishes applicability; actual runs establish
   useful CI behavior. For a causal merge-gate claim, first satisfy neighboring
   gates, vary the selected cause, observe rejection attributable to it, then
   restore the control and observe acceptance. Record target revision, actor,
   bypass, rule, result producer, event, and neighboring gates. Failure,
   skipped, and missing results are distinct cases. Execute experiments only
   within their existing authorization and cost boundary.
7. **Return the changed premises.** Tell existing lifecycle consumers when
   settings/check identity/events alter their assumptions. Invalidate affected
   readiness, relation, or review conclusions and let their owners renew them.
   Report the applied/no-op/partial/unavailable/unknown result and the evidence
   supporting each claimed effect. Separate remaining work from demonstrated
   behavior.

Authorization persists across steps and invocations within the task's scope.
Do not repeat settled approval questions. Conversely, successful preparation,
review, or readback does not supply missing authority for a consequential
effect. Destructive operations, paid activation, organization-wide policy,
visibility exposure, and ownership transitions need the actual scope checked
against the user's request rather than a presumed universal exception.

Keep recovery concrete. Retain the prior owned values or source revision and
the supported way to restore them, without secrets. Apply restoration only
when authorized, still appropriate, and compatible with intervening changes.
Use disable-and-retain cleanup where that is the chosen fixture contract;
deletion is a different effect. Do not overwrite another actor's updates to
make cleanup look complete.
