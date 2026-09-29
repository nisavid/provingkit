## Proposed contract

The candidate remains inert until a fresh, exact binding is armed. It never enumerates or chooses a target.

1. The operator creates a new `0700`, same-owner run directory containing only `config.json`.
2. `config.json` has exactly: `schema`, `runId`, `targetTaskId`, `targetCodeSessionId`, and `getterSetId`. It is a regular, single-link `0600` file, no larger than 4 KiB.
3. On startup, the adapter:

   - opens the configured directory without following a final symlink;
   - checks owner, mode, allowed contents, and each input file’s type, link count, owner, and mode;
   - obtains a cryptographically random app-start nonce, PID, and Linux process-start ticks;
   - performs one exact target lookup, never enumeration;
   - checks the supplied task and Code-session IDs;
   - captures the exact query object and current monotonic generation without calling getters;
   - publishes one exclusive `bootstrap.json`.

4. `bootstrap.json` has exactly: `schema`, `runId`, `configSha256`, `adapterSha256`, `copiedAsarSha256`, `appStartNonce`, `pid`, `processStartTicks`, `targetTaskId`, `targetCodeSessionId`, `queryGeneration`, `getterSetId`, `limits`, and `securityNotice`. Hashes identify reviewed bytes; they do not authenticate them.
5. The operator then creates `arm.json`, which echoes every binding field and selects limits no greater than the compiled caps. Any missing, stale, malformed, replaced, or mismatched arm leaves the adapter unarmed. An invalid arm is terminal for that app start.
6. Accept one arm per app start. Do not renew or retarget it. Expiry, sample exhaustion, identity change, generation change, timeout, or exporter failure permanently disarms that instance. Rearming requires a restart, a new nonce, a new bootstrap, and an explicit target. There is no default target.
7. The arm must be accepted within 60 seconds of bootstrap. Recommended hard caps are three sample attempts, a 30-second observation window, at least five seconds between sample starts, two seconds per getter, three getter invocations per sample, and a 6-second sample deadline.

The arm keys are exactly: `schema`, `runId`, `configSha256`, `appStartNonce`, `pid`, `processStartTicks`, `targetTaskId`, `targetCodeSessionId`, `queryGeneration`, `getterSetId`, `maxSamples`, `minIntervalMs`, `observationWindowMs`, and `perGetterTimeoutMs`.

## Sampling and getter controls

Sampling is a single serialized state machine. Before each getter and after each settlement, it verifies the app-start binding, task record, query object identity, Code-session ID, and generation. It repeats the full check before export.

Generation is monotonic for the app start and increments on query installation, teardown, and Code-ID change. It is never restored when an earlier ID or object returns, so an away-and-back transition is detected. Overflow terminates the adapter.

Invoke getters sequentially. Start the deadline before invocation. Do not invoke getter two until getter one has settled successfully and all identities still match; apply the same rule to getter three. A rejection records only a fixed error class. A timeout cannot cancel an unsupported promise, so it latches the adapter terminally: remaining getters and all later samples are forbidden even if the promise later settles. Attach a settlement handler only to suppress late unhandled rejection and discard the value. A synchronous block inside a getter cannot be bounded by a JavaScript timer.

The exact three getter names and order must be frozen in `getterSetId` before source acceptance. Their support, read-only character, and side effects remain live unknowns.

## Output controls

Use per-attempt exclusive files, not replacement. Fixed names such as `sample-000001.json` make omissions and duplicates reviewable. Write a complete `0600` temporary file, `fsync` it, publish it with an exclusive same-directory hard link to the final name, remove the temporary link, then `fsync` the directory. Never overwrite or clean up an existing final file. Any collision or filesystem error terminates export.

Each sample envelope has exactly:

```text
schema
sequence
observedAt
state
binding
result
failureClass
observation
```

`state` is always `unqualified`. `binding` has exactly the bootstrap binding fields. `result` is `complete` or `failed`. `failureClass` is null or one of: `unsupported`, `rejected`, `timeout`, `identity_changed`, `shape_invalid`, `limit_exceeded`, or `io_failed`. No error message, stack, code, getter argument, or rejected value is retained.

