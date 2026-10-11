# Write the invocation accounting records

Preparation only: the coordinator writes the records below; the existing collector, native controls, Git helper, and comparator retain their own evidence. Freeze and independently review this plan and producer before execution acceptance. The proposed 9000/3600/5/5-second amounts remain unaccepted. This plan adds neither a collector interface nor observation.

## Freeze table

| Binding | Still needed |
| --- | --- |
| Record producer | Exact plan/producer paths, SHA-256 digests, and clean review identities; new invocation directory outside the worker project; invocation/coordinator/Linux host identity |
| Source identities | Published collector, transport, Git helper, seed producer, comparator, maintained comparison procedure, ledger vocabulary, and applicable clean reviews |
| Preparation | Bound copy/baseline/profile actions and receipt locations; seed/spec/cases, two requests, trigger paths, omission overlay, baseline receipt |
| Prepared package | Manifest and native-profile paths/digests/reviews; baseline commit/branch/inventory; evaluator inputs; contract path/digest. Bind later if absent at outer start. |
| Native controls | Exact reviewed start, one amendment delivery, input handling, shutdown/source retention, final Git capture, and analysis-review actions; existing output paths/selectors |
| Freshness | Bound preflight and selectors for accepted package/source/profile, Git executable, baseline, modes/content, branch, clean tree, and absent remotes; coordinator verifies results |
| Limits/acceptance | Proposed 9000 coordinator seconds, 3600 native seconds, two five-second waits, 64 MiB ceiling; actual collector behavior; original operator acceptance and accepted contract/manifest/limits; observed acceptance/start boundary or gap |
| Close/accounting | Comparator and grading directory, completion template, final-source/Git/review identities, handback path/digest; construction/prior-preparation coverage; raw counter scope/model/rate partitions; optional operator evidence and unknowns |

The private invocation binding supplies the collector/profile commands from the observation contract. Fill every execution binding before acceptance. Untimed earlier preparation stays unknown; do not replace it just to create a measured interval.

## Coordinator record producer

Save this code at the frozen producer path. Supply its initial values from the private invocation binding, then keep one coordinator Python session for this invocation, including acceptance waiting. Bind that session and its startup command before preparation. Do not assume independent shell calls share Python globals. Records use exclusive creation and a preceding-record digest. A failed write or session loss stops new dispatch. Preserve all existing files and report accounting as incomplete; do not recreate an outer start or resume a work window from an invented clock boundary. Minimum preservation and assessment of already-incurred work still proceed with explicit accounting gaps.

