# Review of the receiver-observation lane handoffs

The three source-design handoffs have clean independent reviews for contract
fit, source accuracy, and architecture/operating costs. This is acceptance of
the research handoff. Component selection, implementation, and live
qualification remain open.

The reviewed [packet](2026-10-02-parallel-receiver-observations/README.md)
contains ten files, all bound by the snapshot below. The coordinator checked
all candidate hashes and modes again after the reviews. Report hashes match
the evidence manifest; relative links resolve; no machine-local paths remain;
whitespace checks pass. No new prototype tests or live observations were run.

The ordinary Tricritical review used fresh, separate leader-owned native
critics with GPT-6.1 Sol xhigh requested. The reports record same-leader
observations, without authenticated execution or product-enforced authority
attestation. The coordinator adjudicated no substantive findings. Every
selected scope has a current independent pass on the unchanged candidate.

The first contract and source critics read the memory registry while opening
their briefs, outside the frozen input boundary. Their reports were retained
and rejected as clean acceptance evidence. Fresh critics repeated those scopes
on the same candidate with the input restriction explicit in the initial
request. No first-review result was silently upgraded or used to replace a
missing pass. The architecture critic's independent pass remained applicable.

## Candidate identity

Snapshot SHA-256: `a296c062e617b879d5531c9d5b4518f6de6e81036bf8e508301f9eabd8e1f038`.

```json
{
  "docs/superpowers/research/2026-10-02-parallel-receiver-observations/README.md": {
    "mode": "0o644",
    "sha256": "8b2965f228881d043aa320c16d007a3faebe424c766ed074bdff66a53be7f196",
    "type": "file"
  },
  "docs/superpowers/research/2026-10-02-parallel-receiver-observations/app-final.md": {
    "mode": "0o644",
    "sha256": "e9c8cd602b347c6445c39cb325d3bfc151126931fcb78dcef866904cfcb924ff",
    "type": "file"
  },
  "docs/superpowers/research/2026-10-02-parallel-receiver-observations/app-first.md": {
    "mode": "0o644",
    "sha256": "8e47079da9e47d35482ea75810cde27d6b82217bfc1c17840e85c26b0d2c198e",
    "type": "file"
  },
  "docs/superpowers/research/2026-10-02-parallel-receiver-observations/evidence.json": {
    "mode": "0o644",
    "sha256": "7345aeb979b1e03a150ad6e1d300c6be1f3ecadfe7e4eb68c0609bef63e4a80c",
    "type": "file"
  },
  "docs/superpowers/research/2026-10-02-parallel-receiver-observations/existing-final.md": {
    "mode": "0o644",
    "sha256": "c174621cc01ce95cd9cecabc200daa27bcbd9ccc80873c64d1736c36324d6848",
    "type": "file"
  },
  "docs/superpowers/research/2026-10-02-parallel-receiver-observations/existing-first.md": {
    "mode": "0o644",
    "sha256": "c6043dc3b1ad469be964aa99ff538a59b4012a4cf6fe19eb1b671f12e1ca1e08",
    "type": "file"
  },
  "docs/superpowers/research/2026-10-02-parallel-receiver-observations/hooks-final.md": {
    "mode": "0o644",
    "sha256": "3127c5178c4c6b4489907749eb92698a16961fdbcd86e29d23eaddeda0ce1623",
    "type": "file"
  },
  "docs/superpowers/research/2026-10-02-parallel-receiver-observations/hooks-first.md": {
    "mode": "0o644",
    "sha256": "e6cbfdb10ada587a18147580d144c75269b2fbfaffc98f747ee6696f21ad39c4",
    "type": "file"
  },
  "docs/superpowers/research/2026-10-02-parallel-receiver-observations/method.md": {
    "mode": "0o644",
    "sha256": "ba172da3571c0b5c1a91001e8a0fe65b90e2a7b1f880403d95e2763c4ff7b7d0",
    "type": "file"
  },
  "docs/superpowers/research/2026-10-02-parallel-receiver-observations/source-correction.md": {
    "mode": "0o644",
    "sha256": "1eb4a98855ce64070b7cc687212e397e5476c20b49b680bd13c7230dff72f447",
    "type": "file"
  }
}
```