`observation` is null on failure. Otherwise it has exactly: `cachedProvider`, `providerSource`, `reportedModel`, `rules`, `workspaceGrants`, `errorCount`, and `host`. `host` has exactly: `mode`, `event`, `spawnRoute`, `cwd`, `grantCount`, and `pendingCount`. Selection uses named property reads only; spreads, generic serialization, recursive copying, and arbitrary source keys are forbidden.

The frozen input does not supply the accepted projector’s nested rule and workspace-grant key names. The schema version must enumerate those keys explicitly in source and tests. Generic rule or grant objects are not acceptable.

Recommended bounds are 16 KiB per sample, 64 KiB for the whole run, 32 rules, 32 workspace grants, 256 UTF-8 bytes for ordinary strings, and 1,024 bytes for `cwd`. Counts must be nonnegative safe integers; `notInEffect` must be boolean. Reject control characters and invalid types. Do not truncate over-limit arrays or strings because truncation could imply complete permission data; emit `limit_exceeded` with no observation.

A strict reader opens files without following symlinks, validates regular-file type, owner, `0600` mode, single link, size, schema, exact keys, enums, and bounds, then checks the same descriptor again after reading. It rejects unknown, missing, duplicate, or prototype-sensitive keys. Bootstrap and reader documentation must state:

- another process with the same UID can tamper with the adapter, arm, or output;
- nonces and hashes provide freshness or byte identity, not authentication;
- the observation is neither qualification nor proof of effective account, model, permission completeness, route, or cwd semantics;
- projected rules, grants, and cwd may still be sensitive.

These controls reject ordinary symlink, ownership, and permission mistakes. They do not claim hostile-path resistance against malicious same-UID code.

## Required synthetic evidence

At the public adapter/exporter seam, tests should demonstrate:

- importing the module has no side effects and executes no app modules;
- disarmed, absent-target, stale-arm, and malformed-arm paths call no getters;
- lookup uses only the supplied exact task ID and never enumerates or auto-selects;
- every binding field is checked, including query reference and generation;
- query or Code-ID changes, including away-and-back changes, discard the observation and terminate the arm;
- no getter overlap occurs, no more than three calls occur, and call order matches `getterSetId`;
- rejection and timeout prevent later getter invocation;
- late resolution after timeout cannot export or restart sampling;
- canary prompts, transcript text, environment values, credentials, raw errors, and random object keys never cross the projector;
- every output key and nested key is schema-enumerated;
- array, string, depth, integer, and total-byte limits fail closed without truncation;
- symlink, wrong-owner, permissive-mode, non-regular, multi-link, unexpected-entry, and existing-final-file cases are rejected;
- exclusive publication never replaces an existing sample;
- failure files contain only the fixed class and binding metadata.

## Later probe gates

A live probe requires separate operator approval for the copied-ASAR execution and patch, restart, disposable task and exact short prompt, target identifiers, the named getters and their order, timing and sample limits, projected cwd/rule/grant exposure, output retention, and cleanup.

Before invoking any getter, the later probe must tie the reviewed adapter and copied ASAR hashes to the launched bytes; identify the exact source hooks and task lookup; confirm the patch adds no IPC/network listener, setter call, permission-setting change, session enumeration, or raw-payload logging; and rerun the synthetic seam suite against that revision. It must report getter support and observed effects as probe evidence, not assumptions. It must not claim an effective account, reported-model correctness, complete permissions, route qualification, or cwd meaning unless separately established.

## Consequential choices for the operator

The operator must decide whether to authorize any live getter invocation while getter support and effects remain unknown; approve the exact getter set, order, and timeout behavior; approve exporting potentially sensitive cwd, rule, and grant fields; and choose retention and deletion handling. Restart-per-arm is the recommended policy.

Principal residual risks are same-UID tampering, uncancellable or blocking getters, build-specific hook drift, sensitive allowlisted values, and mistaking source-reported state for effective state.

This is design guidance for a source-only candidate, not an independent source acceptance or live qualification pass.

DONE_WITH_CONCERNS