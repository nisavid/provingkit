# Review of the receiver-observation comparison

The [component comparison](2026-10-02-receiver-observation-comparison.md) has a
clean current independent pass for intent, source/evidence accuracy, and
architecture/operating costs. It is ready for the operator's component choice;
no implementation or runtime qualification is accepted by this review.

Three separate native critics reviewed the same frozen candidate under
Tricritical. One intent finding identified a missing explicit prohibition on
automatic resend after unknown, held, or refused outcomes. I accepted it
against the original route decision, made the reconciliation and outcome rows
explicit, then reran all three scopes on the successor. The current reports
have no actionable findings. The original findings and first-pass reports
remain retained; none was discarded because another critic passed.

I rechecked the candidate identity, report digests, relative links, absence of
machine-local publication paths, and whitespace. No tests or live operations
were run. All scopes used fresh independent contexts initially and the same
respective critics for successor review, with no cross-critic report exchange.
GPT-6.1 Sol xhigh was requested through native tools. The records supply
ordinary same-leader observations, without authenticated execution or
product-enforced authority claims. No general security acceptance is claimed.

## Candidate and correction

- Source dependencies: `f121c9d8108a03fc1185da1d6e67d332e860478b` and the
  immutable sources it cites.
- First candidate SHA-256:
  `98b07f09b00d58d835538d4618b159669d27c645666725295caa3945cd7d7f90`.
- Current candidate SHA-256:
  `126d6e88beb2eba75cc0b819a2c669e6f8c4a40fd19c705d5c3e3bd3e20c1181`.
- Current snapshot SHA-256:
  `02890e24e7beda6cdd289206abd2273f4af67ee655cd88b38e1984ba1b74c687`.

The only candidate change between review rounds is the two outcome-table cells.
Unknown reconciliation now observes only and never automatically resends;
held/refused neither count as acknowledgment nor trigger automatic resend.
The predecessor bytes were recovered by reversing that exact change and
verified against the candidate digest in the first snapshot.

## Execution records

```json
[
  {
    "current_pass": false,
    "plan_sha256": "3f939f84d9e9f27c0ee3f7d3e28741342b11389bb350cbb1b6f911b662e32733",
    "report_sha256": "99892f2e50ccefd1747899057327649a1fb0883c1ca780175e632aba2da869f0",
    "round": "r1",
    "scope": "intent",
    "selection_sha256": "a1aae27b59656fcedfbc9d871b41c057672ac598a04d304c67cb4b30ae93a9c1"
  },
  {
    "current_pass": false,
    "plan_sha256": "63892c1adbc053aa275802d38594821e6c8aab7e1251c85711d1c467e44acf02",
    "report_sha256": "ae6588d387af86435a9c3b0ca70c5ebf20446d06ae3717d6069c4494cd60b00b",
    "round": "r1",
    "scope": "source",
    "selection_sha256": "6662ccc996398b97704e0c0c21c27a225c480dc78dd2267f7ea9d72a15db0f56"
  },
  {
    "current_pass": false,
    "plan_sha256": "16c9ecaddbc54bd585a419262b27893243211e770afbbc9670e9e1470c0f3f75",
    "report_sha256": "cdd49c447570e40372dd279d77d733a2cc8a359fad87c58982afb7d76f009384",
    "round": "r1",
    "scope": "architecture",
    "selection_sha256": "accf1c9cddf175c0e356b3f4821a1d92c0f1f0bbcda99f3d814138f9b8173959"
  },
  {
    "current_pass": true,
    "plan_sha256": "4c4fc9aca41d5cd9822e7fac76350d2ad0f063cf6bca830db9e6fb47c13d00e3",
    "report_sha256": "b1b7c3ce01e5f797af60e1ee343fcaef11e88ec9265065560279b8d3204a58c4",
    "round": "r2",
    "scope": "intent",
    "selection_sha256": "35aa8330158b7a36ee3dc5c89d8fa8536d3f6635ef8850f54535b5b1014cea81"
  },
  {
    "current_pass": true,
    "plan_sha256": "0cb2ad0c31f4960f4eaae8659b00bf5608453255dc37beed55c6aaea8c1ebbbe",
    "report_sha256": "fa5bdc041c93f19ce774190993df93f17bf381af7b18504d3aaae8f5eddbbb0d",
    "round": "r2",
    "scope": "source",
    "selection_sha256": "535a832e0898a1f1a041bcf3b8b83c8f99ad0cd3018036200c61a1e972eaf3fa"
  },
  {
    "current_pass": true,
    "plan_sha256": "83d8e4f2f6c04bc519e7b8894420a2d394a6e43f9d3d584097b081681192974d",
    "report_sha256": "d040e99daa5f23376397c6e4a58b807c4f8d1fed06ad60ca867ee0cd042d5b96",
    "round": "r2",
    "scope": "architecture",
    "selection_sha256": "e8b58058ae09ca32ed072e0b34d321adde103cc289181c6afdef951df994c3a3"
  }
]
```