## Execution records

```json
[
  {
    "accepted": false,
    "plan_sha256": "9661f1bcbf0fa37e5964596b7e62a299dd6aca7c92b8ba4f90402b3bc876104b",
    "report_sha256": "d028b112ee39b45fc00a5aea32c137fffa1a9093c19bf9d13d9654cb7ff132d3",
    "scope": "intent",
    "selection_sha256": "dc4306c71805d1b911d1e945e024ea2569815855ea4b7f360f4590f3ef5c86fd"
  },
  {
    "accepted": false,
    "plan_sha256": "40a7ad7720f9e7362c5983fd09986242a2ac926cf7a815379a6e7e80834264bd",
    "report_sha256": "098036e46011986680d8e7f3ce9ba4b5aa43cfe3ea2f0ae58d80a1fa7b65d49f",
    "scope": "source",
    "selection_sha256": "597541cb5b88a08563bd81a5c77ef03f0484d0e74ef535d50efeb78d51888c58"
  },
  {
    "accepted": true,
    "plan_sha256": "f883f1bc223bc5832e588c8e8a0f1f42e08157564aeba75f9a0826bafb40cf67",
    "report_sha256": "f2e966531567a1108dc3895521e6758f961bdfe49b80054d6c86db47060bd5de",
    "scope": "architecture",
    "selection_sha256": "1bafc48e81cf790964a96c660c07ff985f3de4b6c940bc1514442f9d2f8b53e9"
  },
  {
    "accepted": true,
    "plan_sha256": "09c22fb1fcf3c1129897782694176a8733b500dc295054741bec5d17a0f829c1",
    "report_sha256": "6da979e8e8445784dff5e4f7d2102fa093030f8a6e83582ff0639a21d8a8fd62",
    "scope": "intent-retry",
    "selection_sha256": "3f8cc8678203aa85974c4bbba766b214cc6cb7e3d841a6bc6821b4d880e85081"
  },
  {
    "accepted": true,
    "plan_sha256": "a51effb46d9d4781e4f9fabbf8c7951fb8c0ac3520281e04a4366bcdb207b4cf",
    "report_sha256": "425d5224c70339ed89c5ea7ecec5b1cbf22b4445e8a3a55a64805df74eff67ab",
    "scope": "source-retry",
    "selection_sha256": "0a717b05191645b9e109a36d97a591f1b29a14491b7e674aa7968401785a8d02"
  }
]
```

The reports below retain their wording with trailing whitespace removed for
publication. Execution-record digests identify the original captured text.

## Accepted critic reports

<details>
<summary>Contract fit</summary>

## Findings

**PASS for the selected Tricritical intent scope.** I found no actionable contradiction in the current three-lane research handoff. The packet supplies partial observation candidates, preserves the accepted qualification requirements, and leaves component selection with the operator. This verdict covers the evidence handoff; it does not qualify the notification route or establish an adoptable implementation.

I reviewed the shared documents and all three final reports against the frozen brief, the supplied requirements, and cited repository sources at `6fbddb3883e08476af9fffe1410863f0e89f0cd6`. All ten candidate files matched the snapshot’s hashes, modes, and file types before and after review. The snapshot SHA-256 remained `a296c062e617b879d5531c9d5b4518f6de6e81036bf8e508301f9eabd8e1f038`. The named offline members and public SDK member also matched their recorded digests.

