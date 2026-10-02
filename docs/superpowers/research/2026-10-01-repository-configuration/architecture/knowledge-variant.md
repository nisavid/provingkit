# Structured decision knowledge with focused evaluators

A small library of configuration decisions can make consequential relationships repeatable without becoming a universal configuration solver. This variant maintains explicit applicability conditions, related decisions, and named evaluators; an agent uses their results to recommend a coherent set, explain it, and carry an authorized change through existing tools.

Unlike my initial document-first proposal, this design puts some recommendation logic in maintained data and executable modules. The document remains an output. The knowledge and its consumer are the reusable equipment.

## Smallest viable structure

Use a **decision library**, not a row for every platform setting. A decision describes a supported outcome such as “choose mandatory CI results,” with several possible configuration choices. A decision can affect multiple settings; one setting can participate in multiple decisions. Native configuration owners still determine how selected changes are represented and applied.

The maintained source has three parts:

1. Short data records identify concerns, applicability predicates, needed observations, alternatives, explicit relationships, evaluator identities, and supporting source references.
2. Prose explains mechanisms, alternatives, rationale, limits, and stakeholder questions. A record references this prose rather than duplicating it into field-sized fragments.
3. Focused evaluators implement interactions that benefit from repeatable computation, such as matching required checks to producers, events, and selected acceptance claims. They do not decide the user's desired policy.

A minimal illustrative record and relationship could look like this. Identifiers describe the proposal, not existing equipment:

```yaml
id: choose-required-ci-results
concerns: [ci-security, acceptance]
applies_when:
  all:
    - [provider, equals, github]
    - [contribution_path, equals, pull-request]
observations:
  - selected_acceptance_claims
  - check_contracts
  - effective_requirements
  - intended_merge_availability
  - configuration_owner
choices:
  - preserve-current
  - repair-check-execution
  - change-required-results
evaluator: ci-result-contract/v1
explanation: required-ci-results.md
sources: [github-required-check-semantics]
relations:
  - kind: consider
    decision: choose-security-analysis
    when: [concern, includes, ci-security]
    reason: Security analysis may supply a missing acceptance claim.
  - kind: recheck-before-application
    observation: effective_requirements
    reason: A changed inherited rule can change the proposed result.
```

The condition language initially needs only typed equality, membership, and conjunction. No arbitrary expression evaluation, general constraint optimization, or invented scoring weights. Additional operators require a demonstrated decision case and tests. `consider` expands the candidate set; it neither mandates the related setting nor claims that following links exhausts relevant knowledge. `recheck-before-application` invalidates an application assumption, not the user's preference or the entire recommendation.

An evaluator consumes the relevant facts and selected choices and returns explainable findings: which option is supported, which conflicts with an identified policy or requested outcome, which facts are missing, and which behavior claims remain unqualified. It returns evidence references and the premises it actually used. For a check contract, a result named `tests` from a different producer is a changed premise, not automatically equivalent evidence.

## The consumer and its interface

The **configuration adviser module** takes a target, concern or desired outcome, preferences and overrides, known policy, and the requested operation. It acquires discoverable facts, selects matching decisions, follows applicable relations, runs their evaluators, and synthesizes a recommendation. The caller need not supply the internal record identifiers.

This is a deep module when it saves callers from repeatedly reconstructing known interactions. Its **seam** is the advice or preparation request and the resulting proposal, including required context, limitations, and next steps. The library and evaluators are internal implementation, not an extensibility framework every user must learn.

Facts retain target/surface, value, evidence identity, and observation time where relevant. Each fact is known, unknown with a reason, or conflicted with its competing observations. Unsupported is an explicit capability result. It must not be disguised as false. Conditions with unknown inputs cannot silently pass; the consumer can present a conditional recommendation and investigate or ask only when that uncertainty changes a decision. Conflicting documentation remains conflicted even when one page seems more plausible.

Order matters: identify purpose and applicable policy; acquire the supported context; select decisions and relevant relations; evaluate options; present the concrete set; then prepare or apply through the authorized owner. Re-evaluate affected conclusions when their inputs change. Invocation should report its assessed scope and unresolved relationships, so a finite library does not imply a comprehensive review.

For the constructed public Python/plugin repository, `ci-security` selects mandatory-result reasoning and security-analysis suitability. The first evaluator distinguishes selected acceptance claims from names merely present in a ruleset. The second asks what Python and workflow content could be analyzed and what useful coverage is evidenced. `not-configured` default setup does not become “no scanner exists.” The adviser can recommend specific checks only after learning their behavior and repository fit. Agent assistance is not converted into an eligible independent approver.

For a new repository, planned facts replace unavailable observations and remain visibly planned. A defaults request selects recommended alternatives for the supplied context and presents one confirmable set. A focused request follows only consequential relations. An override fixes the selected preference while evaluators reconsider its consequences; the library does not restore its favorite value during the next run.

## User choice and unfamiliar settings

A policy decision is an input with its applicable source and owner. Library recommendations cannot create policy. An evaluator may establish that a choice fails a supplied policy or cannot satisfy the requested outcome; those are different findings. Ivan selected contextual judgment after the initial designs froze: honor informed choices, explain consequential tradeoffs, cite real policy constraints, and intervene for concrete active harm. The consumer must not encode harm as “deviates from recommended”; exposing privileged CI credentials to untrusted code is a concrete concern, while an intentional freeze is valid.