## Current critic reports

The reports retain their wording with trailing whitespace removed and local
links converted to the repository artifact. Digests above identify the original
captured responses.

<details>
<summary>Contract fit</summary>

## Findings

**PASS — no current actionable intent findings.**

The revised comparison preserves the accepted no-resend rule explicitly. [Lines 53–54](2026-10-02-receiver-observation-comparison.md) now say reconciliation uses observation only and never automatically resends; held and refused outcomes neither count as acknowledgment nor trigger automatic resend. This resolves INTENT-01. The language matches the frozen requirement and the source-lane outcome distinctions without deciding whether a separately authorized later send is permissible.

The comparison is ready to inform the operator’s component choice within its stated scope. It identifies useful components, their access and operating costs, the remaining producer gaps, and bounded next checks. It does not claim that any combination satisfies full preservation or that any component has been adopted.

Candidate SHA-256 was `126d6e88beb2eba75cc0b819a2c669e6f8c4a40fd19c705d5c3e3bd3e20c1181` before and after review. The snapshot also remained unchanged, with SHA-256 `02890e24e7beda6cdd289206abd2273f4af67ee655cd88b38e1984ba1b74c687`. Source and contract dependencies remain pinned to the supplied immutable revisions.

## Falsification attempts

- **Could uncertainty still cause duplicate notification?** I checked the revised unknown and held/refused rows against the accepted rule and the unchanged lane sources. Missing, delayed, or incomplete records remain unknown; reconciliation observes rather than sends. Held may later release, while neither held nor refused supplies ACK evidence. The comparison now carries the operational restriction directly where a downstream interface designer would encounter it.

- **Could a sender result or assistant echo satisfy receipt?** The requirement table keeps receiver-origin delivery separate from explicit correlated ACK. Lines 51–52 require the actual external native ingress row and attribution, selected-engine ACK emission, correlation, and quotation/echo rejection. Stop text remains an ACK candidate and expressly does not prove incoming delivery. Line 50 preserves informational text, context link, correlation ID, and ACK as receipt. I found no substitution of sender success for receiver evidence.

- **Could the recommendation make receiver changes without another decision?** I tested the imperative wording in the opening against the actual authority statements. Lines 16–18 adopt nothing and authorize no live access or operation. The next-work section describes a source increment, followed by separately authorized experiments. Its proposed logger and harmless setup prompt cannot proceed before identity, acquisition, procedure review, and live authority are settled. The recommendation does not supply permission for installation or execution.

- **Could the cheaper combination silently weaken actual-state coverage?** Lines 55–58 retain fresh account-route, actual-model semantics, combined applied mode/rules/grants/pending changes, and current worktree/cwd gaps. Completed host pushes cover specific categories; event-time fields need qualified endpoint meaning; `harnessCwd` is not an arbitrary current-cwd getter. Lines 62–64 prohibit substituting weaker evidence for an uncovered field. These are honestly stated future evidence gaps, rather than errors in the comparison’s current claims.