**Remaining research and qualification limitations:** Fresh authenticated account-route observation, complete combined applied permissions, arbitrary endpoint model/mode/cwd freshness, exact Desktop/Code/native-address binding, and actual incoming-delivery and ACK behavior remain unresolved. Collection timing and the ordinary operating lifecycle also require decisions. Those limitations are explicit in the candidate rather than hidden behind its completion labels. No tests were run, and no receiver data, application execution, live operations, memory, other chats, or reviewer reports were used. The packet’s same-leader capture and selection records are ordinary review evidence; I did not independently authenticate their execution provenance.

Packet anchors below refer to `docs/superpowers/research/2026-10-02-parallel-receiver-observations/`.

## Falsification attempts

1. **Could lane completion conceal a narrowed notification contract?**
   I approached the handoff as an operator expecting the full accepted first-notification qualification, including exact consented-peer selection, independent receiver delivery and correlated ACK, outcome distinctions, and actual before/after state. `method.md:11–22` preserves that contract and limits this increment to source/design investigation. `existing-final.md:47–60`, `hooks-final.md:57–70`, and `app-final.md:25–36` retain its observation obligations and identify uncovered fields. The existing-interface lane also preserves busy continuity as a diagnostic (`existing-final.md:60, 99`). The shared README explicitly places comparison and component choice after this handoff (`README.md:19–23`). I found no claim that completing these lanes completes qualification.

2. **Would sender success, assistant text, or stored silence be promoted into receiver delivery?**
   A plausible consumer might combine a successful send with matching assistant text and infer delivery. The reports resist that shortcut. `existing-final.md:27, 51–54` separates final ACK text from independent incoming evidence and leaves absence unknown. `hooks-final.md:23–25, 51, 82` explains persistence limits, distinguishes assistant hooks from incoming-message witnesses, and rejects automatic resend after uncertainty. `app-final.md:28–29` preserves distinct held, refused, and unknown handling. These statements fit the pinned observer contract at `docs/superpowers/specs/2026-09-29-desktop-runtime-observer-design.md:196–208`, which requires distinct, correctly bound receiver evidence and rejects quotation, echoes, and sender success as substitutes.

3. **Does the corrected task-creation return actually solve fixture acquisition?**
   I checked the named `index.chunk-COPWZCsC.js` bytes `27800–28640`. The normal successful path returns the Desktop session ID after the conditional typed-text side effect. The correction is therefore supported. I then looked for an unjustified inference from that internal return to an external identity surface. `source-correction.md:25–27`, `existing-final.md:33, 66–75`, `hooks-final.md:17–19`, and `app-final.md:9–11` explicitly retain the access and independent-binding gaps. Directory novelty and newest mtime are not accepted as fixture identity. The correction improves the internal contract without claiming a demonstrated external acquisition path.

4. **Could a small retained projection disguise broader private acquisition?**
   The hooks final report’s explicit-directory statement could be read too narrowly on its own (`hooks-final.md:23, 80`). I checked it against the governing source correction and the public SDK member. The inspected `GD → Vo` route, directory lookup, worktree lookup, and long-path fallback support the warning that explicit `dir` is not an exact-file boundary. `source-correction.md:29–50` directly limits the hooks interpretation; `existing-final.md:41–43` carries the same correction. The packet therefore requires either separately bounded exact-file acquisition or assessment and authorization of the SDK’s actual footprint. Its reading order makes that correction part of the current candidate; retroactive rewriting of historical reports is unnecessary.

5. **Are app-side cached or completed-push values presented as complete applied state?**
   I inspected the manager’s completed-push span `1332000–1336850` and worktree-resolution spans `506700–511400`. They support the report’s narrower meanings: host caches record a completed push while the selected query still matches, and `harnessCwd` comes from registered-worktree resolution. `app-final.md:40–48` preserves those limits and avoids equating them with fresh authenticated account state, complete executor permissions, or arbitrary cwd. The retained adapter projection at `desktop-adapter.mjs:396–434` also supports the report’s claim that the proposed completed-push cache fields are absent from the current projection. I found no promotion of these partial producers into a preservation result.