For example, a merge-availability evaluator receives whether a freeze is intended. No eligible approver can therefore produce a useful accidental-deadlock finding or an expected freeze observation. If purpose is unknown, it preserves that ambiguity. It does not universally optimize for merge liveness.

Unfamiliar settings follow an explicit unmodeled route. The agent researches and explains them, preserves native configuration, and states which conclusions lack library qualification. It can produce a bounded recommendation from adequate evidence; missing a record does not forbid a supported user choice. Direct application additionally needs a qualified owner route and its own authority. A reusable new decision enters maintained knowledge only after review and relevant behavior evidence. An ad hoc user exception stays local unless separately adopted as general guidance.

This gives the library a growing supported core while keeping arbitrary repository work possible. It also creates two evidence classes that the output must distinguish: evaluated decisions and advisory judgments outside the modeled support.

## Ownership, maintenance, and dependencies

Data owns selection, predicates, relation meanings, dependencies, and evaluator binding. Prose owns explanation and interpretation guidance. Evaluator code owns its named computation. None may silently redefine another: a semantic change to a predicate or evaluator invalidates dependent evidence even when the prose is unchanged. Source claims carry primary references and their scope; target observations carry a separate freshness record.

The first maintenance cost is deliberate authoring of a decision and its actual interactions. Adding an ordinary alternative can require data and explanation changes; adding a new interaction may require evaluator code. Both require positive, negative, and unknown-context cases. Sparse relationships are cheaper than an exhaustive graph but permit missing edges. Review must test omitted interactions, not merely validate present records.

Local files, source analysis, and configuration drafts are local-substitutable dependencies tested with fixture repositories. GitHub is true external. A narrow observation interface has a real CLI/API adapter and a replay adapter for the selected observation scope. Permission failure, pagination, unsupported responses, and contradictory readings must survive both. Replay establishes handling of those inputs, not actual provider behavior. Evaluators themselves can often run in-process without further adapters.

An existing configuration manager remains the writer. Records name affected surfaces; discovered ownership determines whether preparation targets infrastructure source, an App-owned file, or an operation-specific actuator. The library does not become desired-state authority or a competing reconciler. Versionkeeping, Mergecraft, Rolecasting, security review, component governance, and release owners retain their existing work.

The selected alpha must cover creation, assessment, defaults adoption, focused changes, and project-specific CI hardening end to end, including authorized application through existing tools. Each supported change has maintained operation instructions: resolve its owner, prepare the concrete native delta, check actual authority and current preconditions, use the existing tool, and verify the selected result. The library references that procedure rather than executing arbitrary record-supplied commands. Applied, unchanged, and unknown effects remain distinct. A timed-out write is not safely retryable merely because an evaluator likes the desired value. Recovery follows the operation contract and current state; records describe dependencies without promising a universal transaction.

The source could be repo-carried Agent Equipment with a discoverable Skill front end and internal helpers. A new Plugin or another interface remains a packaging decision. Canonical source, projections, local installation, fresh invocation, and hosted enforcement require separate evidence. Supported qualification contexts and deployment targets remain pending; an advice-only alpha no longer satisfies the selected capability scope.

## Verification and strongest tradeoff

Test the adviser through its interface using the shared cases. Exercise all five selected workflows in supported contexts, including authorized application, no-op, and recovery branches. Verify fresh local discovery and invocation separately from the hosted outcomes claimed. Mutate one premise at a time: producer identity, event eligibility, skipped versus missing results, intended freeze, inherited rule, source revision, or writer ownership. Verify both the recommendation and its stated limits. Include source-pinned/admission-permissive and enabled-scanner/incomplete-coverage cases to catch collapsed claims. Contradictory documentation must not be resolved by retrieval order. Correcting a consumed procedure should invalidate its dependent conclusions while preserving unrelated choices.

Compare this variant with my first proposal using identical knowledge and unfamiliar tasks. Measure consequential omissions, false prohibitions, useful explanations, authoring work, and changes needed after one procedure correction. Withhold an interaction hint to test discovery beyond known edges. A second test introduces a novel native setting: determine whether the library produces a useful qualified answer or forces unnecessary schema work.

This variant is worthwhile if explicit relationships and evaluators repeatedly prevent omissions across varied repositories. It loses if maintaining an incomplete model costs more than the repeated errors it prevents, or if users receive false confidence because an answer passed the modeled checks. The initial proposal favors immediate flexibility and native-owner composition; this one spends maintenance effort to make supported reasoning more repeatable. Neither a valid record nor a persuasive explanation is behavioral qualification.

## Actual exposure

This variant remains isolated from peer architecture outputs. I verified my initial report at SHA-256 `8c09acfa0b893010cfd1ba8284506381074b15546c95feae452f6b244904a487` before contrast. I reread its first 85 lines and inspected Git status, which exposed the existing untracked research `architecture/` directory name only. No contents from that directory were read.

The earlier lane's recorded research, source, skill, and ambient-metadata exposures remain this variant's inputs. I opened no new research source, memory file, live documentation, provider response, installed equipment, or peer report. No external probe, delegation, repository/configuration mutation, or executable experiment occurred. The only authored file in this additional pass is this report. Its structure, consumer, behavior, examples, and tests are proposals.

Later exposure: while drafting this variant, I verified and read `operator-choices-1.json` at SHA-256 `7faee4d71242a99552752e04c5b6e80bc481dad27f97c6143007d7e901fc41c9`. It records Ivan's direct end-to-end workflow and contextual-judgment choices, not live-change authority. I updated this variant accordingly and left my initial report frozen. No peer design accompanied those choices.
