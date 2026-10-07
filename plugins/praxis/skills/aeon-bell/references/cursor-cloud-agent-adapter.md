# Cursor Cloud Agent continuation controls

`scripts/cursor_cloud_agent_adapter.js` is a Node-free ECMAScript resource for
one partial native binding: reading a Cursor Cloud Agent and sending an Aeon
Bell continuation to that agent. It supplies `taskRead` and `send` controls
that can be passed to `createNativeAdapters`. It does not install or activate
those controls and does not supply Cursor Automations scheduling, monitor
state channels, deployment, or account configuration.

## Fixed boundary

Evaluate the resource in the native ECMAScript host, then call
`createCursorCloudAgentControls({request})`. `request` is an owner-supplied,
already-authenticated HTTP control. The resource does not read credentials,
open a network connection, execute a process, or accept an origin or endpoint
option. Every request is under `https://api.cursor.com/v1/agents/`.

The Aeon target must have the exact host class `cursor-cloud-agent`. A local
Cursor IDE or CLI target, a target registered for another host, and malformed
target or message values return `not_started` without calling `request`.
Agent and run IDs remain opaque; this adapter does not impose an undocumented
Cursor identifier grammar. Before an ID can enter a request path or support an
authoritative result, it must be well-formed NFC and NFKC text and must not be
`.` or `..`, a percent-encoded dot segment, contain a raw slash or backslash,
or contain a percent-encoded slash or backslash. Invalid requested agent IDs
return `not_started` before the authenticated request control is called. An
invalid `latestRunId` fails the task read before a run request, and an invalid
run ID in a create-run response cannot establish acceptance.

The request control receives these objects:

- Agent read: `{method: "GET", url}`.
- Latest-run read: `{method: "GET", url}`.
- Continuation: `{method: "POST", url, headers, body}`, where the sole header
  is `Content-Type: application/json` and `body` is exactly the JSON encoding
  of `{prompt:{text:message}}`.

The control returns `kind: "not_started"` only when it knows no HTTP request
started. A completed HTTP observation uses `kind: "completed"`, its integer
HTTP `status`, and the raw response text in `body`. For a busy rejection, it
also supplies `error_code: "agent_busy"` only when that exact code was
observed. `error_code` is normalized control evidence, not an invented Cursor
response-body schema. Throws and `kind: "unknown"` mean the request outcome is
not known.

## Continuation outcomes

The control makes one POST and never retries it.

- A 2xx response is `accepted` only when its JSON is the documented create-run
  shape, the returned run is `CREATING`, `run.agentId` exactly matches the
  requested target, and `run.id` supplies the native run identity.
- A completed `409` is `not_sent` only when the request control also observed
  the documented `agent_busy` code. This combination proves nonadmission.
- A lost outcome, malformed body, other HTTP response, missing run identity,
  or mismatched `agentId` is `unknown`. The evidence is bounded and does not
  include the target or prompt. Aeon Bell must retain and reconcile that
  unknown attempt; the control does not replay it.

Acceptance is the native API's admission of the run, not delivery, execution,
or completion evidence.

## Task-read limit

The read control gets the agent, takes its `latestRunId`, then gets that exact
run. It accepts only documented lifecycle and run states and requires both
responses to bind back to the requested agent and run IDs. The request control
supplies `observed_at`; the adapter does not use an ambient clock. It exposes a
bounded lifecycle summary and only whether a terminal final reply is present,
never the reply text.

These reads do not prove that the latest turn is the registered Aeon wait for
the action's episode. Consequently the summary always has
`episode_matches: false`, including when the agent is `IDLE`, the run ID
matches `latestRunId`, and the run is terminal. The structured monitor must
classify that relation as `unknown`; this native read cannot authorize a send.

The request and response facts above come from the
[Cursor Cloud Agents endpoint reference](https://cursor.com/docs/cloud-agent/api/endpoints),
observed on 7 October 2026. The
complete monitor cycle remains owned by the existing engine and structured
binding.
