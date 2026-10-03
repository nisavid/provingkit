# Runtime access cross-examination of the frozen Stop collector

**DONE_WITH_CONCERNS.** The collector is useful for the accepted first fixture check: it preserves a matching setup response and observed session ID without treating that ID as independent binding, records one asserted endpoint, and keeps publication failure separate from observation absence. Its first unbound acquisition does not retain event-time cwd or permission mode. The reconciled design must correct that optional-field claim, define the non-atomic association interval, and keep native endpoint/executor results distinct from a successful UI/Code association.

This is the exchange of frozen findings, not an independent final review or authorization of live use. I used `research` and `capturing-agent-procedures`, read the complete collector, tests, contract, procedure, and findings, and compared them with the frozen runtime report and retained source. I made no edits or live observations and did not rerun the synthetic tests.

## Frozen identities and source anchors

I recomputed and matched the complete supplied manifest and every listed member.

| Input | SHA-256 |
| --- | --- |
| Collector-first manifest | `c1905d33d2c0ad4b269d64aeff546a34f9442bea235e3d094fe4a2b7e26a222e` |
| `collector.mjs` | `7500bb30d898771a2658b2f7ae1c03a16c7cd1c07bf76328317291d8397dca1c` |
| `collector.test.mjs` | `34b9a127adc8b17805fd8a142c84f6f89f03f8ddc004ad06742bedd1099249fb` |
| `collector-contract.md` | `cf2d59c2010acb9d6960992846b47ebe59c57e6083834298786e38eb2f09294e` |
| `fixture-check-procedure.md` | `0fbca6938111306d102713099f98a1cdfaee9c4daa9d50c72e47ac0f628c80db` |
| Collector first findings | `9394b13d6f7865285ec13dcb6bdf740db5e87132d31502ef56d2d4b6298ced63` |
| Runtime first report, 30,074 UTF-8 bytes | `7752f4b264a19caa390e785fd2c7e656d0ebcb20e876f28e9fabd3da957b6835` |

Collector file references below denote the frozen members destined for `docs/superpowers/prototypes/receiver-evidence/`. The projector was read through `git show` at `88d1962aefdf40676148462fc495089fb18d1026`: `docs/superpowers/prototypes/receiver-evidence/hook.mjs`. Public RC byte spans refer to the previously verified 243,059,896-byte engine with SHA-256 `dee301c3e248c62137cc15aafc2781bd5316c66720dd890d72e0054a024ce7d9`.

One preliminary runtime transport finding reached the coordinator before the collector freeze. Both frozen reports disclose that fact. This exchange should retain that provenance and should not describe coordinator integration as wholly blind.

## Material reconciliation findings

### 1. First acquisition discards the optional event fields

The procedure selects `expectedCodeId: null`. The wrapper passes that null directly into `projectStop`; the projector returns at its binding validation before examining cwd, permission mode, event identity, or text. Consequently `projection.eventFields` is empty even when the complete acquired event contains valid cwd and mode. The separate unbound branch retains only `observedCodeId` and the matching final text; it does not recover optional-field values or missing/oversized-field diagnoses. [`fixture-check-procedure.md:50–56`; `collector.mjs:101–126`; pinned `hook.mjs:10–12,25–33`.]

This preserves a useful separation: the wrapper never supplies its observed ID as its own expected ID, and `responseCandidate` stays null. It also means my first report's statement that the fixture can test event-time optional fields is too broad for these frozen bytes.

**Recommended disposition: correct before the reconciled publication.** If optional-field observation is selected for this increment, add a bounded, separately named projection under the admitted unbound setup event. It should retain cwd and permission mode with missing/oversized gaps and keep `binding:"unbound"`, `projection.status:"unknown"`, `responseCandidate:null`, and all independent-binding requirements. Do not feed the observed ID back into the bound projector. Retain these as event-time observations, not endpoint state.

The smallest meaningful command checks are a null-expected-ID event with valid optional values, missing values, and oversized values, asserting both the bounded observations and unchanged unbound status. If the coordinator keeps the current output instead, narrow the reconciled experiment coverage to session ID, setup text, receipt/acquisition, and asserted endpoint. No extra setup turn or event replay follows from this remedy.

### 2. The association needs its observation intervals and success facets stated

