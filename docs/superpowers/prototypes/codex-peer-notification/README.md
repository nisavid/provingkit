# Queue and Steer evidence model

Open `demo.html` to explore a synthetic notification request and its evidence stages. The same pure input/output function supports two separately tracked preparation profiles: Claude Desktop-hosted Code to ChatGPT in Codex mode, and ChatGPT in Codex mode to an independently opened Codex terminal task.

This is a throwaway source prototype. It has no transport, process reader, account access, persistence, task discovery, or harness connection. Every result is unqualified. The common comparison in [#569](https://github.com/nisavid/provingkit/issues/569) owns the reaction to this experiment and later candidate choices.

## Public interface

`peerNotificationPrototype.inspectNotification(input, events)` takes invented peer, owner, independent-witness, consent, message, strategy, retry, and observation-time records. It returns the captured request, profile, evidence stages, current outcome, retained prior grant references, ignored observations, and resend eligibility. Its supported inputs are the structured records shown in the demo and tests; it is not a parser for untrusted acquired files or a permission-enforcement mechanism.

Only Queue and explicit Steer are modeled. Queue encodes `thread/queue/add`; Steer encodes `turn/steer` with the supplied current-turn precondition. Unsupported controls stop, without starting, resuming, or replacing a task. `turn/start` remains outside this experiment because the inspected implementation can steer an already active turn.

The independent witness and consent are supplied assertions in this model. Matching them can reject inconsistent invented records; it cannot authenticate an owner, sender, consent, grant, or receiver. Observation times are supplied synthetic numbers. The freshness rule illustrates bounded comparison, not a chosen live deadline. Prior grant records are copied unchanged and referenced in the disclosed peer-labelled user-role text. The model creates no authority and does not decide which transitive scope is valid, classify action requests, or detect instructions embedded in text.

## Reading an outcome

- A constructed request is `not_attempted`; construction performs no submission.
- Queue admission and dequeue do not establish receiver receipt.
- Correlated receiver receipt and explicit acknowledgment are separate stages. An acknowledgment alone does not manufacture a receipt record.
- Held and refused outcomes stay distinct and do not invite automatic resend.
- A lost response preserves possible submission and requires reconciliation. Later matching receiver evidence can establish receipt without repeating the send.
- Only a supplied proof of transient non-submission, within the declared attempt and time bounds, makes a bounded retry eligible. The model never executes one.
- Later lower-stage events do not erase an already proved receipt or acknowledgment; their observations remain in the evidence list.

Events are normalized invented observations, not a decoder for actual App Server responses. The model does not prove that a real harness produces a held/refused event, inherits grants, exposes a usable reader, or retains context. Idle/busy/unloaded behavior and source-to-installed-build applicability remain later evidence obligations.

## Source binding

The captured fields follow the inspected Codex source at commit `97239fd052db455bd08c41afcdab738e0fe83b87`:

- [Queue call](https://github.com/openai/codex/blob/97239fd052db455bd08c41afcdab738e0fe83b87/codex-rs/tui/src/session_queue_commands.rs): method and client-user-message correlation, with UUID generation inside the ordinary CLI path.
- [Queue parameters](https://github.com/openai/codex/blob/97239fd052db455bd08c41afcdab738e0fe83b87/codex-rs/app-server-protocol/src/protocol/v2/thread.rs): `threadId`, `input`, and `clientUserMessageId`.
- [Turn and input parameters](https://github.com/openai/codex/blob/97239fd052db455bd08c41afcdab738e0fe83b87/codex-rs/app-server-protocol/src/protocol/v2/turn.rs): Steer also requires `expectedTurnId`; text input retains the serialized `text_elements` field.
- [Receiver item declaration](https://github.com/openai/codex/blob/97239fd052db455bd08c41afcdab738e0fe83b87/codex-rs/app-server-protocol/src/protocol/v2/item.rs): user-message correlation is represented by `clientId`. A declaration alone does not establish an accessible producer or reader.

Those source declarations do not identify the currently installed GUI or terminal build. Placeholder identifiers in the demo are invented strings, not validated native UUIDs. A later adapter must bind actual native identifiers, request/attempt identities, schema, receiver records and observation completeness under its reviewed grant.

## Run the synthetic checks

From the checkout root:

```sh
node --test docs/superpowers/prototypes/codex-peer-notification/test-model.cjs
```

The checks cross the same exported model interface used by the page. They examine captured requests and staged results using invented inputs and fake events. They do not mock internal collaborators or connect to a harness. Passing them establishes constructed behavior only.

## Preparation consumers

[Desktop-to-ChatGPT preparation (#561)](https://github.com/nisavid/provingkit/issues/561) and [ChatGPT-to-terminal preparation (#562)](https://github.com/nisavid/provingkit/issues/562) can consume the model while retaining their distinct caller and owner gaps. Both feed the reviewed comparison and prototype-reaction join. The [separate first Desktop notification route (#212)](https://github.com/nisavid/provingkit/issues/212) retains its stronger acknowledgment and runtime-preservation contract.

The maintained catalog update is pending the reviewed catalog/procedure and the cohort join. No synthetic result here adds a live operation claim. Installation, receiver reads, task actions, provider use and sends require their applicable later grants.
