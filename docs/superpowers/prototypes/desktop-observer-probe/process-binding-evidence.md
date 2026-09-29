# Binding a query report to a local process

Desktop retains a PID reported by a specific Code query. The inspected source
does not supply a complete OS-backed association from that query to an
executable. The probe must retain that distinction when identifying its Code
dependency.

## Existing source producers

In `.vite/build/index.chunk-B9SZqsi8.js`, at zero-based byte 1566124, the local
session path calls the captured query's `initializationResult()`. Its
continuation reselects the task and rejects a replaced query before considering
the returned `pid`:

```js
let i=this.sessions.get(r);
if(!i||i.query!==e)return;
ZT(i);
let a=n?.pid;
typeof a==="number"&&t.bl(a,r)&&
  (i.cliPid=a,i.cliPidAtMs=Date.now())
```

`cliPidAtMs` is the time the report was recorded, not a process-start identity.
Published SDK `0.3.284` declares `Query.initializationResult()` but does not
declare `pid` in `SDKControlInitializeResponse`. This producer is an internal
dependency requiring its own compatibility assessment.

In `.vite/build/index.chunk-DuaKZOPP.js`, `t.bl` exports `Oti` (byte 5124588),
which associates a PID with a task and asynchronously requests native creation
time. `t._l` exports `Iti` (byte 5125928), which returns `{creationTime,gone}`
only for a matching task owner. `Brn` (byte 3025281) invokes
`@ant/claude-native.readProcessCreationTime(pid)` when available and otherwise
returns null. These JavaScript files do not establish the native method's Linux
support or units.

Registry sampling can detect a later creation-time mismatch. Missing creation
time does not establish continuity, and PID reuse before the asynchronous
capture remains unresolved.

## Session lineage and reported version

The manager's `handleInitMessage(e,r)` (byte 1518617 in the manager chunk)
checks `i.query !== e.queryObj` before processing initialization data. It records
`r.claude_code_version` as `cliReportedVersion` and validates/adopts
`r.session_id` as `cliSessionId`. Those are query-bound reports. The manager's
prior-session and rewind records supply recorded lineage rather than an
independent account of process history.

The manager also has an internal `get_binary_version` request path (`MM`, byte
819230). It reports a version and does not yield an executable hash. The
proposed three-getter probe does not include this additional request.

`applyFreshBinaryPath` selects an executable and may introduce a launcher;
`spawnSessionQuery` creates the query. The inspected boundaries do not retain
the actual local `ChildProcess` handle. A selected path or a process tree alone
cannot establish that the selected query runs that executable.

## Required probe disposition

The app projection can retain query-bound `cliPid`, Code session ID, reported
version, and task-owned creation-time evidence with their intervals and unknowns.
`selected-executor-linux-identity.mjs` supplies a separate bounded observer for
the reported PID. It acquires the selected sample through `readProbeSample`,
checks that both host snapshots carry the same report, and retains the sample's
binding, sequence, and collection interval. Its live entrypoint fixes the
process root to the Linux process filesystem. The expected UID must match the
calling user, and the selected process directory must have that owner before
any process file is opened. It reads the selected process directory metadata,
three bounded `stat` samples, and the executable through two opens of `exe`.
It hashes at most 256 MiB and compares start, owner, and executable metadata
around the read. It then reacquires the same sample with a fresh timestamp and
requires unchanged evidence. It never enumerates processes or follows a
different PID. Synthetic checks exercise these controls; live use remains
unqualified.

The app exports the query-bound retained report in each host snapshot. The
Linux helper is a separate, explicitly invoked consumer; the sidecar neither
imports nor invokes it. The report, app identity, and Linux observation remain
distinct. Even matching observations leave query-to-OS association unknown.
The executable digest describes bytes read from an inode, not a complete
attestation of the launched image, interpreter, libraries, or ancestry.

The later authorization must name the exact process fields and data access
before such a read. Missing or mismatched identity evidence must remain unknown;
a successfully parsed PID does not resolve the complete association.

## Source identity

An independent read-only scout inspected these exact sources:

| Source | SHA-256 |
| --- | --- |
| Manager chunk `index.chunk-B9SZqsi8.js` | `bd2144a3653bb843f4b75fe652124a4e478f273b5f6c2e10a2139fa3a9a3152f` |
| Companion chunk `index.chunk-DuaKZOPP.js` | `f160a24940ee11cea6a788a9038e95c14fb150889977dcfa331fd9b07aba0c96` |
| Published SDK `sdk.d.ts` | `048ae2e6c796cc2aa3c423afaad59a08972cb48c271ffcc9847d910ff65f61b2` |

No live process, environment, credential, task record, or receiver data was
read for this investigation. No app module was executed.