The procedure requires the selected UI response and exactly one current metadata `cliSessionId` match among the authorized candidates. It correctly excludes historical lineage and disclaims global uniqueness. The Stop receipt interval, later metadata read, UI witness, and executor witness are still separate observations. A later current-ID match does not make them an atomic snapshot or establish that the same query/socket remains current after the event. [`fixture-check-procedure.md:98–117,138–149`; `collector.mjs:90–111`; runtime first report, “Binding and sampling procedure for a later collector”.]

Step 7 requires the UI/Code association, then says to record endpoint and executor evidence separately. That wording permits a partial successful association with a missing endpoint or unobserved executor. Such a partial result is useful, but it cannot be reported as complete Desktop/Code/native-endpoint binding.

**Recommended disposition: refine the procedure before a live proposal.** Record the collection interval for each UI, event, selected metadata, and executor observation. State the selection/lifecycle recheck the grant will permit, or retain that check as unavailable. Keep separate results for UI/Code association, event-time endpoint association, actual executor, activation/collection, and restoration. Complete native-endpoint association requires a present bounded endpoint from the admitted event invocation and the successful independent join; actual-executor success requires its own observed witness.

Do not expand discovery or add an app adapter merely to claim atomicity. The smaller result can remain an event association over stated intervals. Exact current-peer admission and full endpoint sampling belong to later qualification and sends.

### 3. An arbitrary Stop session string is not necessarily an ordinary Code identity

The unbound branch accepts any nonempty session string of at most 256 code units. The RC `Tc` producer has a served-call branch whose `session_id` is `served:<caller-or-unknown>`. Main and served Stop input must remain distinguishable; a length check does not establish ordinary local Code identity. SubagentStop is already excluded by the wrapper's exact event-name check. [`collector.mjs:122–126`; RC `[207318493,207319450)`; runtime first report, sampling step 6.]

The later exact current-`cliSessionId` join remains necessary and should leave an unmatched served event unknown. The wrapper's field name `observedCodeId` nevertheless overstates the initial classification.

**Recommended disposition: preserve identity kind explicitly.** The smallest remedy is to label the initially retained value as an observed hook session identity, and mark the known `served:` case separately or reject it for this ordinary Desktop fixture. Do not infer that all other strings are authenticated Code IDs. Add a source-shaped served-Stop command specimen showing that it cannot produce an ordinary fixture association. No new receiver interaction is needed.

### 4. The pending-byte counter has no measurement behind its zero

`readInput.finish` writes `pendingBytesAtStop: 0` for every outcome. The implementation measures `bytesObserved` through its bounded read callback; it does not measure unread data remaining in the inherited pipe or data the producer still intends to write. An over-limit or timeout result therefore cannot claim that no input remains pending. [`collector.mjs:49–76`; `collector.test.mjs`, stalled-input case.]

The byte acquisition ceiling remains a separate useful fact: the provided read buffer cannot exceed `limit + 1`, and incomplete acquisition is not parsed as a completed event. The hardcoded counter should not widen that claim.

**Recommended disposition: clarify or remove the counter before publication.** If it means no extra bytes retained by this reader beyond the copied observed prefix, name and document that meaning. For remaining pipe/producer bytes, return unknown or omit the field. Keep EOF and acquisition status as the completion evidence. Adjust the command test to assert the stated meaning rather than a generic pending-byte bound.

## Input, output, and lifecycle conclusions

The source validates the exact command shape and configuration fields, reads at most 32 KiB plus an overflow byte of configuration, and allocates a stdin buffer of the configured limit plus one. Only EOF-complete UTF-8 JSON objects are interpreted. Over-limit, stalled, failed, and malformed input cannot supply the admitted unbound setup event. This is a bounded acquired prefix and completion result, not proof of complete native hook production. [`collector.mjs:8–29,49–98,122–128`.]

The claim is created exclusively before stdin acquisition and survives success and failure. Publication creates a partial file exclusively, writes and synchronizes it, closes it, and links completed bytes without replacing an existing destination. Handled failure preserves the claim; abrupt termination may leave artifacts. The contract correctly distinguishes normal exit 0 from an unknown observation and caught exit 1 from native hook treatment. It makes no total filesystem deadline or crash-durability claim. [`collector.mjs:32–46,85–89,129–134`; `collector-contract.md:85–110`.]

