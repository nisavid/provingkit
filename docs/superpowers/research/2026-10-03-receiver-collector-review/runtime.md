# Runtime review

The frozen candidate is clean within the assigned runtime scope. I found no current-contract contradiction or material risk over the documented regular configuration, Linux pipe input, synthetic environment, and trusted task-owned directory. This is a source/synthetic result, not live readiness or security acceptance.

## Review identity and verification

- Candidate manifest SHA-256: `e351c7b93edec24222ee3edb5edaaa28f0d0897ddbd3dce3871b29fa0823f369`.
- Requirements SHA-256: `32cc418581e34f9d006dcbc6ac5a5dbdd85b471905468dfadeddb4b2d8425535`.
- Comparison base: `88d1962aefdf40676148462fc495089fb18d1026`.
- Before and after review, I independently verified both identity digests and every one of the manifest's 27 file SHA-256 digests and byte counts. All matched; no binding changed.
- I applied Tricritical `runtime`, its input/output/invocation boundaries, topology, and runtime rubric. Candidate evidence came exclusively from the frozen snapshot. I used `git show` and `git cat-file` for immutable base comparison. The reader, projector, their tests, file adapter, fixtures, and demo source/build/output are byte-identical to base; the collector, collector tests, command contract, and fixture procedure are new. README and prototype contract changes point to the new command and preserve evidence limits.
- On Node.js `v24.21.0`, I ran `node --test docs/superpowers/prototypes/receiver-evidence/reader.test.mjs docs/superpowers/prototypes/receiver-evidence/hook.test.mjs docs/superpowers/prototypes/receiver-evidence/collector.test.mjs` from the frozen snapshot: 36 passed, zero failed, cancelled, or skipped.
- I also ran six independent command scenarios with invented inputs: exact byte ceiling, one-byte overflow, empty EOF, fragmented pipe delivery, competing invocations, and invalid argv. Each met the asserted output/exit/lifecycle behavior. I removed my disposable files and left no test child running.

## Findings

None within the assigned runtime scope. I make no finding or acceptance judgment about hostile paths, producer authentication, private-data protection, or live integration; these guarantees are explicitly excluded from this increment.

## Falsification attempts

1. **Acquisition boundaries and liveness.** I challenged `collector.mjs:49` with a 148-byte event at an exact 148-byte ceiling: acquisition completed at EOF and produced a candidate. Adding one byte produced `over_limit`, exactly 149 observed bytes, no EOF claim, and an unknown projection. Seven-byte fragments still produced the complete candidate; empty EOF produced an unknown record. The suite's stalled-pipe case independently passed and exited normally while its producer had not sent EOF. These observations support the bounded inherited-pipe interface without implying a total filesystem deadline or measuring unread producer bytes.

2. **One-shot ownership under competition.** I kept the first invocation's pipe open after its claim appeared, then started another invocation on the same slot. The second exited `1` without waiting for EOF. Feeding the first its invented event produced exit `0`, one claim, one complete result, and no partial file. This challenges the actual exclusive claim at `collector.mjs:88`, beyond the suite's sequential reuse check. It supports preventing reacquisition in that slot; deleting claims or creating a replacement slot remains a separate decision.

3. **Publication failure and interruption.** I traced exclusive partial creation, file synchronization, close, hard-link publication, and cleanup at `collector.mjs:32`. The passing suite preserved an occupied destination and an unrelated neighbor while removing the newly created partial file. Its `prlimit` write-interruption case published no result and retained the claim; its SIGTERM-during-input case left only configuration and claim. These outcomes support the documented distinction between completed output and interrupted artifacts. They do not establish host-crash durability or guarantee cleanup after an abrupt signal.

4. **False identity and false success.** I traced configured mismatches, malformed input, unbound setup admission, and served-session rejection through `collector.mjs:101-136` and the unchanged projector. The passing command checks retained no endpoint for a wrong task/event or served identity, kept unbound projection unknown, preserved optional-field gaps, and never converted setup text into qualified notification evidence. Invalid argv independently returned `1` without creating a claim or output. Exit `0` remains publication success, including explicit unknown observations.

## Limits and required later evidence

I ran only synthetic commands and test-owned child processes/files. I performed no vendor execution, private receiver read, socket connection, settings change, Desktop action, network request, or repository/tracker mutation. I did not attempt to qualify an actual receiver or to independently review all runtime-source semantic conclusions under the intent critic's scope.

The fixture procedure still requires exact integration bytes/environment, selected-executor and independent task witnesses, authorized acquisition paths, lifecycle observations, and the appropriate privacy/security review in preparation. Actual hook loading, Stop representation, early pipe closure and exit effects, and restoration require the separately granted live check. Full account/model/applied-permissions/worktree/cwd qualification, notification delivery, and correlated acknowledgment remain outside this scoped clean result.
