# Claim-support execution contract

This comparison tests categorical relation feasibility on ten supplied cases and records a local unavailable-source control. It schedules 60 isolated API requests. It can describe supplied-case answers and measured work; it makes no native-benefit, author-correction, safety, population-reliability, or utility/economic-superiority claim.

This is an execution proposal. No provider request is authorized until the coordinator binds the final inputs, routes, equipment, and accounting, obtains clean independent review of that revision, and records execution acceptance. Synthetic wrapper/deadline checks establish only the constructed local behavior tested.

## Frozen inputs and consumer procedure

Before dependent execution, load `handling-sys1-incidents` and its maintained `references/comparison-contract.md` at the reviewed source revision recorded in the invocation binding. Apply `adopting-jev` to the finite question and competing alternatives. Preserve producer, corpus, and evaluator identities; verify producer outputs against the maintained procedure and return useful corrections to its source. This increment changes no installed procedure.

The coordinator owns the private spec, bindings, evaluator key, and evidence directories. Public artifacts use repo-relative paths and artifact identifiers, never private machine paths. Bind every complete source and candidate state, ordered source catalog, producer receipt, corpus manifest, question/options, evaluator key and grading procedure, contract, runner/wrapper/preflight source, dependencies, route documentation, and price record with byte count and SHA-256. Bind the final Git revision where applicable. The bindings include every source, not merely the prepared packet. Any material change invalidates affected review before requests.

Use the ten intact inference states as complete `packet.md` files, not producer `packet.json` metadata. Keep `c11` in the spec as unavailable. The reviewed corpus manifest is `caf7ff863fe0fa8ff18d52abcb0ada62edf3f6f01a21ddbdf1d898dfe6435cd2`; the evaluator key is `690796c6b172cbc21ce8cc4ab29c08aec22ebc642e32e30a7d2410f794e84904`; the question identity is `bbf9d6e8c406ef7c339855195474ba25a56c80be5712d1a57f5c405c629a9d67`; the reviewed grading procedure is `8db94b363fd716652da125903d96549bd89e23c56ef86e92d528006ce63bbbe4`. Verify these identities against actual delivered bytes before admission. A key dispute requires explicit adjudication and a new bound key; never relabel retained answers silently.

Inference receives neutral case IDs, the assertion, ordinary enclosing draft context and citations, complete available ordered sources, and supported deterministic status information. Supply the identical state to all six conditions. Exclude the evaluator key, expected relation, corrected answer, revealing class names, provenance commentary, and grading material. Original bytes remain retained. A quotation match recorded only in producer metadata must not be described as information delivered in Markdown.

## Exact question and options

Use this question unchanged:

> Considering only the supplied sources, what relation does the designated assertion have to their evidence? Respect the assertion's scope and any explicit qualifications in the supplied evidence. Do not decide global truth or recommend an action.
>
> Assess evidential warrant, including when the assertion says that reports establish a fact: a derivative assertion adds no independent warrant beyond its supplied cited basis and qualifications. A statement that a fact is unestablished limits warrant; it does not, by itself, establish an incompatible event or state of affairs. Conflicting independent factual accounts that the supplied context cannot resolve remain `unresolved`.

The ordered options are:

1. `supported`: The supplied evidence warrants the complete assertion at its stated scope.
2. `contradicted`: A supplied source explicitly states an incompatible fact, and the supplied sources do not conflict about it.
3. `unsupported_extension`: The assertion claims more than the supplied evidence establishes, without a demonstrated incompatible fact.
4. `unresolved`: Missing referents, conflicting sources, or insufficiently interpretable context prevent choosing the other relations.

Jev and Decisions receive one Choice question named `claim_relation`. Preserve and validate their documented native confidence and all four option probabilities, including finite values in [0, 1] and a probability sum within 0.000001 of one. These fields are descriptive; no confidence threshold governs acceptance. Responses receives the same question and meanings and returns only one JSON object with the required `relation` property and one listed key. Reject duplicate or extra properties, prose, multiple objects, malformed JSON, and incomplete terminal output. Responses categorical output is not a native probability distribution. No output authorizes an edit or action.

## Matrix and schedule

Cases are ordered `c01,c04,c03,c06,c05,c07,c02,c08,c09,c10,c11`. The first ten must be ready; `c11` must be non-ready in its producer outcome and unavailable in the spec. Before any service submission, verify its controlled-unavailable source status, unavailable quotation assessment, no observed source digest or file, expected producer exit status, and zero semantic schedule slots. It receives a separate fallback outcome, never an `unresolved` grade. The corpus contains no conflicting-source control and cannot qualify accuracy for that category.

Conditions in order are:

| Index | Adapter | Requested selector | Effort |
| --- | --- | --- | --- |
| 0 | Jev Choice | `jev-1.13.0` | null |
| 1 | Decisions Choice | `gpt-6-luna` | null |
| 2 | Responses | `gpt-6-luna` | `low` |
| 3 | Responses | `gpt-6-luna` | `medium` |
| 4 | Responses | `gpt-6-luna` | `high` |
| 5 | Responses | `gpt-6.1-sol` | `low` |