```python
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import time

D = Path("<new invocation directory>")
INVOCATION = "<unique invocation ID>"
ACTOR = "<coordinator identity>"
START_REFS = []  # Actual available source/input/plan/producer identities.
D.mkdir(parents=True, exist_ok=False)
seq, tail, work, acceptance_id, work_id = 0, None, None, None, None

def unknown(reason):
    return {"status": "unknown", "value": None, "reason": reason}

def tick():
    try:
        observed = os.uname()
        host = {"sysname": observed.sysname, "nodename": observed.nodename}
    except (AttributeError, OSError):
        host = None
    try:
        boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
        boot = None
    return {"utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "monotonic_ns": time.monotonic_ns(),
            "host": host,
            "clock": [host["nodename"] if host else None, boot,
                      time.get_clock_info("monotonic").implementation]}

def host_reason(at):
    host = at.get("host")
    if not host or not host.get("sysname") or not host.get("nodename"):
        return "Controller host observation is missing."
    if host["sysname"] != "Linux":
        return "Controller host is not Linux."
    if host != outer.get("host"):
        return "Controller host binding changed."
    return None

def ref(path, selector, supports):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(65536), b""):
            h.update(b)
    return {"path": str(path), "sha256": h.hexdigest(),
            "selector": selector, "supports": supports}

def same(a, b):
    return (a is not None and b is not None and a["clock"][1] is not None
            and a["clock"] == b["clock"]
            and b["monotonic_ns"] >= a["monotonic_ns"])

def seconds(a, b):
    if a is None or b is None:
        return unknown("Boundary was not observed.")
    if not same(a, b):
        return {"status": "invalid", "value": None, "reason": "Clock/boot mismatch."}
    return {"status": "derived", "value":
            (b["monotonic_ns"] - a["monotonic_ns"]) / 1e9, "unit": "seconds"}

def record(name, schema, **fields):
    global seq, tail
    data = {"schema": schema, "invocation_id": INVOCATION,
            "record_id": name, "sequence": seq, "actor": ACTOR,
            "preceding_record": tail, "recorded_at": tick(), **fields}
    raw = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode()
    p = D / name
    with p.open("xb") as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    tail = {"path": str(p), "sha256": hashlib.sha256(raw).hexdigest(),
            "selector": "$", "supports": "Accounting record identity."}
    seq += 1
    return data, dict(tail)

def event(purpose, refs=(), **fields):
    return record(f"{seq:04d}-event.json", "compatibility-invocation-event/v1",
                  purpose=purpose, references=list(refs), **fields)

def begin(purpose, refs=(), recurrence="recurring"):
    start = tick()
    _, identity = event(purpose, refs, recurrence=recurrence,
                        start=start, end=None, phase_state="started")
    return purpose, recurrence, start, identity

def finish(phase, refs=(), **measurements):
    purpose, recurrence, start, identity = phase
    end = tick()
    return event(purpose, refs, recurrence=recurrence, start=start, end=end,
                 phase_state="ended", start_record=identity,
                 measurements={"elapsed": seconds(start, end), **measurements})

def remaining(at):
    if work is None:
        return {"status": "not_applicable", "value": None,
                "reason": "No accepted work window."}
    if not same(work["start"], at):
        return {"status": "invalid", "value": None, "reason": "Clock/boot mismatch."}
    return {"status": "derived", "value":
            (work["deadline_monotonic_ns"] - at["monotonic_ns"]) / 1e9,
            "unit": "seconds"}

outer = tick()
_, start_id = record(
    "invocation-start.json", "compatibility-invocation-start/v1",
    start=outer, references=START_REFS, active_deadline=None,
    proposed_coordinator_work_allowance_seconds=9000,
    proposed_native_allowance_seconds=3600,
    proposed_shutdown_waits_seconds=[5, 5],
    historical_construction=unknown("Bind separate construction evidence."),
    earlier_unmeasured_preparation=unknown("Fill actual prior coverage."))
reason = host_reason(outer)
if reason is not None:
    event("Preparation refused", boundary=outer, admitted=False,
          host_reason=reason)
    raise RuntimeError(reason)
```

Use `ref` for retained files and precise selectors; compare its digest with the frozen expected identity. Computing a digest alone does not establish freshness. No record is rewritten or backdated. Missing measurements are null with a reason; statuses may be observed, derived, estimated, unknown, not_applicable, or invalid. Do not call the provider ledger's runner-specific `start` path.

## Coordinator sequence

1. Start the producer before recurring copy/Git/profile preparation. Bracket the exact bound actions, retain their existing receipts, then request acceptance of the exact joined package:

```python
prep = begin("Recurring seed, Git baseline, and profile preparation", START_REFS)
# Coordinator performs the bound preparation actions.
prep_event, prep_id = finish(prep, PREPARATION_REFS)
event("Prepared package", PREPARED_REFS, outcome=PREPARATION_OUTCOME)
wait = begin("Awaiting actual execution acceptance", ACCEPTANCE_REQUEST_REFS)
```

2. At actual acceptance receipt, before final preflight, run this snippet. `ACCEPTANCE_REFS` binds the original receipt and exact accepted contract/manifest; `BOUNDARY_EVIDENCE` explains the observed receipt boundary and any timing gap. A displayed question, silence, or elapsed waiting is not acceptance. If its start boundary cannot be bound, record the gap, establish no usable window, and hold dispatch. Do not backdate receipt time to an untimed operator action.

