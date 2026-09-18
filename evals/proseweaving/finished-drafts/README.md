# Finished-draft application evidence

The finished-draft procedure checks and edits an existing draft or batch while
preserving supported substance, useful first person, required form, and protected
text. Six qualitative application cases exercise correction, conversation and
document register, batch variation, protected spans, an unchanged draft, and a
material evidence gap. A separate grader passed all 18 expectations.

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

## Retained observations

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
These are one-run development observations, with no current
comparative baseline or statistical reliability claim.

## Discovery and invalidation

The twelve skill-local trigger inputs and the shared routing definition are
authored coverage. Automatic discovery remains unqualified: the preparation's
CLI probe failed during initialization, and automatic approval review rejected
the outside-sandbox retry because its service destination and data boundary
were not bound. No retry, fallback probe, or external model call followed.
Explicit application does not establish discovery, installation, release
eligibility, or runtime enforcement.

Changes to a delivered runtime file, prompt, fixture, or delivery method require
new affected application observations. Changes to expectations require grading
review and regrading against the resulting corpus. Metadata-only changes can
reuse observations only after their runtime and case dependencies are compared;
the retained records keep their original source provenance.
