# Preserve Receipts through source landing

This throwaway comparison asks whether an ordinary Receipt can qualify the
actual landed Candidate without rewriting the Receipt solely because Git
history changed. It supplies disposable Git repositories, constructed records,
an unchanged published adapter, and a proposed local consumer. It does not run
models, change repository policy, install a consumer, or qualify production.

The authorized increment is issue [#131](https://github.com/nisavid/provingkit/issues/131).
The accepted starting evidence is
[the constraints report](../../superpowers/research/2026-09-18-receipt-landing-constraints.md).
Strategy adoption belongs to [#132](https://github.com/nisavid/provingkit/issues/132).

## Interfaces and acceptance

The executable comparison observes real Git landing operations, the frozen
ordinary Receipt adapter, and a proposed consumer given the original comparison,
a reviewed landing context, and an independently supplied landing event. Fixture
expectations are literal acceptance outcomes, checked against those interfaces.
This is the executable evidence specifically required by #131, rather than a
production test suite or a measurement of model behavior.

Acceptance includes unchanged inputs across rewrites; changed bytes, modes,
dependencies, mappings, and processing; missing or wrong evidence and coverage;
retained failed observations and thresholds; original comparison retention;
actual-final-commit checking; base movement; and provenance after branch deletion.

The adapter is extracted without edits from commit
`24c2d712a0be6a95958713ec80c7e06a89abdc6c`. Its five processing files also match
the published procedure at `0797623a3d8dfafb600f0cb1009e4f6d4538bb30`.
The older writer processor `957550119aca20a31a26f4e5f9a3f09a2d6bd148` is a distinct
dependency. These fixtures do not establish compatibility or migration for it.

Run from this checkout, with Python, Git, `jsonschema`, and network access to
the public repository available:

```sh
python docs/prototypes/receipt-landing-131/run.py --fetch-processor
```

`--fetch-processor` fetches the retained public `refs/pull/116/head` from
`https://github.com/nisavid/provingkit.git` into a newly initialized temporary
repository. It verifies that `24c2d712a0be6a95958713ec80c7e06a89abdc6c` resolves to
that full commit identity and is an ancestor of the fetched ref before loading
any adapter files. The summary records the fetched head and verified processor.
The prototype checkout neither needs nor receives that ref's objects. If the
ref is unavailable or no longer contains P24, acquisition fails; restore an
owner-approved retained source before rerunning. It never substitutes another
processor. An offline rerun may omit the flag only when the checkout already
contains the verified P24 commit.

All Git mutations occur in newly created temporary directories. No source
branch, installed projection, hosted check, or shared owner checkout is changed.
The harness prints the artifact directory so its actual commits can be inspected.

To regenerate the committed measurement and its standalone replay:

```sh
python docs/prototypes/receipt-landing-131/run.py --fetch-processor --output docs/prototypes/receipt-landing-131/results.json
python docs/prototypes/receipt-landing-131/build_demo.py
```

Open [the replay](index.html) to explore individual observations or the five
walkthroughs. It embeds measured results and never invents a verdict for a new
combination. Its navigation is an in-memory model; the Git comparison lives in
Python. The HTML shell and consumer are both prototype code, kept off `main`.

## Practical result

I recommend taking explicit input correspondence with retained provenance into
the strategy decision while retaining squash as the landing policy. The extra
work is a consumer contract, durable evidence availability, and a real final-commit
caller. Changing the landing operation avoids the new correspondence rule but
does not supply that caller or preserve the original comparison by itself.

| Operation exercised locally | Unchanged ordinary adapter | Proposed correspondence | Proposed ancestry route |
| --- | --- | --- | --- |
| Squash | Fails | Passes | Fails |
| Forced rebase with a changed committer date | Fails | Passes | Fails |
| Merge commit | Passes | Passes | Passes |
| Fast-forward with an unchanged target | Passes | Passes | Passes |
| Fast-forward after target divergence | No landing | No candidate checked | No candidate checked |

The rebase fixture deliberately changes the committer date to ensure Git creates
different commit identities. It does not infer how a particular hosted rebase
implementation constructs its commits. The strategies agree on the negative
controls: bound source, Git mode, reference, topology, mapping, or prepared
processing changes; incomplete cases, repetitions, or triggers; incorrect
snapshots; threshold failures; wrong source or skill; rewritten Receipt bytes;
unsupported event operations; and a wrong final commit all fail.

Added and deleted declared dependencies have separate cases. Ownership transfer
selects both the former and new consumer. Removed skills remain unsupported
required coverage. Malformed corpora fail selection; valid corpora with unresolved
expectation classifications fail descriptor resolution. Malformed committed
Receipts fail parsing or schema validation. Duplicate repetitions, missing
expectations, and wrong severity fail historical validation. These cases assert
the exact rejection reason and stage, plus affected consumers or diagnostic
codes where relevant. Selected negative fixtures bind the intentionally invalid
Receipt bytes in their constructed handoff so an earlier digest mismatch cannot
masquerade as evidence of parsing, coverage, or lineage validation.

The constructed corpus has two cases, three repetitions per case, and two
triggers. Each case retains one failed quality observation and passes quality
at two of three; safety remains three of three. Removing a case or a repetition
fails coverage. One additional quality failure or one safety failure fails the
unchanged policy. Reconciled fixtures retain original records, use distinct
evaluated and processing commits, and reject an altered processing identity.
No historical measurement from another owner is imported as a new run.

The changed-rubric fixtures retain six constructed original execution records at
the original source revision. Their original grading contains four failed quality
observations. A separate constructed regrading record applies the revised rubric
to those same six responses, retains two current failed observations, and carries
six references to original grading plus six adjudication references. The source
with the revised rubric has a different commit identity; original execution,
corpus, response, delivered-input, and configured model evidence remain bound to
the originals. No application is executed again. Squash and merge pass with the
complete lineage. Removing either prior grading or adjudication from the landed
Receipt fails specifically at the changed-rubric lineage check. The measurement
includes both constructed raw records and the public Receipt for inspection.

The full [measurement](results.json) contains 47 landing/check scenarios, four
fresh-clone observations, a genuine Receipt-only comparison, and the divergent
fast-forward refusal. It records concrete commits, adapter results, expected
outcomes, processing file hashes, prototype Python file hashes, and the retained
source bundle and constructed-original-record digests.

## Consumer contract under discussion

`consumer.check` receives an independently retained reviewed context and an
independently supplied landing event. The context binds the original base,
reviewed target, Receipt raw bytes, and processing revision with all five
processing input identities. The event supplies the actual landing commit,
observed target before landing, and operation. A copy of the context is committed
with the source and Receipts; that copy cannot replace the independent handoff.
The context never contains its own containing-commit hash, avoiding a self-reference.

The consumer checks the event commit, expected target, ancestry of the original
base and target, and committed context. It discovers affected skills across the
entire original base-to-final comparison. For each selected skill it reads the
Receipt from the actual final Git tree, matches its reviewed bytes and processor,
and asks the unchanged adapter to validate the historical evaluated source.
It then compares the complete landed path/byte/mode closure and authoritative
descriptor to the recorded evaluated closure. Only this additional consumer,
not the unchanged adapter, accepts rewritten history.

The stable identity includes the full skill descriptor, complete input map of
paths, bytes, and Git modes, and processing input identities. Commit revisions
remain provenance. A matching digest is only a compact identity; it is not a
substitute for historical validation, complete selection, source availability,
or a trusted caller. The ancestry variant adds the evaluated-source ancestor
requirement and invokes the ordinary adapter against the final commit.

A moved target requires an explicit refreshed context. An unrelated target
change then passes correspondence. A newly affected second skill fails because
the original comparison selects it and the reviewed Receipt set does not cover
it. A genuine Receipt-only follow-up returns `not-required` through the ordinary
adapter when supplied only its immediate range; the proposed consumer rejects
that range because it differs from the independently retained original base.

## Evidence availability and limits

Fresh clones use `--no-local --single-branch` after deleting the disposable source
branch. A clone of squashed `main` lacks the evaluated commit and fails. Explicitly
fetching a retained evidence reference or importing its Git bundle restores the
correspondence check. A clone of merged ancestry retains the source automatically.
The reference and bundle are two delivery options for the same strategy, not a
third identity model. The fixture proves local recovery, not a hosted retention
service, durable retention promise, or retention of real private model records.

The current repository configuration, observed on September 18, 2026, permits
squash and rebase and disables merge commits. Active ruleset `22036701` requires
the PR route, allows only squash/rebase, and requires current-base status checks.
An ancestry-preserving merge therefore needs a separate policy decision. The
fast-forward fixture is a local alternative, not an available hosted PR route.

The independent caller is constructed here. Authentication of its context and
event, protected execution, event delivery, required checks, pre-merge prediction,
post-merge action, and race handling at the forge remain implementation and
security-review work. Local automatic checking proves the consumer examines the
supplied actual Git commit; no hosted automation is implemented or qualified.
The current consumer uses the adapter's private `_freeze` helper; adoption needs
a reviewed public closure-comparison interface. Malformed arbitrary request
objects, unlisted Git operations, conflicts, waivers, release evidence, and
cross-version processor migration are outside the supported prototype inputs.

## Decision and procedure capture

I [accepted taking correspondence and retention into #132](https://github.com/nisavid/provingkit/issues/131#issuecomment-5733715226).
That prototype reaction does not adopt the strategy or authorize migration.
Closing #131 requires independent review of the final candidate and coordination
review of that evidence and the recorded response.

If #132 selects correspondence, the proposed maintained source is the existing
ordinary Receipt contract and adapter owned by #33: the public closure interface,
caller handoff, original comparison, evidence retention, and final-commit check
must be documented and validated together. Downstream consumers, including the
owner-coordinated PR #84, #116, #126, and #127 paths, must explicitly load that
reviewed procedure revision before dependent migration or landing. The older
writer processor needs its own compatibility evidence; publication of a newer
processor does not itself make historical use stale. No downstream instruction,
installed skill, owner reservation, or shared source is changed by this proposal.

If #132 selects ancestry preservation, the maintained procedure still needs the
original comparison and independent final-commit caller, plus the deliberately
changed hosted landing policy. The same owner-coordinated adoption gate applies.
This proposal uses `capturing-agent-procedures`; it does not install unsettled
behavior in shared instructions.

The frozen candidate should be reviewed for (1) issue coverage and truthful limits,
(2) the correspondence and provenance contract, (3) independence and sensitivity
of the executable cases, and (4) source/derived-artifact consistency and repository
standards. Review must name the candidate commit and these evidence dependencies.