```python
accepted_at = tick()
assert ACCEPTED_LIMITS == {"coordinator": 9000, "native": 3600, "shutdown": [5, 5]}
_, acceptance_id = event(
    "Actual execution acceptance", ACCEPTANCE_REFS, boundary=accepted_at,
    accepted_limits=ACCEPTED_LIMITS, boundary_evidence=BOUNDARY_EVIDENCE)
work = {"start": accepted_at,
        "deadline_monotonic_ns": accepted_at["monotonic_ns"] + 9000 * 1_000_000_000}
work_record, work_id = record(
    "coordinator-work-start.json", "compatibility-coordinator-work-start/v1",
    **work, acceptance_event=acceptance_id, references=ACCEPTANCE_REFS,
    accepted_allowance_seconds=9000, boundary_evidence=BOUNDARY_EVIDENCE)
wait_event, wait_id = finish(
    wait, [acceptance_id], acceptance_waiting=seconds(wait[2], accepted_at))
event("Acceptance recording latency", [acceptance_id, work_id],
      measurements={"elapsed": seconds(accepted_at, work_record["recorded_at"])})
```

The work start uses that acceptance boundary, so recording and admission consume time. Never reset it. Different limits require a revised joined contract/review. Without acceptance, finish waiting at an observed stopping boundary, leave `work` absent, and retain the incomplete outcome.

3. Run the bound preflight. The coordinator compares actual outputs with every accepted binding and sets `fresh` from that verification; `FRESHNESS_REFS` retains selectors. Do not discard unexpected dirt. Require clock continuity and the entire native/shutdown reservation:

```python
admission = begin("Final freshness and admission", [acceptance_id, work_id])
# Coordinator performs and evaluates the exact bound preflight.
at = tick()
r = remaining(at)
reason = host_reason(at)
admitted = (reason is None and fresh and same(outer, at)
            and r["status"] == "derived" and r["value"] >= 3600 + 5 + 5)
_, admission_id = event(
    "Admission", FRESHNESS_REFS, boundary=at, admitted=admitted,
    host_reason=reason,
    measurements={"remaining_seconds": r,
                  "reservation_seconds": {"status": "derived", "value": 3610}})
finish(admission, [admission_id])
# Recheck immediately before the bound start action:
at = tick()
r = remaining(at)
reason = host_reason(at)
admitted = (admitted and reason is None and same(outer, at)
            and r["status"] == "derived" and r["value"] >= 3610)
event("Dispatch-boundary reservation", [admission_id], boundary=at,
      admitted=admitted, host_reason=reason, measurements={"remaining_seconds": r})
if admitted:
    native = begin("Native collector call, including shutdown and retention", NATIVE_INPUT_REFS, "episode")
    # Coordinator invokes the bound collector run CLI locally exactly once.
```

The accounting session observes the controller host before recurring preparation and retains its sysname and nodename in the original records. Preparation requires Linux; admission and the immediate local dispatch check require that original host binding unchanged. Missing, unsupported, or changed observations retain a refusal reason and start no collector call. These ordinary supported-platform observations are not attestation or OS enforcement.

Failed admission starts no author work. Admission does not guarantee later grading/handback will fit.

4. The single collector run performs initial delivery and the once-only amendment automatically. After it returns, index those retained events with outgoing-byte references, responses, observed timestamps, and thread/turn IDs. The coordinator does not send an amendment. Preserve the original event time separately from the later indexing time. RPC acceptance establishes server acceptance, not comprehension.

For tests, corrections, observed reviewer/child work, usage, and input requests, reference the existing stream without adding child-history collection:

```python
event("Observed work or usage", STREAM_REFS, recurrence="episode",
      subject_actor=OBSERVED_ACTOR, start=OBSERVED_START_OR_NONE,
      end=OBSERVED_END_OR_NONE, measurements=SUPPORTED_MEASUREMENTS_OR_UNKNOWN,
      allocation="Shared production once; overlapping intervals are not summed.")
```

Use stream times only with a supported clock binding. Missing review reports, child totals, and operator effort remain unknown. Retain raw reported token partitions unchanged; derive root deltas only with established cumulative scope. Do not sum root/child counters without inclusion/overlap evidence or convert tokens to quota.

5. When the collector call returns, finish `native` using its retained outcome, process record, final-source receipt, and final-Git receipt. This outer interval includes shutdown and evidence retention. Index supported internal intervals afterward; mark unavailable subdivisions unknown rather than inventing separate begin/end observations. The collector has already performed shutdown and capture: do not call them again. Preserve its original outcome even when capture is incomplete, along with every failed attempt. Do not repair the candidate.

