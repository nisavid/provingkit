# Prepare optional review decisions from existing questions

I recommend comparing a small, source-linked view of unresolved review questions with ordinary coordinator planning at the next discretionary review decision. Start with deterministic preparation and ordinary reasoning. Keep Jev as a challenger for routing supplied questions only if that decision remains costly after preparation.

This is a proposal for scope selection, not an experiment selection or behavior assignment. Required reviews, selected review focuses, and their revision-specific completion criteria remain unchanged.

## What makes this the strongest candidate

The opportunity is the coordinator’s decision: **“What additional review, if any, could change the next decision?”** It differs from checking whether a task is complete or detecting suspicious repetition.

A plausible saving is avoiding an optional broad reread when the unresolved issue instead needs one cited passage, a missing observation, or no further work. Another is directing an already contemplated specialist review toward the actual uncertainty. Successful work can benefit; a prior failure is unnecessary.

The public portfolio already suggests focused review allocation, but leaves question generation and context production unresolved. I narrow that proposal to **questions already written during ordinary work**. The candidate does not commission a new reviewer to discover its own routing inputs, construct a new requirements ledger, or repeatedly inspect tool history.

The retained research packets contain examples of reusable material: explicit questions, cited evidence, review scopes, candidate identities, and limitations. These are available artifacts, although their existence does not prove that an ordinary coordinator uses them efficiently or performs an avoidable additional review. The [workflow packet](https://github.com/nisavid/provingkit/blob/ca2c510c304cb7fd3216a1f2b0ac02645dceea12/docs/superpowers/research/evidence/jev-axi-workflow-opportunities-2026-10-05/README.md) establishes this distinction.

My recommendation is therefore a testable design judgment: preparing existing questions has a more bounded production problem than generating alternative debugging observations or interpreting every tool event.

## Consumer, workflow, and proposed assistance

The consumer is the coordinator preparing an optional review dispatch for an ordinary documentation or research change. Ivan remains the consumer of the resulting scope recommendation.

The ordinary workflow is to read the current task, candidate, review findings, and evidence; determine what remains uncertain; and decide whether another reviewer would help. The proposed aid appears **when that dispatch decision is already being made**, not after every tool call or at every response boundary.

It presents only existing material:

| Supplied material | Producer | What preparation can do |
| --- | --- | --- |
| Current unresolved question and decision it affects | Author or coordinator during ordinary work | Preserve the wording and source link |
| Relevant claim and cited passages | Existing document and evidence artifacts | Retrieve the named passages; expose unavailable references |
| Prior review scope and reviewed revision | Existing review record | Show identity matches and changes without declaring semantic validity |
| Required reviews and selected focuses | Current task and governing policy, interpreted by the coordinator | Keep them visible and separate from discretionary additions |

Ordinary coordinator judgment then chooses among four meaningful next actions:

- Ask an optional reviewer the supplied question.
- Read or retrieve the identified evidence directly.
- Obtain a missing observation through its separately authorized workflow.
- Request no additional review.

These are decision alternatives, not proposed automatic labels controlling execution. Deterministic preparation cannot establish that an arbitrary question is answered, that a review covers a changed claim, or that a missing observation is unnecessary.

The expected benefit is less reconstruction and fewer misdirected optional dispatches. Both remain unmeasured. Until an actual activity is observed and removed, this is an addition—not a replacement of review work.

## An illustrative decision

Consider the published [publication-observation result](https://github.com/nisavid/provingkit/blob/ca2c510c304cb7fd3216a1f2b0ac02645dceea12/docs/superpowers/research/evidence/jev-axi-publication-observation-2026-10-05/results.md). It states that the observation retained 22 artifacts, acquired no current chat events, and ended at a verification gate; the later successful publication was outside the observation.

Suppose a coordinator has two optional questions before publishing a synthesis:

1. “Does this result establish publication during the observation?”
2. “Would the recording route capture current requests in another invocation?”

This is an authored decision example, not a reconstruction of an observed dispatch.

For the first question, the existing result supplies the answer directly: no. The coordinator can correct an overbroad synthesis claim without asking an extra reviewer to rediscover that fact.

For the second, another source reviewer cannot establish future recording behavior from the retained result. The decision is whether to propose verification of a current recording route, under separate authority. An optional broad review would not supply that missing observation.

Now change the example: the synthesis accurately states those limitations, but its conclusion depends on whether two independently supplied evidence passages support a broader inference. That may justify a focused optional review. The preparation should expose the actual inference and passages, not issue a generic “high risk” notice.

The aid changes **which work is worth commissioning**. Ordinary planning may reach exactly the same decisions more cheaply; that outcome defeats the addition.

## Serious rivals

### Ordinary planning with no added view

This is the strongest rival and my default outside the proposed comparison. A coordinator who just authored the synthesis may already know the question, evidence, and answer. Reformatting that knowledge could add retrieval, tokens, and maintenance without saving anything.

The candidate becomes more plausible when questions originated in different existing artifacts or when the coordinator is returning after a handoff. It becomes less plausible for a small change with one obvious uncertainty. These are eligibility hypotheses, not measured thresholds.

### Jev routing over supplied questions

Jev could classify whether a supplied question is answerable from the included evidence, requires additional observation, or warrants specialist interpretation. It could also select among already described reviewer focuses. Its structured-choice and supplied-state mechanics support that shape; they do not establish correctness or usefulness here. [TypeSafe Choice documentation](https://docs.typesafe.ai/primitives/choice.md), [State documentation](https://docs.typesafe.ai/concepts/state.md).

A serious Jev comparison must give ordinary reasoning the same prepared evidence. Comparing Jev with a poorly informed baseline would credit context preparation to the classifier.

There is also direct caution against treating an advisory suggestion as harmless. TypeSafe’s skill-suggestion cookbook reports a two-stage selector over 182 skills, evaluated on 488 authored requests using `jev-1.12` and `claude-haiku-4-5-20251001`. Among 315 covered requests, it reports 37 corrected selections and seven previously correct selections spoiled by suggestions. These are vendor-reported, single-turn skill-selection results, not review-allocation evidence or population estimates. They establish a relevant design concern: a recommendation can change an otherwise correct consumer decision. [Skill-suggestion cookbook](https://docs.typesafe.ai/cookbooks/skill_suggestion.md).

Under the accepted bar, average improvement does not excuse added false steering on agreed critical cases. I would not lead with Jev where a coordinator is choosing among a few questions it already understands.

### Delay optional assessment until the candidate is ready for review

Coalescing optional assessment at an existing review boundary could avoid judging intermediate work repeatedly. Anthropic reports moving evaluation from each sprint to the end of a build as model capabilities changed, while retaining evaluation where it still helped. That supports investigating timing, not importing its outcome into this repository. [Anthropic’s harness report](https://www.anthropic.com/engineering/harness-design-long-running-apps).

The weakness is that some questions determine what should be built or researched next. Waiting until the end can make correction more expensive. The proposed question-based decision handles that distinction more directly: assess when the answer can change the next action, rather than using elapsed time or tool count.

## Why repetition detection ranks lower

The [resumption study](https://github.com/nisavid/provingkit/blob/ca2c510c304cb7fd3216a1f2b0ac02645dceea12/docs/superpowers/research/evidence/jev-axi-resumption-study-2026-10-06/results.md) positively supports recovery of a settled review choice and continuation of unfinished preparation. It also reports reasons to distinguish fresh checks and changed dependencies from wasted reconstruction. Repeated reads are therefore an ambiguous signal in precisely the available material.

A useful loop intervention would need to compare an intended learning goal, previous observations, changed conditions, and available next observations. Generating those alternatives may require the same debugging judgment the intervention purportedly saves. Counting repeated commands avoids that production cost but loses the decisive meaning: an unchanged retry, a controlled reproducibility check, and a check after a relevant change can look similar.

I would retain ordinary debugging and explicit dependency checks for that branch. This does not claim that unproductive loops are rare or that supervision cannot help. It ranks the next comparison by tractability and plausible net value.

## A minimal comparison that could defeat the recommendation

Use a future, independently authorized research-publication task **only when ordinary preparation already exposes a discretionary review decision**. Do not create an extra review merely to remove it.

Compare ordinary planning with the proposed source-linked preparation. Preserve the same required reviews, candidate scope, evidence access, and available discretionary actions. A Jev arm is justified only if the remaining selection work is substantial enough to plausibly replace; it must use the same supplied questions and evidence.

The distinguishing observations are concrete:

- Which optional action the coordinator chooses and whether it resolves the stated uncertainty.
- Whether a reviewer discovers that the requested answer was already explicit, or that the necessary evidence was unavailable.
- Preparation and coordinator effort, reviewer work, reopens, corrections, and unnecessary questions.
- Whether useful concerns are overlooked or postponed, and whether final quality changes.

Include an already-clear question, a genuine semantic ambiguity, missing evidence that review cannot manufacture, changed evidence, and a legitimate repeat check. These can shape later qualification cases; authored examples alone cannot demonstrate native benefit.

**Defeat the candidate** if preparation costs at least the reconstruction it avoids, the ordinary coordinator already makes the same choice with less work, the aid induces a needless dispatch or question, or a narrowed focus causes a material concern to be missed. No additional review is a valid successful decision. A single native comparison can expose these mechanisms; it cannot establish a general reliability rate.

## Costs and the next decision

The author owns the ordinary cost of writing questions and citations. Any extra extraction, reconciliation, or question rewriting belongs to the aid. The coordinator owns evidence selection, freshness interpretation, and dispatch decisions. Reviewers own investigation and rework; Ivan’s checking and interruptions remain separate costs. Integration ownership includes retrieval, retention, refresh, failures, and maintenance.

Count model attempts, context, cache behavior, latency, money, service failures, and downstream work through completion. Shared evidence preparation may overlap completion or continuity assistance: charge it once in combined use, while retaining standalone and marginal costs. All comparative savings are currently unknown.

The coordinator should next resolve three specific premises:

1. **Is there a discretionary review decision in the proposed task?** If every contemplated review is required, this allocation comparison has no removable dispatch. Preserve those reviews and choose another opportunity.
2. **Do useful questions and citations already exist before dispatch?** If yes, test preparation. If constructing them requires a fresh semantic review, include that cost and prefer ordinary planning unless another benefit justifies it.
3. **Does preparation leave costly selection ambiguity?** If no, omit Jev. If yes, consider Jev against ordinary reasoning on identical inputs, with no new authority.

This proposal consumes the existing `handling-sys1-incidents` comparison procedure unchanged. It introduces no installed convention. Any later accepted comparison should invoke that procedure; a reusable method correction would require its own reviewed capture and consumer pointers.

## Source identity and limits

All 15 dispatched public inputs matched their frozen SHA-256 identities before and after inspection at revision `ca2c510c304cb7fd3216a1f2b0ac02645dceea12`. The acceptance document and comparison procedure also matched that revision. The consumed comparison-contract digest is `9f876cd27c4bd6fe82d56feabc6e31e05d029d7cac18f9651194218e2e1aa981`.

Public TypeSafe documentation was fetched on October 7, 2026; the skill-suggestion page digest was `c59bf591db3d45e20b90a93a4526775e5188c479c6366b9a4267cb37ab51fc90`. I inspected no sibling findings or private histories and performed no experiments, Jev requests, writes, or subdelegation. Requested Astra/high settings are not independent effective-model attestation. Earlier bounded no-advance dispositions remain intact; this handback supplies a different decision to investigate.