Each ready case rotates condition order by its zero-based position modulo six, then runs the other conditions cyclically. Verify the generated schedule equals these 60 slots. Run serially with concurrency one and fresh independent context per slot. No retries, diagnostics, batch-hidden questions, evaluator feedback, other-case output, or author-consumer requests are included. A failed submission consumes its slot. Ordinary authoring and deterministic-only preparation remain alternatives whose unmeasured effort is unknown.

## Routes, bounds, and invocation

Use these fixed documented POST routes with runtime environment-backed Bearer authentication:

| Adapter | Endpoint | Credential selector | Billing |
| --- | --- | --- | --- |
| Jev | `https://api.typesafe.ai/v1/systemone` | `TYPESAFE_API_KEY` | Bound TypeSafe service route |
| Decisions | `https://api.openai.com/v1/decisions` | `OPENAI_API_KEY` | API-billed |
| Responses | `https://api.openai.com/v1/responses` | `OPENAI_API_KEY` | API-billed |

Freeze the Jev version, documented schemas, supported requested efforts, terminal semantics, and price assumptions. A completed answer requires an observed returned model exactly equal to the requested selector; accept no undocumented alias. Missing model identity leaves `model_unobserved` and stops that condition. Retain raw evidence and usage; failed or incomplete transport keeps its observed failure state rather than inventing an identity mismatch. Record observed effective effort, tier, and region from retained raw evidence, otherwise null with a reason. Never infer effective effort from the requested value. Responses uses streamed, nonstored output. No automatic billing or endpoint switch is allowed. No hard output-token control is requested.

The proposed limits are `request_seconds=120`, `run_seconds=9000`, `input_bytes=65536`, `request_bytes=131072`, `response_bytes=1048576`, and `requests_per_cell=1`. Reject oversized sources and requests; never truncate supplied sources. Recheck serialized size before submission. Response retention stops at the byte cap, preserving the bounded prefix and failure marker. Cancellation does not establish that provider work or charges stopped.

From the repository root, the coordinator substitutes its private paths and printed digests:

```sh
python docs/superpowers/research/evidence/jev-axi-comparison-runners-2026-10-07/ordinary_preflight.py --spec "$claim_spec" --spec-sha256 "$claim_spec_sha256" --bindings "$claim_bindings" --bindings-sha256 "$claim_bindings_sha256"
python docs/superpowers/research/evidence/jev-axi-comparison-runners-2026-10-07/ordinary_invocation.py start --spec "$claim_spec" --spec-sha256 "$claim_spec_sha256" --bindings "$claim_bindings" --bindings-sha256 "$claim_bindings_sha256" --output "$claim_invocation"
```

Preflight submits no requests. `start` begins the outer clock before final preparation, invokes `comparison_runner.py prepare`, binds its manifest, verifies schedule and identities, and invokes `comparison_runner.py run` with `--deadline-monotonic-ns` set to the same absolute deadline. Do not grant requests a new 9,000 seconds. Linux is the supported execution environment. `--local-http` is solely for constructed loopback tests and is omitted for this comparison. The wrapper sends SIGTERM at its child deadline, waits up to two seconds, then sends SIGKILL and reaps if necessary; kill/reap completion is not hard bounded.

## Failure and grading

Shared identity drift, incorrect producer/control outcome, evaluator leakage, source truncation, forbidden action, failed shared review, or compromised evidence integrity stops all requests. A missing or invalid credential or condition-specific route failure leaves its slots unattempted; independently supported conditions may continue within the accepted scope. Once a claim attempt is not completed, the current runner stops that condition's remaining slots. Preserve refusal, malformed/incomplete response, timeout, HTTP/provider error, model mismatch, and accounting error distinctly. A semantic disagreement is graded later and does not adapt the schedule. Mark every remaining slot with its reason. No resume or retry occurs inside this invocation.

Close the request phase and fix all attempt records before grading. The outer clock continues through deterministic grading, evidence review, corrections, and handback. Grade each of the 60 scheduled slots once as `matching`, `nonmatching`, `invalid_output`, `refused`, `failed`, or `unattempted`. Keep transport, identity, and accounting errors separate. A parseable relation from an unsuccessful attempt may be described but cannot count as success. The denominator is ten per condition; categorical feasibility passes only with ten valid matching terminal answers. The unavailable control is separate. Preserve native probabilities without claiming calibration. No hidden grading-model call, output repair, answer feedback, or selective retry is allowed.

The retained claim grading procedure's “after the invocation closes” means after the fixed request phase closes. It does not mean after `ordinary_invocation.py close`. Keep the bound semantic key and grade names unchanged. Finish grading, independent final result review, any correction, and handback, bind their artifacts in closeout events, and then close the whole invocation under its original deadline.

Apply `invocation-accounting.md`. Record grading UTC/monotonic intervals, hash grades and accounting joins, and retain independent final result review and correction costs. The wrapper's `close` validates the ledger and records deadline overrun; ledger closure alone proves neither grading completion nor complete accounting. A handback after the outer deadline is incomplete for the accepted timing claim. Report slots before aggregates, fallback separately, and all missing measurements beside observed results.