6. Before each discretionary action, record the window check below. Start the frozen comparator only with a positive valid remainder and complete captured final source:

```python
at = tick()
r = remaining(at)
may_start = r["status"] == "derived" and r["value"] > 0
event("Before discretionary action", boundary=at, allowed=may_start,
      measurements={"remaining_seconds": r})
```

```sh
python "$COMPARATOR" --before "$PACKET/seed" \
  --after "$OBSERVATION/attempt/final-source" \
  --contract-cases "$PACKET/cases" --output "$GRADING/behavior"
```

Bracket the comparison, completion grading, required independent analysis review, operator recovery, and handback preparation separately. Their producers retain original outputs; coordinator events reference identities/selectors. An amended oracle after absent/rejected amendment delivery is diagnostic only. Keep native outcome, capture, behavior, each completion obligation, and accounting separate.

At observed expiry or clock failure, start no discretionary new work, comparison, retry, or replacement. Preserve current outcomes and perform minimum necessary preservation/assessment of already-incurred work, including required review. Record later intervals and overrun. An unfinished required review keeps the outer record open; hand back its checkpoint explicitly. This does not preempt the collector, answer input, renew authority, or enforce security.

7. Prepare exact handback bytes in a new file and hash them as `HAND_BACK_REF`. `RESULT_REFS` binds original outcomes/capture/Git/comparator/assessment/review evidence and explicit absent-record entries; `GAPS` lists concrete unknowns. After required preservation, assessment, independent review, and handback preparation, close:

```python
end = tick()
r = remaining(end)
overrun = ({"status": "derived", "value": max(0, -r["value"]), "unit": "seconds"}
           if r["status"] == "derived" else r)
work_elapsed = (seconds(work["start"], end) if work else
                {"status": "not_applicable", "value": None,
                 "reason": "No accepted work window."})
state = ("closed_after_coordinator_deadline"
         if overrun["status"] == "derived" and overrun["value"] > 0
         else "closed_with_gaps" if GAPS or seconds(outer, end)["status"] != "derived"
         or r["status"] == "invalid" else "closed")
close, close_id = record(
    "invocation-close.json", "compatibility-invocation-close/v1",
    end=end, accounting_state=state, start_record=start_id,
    acceptance_event=acceptance_id, work_start_record=work_id,
    phase_chain_tail=tail, references=RESULT_REFS + [HAND_BACK_REF],
    prepared_handback=HAND_BACK_REF, gaps=GAPS,
    measurements={"whole_elapsed": seconds(outer, end),
                  "preparation": PREPARATION_MEASUREMENT,
                  "acceptance_waiting": WAITING_MEASUREMENT,
                  "coordinator_work_elapsed": work_elapsed,
                  "deadline_overrun": overrun,
                  "root_tokens": ROOT_MEASUREMENT,
                  "whole_child_tokens": unknown("Complete scope unavailable."),
                  "equivalent_api_value": API_VALUE_OR_UNKNOWN,
                  "actual_charges": unknown("No billing evidence."),
                  "subscription_effect": unknown("No token-to-quota mapping."),
                  "operator_effort": OPERATOR_MEASUREMENT_OR_UNKNOWN,
                  "eventual_delivery": unknown("Close measures prepared handback.")})
```

Use `prep_event["measurements"]["elapsed"]` and `wait_event["measurements"]["acceptance_waiting"]` where observed; supply unknowns for missing boundaries. API value requires supported scope/model/rate/partition mapping. Full elapsed is outer start to close, never a sum of phases; construction remains separate.

Verify the retained chain and handback digest. Report delivery, native outcome, capture completeness/correspondence, behavior, all completion obligations, observed corrections/review work, full/preparation/waiting elapsed, accepted-window timing/overrun, and gaps. Name the close and handback identities in the delivery envelope, avoiding a close-file self-reference in handback bytes. A later communication receipt is a separate exclusive event, not a closure rewrite. No acceptance, runtime success, whole-cost completeness, or native qualification is established by this draft.
