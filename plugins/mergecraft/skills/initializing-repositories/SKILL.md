---
name: initializing-repositories
description: Use when setting up a new UI repository end to end in Codex, including GitHub, local tooling, product context, scaffolding, and CI. Route GitHub-only work to configuring-repositories.
---

# Initializing Repositories

Coordinate a usable greenfield UI repository through its existing component
owners. Forks, existing projects, and stack-only or design-only requests use
their own workflows. Bind the project purpose, repository owner and visibility,
current state, applicable policy, credential boundary, and permitted effects. A
public-facing product can have a private source repository. Inspect what can
be established from the target and existing decisions before asking the user.
Invocation coordinates the work; each effect needs authority under its owner.

1. Bind the Versionkeeping baseline before starting any route that can write
   to a checkout, including a maintained declarative configuration writer.
   Record the repository and worktree, source commit and branch state (or
   unborn HEAD), index, worktree, unpublished state, push configuration or
   its absence, and in-progress Git operations. Retain it for the checkpoint.
   While no checkout exists, read-only preparation and authorized hosted-only
   creation can proceed. Establish the intended checkout and capture its
   baseline before the first setup write.
2. Use [configuring-repositories](../configuring-repositories/SKILL.md) for
   `operation:repository-configuration`. Prepare or apply the authorized
   GitHub creation and initial controls, using the actual owner, visibility,
   entitlement, and eligible actors. Assess applicable CodeQL and code
   scanning, GitHub Code Quality, AI Scan, and third-party checks as distinct
   choices with their own access and cost. Stage stack-dependent checks and
   approval requirements until their producers and reviewers are verified.
3. Reuse an approved license decision or help the operator select one.
   Apply the approved license. Recover the project's Git policy and inspect
   existing hooks, then use Cocogitto's documented setup to add the selected
   configuration and hooks without replacing unrelated hooks. Verify both.
   Reuse the applicable approved automation policy in the repository
   instructions and read it back, or identify the missing decision and its
   owner before relying on it.
   Verify any already established tracker and domain setup. When setup is
   needed, ask the operator to invoke `/setup-matt-pocock-skills` in the
   target checkout. Only the operator can invoke it. State the expected
   instruction block, tracker and domain guidance, and applicable triage
   guidance. Await the actual operator step in that checkout, then verify
   its approved outputs before resuming dependent work.
   If the initial setup needs an authorized Git checkpoint, end this
   invocation. Return the checkout, original Git baseline, approved setup
   paths, and local checkpoint authority to the ongoing task. That task
   routes the applicable independent review and invokes
   `versionkeeping:checkpointing-and-publishing-git-work` for the authorized
   local commit. It checks the reviewed commit and preservation of unrelated
   state against the baseline and live checkout. Reconcile an interrupted or
   unknown checkpoint before continuing. Once the result is verified, the
   ongoing task starts a fresh initializer invocation at product setup from
   the verified state. Publication requires its own authority.
4. Use `impeccable:impeccable` with `init` in the actual checkout. Carry
   forward any confirmed stack or deployment constraints. Keep open component
   choices pending during the product interview and record them as such.
   Before detailed tooling or design, verify `PRODUCT.md` and confirm it
   reflects real operator answers or explicit delegation. When the interview
   cannot obtain a response, retain any provisional record and wait for
   confirmation before continuing dependent work. Identify components
   from the product's build and deployment surfaces. Discover configured
   preferences and other reliable hints for each component. Use applicable
   preferences as the starting recommendations. Where those sources supply no
   useful default, research the latest stable, actively maintained and
   well-supported options that fit the product. Present the recommendations
   by component in `mattpocock-skills:grilling` and confirm consequential
   choices with the operator. Treat comparison and product selection as
   read-only with respect to third-party adoption. A confirmed selection
   supplies adoption, maintenance, or execution authority only when it
   expressly includes that exact authority and its effects; carry its
   authority identity into the lifecycle handoff rather than asking twice.
   Before writing a selected third-party component into the repository or
   running any generator, install, build, or test that resolves, loads, or
   executes it, bind the exact candidate and policy identities, exact
   lifecycle action and authority identity, and intended effects. When no
   policy applies, record that absence instead of inferring one. End this
   invocation and return the binding, any missing authority, and the intended
   continuation to the ongoing task. That task either reuses a prior successful
   result under the match check below or, with matching authority, invokes
   `artifact-customs:adopting-third-party-components` for a new or materially
   revised trust boundary, or
   `artifact-customs:maintaining-third-party-components` for an ordinary
   lifecycle action under a named matching existing policy. Name any missing
   operator decision and boundary in the return. If the applicable owner is
   unavailable, return that owner, action, and evidence needed to continue.
   Do not perform any dependent component write or execution in this
   invocation.
   The ongoing task starts a fresh initializer invocation only after verifying
   an `adopted` or `maintained` result whose exact candidate, policy, authority,
   and authorized effects still match. It may reuse a prior successful result
   only after the same check. A read-only assessment result alone, including
   `cleared`, cannot resume scaffolding; neither can a negative, `no-go`,
   `operator decision`, `blocked`, `deeper autonomous investigation`, unknown,
   or drifted result. After satisfying this gate for each selected third-party
   component, choose the layout, scaffold, and verify each selected stack
   within the applicable authority.
5. Select general CI under the applicable provider policy. Assess scanner
   dependencies, coverage, entitlement, and spending separately. Return to
   `operation:repository-configuration` for GitHub changes through its
   `ci-hardening` workflow and the maintained writer. Apply the authorized
   effects. Verify producers and eligible reviewers before enforcing checks
   and approvals. Independent source review and eligible GitHub approvals
   establish different facts. Verify effective enforcement on the
   target for the intended changes and actors.

At a missing decision, authority, or control, stop the dependent effects and
give the responsible owner the next action and evidence needed to resume.
Reconcile partial or unknown effects before depending on them. Report the
observed checkout and configuration, completed component results, and open
choices or holds. Claim CI coverage and merge enforcement only where each was
observed.
