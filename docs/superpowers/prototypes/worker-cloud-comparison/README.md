# Compare worker and Cloud operation evidence

Open `demo.html` to drive invented worker and Cloud traces. The prototype makes
submission, receipt, addressability, execution, output, terminal status, caller
checks, and same-task continuation visible separately. It helps inspect the
state model before choosing live probes.

This is throwaway source equipment for
[Compare the first cohort prototypes and record the operator reaction](https://github.com/nisavid/provingkit/issues/569).
All results have `qualified: false` and `evidenceKind: "synthetic"`. The page
uses memory only and performs no discovery, transport, authentication, provider
request, task operation, file acquisition, or retry.

## Public interface and supported specimens

The pure `WorkerCloudModel.evaluate(input)` module is in the `trace-model`
script. Input supplies invented caller, fabric, operation (`work` or
`continue`), exact target/owner association, task-and-purpose consent, prior
grant references, requested/applied setting observations, request/correlation
IDs, arithmetic checks, and normalized events. The prototype supports
well-formed specimens shaped like the test fixture; it is not a raw vendor
protocol parser or a general untrusted-input validator.

A controlled `work` specimen represents the first creation/work experiment.
An independently acquired `addressable` event establishes its constructed
creation observation; returning an ID alone does not. A `continue` specimen
uses the existing native identity and a prior marker omitted from the captured
request. An existing Cloud work specimen additionally requires admitted
receiver input association. These are conservative prototype conditions for
the selected experiments, not assertions about a vendor's event grammar.

The output contains an abstract captured request or an admission gap, separate
observed stages (including addressability), raw normalized terminal statuses, literal check status,
submission outcome, gaps, and a next recommendation. Later evidence gaps do
not erase the captured request. The request records original grant references;
it neither authenticates them nor creates authority. The setting request and
the separately supplied applied no-edit observation remain distinct.

Normalized events must match the declared owner, native task, request, and
correlation. Receiver observations require receiver origin. The SSE receipt
specimen additionally ties the envelope to the same JavaScript event object;
a copied object supplies no such association. Real envelope acquisition and
normalization remain absent. Matching receiver output is retained as operation
evidence even when merged input association excludes it from caller checks;
that uncertainty requires reconciliation and withholds fulfillment. Same-text
complete independent readback survives weaker duplicate observations. Different
text or terminal conflicts remain incomplete or require reconciliation. Correct arithmetic from a failed
or interrupted run does not establish fulfillment.

Caller checks parse complete JSON and compare `ascending` and `sum` with the
declared finite numbers. Extra JSON fields are ignored. Continuation also
compares the prior marker. Failed, incomplete, absent, or uncorrelated output
cannot pass these checks. No semantic model or behavioral eval is invoked.

A recommendation can be `hold`, `read`, `reconcile`, or
`eligible-bounded-retry`. The last requires supplied proof of non-submission,
remaining declared attempts, and no contradictory operation evidence. It
performs no retry. Possible submission remains a separate fact requiring reconciliation even
when later output is incomplete. One final rule owns the recommendation; held
and refused responses do not trigger resubmission. A continuation identity
replacement refuses the request and its success claims while retaining earlier
observations from the unchanged admitted task scope.

## Source candidates and directional limits

| Preparation profiles | Candidates represented | Observations still missing |
| --- | --- | --- |
| ChatGPT and Claude Desktop to created Codex workers | Direct CLI, Python/owning App Server, ACPX/Codex adapter | Actual caller entrance, native mapping, independent readback, applied settings, complete successful result, continuation |
| ChatGPT, Claude Desktop, and Codex terminal to existing Claude Cloud tasks | Exact-ID CLI plus selected reader, active browser SSE, legacy WebSocket | Caller/auth/account/task binding, independent reader, input/result association, initialization effects, ambiguous-write reconciliation |

The three separately tracked existing-peer notification preparations consume
the [Queue/Steer model](https://github.com/nisavid/provingkit/tree/5ac4b8e362e35d3972802c67057814a0dfc09464/docs/superpowers/prototypes/codex-peer-notification).
It is not implemented again here. All eight preparation profiles remain
separate in the cohort comparison. Selecting a caller or candidate on this
page reuses a constructed model; it establishes no outside caller exposure,
reverse route, or native task-population equivalence.

Consume the complete published
[worker preparation](https://github.com/nisavid/provingkit/tree/3b0c946c9d4d85ccfabc83c8209b0238f4a8a831/docs/superpowers/research/codex-worker-preparation-2026-10-13)
and
[Cloud preparation](https://github.com/nisavid/provingkit/tree/7abc9202853e430eb0f92d187b9305080a8426de/docs/superpowers/research/claude-cloud-preparation-2026-10-13).
Python's accepting default approval handler and incomplete settings projection,
ACPX installed resolution versus fallback range and replacement behavior,
Cloud active initialization and ambiguous POST retries, and missing passive
readback remain source gaps. The prototype implements no vendor decoder,
launcher, approval handler, catch-up reader, idempotency contract, or restoration
procedure.

## Verify and consume

From the repository root:

```sh
node --test docs/superpowers/prototypes/worker-cloud-comparison/test-model.cjs
git diff --check
```

The tests extract the same pure script from the HTML and exercise the agreed
public input/output interface. They test invented-record behavior; they do not
run a harness, certify source observations, or exercise the browser shell.
Browser interaction remains a separate observation.

Load `updating-cross-harness-catalog` at reviewed revision
`701af706a0b2d70a9161742453bfc7c99aab952c` for the coherent comparison batch.
Retain this source/synthetic evidence separately from actual operation claims,
reconcile the affected records, regenerate graph and matrix inputs, and obtain
current independent review before batch closeout. The separate atlas prototype
owns its UI interaction. This artifact adds no maintained procedure or operating
dependency; useful corrections return to the existing cohort/panel workflow.

The prototype reaction supplies no installation, private receiver access,
provider, task, message, restart, release, or Hatchery deployment grant. Live
probe selection follows the reviewed comparison and its concrete scope decision.
