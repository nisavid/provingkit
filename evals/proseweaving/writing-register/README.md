# Check medium and register guidance

These development checks exercise the procedure in
`plugins/proseweaving/skills/writing-for-people/SKILL.md` for
[the source split](https://github.com/nisavid/provingkit/issues/26). They
cover publication, documentation, conversation, review replies, useful
first-person openings, and evidence claims. [Source placement](source-placement.md)
records each contribution's maintained owner and the downstream invocation.

## Application checks

The twelve cases come from the skill's `evals/evals.json`. Each executor receives
the raw task, its synthetic fixture, and the candidate skill plus routed
references. Expectations and expected output stay with the separate grader.
The explicitly delivered bundle exercises application of the instructions;
it does not test native discovery.

Each case ran once in a fresh Codex CLI session requesting `gpt-6-astra` with
`xhigh` reasoning, an ephemeral session, and a read-only worker sandbox.
The executor was instructed to return prose without tools. The retained traces
show completed responses and no task-tool events. This observed behavior does
not establish enforced tool isolation. The standard CLI used the operator's
existing ChatGPT login; no credential was read, copied, or recorded.

`--ignore-user-config` did not remove host-global writing instructions and skill
metadata. No isolated baseline comparison is available. Provider-owned context
is opaque, and the requested model selector is not a returned immutable model
identity. These are qualitative development observations, not evidence of
causal improvement, native plugin behavior, cross-harness compatibility, or
preview/release qualification. The preview panel remains separately owned.

- [Iteration 1](application-iteration-1.json) retains the original candidate,
  prompts, fixtures, responses, traces, and independent grading: 33 of 36
  expectations passed. Its [adjudication](iteration-1-adjudication.json) records
  an audience-order correction and two unnecessarily prescriptive rubric rules.
- [Iteration 2](application-iteration-2.json) reruns all twelve cases after that
  source change. Its frozen rubric grades 35 of 36 expectations as passing.
  The [second adjudication](iteration-2-adjudication.json) replaces the recurring
  paragraph-placement constraint with semantic reader orientation. It preserves
  the failing grade; only the affected criterion needs regrading because no
  executor input changed.

The [final grading](final-grading.json) passes all 36 expectations across the
twelve cases. It binds the final corpus, regrades only the changed criterion,
and retains the unchanged grades with their provenance.

The shared CLI installation changed from 0.154.0 to 0.155.0 between iterations.
The second record corrects its earlier version declaration using the later
version and binary observation. It makes no controlled comparison across
iterations. Timings and token usage are observations, not comparative metrics.

Each application record stores its candidate bundle once. Reconstruct an input
by forming the ordered JSON object `prompt`, `fixture`, `candidate_bundle`,
using the recorded indentation and Unicode setting, and surrounding it with
the recorded prefix, two newlines, and final newline. Its SHA-256 must match
`submitted_prompt_sha256`. The response digests cover the exact retained text.
Original grading stays beside the rubric used for that run. Changes to the
candidate, prompt, fixture, or delivered dependencies invalidate affected
application runs; a rubric-only correction invalidates the affected grade.

## Discovery checks

[The seven queries](trigger-evals.json) exercise the skill's name and
description through the maintained `adapting-skill-creator-to-harnesses`
Codex sentinel procedure. [The record](discovery.json) binds that procedure's
source digests, probe bodies, queries, outcomes, and traces. It records five
matching writing requests and two non-writing requests, all classified as
expected. The unique sentinel is supplied only in the temporary skill body.
Local paths are normalized in the public trace projection; original trace
digests are retained.

Use that maintained procedure for another discovery run, with a fresh probe
workspace and a concretely authorized service, account, and public dataset.
These probes used Codex CLI 0.154.0 with its existing ChatGPT authentication and
the public synthetic queries here. They establish discovery for the recorded
name and description only. A body change requires fresh application evidence;
a name or description change also invalidates these discovery results.
