# Bind the fixture executor and acquisition directory

**DONE_WITH_CONCERNS.** The retained source supports a narrowly selected Linux process witness for the fixture's actual native Code executable, with an optional single registry record to strengthen the Desktop-to-Code join. Desktop constructs the metadata directory from its own user-data root and manager account/organization pair. Those current values require an independently supplied binding or a small app observation; the hook's socket and Code config home do not supply them.

This is a source design for [fixture executor and acquisition scope](https://github.com/nisavid/provingkit/issues/410). No process, private profile, registry, executable on the live host, socket, hook, task, or receiver was observed. The design supplies a concrete later acquisition proposal, not permission to perform it.

## Controlling inputs and source identity

I consumed the published collector, command contract, fixture procedure, reconciled findings, and retained identity/runtime investigations at repository revision `e971ae6fde6f4f4fa0b603e3a08bd0369b9481c6`. In particular:

- `docs/superpowers/prototypes/receiver-evidence/collector.mjs`;
- `docs/superpowers/prototypes/receiver-evidence/collector-contract.md`;
- `docs/superpowers/prototypes/receiver-evidence/fixture-check-procedure.md`;
- `docs/superpowers/research/2026-10-03-receiver-collector-findings.md`;
- `docs/superpowers/research/2026-10-03-receiver-collector-sources/runtime-first.md` and `runtime-cross.md`;
- `docs/superpowers/research/2026-10-02-reader-hook-sources/identity-first.md` and `identity-engine.md`.

The accepted [experiment decision](https://github.com/nisavid/provingkit/issues/397#issuecomment-5972295427) remains controlling. Full account/model/applied-permissions/worktree/cwd qualification remains separately required. This smaller fixture design cannot replace it.

All offsets below are zero-based, half-open byte spans in the named retained member. I recomputed the member lengths and SHA-256 values:

| Name | Retained source member | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| Manager | Desktop `.vite/build/index.chunk-B9SZqsi8.js`, retained as `manager-pristine.js` | 1,596,495 | `bd2144a3653bb843f4b75fe652124a4e478f273b5f6c2e10a2139fa3a9a3152f` |
| LocalSessions | Desktop `.vite/build/index.chunk-COPWZCsC.js` | 74,622 | `b22a9dc34684cef348f9c0e72abe88c433bbfc2d350d9a3e61faf7ae22858950` |
| Desktop core | Desktop `.vite/build/index.chunk-DuaKZOPP.js` | 6,751,779 | `f160a24940ee11cea6a788a9038e95c14fb150889977dcfa331fd9b07aba0c96` |
| Serializer | Desktop `.vite/build/index.chunk-CKt-cwRV.js` | 648,655 | `dad88ac66fe13f72d0225c49d48e124d238ff643ff96426c4a2020482621e62d` |
| Public SDK | Stable SDK 0.3.284 `sdk.mjs` | 1,159,746 | `32d062c37b03e10870fbf839f54694545ee01bc0ec719e47078fbed76e30ef71` |
| Code RC | Decompressed Linux x64 Code 2.1.284 artifact, read as data | 243,059,896 | `dee301c3e248c62137cc15aafc2781bd5316c66720dd890d72e0054a024ce7d9` |

Desktop declares version 2.9939.4, commit `a166d8a7c640e65ad825ebfb99d74ccbb9c8940d`, and targets Code 2.1.284, commit `16cbb4ddeeb473f57fd8d5b713764903d7928e66`. The declared SDK wrapper is `0.3.284-rc.20260927.t043816.sha16cbb4d`; the stable SDK is a separate input, not a demonstrated match to that wrapper. These declarations do not identify any selected live executor.

## Concrete execution chain

### Desktop session to Code process

Manager `buildSessionEnv` sets `CLAUDE_CODE_HOST_SESSION_ID` to its Desktop session argument after constructing the spawn environment. Source: Manager [1,321,560, 1,322,620). The metadata association is produced independently: `handleInitMessage` maps the Code-reported `session_id` into the held Desktop record's `cliSessionId` and saves that record. Source: Manager [1,520,100, 1,521,900).

The native Code initialization result supplies `pid: process.pid` in `Zc`. Source: Code RC [221,256,750, 221,258,600). Manager `setupQueryHandlers` takes `initializationResult().pid` only for a local backend and only while the session's query is the same query object. It then records `cliPid` and `cliPidAtMs`. Source: Manager [1,565,500, 1,566,750). Teardown clears the query/input stream and retires the PID tracking. Source: Manager [1,034,800, 1,038,500), with `ZT` around [634,919, 635,100).

That is an existing app-side PID producer. It is available to a proposed observer inside the already loaded app; the inspected external interfaces do not establish a passive connection exposing it to this source task. Calling a new SDK query, resume, or direct-connect initialization would introduce other effects and would not witness this selected query.

Manager `applyFreshBinaryPath` resolves the requested binary, then can route execution through a host CLI launcher or another launcher. Source: Manager [1,285,600, 1,289,250). A requested path, pin, or launcher child PID is therefore weaker than the Code-reported PID followed by an executable observation.

### Code Stop to command hook

For an ordinary Stop, `Tc` supplies the session's Code ID, transcript path, cwd, and permission mode. A served-call branch instead emits a `served:` identity. Source: Code RC [207,318,493, 207,319,450). The published collector correctly keeps initial identity unbound and excludes that known served kind.

The command dispatch passes `Vee(n)` into `y0`, so the hook-input session ID is also the input to the child-environment builder. Source: Code RC [207,377,300, 207,378,500). `ZLe` constructs:

| Child value | Source meaning |
| --- | --- |
| `CLAUDE_PID` | `String(process.pid)` of the Code process dispatching the command |
| `CLAUDE_CODE_SESSION_ID` | The supplied hook-input session identity |
| `CLAUDECODE` | `"1"`, marking a child context |
| `CLAUDE_CODE_CHILD_SESSION` | `"1"`, marking a child context |
| `CLAUDE_CODE_SESSION_ATTENDED` | Derived attendance state |

Source: Code RC [203,572,506, 203,572,856). Neither `CLAUDECODE` nor the child-session flag is the Desktop identity.

`y0` builds the command environment from the selected base or `hs()`, extra environment, `ZLe`, and the project directory. It uses `spawn` imported from `child_process` at byte 205,652,765. With `args`, it spawns an executable directly; ordinary shell-form settings commands use `shell: true` on Linux. A configured shell prefix can add another launcher. Code writes the serialized event and closes the child stdin. Sources: Code RC [207,328,962, 207,335,850), [205,652,600, 205,653,100).

The ordinary local chain is consequently:

```text
Code engine P
  -> command-hook shell or reviewed launcher, if present
  -> pinned Node collector C
```

A direct exec-form hook can omit the shell. The collector's `process.pid` identifies C; its immediate parent can be a shell. `CLAUDE_PID` names P in the assessed producer. A bounded ancestry check can test that P is actually an ancestor of this invocation, instead of assuming that C's immediate parent is Code. These are ordinary process/interface observations, not authenticated producer claims.

The hook environment can contain `CLAUDE_CODE_HOST_SESSION_ID` inherited from Desktop and `CLAUDE_CODE_MESSAGING_SOCKET` exported by the engine. `hs()` and selected hook contexts can alter inherited values, so their presence must be observed. Source: Code RC [199,362,860, 199,366,950), [207,332,500, 207,334,500). The inbox binds first, exports the actual path, and clears it on teardown. Source: Code RC [221,440,600, 221,444,000), [221,457,200, 221,459,500). Socket basenames can change because of collisions or path-length fallback; a PID parsed from a socket filename is not an executor witness.

## Recommended executor observation

For a local native Linux fixture, propose adding a bounded witness to the same admitted hook invocation. Keep it a separate output facet from the unbound Stop observation. The existing collector selects only the socket variable and performs no process reads; this recommendation requires new source, synthetic checks, integration review, and a later positive grant.

### Acquisition proposal

The following numeric limits are proposed design inputs, not existing acceptance requirements or authorized reads.

| Acquisition | Proposed exact selection and bound | Retained meaning |
| --- | --- | --- |
| Hook environment | Select `CLAUDE_PID` (at most 10 ASCII digits, integer from 2 through 2,147,483,647), `CLAUDE_CODE_SESSION_ID` (256 UTF-16 code units), `CLAUDE_CODE_HOST_SESSION_ID` (78 ASCII characters), and the existing socket value (4,096 UTF-16 code units). Acquire no process environment file. | Asserted invocation values, each with missing/oversized/invalid gaps |
| Ancestry | Starting at collector C, read `/proc/<pid>/stat` for C, at most four intermediate parents, and the single candidate P: at most six distinct PIDs. Stop when P is reached; never continue above P or search siblings. | Parsed PID, state, parent PID, and raw start-time token |
| Stat bytes | At most 8 KiB plus one overflow byte per read; at most two reads per selected PID for before/after checks, hence at most twelve reads. The grant covers every byte of each stat record, not only the retained fields. | Process identity and observed parent edges over recorded intervals |
| Executable link and target metadata | For P only, at most two link reads of `/proc/<P>/exe`, each using a 4,097-byte buffer and rejecting more than 4,096 bytes; at most two target-metadata observations of that same proc entry. Record link text, target device/inode, and intervals. | Executable pathname/object observations; a pathname alone is insufficient for the assessed build |
| Executable content | Open `/proc/<P>/exe` once as data, obtain descriptor metadata, and require the expected native artifact size before hashing. Bound the read to 243,059,896 bytes plus one overflow byte, require EOF, and compute SHA-256. Record device/inode, size, and relevant change times before/after. | The executable object opened for P and its exact-byte comparison with the assessed RC artifact |
| Namespace scope | Use only the local namespace in which the collector runs. If P cannot be reached in that namespace, report unavailable/mismatch; do not translate or scan another namespace. | The limit of this local witness |

The ancestry budget counts the engine and collector as well as intermediates. A longer wrapper chain yields a gap, not an automatic increase. The parent records expose command names and all other stat fields within the byte cap; the executable link exposes a pathname; the executable read acquires the whole native binary. Retaining only hashes does not reduce those acquisitions.

Linux documents `stat` parent PID and start time as distinct fields. The Code producer's `Wre` takes field 22's raw token after the last closing parenthesis, and `Il` reads that token from `/proc/<pid>/stat`. Sources: Code RC [198,539,201, 198,539,750), [199,152,205, 199,153,300). A parser must handle the parenthesized command field rather than split the whole line naïvely. [Linux stat interface](https://man7.org/linux/man-pages/man5/proc_pid_stat.5.html).

Linux's `exe` link opens the process executable; an unlinked executable can have a ` (deleted)` pathname suffix. Hash the opened executable descriptor, not a separately reopened pathname obtained from the link. Permission denial or unavailable process state remains a gap. [Linux executable interface](https://man7.org/linux/man-pages/man5/proc_pid_exe.5.html).

The native artifact is roughly 243 MB, so hashing it has a real I/O and latency cost. No duration was measured here. Keep the existing stdin acquisition deadline's meaning intact; do not quietly charge an unmeasured binary read against the five-second suggested input window or represent it as a total deadline. Specify a separately bounded observation stage and its failure output in the reviewed implementation. If the process disappears before that stage, preserve the completed event with executor evidence unavailable.

### Supported join

A successful prospective record would require all of these observations:

1. The independently selected UI task and dedicated project display the approved whole setup response.
2. The unbound Stop record has complete admitted input and that exact response, with ordinary hook identity E.
3. The hook's bounded `CLAUDE_CODE_SESSION_ID` equals E; its valid `CLAUDE_PID` is P.
4. The observed parent chain from C reaches P within the declared bound, with consistent PID/start-time checks.
5. P's opened native executable matches the assessed artifact's length and SHA-256, with before/after proc-target object identity agreeing with the opened descriptor. A different hash or observed replacement means the assessed compatibility has not been demonstrated.
6. Exactly one authorized metadata candidate has current `cliSessionId = E`, an agreed project binding, and filename/object Desktop identity S.
7. If available, the hook's host ID and the selected registry record's host ID equal S. Missing values remain explicit gaps; they are not fabricated from the metadata.

Step 5 distinguishes the actual observed executable from an intended pin. For an interpreter-based engine, `exe` would identify the interpreter, not the loaded Code script. Do not substitute a guessed script pathname or installed package hash. Return that named gap for a separate exact script/module observation or app design.

This witness does not prove that the binary stayed unchanged throughout the model turn, that every runtime module matches its source artifact, or that a same-PID exec never occurred between observations. A stable start-time token handles PID reuse; it does not detect every exec. The supported statement is a process/executable observation near this admitted hook invocation, joined to the independently witnessed fixture, with its actual intervals and any lifecycle gaps.

## Optional single registry record

A registry record is useful supporting evidence when its root can be supplied independently. It cannot replace executable hashing.

### Exact path formula and producer

In the Code RC, `Se` resolves the config home as:

```text
R = NFC(CLAUDE_CONFIG_DIR ?? join(os.homedir(), ".claude"))
registryDirectory = join(R, "sessions")
registryRecord = join(registryDirectory, String(P) + ".json")
```

Sources: Code RC [197,642,650, 197,643,150), [199,377,873, 199,378,100), [200,583,000, 200,586,900). The nullish choice is part of the source formula. R is Code's config home, not Desktop's user-data root, and is not an account/organization metadata directory.

Registry `ND` writes the engine PID, current Code session ID, cwd, started time, `procStart`, version string, peer protocol/features, kind, entrypoint, optional `hostSessionId`, `pidDomain`, messaging socket, name metadata, log path, agent/job/spare fields, and optional tmux value. Subsequent updates merge into the existing serialized record. A session adoption updates `sessionId`; cwd/name/status/socket can also change. Source: Code RC [200,583,000, 200,588,300).

`N6n` includes a host ID only for a qualifying host/main context, and validates it with `/^local_[0-9a-f-]{8,72}$/`. Sources: Code RC [200,576,500, 200,577,100), [200,587,025, 200,587,160), with context predicates [197,875,000, 197,877,000). Absence is possible. Version is a string, not a binary digest.

A storage-backend branch writes the session key through the supplied storage interface instead of this raw file path. A missing exact raw record must remain unavailable; it does not justify backend enumeration or a broad fallback.

### Additional scope to propose

Receive an exact absolute R as a supplied binding. Do not reconstruct it from a possibly filtered hook HOME/config value, private settings, or a parent-directory scan.

Read exactly `registryRecord`, with no listing: at most 256 KiB plus one overflow byte per complete acquisition, at most two acquisitions for a stated before/after comparison. This cap matches the source reader's `Z8e = 262144` ceiling. Source: Code RC [199,163,300, 199,164,750). Check regular-file/opened-file identity, complete JSON, and filename PID versus serialized PID. This adds one private registry file, up to 524,290 acquired bytes across two reads, beyond the accepted Desktop metadata directory.

Acquire the entire selected serialized record, including optional names, former names, log paths, status/detail, waiting state, and any other fields present within the bound. Retain only approved identity/provenance fields; do not open log paths, job directories, transcript paths, socket key files, or paths named in the record.

Compare its `sessionId` with E, `hostSessionId` with S if present, socket with the event endpoint, and `procStart` with the observed Linux start-time token for P. `pidDomain` is an opaque source value in this proposal: do not claim independent host-domain verification. Its source producer can read machine ID and PID-namespace links; obtaining those for comparison would be a separate acquisition.

Do not call `F`, `u3`, `fOr`, `XMt`, `ListAgents`, or a wrapper around them. The inspected helpers list other records; some test processes or sockets and delete stale records. Sources: Code RC [204,386,076, 204,391,200). Implement the exact-file read independently under its declared scope.

Registration time and update time are not the hook's production time. A valid record without the process/executable checks proves a recorded association, not present execution or present peer admission.

## Bind one Desktop account/organization directory

### Source formula

The Code manager is instantiated with Desktop core's `sW = "claude-code-sessions"`: Manager ends with `new aF(t.By)`, and Desktop core exports `By` as `sW`. Sources: Manager [1,593,000, 1,596,495), Desktop core [3,869,400, 3,869,900), [6,550,130, 6,550,280).

Manager stores `app.getPath("userData")` in `userDataPath`. Source: Manager [870,200, 870,700). Its metadata path formula is:

```text
U = selected running app's manager.userDataPath
B = "claude-code-sessions"
A, O = selected manager's currentAccountId, currentOrgId
D = join(U, B, A, O)
metadataFile(S) = join(D, S + ".json")
```

Source: Manager `getStorageDir`, `storageDirFor`, and `getSessionFilePath`, [919,200, 919,920). A parked task uses its recorded account/org pair; a newly created active fixture should be bound through its own selected manager state, not a parked record from another account.

The manager superclass resolves its account/org pair, flushes prior saves, changes the held pair, and reloads sessions. Source: Serializer [451,900, 454,050). Its account resolver maps to Desktop core `Mk`; the org resolver maps to `Dk`. `Mk` can use a provider override, current account details, an IPC wait, or bootstrap fallback. `Dk` can use cached/overridden org state or the default session's `lastActiveOrg` cookie. Sources: Desktop core [3,010,750, 3,012,600), [3,014,200, 3,015,850), [3,021,638, 3,022,900), export aliases `WM`/`RM`.

Calling those resolvers can perform additional private or network acquisition. A narrow app observation should read the already bound manager fields and selection/lifecycle state, not call account resolution or trigger loading.

The retained inputs do not establish the current U, A, or O on this host, nor a public selected-profile control returning all three. A profile label/title is not U. The retained core uses `CLAUDE_PROFILE` in window titles, while several profile/path helpers have other purposes; do not infer the metadata root from that label or choose a sibling-profile fallback. Source: Desktop core [652,900, 655,800), [1,109,200, 1,112,800).

### Smallest route: explicit operator binding

Before fixture creation, obtain this concrete supplied tuple:

| Input | Required content |
| --- | --- |
| Selected profile | The exact running Desktop profile/window and the independently known absolute U, with the source of that binding |
| Selected manager pair | Exact account directory token A and organization directory token O for the intended active Code manager, with the observation or operator knowledge establishing the pair |
| Directory | Exact D and a check that it equals `join(U, "claude-code-sessions", A, O)` |
| Fixture scope | Exact dedicated project, normal-UI selection region/actions, approved setup token, observation window, and required lifecycle recheck |
| Executor scope | The selected process-witness alternative, named environment values, all path formulas, and byte/process/read limits |

The supplied tuple must describe current selection, not a path guessed from existing files. The source task needs no parent listing or private settings read to receive it. Before the live proposal, the coordinator must either obtain that binding or identify it as missing.

Later verification checks the supplied D's directory identity under the granted path, preserves it across the bounded listing/read interval, and joins the normal-UI fixture response to E and exactly one current metadata candidate S in D. Filename S must equal serialized `sessionId`; current `cliSessionId` must equal E; project fields must agree with the fixture's declared project/worktree semantics. A prior/historical Code-ID match is explanatory only.

The successful join supports that this independently witnessed fixture is associated with this supplied directory. It checks the operator tuple's consistency with the fixture. If U/A/O have no independent provenance, retain the narrower result as association with a declared directory; do not describe it as verified selected-profile binding or an authenticated inference account.

### App observation for the missing binding

If the operator cannot supply U/A/O independently, the smallest named app gap is a selection-bound projection from the existing Code manager:

- selected Desktop session S and its active/parked classification;
- manager `userDataPath` and `baseDir`;
- manager `getAccountIds()` and the selected task's `storageDirFor(S)` / `getSessionFilePath(S)`;
- current `cliSessionId` and, once initialized, `cliPid`;
- an observer-local query identity token and before/after lifecycle/selection comparison.

For a new active fixture, require the current manager pair rather than silently accepting the parked branch. No session enumeration, metadata listing, account resolver, or transcript read is needed to calculate this projection. `getAccountIds` is a direct getter in the assessed superclass. Desktop core `_C()` peeks the already loaded Code manager; it does not itself load one. Source: Serializer [450,000, 451,000), Desktop core [2,350,500, 2,351,100).

This projection is a proposed adapter inside the app, not an established external callable observer. Its output could bind D before listing, and its Code-reported PID could independently select the same P as the hook. It would still need the executable observation to bind assessed bytes. Patch/installation, exposure mechanism, any restart, selection integration, retention, and restoration would need their own exact proposal and grant. The prior adapter's deadline and restart allowance do not carry over.

### Scope that parent discovery or settings would add

If a preparation-read alternative is considered, enumerate it explicitly. For example, one nonrecursive listing of `join(U, B)`, followed by one operator-selected account directory listing, each capped at 128 entries plus one overflow entry, would acquire names/types for account and organization candidates outside D. It can nominate a directory; it does not establish which pair is active. Do not list every account's organizations.

Reading `join(U, "config.json")` would acquire a private settings object, not just any retained identity fields. A hypothetical whole-file proposal would need an exact path, an independently supplied U, a declared byte ceiling such as 1 MiB plus one overflow byte, and all acquired contents in its exposure scope. The retained account path uses current details and possible bootstrap fallback; the org path uses state/cookies. A cached account key or a settings read alone cannot be treated as both current manager values. No settings or cookie acquisition is recommended by the minimal route.

These are additional possible scopes for a decision. Neither belongs to the accepted one-directory discovery grant.

## Preserve the accepted metadata bounds

Inside the single independently bound D, keep:

- one nonrecursive streaming listing of at most 128 entries plus one overflow entry;
- at most three explicitly selected regular JSON basenames;
- each whole file capped at 1 MiB plus one overflow byte;
- opened-file identity/size checks and complete JSON validation;
- no dereference of values found in metadata.

The serializer `nE` persists the Desktop/Code IDs and project/lineage information alongside titles, settings, grants, reminders, summaries, errors, remote/MCP details, and other emitted fields. Source: Serializer [503,942, 509,796). The acquired object is the entire selected file. A metadata field alone does not establish the running app's current directory pair or actual executable bytes.

Candidate selection may use an independently supplied host/Desktop ID to nominate a basename after the bounded listing. Without it, the operator selects at most three candidates under the reviewed rule. New filenames, titles, and mtimes are candidate hints, not identity proof. No match within that set does not prove that no fixture metadata exists elsewhere.

The registry file and process/executable observations are separate additions. Their acquisition cannot be hidden inside these metadata caps.

## Comparative choice and live costs

| Alternative | Useful evidence | Added scope/effects | Remaining gap |
| --- | --- | --- | --- |
| Hook PID plus bounded ancestry and native executable | Actual process and executable near the admitted Stop invocation; no broad process or registry listing | Up to six PIDs, twelve bounded stat reads, two executable-link observations, one whole native executable read; new witness source and later hook integration | Supplied profile directory and independent UI/metadata join; wrappers/namespaces/interpreters can make witness unavailable |
| Exact PID registry record plus executable | Recorded Code/host/socket/start-time association supporting the process witness | One independently rooted registry file, up to two 256 KiB plus overflow reads, in addition to executable/process scope | Registry root, availability, freshness, and actual executable still require independent checks |
| Existing app fields through a new narrow adapter | Selected profile directory, selected query/Code ID, Code-reported PID, and lifecycle comparison | Selected in-memory field projection, new access mechanism, possible patch/restart/restoration; executable scope still needed | No demonstrated external observer; actual app integration/effects remain unselected |
| Parent listings or private config discovery | Directory candidates or cached settings evidence | Explicit additional directories/files and their complete bounded contents | Does not by itself bind active profile/account/org; broader than a supplied binding |

For the ordinary local native case, I recommend the first alternative with an independently supplied directory tuple. Add the exact registry record only if its extra host-ID association is needed and R is independently available. Use the small app projection for the specific missing U/A/O or selected-query/PID access gap; do not select it merely because the binary witness or a required runtime producer is missing.

## Order, intervals, and partial outcomes

Before fixture creation, bind the published source, exact hook/launcher bytes, Node identity, intended artifact identity, dedicated project, operator directory tuple or selected app-observer design, added acquisitions, numeric caps, output slots, setup prompt, lifecycle recheck, and restoration/disposition. Current fixture S, E, P, and an actual executor hash are not yet known. Expected values are prospective compatibility targets.

During the separately authorized setup turn, capture the independently selected UI response and unbound event. Observe the named hook values and bounded process/executable witness while the invocation is present. If selected, acquire only the PID-derived registry record. Acquire the authorized Desktop metadata candidates afterward, joining their current identity to E and the declared project. Do not spend a second setup turn to repair an unavailable witness.

Record separate intervals for UI selection/response, event receipt, every process/link/content observation, registry reads, metadata reads, and lifecycle recheck. Use monotonic elapsed measurements as well as wall-clock ordering where the new implementation needs them. Bind a maximum allowed join age and the exact recheck in the later packet; this source task supplies no inherited deadline. A later file read does not freshen the original event.

Linux notes that an opened proc descriptor does not prevent PID reuse; operations through descriptors associated with a dead process do not act on its replacement. Use held descriptors where practical and compare start tokens rather than repeatedly selecting a bare PID after a delay. This does not create an atomic snapshot. [Linux proc lifecycle semantics](https://docs.kernel.org/filesystems/proc.html#process-specific-subdirectories).

Do not add `/proc/<P>/environ` to seek only selected keys. It contains an initial environment and can miss subsequent environment changes, including later socket export. Reading/filtering it would acquire other entries too. The proposed route selects named values from the admitted child invocation instead. [Linux environment interface](https://man7.org/linux/man-pages/man5/proc_pid_environ.5.html).

Retain these outcome facets separately:

| Facet | What a positive observation supports |
| --- | --- |
| UI/Code association | Selected fixture response joined to E and a unique current metadata match among the authorized candidates |
| Supplied-directory binding | The above fixture associated with D, with independent U/A/O provenance stated |
| Event-time endpoint association | The bounded endpoint from this admitted invocation joined to that fixture |
| Executor identity | The observed process/executable and assessed-artifact comparison over its recorded interval |
| Hook activation/collection | Actual command/input/EOF/output behavior observed in the fixture |
| Lifecycle recheck | Only the checked selection/query/process state and interval |
| Restoration/disposition | Verified removal of the introduced entry and agreed fixture/run-file closeout |

A successful UI/Code join with an unavailable executable check remains partial. An executable match without the independent UI/metadata join identifies a process, not the fixture. A registry match without executable evidence remains a recorded association. A valid event endpoint does not prove that the same socket/query is current afterward or that a current peer admits a message.

No atomic snapshot is required. Full qualification, affected requalification, delivery consent, current-peer admission, account/model/full permission state, and notification acknowledgment remain separately required. There is no automatic resend or setup retry after an uncertain outcome.

## Smallest remaining decision and downstream contract

The smallest next decision is whether the live preparation packet can receive an independently known U/A/O/D tuple and cover the hook-selected local process/executable reads. If the tuple cannot be supplied, select or decline the narrow app projection for that exact binding gap. The optional registry record is a separate addition; it is not required merely to avoid broad scanning.

The current published collector does not implement this witness. [Probe preparation](https://github.com/nisavid/provingkit/issues/278) must integrate the selected design, freeze the resulting source, review the new acquisition/effects and relevant security controls, and bind exact inputs before a live authorization proposal.

Under `capturing-agent-procedures`, capture the reviewed selection, producer spans/source identities, entry tuple, exact limits, interval/partial-result rules, actual later observations, and cleanup evidence at the final revision. The downstream preparer must load that captured revision and the existing collector/procedure before constructing the packet, and return corrections to the same source.

I used `research`, `capturing-agent-procedures`, and the read-only checkpointing rule. The documentation check was limited to generic primary Linux process semantics. Retained artifacts were read as data; no vendor code was executed/imported, no tests were run, no files were edited, and no tracker or live receiver action was performed. Authentication, containment, resistance to hostile processes, and private-data protection are not certified by this ordinary source/interface design.