6. **Is a candidate-specific observer architecture being imposed as a universal requirement?**
   An operator could reasonably prefer cheaper hooks and stored readers, or qualification-only instrumentation. `app-final.md:5, 23` corrects the asserted eight-anchor minimum into a candidate subset rather than a proved minimum. `existing-final.md:31, 79–85` and `hooks-final.md:29–33, 70` reject added lease-preservation and interval-wide obligations. They leave repeated full-state sampling during ordinary operation unresolved. The pinned design likewise distinguishes endpoint equality from an interval-wide guarantee (`desktop-runtime-observer-design.md:174–179`). The packet does not choose an ongoing service or silently require perpetual sampling.

7. **Does deferring new prototypes evade unfinished claimed work?**
   I challenged the rationale that missing runtime producers make every synthetic experiment pointless. The final reports correct that blanket conclusion. They name concrete seams: hook evidence projection (`hooks-final.md:88–99`), completed host-push projection, and explicit endpoint collection (`app-final.md:66–71`). The shared disposition explains which acquisition, retained-observation, and request-timing decisions those implementations would select (`source-correction.md:52–66`). These are specific deferred candidates pending component and test-boundary decisions, not claims of completed implementations. Historical demonstrations remain attributed, and the packet makes no new test-pass claim (`method.md:55–60`).

8. **Could temporary instrumentation qualify restored Desktop, or could automatic samples supply the intended endpoints?**
   The retained prototype’s `observer-contract.mjs:36–38` confirms its three-sample, 30-second limits. `app-final.md:54–62` explicitly states that this cadence does not establish the required before/after fit and may miss busy delivery or ACK timing. It also distinguishes restored bytes from restored application/task behavior and requires evidence supporting transfer to unmodified Desktop. Those limits agree with pinned `packaging-evidence.md:139–151`. `existing-final.md:83–85` and `hooks-final.md:78` retain the same boundary. The handoff survives this alternate framing because it identifies endpoint scheduling and transfer evidence as remaining work, without claiming either has been demonstrated.

</details>

<details>
<summary>Source accuracy and evidence</summary>

## Findings

**PASS for the selected Tricritical `runtime` source and evidence correctness scope.** I found no actionable contradiction in the current handoff.

I checked snapshot `a296c062e617b879d5531c9d5b4518f6de6e81036bf8e508301f9eabd8e1f038` before and after review. All ten candidate paths, modes, and hashes matched. The four named offline source members, retained SDK member, and SDK identity file also remained unchanged. Repository source was read at `6fbddb3883e08476af9fffe1410863f0e89f0cd6`. I independently retrieved the public SDK archive, verified its declared archive digest, and read declarations as data without executing package code.

The handoff remains incomplete as route qualification: no combination establishes fresh account-route identity, complete applied permissions, or every required endpoint observation. Those gaps are stated in the final reports. Component selection, agreed implementation seams, and separately authorized receiver experiments remain downstream work. This pass establishes neither live preservation nor general security acceptance.

## Falsification attempts

1. **Could explicit SDK `dir` accidentally authorize an exact-file-only read?**
   I traced the exported `getSessionMessages` through `Fbt` (SDK byte 1152353), `GD` (530964), and `Vo` (406889). Its explicit-directory branch resolves project paths, invokes `kn`, and searches related worktrees through `Vfe`. The long-path branch of `kn` can call `Aa`, enumerate `.jsonl` candidates, and inspect their transcript data. `Vo` accepts the first suitable result; it does not demonstrate uniqueness. This independently supports `existing-final.md:41–43` and `source-correction.md:29–50`. The correction explicitly governs the hooks report’s narrower statement. Filtering returned fields therefore supplies no acquisition restriction, and the current packet does not claim otherwise.

