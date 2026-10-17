# CI proposals and changed-producer source exercises

The repository-configuration source exercises now include Python hardening, private TypeScript CI, and repair of a changed required-result producer. The changed-producer proposal met all six expectations. The two CI proposals needed corrections, which passed fresh independent review, adjudication, and final verification as assisted successors. Their original failures remain recorded.

These are cases 4, 5, and 8 of the [frozen corpus](https://github.com/nisavid/provingkit/blob/e50777edc12c17f5c5f1c4ede245c2a45064476a/evals/mergecraft/skills/configuring-repositories/evals.json), supporting the source-behavior phase of the [alpha qualification contract](../specs/2026-10-06-repository-configuration-alpha/qualification.md). They establish no installed discovery, executed workflow, usable CodeQL coverage, account capacity, or live merge enforcement.

## Original executions and grades

Each case used two fresh isolated Codex CLI 0.163.0 sessions requesting `gpt-daybreak-blue-latest` at high effort. Both conditions received identical tasks, synthetic fixtures, primary documentation, general operator guidance, and tool restrictions. The source condition additionally received the complete six-file `configuring-repositories` Skill directory at commit `e50777edc12c17f5c5f1c4ede245c2a45064476a`. Neither performer received its rubric or condition label. The control received no supplied configuring-repositories Skill; this does not establish globally absent ambient guidance.

The coordinator materialized the six original Markdown responses at fixed paths, read back their exact bytes, and parsed their YAML snippets for syntax. It ran none of their contents and followed no model-selected output path. A fresh independent grader received the original tasks, all 40 expectation judgments, the original responses under opaque identifiers, and attributed execution and materialization evidence. A separate adjudicator resolved all ten resulting findings and additional concerns.

| Case | Original source response | Original control | Outcome |
| --- | --- | --- | --- |
| Python/plugin hardening | 6/7 | 7/7 | Two unsupported cache inputs corrected in a distinct assisted successor. |
| Private TypeScript hardening | 6/7 | 5/7 | Competing-usage admission and aggregate-run claims corrected in a distinct assisted successor. |
| Changed producer and skipped/missing result | 6/6 | 5/6 | Source proposal accepted after final binding verification. |

The original grade remains 35/40 judgments across the six outputs. It is not rewritten to reflect later corrections, and this small comparison establishes no general relative benefit from the Skill.

An earlier Python source attempt reached its 180-second response deadline without completing a final proposal. Its partial protocol and process closure remain retained privately. Before any semantic grading or performer feedback, both conditions for the two CI cases were prospectively given a 300-second response deadline within the existing finite execution envelope. The final six responses completed. The incomplete attempt is not a seventh scored output or a successful execution.

## Corrections and retained control concerns

The Python source used `cache: false` in two `actions/setup-python` steps. The pinned action treats a nonempty cache input as a package-manager selector; `false` is not a supported selector. The correction removes exactly those two lines. The supplied [action metadata](https://github.com/actions/setup-python/blob/a26af69be951a213d495a4c3e4e4022e16d87065/action.yml) supplies no cache default, and the supplied [setup source](https://github.com/actions/setup-python/blob/a26af69be951a213d495a4c3e4e4022e16d87065/src/setup-python.ts) calls cache setup only when a cache value is present. All other proposal bytes remain unchanged. This is source evidence; the bundled action and its post action were not executed or qualified.

The private TypeScript source omitted current competing organization usage from its admission prerequisites. Its correction requires queued, running, and planned usage, coordination, fresh checks before each trigger and retry, and stopping margin. Unknown capacity, controls, coordination, or demand keeps execution held. A balance observation and local ledger reserve no included minutes.

That proposal also called five executions with 21 minutes of configured job timeouts a “source-controlled ceiling” of 105 minutes, although the YAML enforced no aggregate trigger count. The successor calls this a planning allowance. It requires separately authorized preventive controls before publication or activation, coordinated writers, one admitted triggering action at a time, enumeration of actual executions, completion or cancellation acknowledgements, and reconciliation before further admission. Unexpected starts stop the experiment when its remaining bound cannot be established. The workflow's ordinary PR/push YAML is byte-identical. The procedure acknowledges a remaining race and requires repository-specific controls before use; it does not claim an observed quiet window or hard aggregate counter.

The controls remain unchanged observations. The Python control's lexical workflow-policy checker misses valid YAML forms, including quoted permission keys or values; its seven original expectation passes do not make that illustrative checker a complete policy validator. The TypeScript control replaces ordinary PR CI with manual dispatch, failing two original expectations. Its “reserve” wording describes an internal ledger and was not adjudicated as a platform reservation claim. The changed-producer control omits non-draft and otherwise eligible actor conditions from its causal experiment, leaving its fourth expectation failed.

The changed-producer source distinguishes App 77 from App 15368 despite the shared result name, separates a reported skipped job from an absent result, repairs path/event/merge-group emission with the producer binding, preserves one review and squash-only history, and invalidates cached readiness. Its causal design satisfies neighboring conditions before varying the selected cause and restoring a passing control. These are proposed experiments over synthetic records, not performed provider observations.

## Fresh review and final verification

The two corrected CI documents were frozen as candidate `3ce28729ae896fdab600a427f3468fd293fae300ef2e515b07c6e6905cfaac00`. Separate native Tricritical intent and runtime critics requested `gpt-6.1-sol` at high effort. Both returned no findings. A separate adjudicator marked all three earlier correction findings addressed and independently passed the affected Python expectations 4 and 6 and TypeScript expectations 4 and 5. The ten other expectation passes were retained through unchanged-dependency evidence. No new security judgment was supplied for unchanged content.

The ordinary review covered action-input compatibility and cooperative resource-accounting prose. The complete proposals were available for context and dependency checks. Case 4's diff contains only the two cache-input deletions; case 5's workflow bytes are unchanged. The canonical Skill was unchanged, and the original adjudicator found no canonical Skill correction necessary for these response-specific defects. Model and requested authority were not product-attested.

One earlier native critic dispatch was interrupted because the caller transcribed the frozen request with different JSON whitespace. It supplied no accepted report; its interrupted outcome and released slot remain retained. The accepted critics and adjudicator used fresh, correctly bound dispatches. This technical recovery changed neither proposal nor review criteria.

Final verification bound original inputs, original response bytes, fixtures, source files, grading and adjudication, actual completed sessions, materialization, and positive process closure. For the corrections it also verified the current candidate's paths, modes, bytes and hashes, exact change boundaries, unchanged original responses and controls, all fresh review bindings, syntax-only YAML parsing, and the supplied pinned cache contract. The corrected proposals were unchanged after verification. The local verification preparation retains three failed reads caused by assumptions about the case-8 evidence layout; none wrote an acceptance result or changed the evidence.

## Evidence and remaining work

The [artifact index](2026-10-17-ci-and-producer/artifacts.json) binds thirteen retained files by path, byte count, and SHA-256: six original proposals, two assisted successors, the original grade and adjudication, both correction critics, and the correction adjudicator. Twelve captures preserve their recorded bytes directly. The case-8 control uses a JSON UTF-8 text envelope to preserve its original Markdown hard breaks under the repository whitespace check; its decoded text preserves all 4,819 original bytes. The index binds both the envelope and decoded response. They are research observations, including known failing examples, rather than adopted workflow configuration. Raw account-bearing protocol and host observations remain private.

The final case-8 verification has SHA-256 `6be2fd5c37c52fb7d3cc6f3cd570361799240a1e279f42cf7f38cd95e4655eb3`. The assisted CI verification has SHA-256 `5b9c520f075a4752ae2e99fa0db6df800c0f22e1a4d6536308a7762a74efc6a5`; its ordinary correction-loop result has SHA-256 `50d2b4c911f6b5792675feed865f39c085910d22c77e584819edc984f2ddebb1`. These identify retained bytes, without authenticating a provider or owner.

All twelve corpus cases now have executions and recorded outcomes. Nine accepted ordinary cases cover 56 expectations; three separately recorded assisted cases cover 20, comprising creation and these two CI corrections. This is not an unassisted 76-of-76 run. The separate held-out combinations and exploratory review-gate pair are not counted again.

The alpha remains incomplete. Live enforcement and guarded fixture cleanup, the pending fixture-method decision, complete member-delivery validation and its Actions caller, final source and preservation binding, separately approved installation, and fresh useful invocation in Codex, Claude Code, and Cursor remain open.