- **Could ordinary operation inherit an unaccepted permanent observer requirement?** Lines 97–105 distinguish full before/after initial qualification from the unresolved policy for ordinary sends. Fresh exact-peer and consent checks remain required per send, while repeated complete sampling and interval-wide invariants are not imposed. The maintained observer remains conditional. The operator can assess source components without treating a recurring service as already required.

- **Could filtered output conceal wider acquisition?** I compared lines 83–95 with immutable `source-correction.md`. The comparison preserves that SDK `dir` can inspect other candidates and that opening JSON acquires full serialized contents despite a narrow retained projection. Internal task creation returning an ID does not establish external access. Bounded discovery is also distinguished from the receipt’s stronger registration and handoff witnesses. No newest-file, socket-only, or title-only shortcut supplies exact-task binding.

- **Could temporary instrumentation establish restored Desktop behavior?** The costs table retains two restarts, possible interruption, package/restoration checks, and an unmeasured window. Lines 75–79 require an observer-effects argument and relevant unmodified-runtime evidence before transferring a claim. The current three-sample cadence does not establish before/after bracketing. Restoration of bytes is therefore not promoted into qualification of behavior.

- **Could prototype work manufacture missing producer evidence?** Lines 118–121 identify projection and scheduling seams while limiting their tests to source behavior. The final source-investigation paragraph asks for actual producer evidence and returns unresolved gaps for decision rather than inventing fields. Graduated compatibility remains tied to relevant dependencies, with justified evidence reuse.

I performed read-only documentary review. I ran no tests, inspected no private receiver data, and made no edits, app operations, external writes, or delegations. This PASS applies to ordinary Tricritical intent review of the frozen comparison; it supplies neither live route qualification nor general security acceptance.

</details>

<details>
<summary>Source accuracy and operations</summary>

## Findings

**PASS for the selected Tricritical runtime/source-evidence scope on the revised candidate.** I found no current actionable contradiction or material unsupported claim.

The outcome rows now explicitly retain observation-only reconciliation and prohibit automatic resend for unknown, held, and refused results. This matches the accepted contract and pinned lane facts without changing the component recommendation or claiming qualification.

The other material source boundaries remain intact: acquisition differs from retained projection; internal IDs differ from externally accessible bindings; documented hooks differ from selected-engine emission; partial host observations differ from complete applied state; and restored bytes differ from restored behavior. No additional specialist is needed for this bounded source comparison. Selected implementation and live qualification would require their own appropriate reviews.

This review uses unchanged pinned dependencies and ordinary cooperative assurance. I performed no tests, modifications, receiver acquisition, app operations, or external actions, and read no memory, other chats, or critic reports.

## Falsification attempts

1. **Unknown submission followed by delayed held-message release.**
   I traced the case in which submission evidence is incomplete, the receiver remains quiet, and a held message later becomes deliverable. An automatic retry could duplicate the notification and resulting receiver turn. The pinned hooks final expressly warns against that retry; the app final distinguishes held release from refusal and says neither authorizes resend. Revised comparison lines 53–54 now require observation-only reconciliation, preserve unknown for missing or incomplete evidence, and prohibit automatic resend. Neither held nor refused counts as acknowledgment. The candidate survives this current-contract challenge.

2. **A selected SDK session ID conceals broader acquisition.**
   The earlier direct source trace remains applicable: `GD` reaches `Vo`, whose explicit-directory route uses project resolution, `kn`, and `Vfe`; long-path candidate inspection can reach `Aa`. I rechecked the retained SDK member digest against its pinned identity. Comparison lines 37–39 and 83–88 preserve the controlling correction: `dir` does not restrict acquisition to one file, and filtering output does not narrow acquired bytes. The proposed grant must cover the actual footprint. An eventual exact-file reader remains a design choice, not an existing property attributed to the SDK.