2. **Could the SDK declaration’s missing `origin` field mean the runtime strips useful delivery provenance?**
   I followed `GD → KD → p_e → gb`. `gb` retains timestamp and normalized origin; `Py` returns non-task-notification origins unchanged. `cb`, at SDK byte 498374, recognizes peer origin for filtering. Conversely, SDK 0.3.284’s `SessionMessage` declaration at lines 6365–6378 omits those runtime fields. That supports the distinction in `existing-final.md:39`: runtime preservation is a pinned source dependency, with compatibility work still required. It does not prove that this external sender produces the needed receiver row. The reader’s empty/error paths and persistence uncertainty remain compatible with “unknown,” rather than evidence of non-delivery.

3. **Could task creation omit its returned ID when `typedText` is absent?**
   In `index.chunk-COPWZCsC.js`, bytes 27800–28640, the successful return is a comma expression: conditional text binding is evaluated, then `{sessionId:d}` is returned. A thrown exception still rejects the call. The correction in `source-correction.md:7–27` is accurate. I also traced LocalSessions declaration and dispatch through `Ob`, `Oo`, and `Ab` in `index.chunk-DuaKZOPP.js`, including sender-frame validation. The internal return establishes a function contract, while leaving ordinary external fixture-ID acquisition unresolved. The final reports preserve that limit and do not promote the return into an external IPC endpoint.

4. **Could modern hook names or SDK callback handling falsely establish selected-engine execution?**
   The public archive declares `MessageDisplay`, `CwdChanged`, and `PostModelSwitch`; `Stop.last_assistant_message` and `SessionStart.model` are optional. The SDK wrapper dispatches received `hook_callback` inputs around byte 1090223. In the manager, the principal `buildStartSdkOptions` path supplies user/project/local settings and host callbacks around bytes 1077013–1077269; a separate branch narrows settings sources around 1086710. `applyFreshBinaryPath` selects the executable identity, and the manager strips unsupported `PostToolBatch` callbacks around 1289004. These facts support `hooks-final.md:37–53`, including its separation of Desktop, SDK, and actual executor versions. They do not establish the selected executor’s emitters.