The frozen tests include command cases for occupied outputs, interrupted writes, consumed slots, stalled-input exit, and termination during acquisition. The collector findings report fourteen command tests plus twenty existing reader/hook checks on Node.js 24.21.0. I inspected those cases but did not execute them; this exchange adds source review, not another observed pass.

I found no material contradiction between the proposed ordinary file lifecycle and its stated trusted-directory contract. The draft appropriately requires later quiescence observation, artifact-scoped cleanup, and preservation of concurrent settings changes. The exact quiescence witness remains an unbound preparation input; a claim's collector PID does not establish it is safe to act on that process later. [`fixture-check-procedure.md:118–127`; `collector-contract.md:87–90,112–115`.]

Capture-window meaning needs one explicit clarification. The unbound branch's `validWindow` checks `startedAt >= since` and clock ordering. The configured projector additionally checks elapsed capture age against `inputTimeoutMs`. The stdin timer governs acquisition, not the whole command, and the unbound evidence does not pass that projector age gate. Document those distinct meanings; do not describe the configured and unbound projections as sharing the same acceptance rule or introduce a producer-freshness claim. [`collector.mjs:99–104,121–128`; pinned `hook.mjs:17–24`; `collector-contract.md:37–39,59–77,109–110`.]

## What the fixture can resolve

| Observation or requirement | Result from this frozen command/procedure |
| --- | --- |
| Setup-response representation | A complete whole-field match can test the chosen token's actual normalized Stop representation. It cannot establish untouched transcript equivalence or intentional notification acknowledgment. |
| Selected task | The command remains unbound. Scoped UI selection and exact current metadata association are the proposed independent join, with the interval limits above. |
| Native endpoint | The command retains the selected environment string without connecting or encoding it. Missing/oversized values remain gaps. A retained path does not prove a working or current sender route. |
| Actual executor and hook loading | Successful collection contributes activation evidence. The actual executor is still a separately required witness; package identity, intended pin, and collector PID do not supply it. |
| Event-time cwd/mode | Not retained on the first unbound path. A separate bounded unbound projection would permit partial event-time observation without qualifying endpoint state. |
| Authenticated account, actual attempt model, complete applied permissions, registered worktree/arbitrary endpoint cwd | Not supplied by this command. These remain the runtime design's separate qualification dependencies. |
| Selected app query and host evaluators | Not accessed. The command's inherited stdin and environment do not establish a control-request attachment. |
| Delivery and correlated notification acknowledgment | Not tested by the no-send setup turn. No outcome authorizes a send or automatic resend. |

Source Stop selects the last assistant record's text blocks, joins them with newlines, and trims the result. `Tc` adds session/cwd/mode fields; command dispatch acquires the complete serialized event, including broader background/cron content before projection. The wrapper's limited retained record does not narrow those acquired bytes. These semantics remain supported by RC `[207307500,207308900)`, `[207318493,207319450)`, and the pinned [identity engine report](https://github.com/nisavid/provingkit/blob/88d1962aefdf40676148462fc495089fb18d1026/docs/superpowers/research/2026-10-02-reader-hook-sources/identity-engine.md).

## Handoff to the coordinator

Resolve finding 1 by retaining bounded unbound optional fields or narrowing the selected observation claim; update my reconciled runtime coverage accordingly. Refine the association intervals and success facets in finding 2, retain served identity distinctions in finding 3, and correct the counter meaning in finding 4. Clarify the configured/unbound capture-window difference without adding a live freshness rule.

Use the command's invented-input/disposable-output boundary for any source changes and bind the resulting tests and independent final review to the revised candidate. This exchange does not supply the later security/private-data review, actual executor witness, settings load mechanism, selected profile directory, escaped launcher/environment, or positive live grant. Those inputs remain explicit in the procedure.

Under `capturing-agent-procedures`, the preparation join must load the reviewed reconciled report and final command/procedure revision before dependent work, record the versions consumed, verify the declared observations and cleanup, and return useful corrections to their source. The frozen first reports remain historical inputs. No temporary adapter or ongoing dependency is adopted, and no qualification obligation is discharged by this source exchange.