3. **An internal Desktop ID or hook socket appears sufficient for consented-peer admission.**
   The retained renderer bytes establish the successful comma-expression return of `{sessionId:d}`, with conditional text binding as a side effect. They do not establish external access. The hook socket offers a Code-to-address lead but does not independently bind the consented Desktop task or native send target. Lines 49 and 83–85 preserve these limits and require fresh identity and scoped consent for each send. The comparison therefore cannot admit a task solely because its metadata is newest, its title matches, or its socket exists.

4. **ACK text substitutes for incoming-delivery evidence.**
   Optional `Stop.last_assistant_message` can supply candidate final-response evidence, but the pinned hooks final states that it is not an incoming witness and is absent on user interruption. SDK origin preservation improves transcript interpretation without establishing the actual external ingress row. Lines 51–52 require separate receiver-origin delivery, distinct correlated ACK, attribution, and quote/echo rejection. Missing hook or transcript evidence remains unknown. This avoids a falsely successful result from echoed text, sender success, or an unrelated assistant response.

5. **Completed host pushes and resolved paths become complete applied preservation.**
   The unchanged manager source records permission arrays after awaited `applyFlagSettings` while the selected query still matches. Those arrays cover particular categories; they do not establish every Code rule, host grant, or pending operation. `applyHarnessWorktreeMove` resolves registered-worktree state rather than arbitrary current cwd. Lines 55–58 retain fresh-account, model-semantic, combined-permission, and endpoint-cwd gaps. Lines 62–64 prevent the assembled partial evidence from satisfying the full claim.

6. **Initial qualification silently creates a recurring-observer requirement.**
   The pinned finals require full actual before/after qualification while leaving ordinary full-state sampling unsettled. They also identify the prototype’s three automatic samples within 30 seconds and one-shot lifecycle. Lines 97–105 retain those distinctions, and the maintained-observer row remains conditional. A fixed cadence is not claimed to bracket busy delivery or ACK; an interval-wide invariant is not added.

7. **Restoration or public declarations create fresh runtime acceptance.**
   Lines 72 and 75–79 carry restart, interruption, package/restore, observer-effects, and unmodified-runtime evidence obligations. Lines 131–135 preserve the missing matched-engine artifact. Historical synthetic checks remain explicitly unr­erun at lines 33–35. Neither restored hashes, modern SDK declarations, nor retained demonstrations are promoted into live qualification.

Candidate identity remained unchanged throughout: candidate SHA-256 `126d6e88beb2eba75cc0b819a2c669e6f8c4a40fd19c705d5c3e3bd3e20c1181`; snapshot SHA-256 `02890e24e7beda6cdd289206abd2273f4af67ee655cd88b38e1984ba1b74c687`.

</details>

<details>
<summary>Architecture and costs</summary>

## Findings

**PASS for the current Tricritical structure scope.** I found no current actionable architecture finding in the revised comparison.

The candidate remains a useful component decision input: it compares combinations rather than selecting a lane by vote, retains app observation only for specific residual needs, and distinguishes acquisition, interpretation, qualification sampling, and ordinary-operation policy. Lines 53–54 now explicitly keep reconciliation observational and prohibit automatic resend for unknown, held, and refused outcomes.

Candidate SHA-256 was unchanged before and after review: `126d6e88beb2eba75cc0b819a2c669e6f8c4a40fd19c705d5c3e3bd3e20c1181`. It matched the frozen snapshot, whose digest remained `02890e24e7beda6cdd289206abd2273f4af67ee655cd88b38e1984ba1b74c687`.

I applied the shared Tricritical contracts to the revised candidate and unchanged immutable dependencies. This was a read-only review without other critic reports, tests, private receiver data, delegation, or live operations. The result supplies no runtime qualification or general security acceptance.

## Falsification attempts

