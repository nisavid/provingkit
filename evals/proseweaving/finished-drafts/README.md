# Finished-draft procedure evidence

The finished-draft procedure checks and edits an existing draft or batch while
preserving supported substance, useful first person, required form, and protected
text. Six qualitative application cases exercise correction, conversation and
document register, batch variation, protected spans, an unchanged draft, and a
material evidence gap. Three runs per case passed all 54 expectation checks
under separate grading. Twelve project-local discovery observations also passed:
five positives and seven negatives.

## Source and procedure consumption

This integration consumes `writing-for-people` and its conditional references
from reviewed producer revision `9f5a0ca40e8bc93869d9f4490e700f1d089505f2`.
The integrated producer checkpoint is
`256887fa3381fdd9335f4d50fdb8dba7ff7812ba`; its metadata correction changes no
runtime skill or corpus bytes. I compared those inputs before carrying the six
observations forward. Their retained record still names the original producer.
The producer's [source-placement record](../writing-register/source-placement.md)
and [evidence report](../writing-register/README.md) define the generic writing
boundary. `editing-finished-drafts` calls that skill for the general register,
evidence rules, and ordinary edit pass; it owns verification and repair of a
supplied finished draft. The topology and literal sibling link make that
consumption discoverable without a reciprocal dependency.

The ten prepared skill files are unchanged from preparation manifest
`73ac8b5bb6c6a1a9ff82f758874231aa7597dd12aed76e36f1301dca250565a4`.
The preparation's earlier application results used an older generic-writing
dependency. These six runs exercise the integrated runtime bundle instead.

## Application observations

[`application.json`](application.json) retains the exact delivered bundle,
source digests, raw prompts and fixtures, packet encoding, response paths, and
response digests. Reconstruct each packet from its prefix followed by the JSON
object with ordered keys `prompt`, `fixture`, and `candidate_bundle`, using the
recorded encoding. The bundle comes from the owning validator's declared-call
closure and contains five runtime files, without evaluator material.

Each case used a fresh native Codex subagent without task history, with inherited
model and reasoning settings and one local packet read. The no-more-tools rule
was an instruction, not enforced filesystem or tool isolation. Provider and
system instructions, installed skill metadata, and ambient harness guidance
remained available. No independent provider trace, model attestation, timing, or
token accounting was exported. The six final messages are retained with one
trailing newline in `responses/`.

[`grading.json`](grading.json) retains the separate grader's results and the
later mapping of opaque randomized output IDs to cases. The grader received
prompts, fixtures, expectations, and responses, without candidate source or
condition labels; [`grading-input.json`](grading-input.json) retains that input.
These original six observations and their grading remain unchanged.

[`repetitions.json`](repetitions.json) adds two fresh runs per case and counts
each original observation as run one. I verified that every delivered runtime
file, prompt, fixture, packet prefix, JSON encoding, and packet digest still
matches the original application record and current source before reuse. The
earlier preparation runs used a different generic-writing dependency and do not
count toward these repetitions.

The twelve added outputs use the same packet contents and native route, with
the ambient-context and enforcement limits above. Their separate grader received
only the randomized opaque output IDs, prompts, fixtures, expectations, and
responses in [`repetition-grading-input.json`](repetition-grading-input.json).
[`repetition-grading.json`](repetition-grading.json) retains all 36 new results
and the later mapping to cases and repetitions. Both graders reported no rubric
concerns. No current comparative baseline or statistical reliability is claimed.

[`acceptance.json`](acceptance.json) applies the accepted
[#29 thresholds](https://github.com/nisavid/provingkit/issues/29#issuecomment-5524457529)
using the severities already authored in the corpus: every safety expectation
must pass all three runs, and every quality expectation must pass at least two.
All 27 safety and all 27 quality checks passed. The record is a bounded corpus
summary; it does not implement the release eval receipt or establish PR
readiness. The native route inherited model settings without exporting an
independent model identifier or immutable served-model attestation.

## Discovery observations

The twelve skill-local trigger inputs and the shared routing definition are
authored coverage. [`discovery.json`](discovery.json) retains a sanitized summary
of the separately approved project-local discovery run against the unchanged
skill and trigger corpus at `e39566188c8ae792aad977bdf76e22147e52b7aa`. It binds
the private source summaries and trace records by digest and includes every
query. Each of the five positives had a successful read of its exact temporary
marker-only skill body and the expected final marker. Each of the seven
negatives returned the exact no-trigger response without a tool action.
Independent trace review confirmed all twelve results under the frozen plan.
Each query ran once; these are separate from the three application repetitions.

The positive reads are observed command executions, not native skill-invocation
events or application evidence. All traces report shortened descriptions in the
ambient skill catalog; complete description exposure is not established. The
launcher inherited plain-pipe stdin without sending input through the control
surface, but stdin was not independently captured or explicitly closed. The
command arguments therefore do not establish complete input provenance. The
requested model was `gpt-6-astra` at `xhigh`; no immutable served model identity
was established. State-database fallback and some shell-snapshot cleanup
warnings occurred, but all commands completed without unexpected model tool
actions. These observations do not establish isolated context, installed-plugin
behavior, live workflow behavior, or release qualification.

The preparation's earlier CLI probe failed during initialization, and automatic
approval review rejected its outside-sandbox retry because the service
destination and data boundary were not bound. That preparation did not retry
or run a fallback. The later observations above used a separately approved plan;
the earlier failed probe remains historical evidence.

## Reuse and invalidation

Changes to a delivered runtime file, prompt, fixture, or delivery method require
new affected application observations. Changes to expectations require grading
review and regrading against the resulting corpus. Metadata-only changes can
reuse observations only after their runtime and case dependencies are compared;
the retained records keep their original source provenance.

Apply the three-run thresholds to each current case using its authored
expectation severities; report missing coverage or severity decisions instead
of inventing them. Reuse a run only after comparing its delivered dependencies,
and preserve different-input runs as history. Discovery must be evaluated
separately under an authorized route and scored against its frozen trigger
inputs. A changed skill name, description, trigger corpus, discovery plan, or
relevant harness context invalidates the affected discovery observations.