5. **Could the proposed ACK hook be mistaken for complete receiver evidence?**
   Current official documentation confirms that Stop can expose final assistant text before transcript persistence is guaranteed; user interruption skips Stop, and API errors use StopFailure. MessageDisplay has a different display-blocking effect and runs once per assistant message in non-interactive SDK queries. These semantics support the packet’s preference to investigate Stop while retaining optional-field and execution gaps. Neither hook establishes incoming peer delivery. The final reports continue to require a distinct incoming record and an adopted correlated ACK grammar. [Official hook reference](https://code.claude.com/docs/en/hooks#stop). The documented socket export likewise supplies an address lead while consent and the exact Desktop-task join remain unqualified. [Official inbox-socket contract](https://code.claude.com/docs/en/cross-session-messaging#the-sessions-inbox-socket).

6. **Could desired host rules or a rejected/stale push masquerade as completed application?**
   At manager bytes 1332000–1336850, `pushFlagPermissionScope` awaits `query.applyFlagSettings`; the three applied-rule caches update only when the selected query still equals the captured query. The `$` wrapper around byte 531044 returns the original promise, so it does not turn rejection into fulfillment. Teardown clears the caches around bytes 1040250–1043400. The current prototype’s `projectHost`, `desktop-adapter.mjs:329–437`, omits those completed-push arrays and `hostMcpHeldForRules`. Thus `app-final.md:42–44` identifies a real projection opportunity while accurately limiting its meaning to the manager’s recorded completed push. It supplies no complete executor-permission claim.

7. **Could `harnessCwd`, account refresh, or mode completion falsely appear fresh and complete?**
   `applyHarnessWorktreeMove`, manager bytes 506700–511400, clears `harnessCwd`, advances a generation, resolves a registered worktree, and stores the resulting path only for the matching generation. Missing state cannot mean empty cwd, and the resolved path is not an arbitrary current-cwd getter. Account refresh, bytes 465700–471200, uses spawn identity and pre/post fences; token pushes enqueue updates with a delivery predicate. Those are intended binding and submission facts. Mode-setting source, bytes 1409450–1413400, tracks pending requests and includes a restart fallback. `app-final.md:40–48` retains these distinctions instead of equating manager state with complete current applied state.

8. **Could prototype reuse hide a claim that the automatic samples satisfy notification endpoints?**
   The retained observer contract permits three samples within 30 seconds (`observer-contract.mjs:36–38`). `desktop-adapter.mjs:625–640` schedules samples automatically, and its manager boot guard at lines 747–779 supports one-shot operation. Binding checks at `observer-probe.mjs:1069–1105` protect collection identity; they do not establish interval-wide invariants. `app-final.md:54–71` explicitly identifies the cadence limitation and proposes finite endpoint collection as a successor seam. The method and source correction preserve historical test attribution and defer implementation pending component and lifecycle choices. I found no new-test or endpoint-qualification claim hidden in that reuse.

I performed no edits, tests, app execution, private receiver reads, delegation, or live mutations. The full peer-origin documentation page could not be independently retrieved; its runtime preservation claim was checked against the pinned SDK source, with actual native ingress attribution still unresolved.

</details>

<details>
<summary>Architecture and operating costs</summary>

## Findings

**PASS for the selected architecture and operational-tradeoff scope.** I found no actionable contradiction in the current source/design handoff. The reports give the comparison concrete components and preserve the missing producer facts. They do not claim that a complete observation route exists or that app instrumentation has been proved necessary.

The reviewed candidate is the ten-file snapshot identified by SHA-256 `a296c062e617b879d5531c9d5b4518f6de6e81036bf8e508301f9eabd8e1f038`, against repository base `6fbddb3883e08476af9fffe1410863f0e89f0cd6`. All ten file hashes, modes, and regular-file types matched at completion; the initial hash and mode check also matched. The inspected manager, renderer chunk, and public SDK member retained their recorded digests. The bound review brief, request, invocation plan, and selection record were unchanged.

I applied `tricritical:structure`, including its shared input/output boundaries and structure rubric, to the architecture and operational concerns in the supplied brief. This was an ordinary independent read-only critic execution. The invocation-plan digest is `f883f1bc223bc5832e588c8e8a0f1f42e08157564aeba75f9a0826bafb40cf67`; the model-selection-record digest is `1bafc48e81cf790964a96c660c07ff985f3de4b6c940bc1514442f9d2f8b53e9`. Launch and completion observations remain the coordinator’s responsibility. These records do not authenticate the executed model or prove product-enforced read-only authority.

Remaining research and qualification limitations are material but explicitly retained: external fixture-ID acquisition; Desktop/Code/native-address binding; selected-engine hook support; actual incoming-message and ACK producers; fresh account/model/mode/cwd evidence; complete applied rules, grants, and pending changes; endpoint scheduling; and transfer from instrumented to restored Desktop. These limit the route’s readiness. They do not contradict this increment’s claim to supply source/design comparison inputs. No general security acceptance, component adoption, test pass, or live qualification follows from this report.

## Falsification attempts

1. **Collapse the architecture into existing Desktop getters.** I tested whether host `get_session` or renderer `LocalSessions` could eliminate the external reader/bridge distinction. The pinned observer design’s “Existing access paths” section traces host tools into Desktop-owned SDK queries and LocalSessions through renderer IPC; it establishes no standalone attach endpoint. `existing-final.md:19–21` and `app-final.md:21` preserve that limitation. The corrected successful `{sessionId}` return in the renderer’s UTF-8 bytes `27800–28640` establishes an internal function result, not externally available identity acquisition. The decomposition survives: adding another internal getter would leave external access unresolved.

2. **Delete app instrumentation entirely and declare hooks plus stored readers sufficient.** This is a credible simplification candidate, but the handoff does not overstate it. `existing-final.md:47–62`, `hooks-final.md:57–70`, and `app-final.md:25–36` identify separate gaps in fresh account identity, endpoint model/mode/cwd, and combined applied permissions. Stored records and event-time hook fields cannot close those gaps merely by being combined. Conversely, `app-final.md:3–5, 73` avoids declaring instrumentation mandatory. The smallest architecture remains a component decision informed by residual producer coverage, rather than a conclusion drawn from the number of existing patch anchors.

3. **Require the fixture receipt’s full continuity machinery everywhere.** I compared ordinary selected-task binding with the stronger receipt claim at the pinned acquisition design’s lines `13–29`. That design witnesses registration, writer fulfillment, exact-file validation, and same-process admission; it expressly does not establish current account, model, permissions, cwd, or native-address binding. `existing-final.md:68–75` and `app-final.md:15` correctly distinguish those guarantees from bounded discovery. The handoff survives both directions of challenge: bounded discovery is not presented as receipt-equivalent, and receipt-specific registration generations and transition epochs are not imposed on every possible collection route.

4. **Remove generation and identity checks as an unnecessary interval-wide requirement.** The retained prototype captures record, query, input stream, generation, and getter references in `observer-probe.mjs:733–759`, then checks those identities in `:1069–1089`. These checks serve the narrower purpose of keeping one multi-getter collection bound to the same receiver. They do not prove that every field remained constant throughout a notification interval. `existing-final.md:31` and `app-final.md:23, 54` keep that distinction explicit. Deleting those checks without an equivalent lifecycle producer would weaken the sample’s identity claim; treating them as proof of interval-wide preservation would also be unsupported.

5. **Turn a finite experiment into an ongoing observer dependency.** `app-final.md:54–58` rejects that premature step. It explicitly says the existing three-sample, 30-second cadence does not establish suitable before/after endpoints and may miss busy delivery or acknowledgment. It proposes finite phase requests as a successor seam at `:68–71`, while leaving ordinary operating lifecycle unresolved. `existing-final.md:79–85` likewise retains fresh peer and consent checks for each send without silently requiring full repeated sampling. The handoff therefore does not hide a recurring-service requirement inside the qualification experiment.

6. **Treat deferred prototypes as unfinished work concealed by missing runtime producers.** The current correction supplies concrete testable seams: hook projection, manager-recorded completed-push projection, and finite endpoint collection (`source-correction.md:52–66`; `hooks-final.md:88–99`; `app-final.md:66–71`). These can test projection, partial evidence, scheduling, and identity rejection. They cannot establish unknown runtime producer truth. Deferral is justified here because component selection and the concrete test boundary remain open, and the handoff makes no new implementation or test-pass claim. This disposition would need revisiting once a seam is selected; the retained prototypes are not sufficient acceptance evidence for a successor implementation.

7. **Simplify acquisition by treating SDK `dir` as an exact-file boundary.** The public SDK source defeats that framing. `GD` at byte `530964` delegates to `Vo`; the explicit-directory path reaches `kn` and `Vfe`, while the long-path fallback can inspect transcript candidates through `Aa`. I inspected the cited spans directly. `source-correction.md:29–50` and `existing-final.md:41–43` preserve the resulting acquisition footprint. Although `hooks-final.md:23` retains its narrower earlier statement, the controlling correction explicitly prevents consumers from using it to authorize exact-file-only acquisition. No current handoff claim depends on that superseded interpretation.

8. **Discount app instrumentation costs as merely packaging mechanics.** The pinned `packaging-evidence.md:139–151` requires stopped-app archive exchange, candidate and restored launches, package-identity rechecking, and separate behavior verification. `app-final.md:60–62` carries those consequences forward: two restarts, possible interruption, an unmeasured total window, and qualified transfer to unmodified Desktop. It also prevents the receipt’s 15-minute acquisition-admission ceiling from being mistaken for a restoration bound. These are decision-relevant costs, and the handoff exposes them without claiming that source inspection measured their runtime impact.

</details>
