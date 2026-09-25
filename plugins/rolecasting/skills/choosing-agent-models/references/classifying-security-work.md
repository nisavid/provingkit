# Classify The Current Scope

Classify the work by what its result must establish. Use this procedure before
execution and each dispatch, resume, follow-up, or review cycle, and when a
block or refusal raises a routing question.

## Required Judgment

Identify the bounded purpose, affected assets, relevant trust boundaries,
plausible failure effects, and judgment needed for the claimed result. Use
concrete task evidence; a possible security consequence of any software bug is
not enough by itself.

Classify the complete operation into one of three security classes or ordinary work. A potential security consequence of any software bug, a security-adjacent project, a syscall name, sandbox tooling, a previous Daybreak assignment, or the word "test" does not classify an operation.

- **Actual cybersecurity work** directly investigates, establishes, or changes a security property: adversarial behavior, unauthorized access or disclosure, containment, vulnerability handling, or cryptographic verification.
- **Obviously cybersecurity-related work with another primary domain** has a different main deliverable, but its complete operation visibly involves security concerns. Judge both the main work and those concerns rather than routing from the document or team label alone.
- **Cybersecurity-adjacent work** has another primary purpose but its behavior enters a concrete security concern in certain cases. Identify the actual implication and required judgment; a merely hypothetical downstream risk is insufficient.
- **Ordinary work** requires correctness, compatibility, reliability, resource hygiene, or settled-policy writing without a security concern in its complete claim. Keep necessary ownership, isolation, and cleanup in that work.

| Current scope and claimed result | Classification |
| --- | --- |
| Remove a test-owned disposable directory or reap a cooperative child process with synthetic inputs; failure leaks only test resources. | Ordinary engineering. |
| Observe whether a synthetic guest starts and reports its own metadata on another platform; report only compatibility. | Ordinary engineering; this observation does not certify containment. |
| Decide whether hostile guest code can escape a restriction, read host credentials, expose a debugger, or attach to an unrelated process. | Actual cybersecurity work. |
| Edit an installation guide whose settled examples plainly cover credential-handling steps. | Obviously cybersecurity-related work with another primary domain; inspect whether the concerns are largely known, uncomplicated, and architecturally clear before an automatic fallback. |
| Fix a routine UI error that visibly displays a token. | Cybersecurity-adjacent work; inspect whether the implication is readily recognizable and easily fixable before an automatic fallback. |
| Test credential handling, access restrictions, or signature rejection as evidence that those protections hold. | Actual cybersecurity work, including with synthetic fixtures. |
| Copyedit documentation or maintain model-routing examples under settled policy. | Ordinary writing. |
| Change what an authorization boundary permits or assess whether a runtime routing control resists bypass. | Actual cybersecurity work, including when the artifact is prose. |

For mixed work, separate independently useful scopes and state each result's
limits. A compatibility observation can proceed separately from a containment
review when it grants no security acceptance. If one result still requires
both judgments, retain Daybreak routing for that combined scope. A changed
label, shorter prompt, or omitted dependency does not remove a security claim.

If missing facts can change classification, identify the smallest missing fact
and return a scoped clarification through the owning workflow. For example,
before classifying unknown file cleanup, establish ownership, contents, and
whether deletion is relied on to protect a secret. Continue independently
bounded ordinary work where its classification is already supported. Keep an
existing security claim routed until evidence supports a genuinely separate
ordinary scope.

Return the classification, a brief reason tied to the required judgment, and
any missing fact or separated claim. Then apply the selected routing policy
and its authority and capability gates. Classification is not execution
permission or proof of runtime enforcement.

## Reclassify A Follow-Up Review

Before each review dispatch or reuse, establish three facts:

1. State the complete claim the next review must establish and the judgment it
   requires. Include dependencies on which that claim relies.
2. Identify which earlier security findings are resolved and whether changed
   inputs or dependencies invalidate the security evidence still being used.
3. Select the route for that current claim. Record its concrete security
   judgment, or explain why the remaining result is ordinary engineering or
   writing. Reviewer identity, ticket history, and membership in a review loop
   supply no classification evidence.

For example, a Daybreak review resolves an unauthorized-access finding. A
later review limited to wording, synthetic fixture plumbing, or parsing,
deadline, and cleanup correctness uses the general matrix when those changes
leave the security claim and its supporting evidence valid. It does not need
the previous reviewer merely to continue the loop.

If a changed parser, deadline, cleanup path, or other dependency invalidates
that security pass, the next review covers the whole affected security-relevant
scope through Daybreak routing. Checking only the convenient delta cannot
renew the pass. Establish the actual dependency and claim before choosing
either branch; ordinary-sounding filenames do not establish independence.

## Diagnose A Block Or Refusal

Classify ordinary work before trying it; it may then proceed under the general
matrix. Classify security work before execution and apply Daybreak routing
without waiting for a general model to refuse. A refusal is evidence to
diagnose, not an automatic classifier or permission to change routes.

Distinguish the response using the actual error or platform notice:

| Evidence | Next action |
| --- | --- |
| Missing model, capability, entitlement, or capacity. | Verify current capability and use the applicable routing disposition. Preserve the classification and existing fallback restrictions. |
| A platform explicitly supports an authorized specialist handoff for this work. | Verify that supported route, authority, and runnability through the existing gates. A handoff notice alone satisfies none of them. |
| A tool or sandbox denies a filesystem, network, or action permission. | Use the owning workflow's ordinary permission or scope-resolution path. A model change cannot grant that permission. |
| An actual safety refusal prohibits the requested operation. | Stop that operation. Offer a permitted alternative or use the platform's clarification or appeal path when available. |
| An ambiguous response does not identify the cause. | Seek the missing explanation or supported platform guidance before retrying or rerouting the affected operation. Independently permitted work may continue. |

Preserve higher-priority safeguards in every branch. Do not switch models,
accounts, or harnesses, disguise the purpose, or split the same prohibited
operation into subtasks to obtain what a safety refusal withheld. A supported
specialist route serves authorized work within the platform's rules; it is not
a workaround for a prohibition. Existing approval for work or a model does not
override a safety refusal.