1. **Remove the app observer and declare readers plus hooks sufficient.**
   Lines 55–58 prevent this simplification from satisfying the accepted full-state requirement. The immutable final lanes identify missing fresh account-route evidence, complete applied-permission coverage, and arbitrary endpoint observations. The app lane’s completed-push evidence improves particular host-rule provenance; it does not establish complete executor permissions. Its worktree source resolves registered worktree state rather than providing an arbitrary cwd getter. The comparison correctly keeps the app bridge as a possible access component while leaving producer truth unresolved. Deleting it from all alternatives would discard a useful source-backed option; adopting it as complete would overclaim. No correction is needed.

2. **Make a maintained observer the default consequence of qualification.**
   Lines 97–105 separate the accepted before/after qualification measurements from fresh per-send peer and consent checks. They leave repeated complete ordinary-send sampling unsettled. Lines 72–73 consequently distinguish temporary diagnosis from a possible recurring dependency, with separate integration, retention, recovery, and update costs. This survives the attempt to collapse them into one lifecycle. A recurring observer remains conditional on the selected operating contract; the comparison does not introduce that stronger guarantee or require interval-wide invariants.

3. **Combine acquisition and interpretation behind the SDK’s explicit-directory helper.**
   The unchanged source correction establishes that explicit `dir` is narrower than all-project lookup but is not an exact-file read boundary. Lines 83–88 preserve directory-entry exposure, full serialized-file acquisition, and possible additional candidate inspection. The recommendation to separate approved acquisition from record interpretation therefore removes a real ambiguity about ownership and grants. Returned-field filtering cannot narrow bytes already acquired. This division earns its maintenance cost by making the exposure independently reviewable.

4. **Use final hook text to eliminate the independent delivery reader.**
   Lines 51–52 retain two evidence channels: actual receiver-origin ingress and explicit correlated ACK. The hook final report describes Stop as an assistant-response event, with optional text and interruption gaps; it does not make it an incoming-message witness. The smaller hook surface remains useful for ACK latency and event-time fields without owning overall delivery conclusions. Quote/echo rejection, correlation, and selected-engine emission remain concrete next checks. The comparison’s decomposition preserves the accepted distinction without duplicating success policy across components.

5. **Require the prior receipt machinery for every acquisition alternative.**
   Lines 90–95 accurately retain the receipt’s stronger registration, persistence, transition, and same-query handoff claims while refusing equivalence with bounded discovery. The immutable receipt design gives those mechanisms a specific purpose and excludes native-address binding and complete runtime-state proof. Treating its internal machinery as universal would add cost without closing the current residual gaps. The comparison instead requires each method to state its supported claim and acquisition footprint. Its conditional treatment of the 15-minute admission ceiling also avoids presenting that limit as a bound on restoration or the whole experiment.

6. **Transfer temporary instrumented observations directly to restored Desktop.**
   Lines 72 and 75–79 preserve the actual proposed intervention: stopped-app archive exchange, two restarts, possible interruption, package checks, restoration, and an unmeasured total window. The retained packaging evidence supports these costs and explicitly distinguishes restored bytes from restored task behavior. The comparison requires an observer-effects argument and relevant unmodified-runtime evidence before transferring a claim. That future evidence gap is honestly stated; it is not a missing proof that the comparison claims to possess.

7. **Either implement all prototypes now or defer every prototype until runtime producers are complete.**
   Lines 118–121 preserve meaningful seams for partial hook evidence, acquisition separated from interpretation, completed-push projection, and finite endpoint collection. These can test selected interface behavior without simulating unknown producer truth. Lines 123–135 then identify a bounded no-send experiment and prioritize matched-engine source questions before receiver intervention. The sequencing gives the operator useful source work while retaining identity, acquisition, review, and authority gates for live work. No additional specialist is needed to resolve a structural defect in this comparison; later implementation and operating procedures retain their own review requirements.

</details>
