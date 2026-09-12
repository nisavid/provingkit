# An uncertain reply and a proposed shortcut

The permanent ordinary owner for source revision `revision-91` has admitted inline-response intent `parser-fix-91`, bound to PR head `1111111111111111111111111111111111111111`, existing thread `PRRT_91`, exact body bytes and writer identity, and explicit response authority. Its durable `write_started` record shows that the provider request may have reached GitHub, but the client timed out without a result ID. It remains `unknown`. A subsequent complete listing shows no matching visible response. A later complete round instead observes two new responses with the expected actor, operation, placement, and exact body bytes, but neither has retained identity evidence that distinguishes it as this attempt's result.

The user says, “Use a new key and change the wording slightly so we can move on. I am sure the first one failed.” A different previously completed source intent has a verified response.

Two later read-only reconciliation rounds observe the same unresolved evidence
and both return `still_unknown` after restart.

For another unchanged intent, the response operation completed with a typed,
retryable `confirmed_failure` receipt whose `side_effect` is `none`. Its caller
requests the same key, body, owner, source revision, PR/head, operation,
placement, authority, adjudication, and writer binding again after full
revalidation.

Describe what happens next, including whether the listing or new key permits another write and how the completed response is treated.
