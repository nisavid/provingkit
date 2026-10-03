# Fixture binding research: intent review

The frozen source design is clean for the selected intent scope. I found no high-conviction contradiction of the research contract. This is a source-review result, not implementation acceptance, live readiness, qualification, or authorization.

## Candidate and review boundary

I reviewed the three frozen files against published revision `e971ae6fde6f4f4fa0b603e3a08bd0369b9481c6`:

| Candidate file | Bytes | SHA-256 |
| --- | ---: | --- |
| `docs/superpowers/research/2026-10-03-fixture-binding-design.md` | 7503 | `b38245cffa5bf572cb049997eb221ee966aa2bda0d8b12e06339c0e399711c12` |
| `docs/superpowers/research/2026-10-03-fixture-binding-sources/manifest.json` | 128 | `569573a6fa13d01fc45c9ee89e96683950340d8bd95191791d71c42a6b42f76e` |
| `docs/superpowers/research/2026-10-03-fixture-binding-sources/research.md` | 33123 | `27fa99cd796cbc2bb640b25de02b26ae1961d7d3a4f1eff37cfa906a8b0edeb1` |

The candidate manifest is `28526030210b9d15217ba919183e6271362e83144b60ec81b47716b7a3944f75`. The frozen requirements are `f51ef02d97592a48ea7b800a444975463a6ebc8b90cdc562b7c774cb298a9ced`: issue #410's source-design requirements plus the accepted qualification clarification. The integrated design is the current synthesis; the raw research remains exact evidence.

I applied Tricritical `intent`, its rubric, shared input/output contracts, and invocation boundary. I read the recorded repository standards through `git show`, and the published collector, command contract, fixture procedure, reconciled findings, and relevant prior source research at the comparison revision. I did not read another current reviewer report or the worker's private conversation.

Before and after review, all candidate lengths and digests matched the manifest, and the manifest and requirements matched the supplied identities. All six retained vendor-source lengths and digests also matched the raw report before and after inspection. The raw research's embedded manifest matches its exact bytes. No changed dependency was observed.

## Findings

None within the frozen intent scope. The required result is a concrete source design with explicit remaining choices and acquisition effects. It does not require implementing the witness or resolving the later live grant. I found no current claim that depends on authentication, hostile-process resistance, an atomic snapshot, per-attempt model proof, or server-attributed account proof.

## Falsification attempts

### 1. A PID or binary pin might be presented as the fixture's actual executor

I tried the alternate operator framing: the useful result must identify the process behind this hook, rather than an installed package or launcher. Code RC `[203572506,203572856)` sets `CLAUDE_PID` from `process.pid`; `[207377300,207378500)` passes the hook session identity to command dispatch; `[207328962,207335850)` builds that environment and spawns the command. Manager `[1285600,1289250)` confirms launcher indirection. The raw design's acquisition table and supported join require bounded ancestry to the claimed PID, start-token comparisons, an opened executable descriptor, and byte comparison. It explicitly treats interpreter execution and longer wrapper chains as gaps. This survived: the proposed executable observation is distinct from a pin, and its positive meaning is limited to its observation interval.

### 2. The app's recorded PID might be an external passive observer already available

Code RC `[221256750,221258600)` reports its own PID during initialization. Manager `[1565500,1566750)` stores it only for a local backend while the held query still matches; `ZT` near `[634919,635100)` clears that tracking. The candidate calls this an existing internal producer and a proposed adapter input, not an externally callable observer. A new query or resume is not substituted for the selected query. This survived the access-versus-producer distinction.

### 3. A metadata match might manufacture selected-profile binding

I tested whether a matching event could silently supply the profile/account/org premise. Manager `[870200,870700)` takes the Electron user-data root; `[919200,919920)` distinguishes the current storage directory from the parked-task branch. Desktop core's `sW` and `By` export establish `claude-code-sessions`. Serializer `[450000,451000)` confirms the direct account/org getter; its initialization source and Desktop core's account/org resolvers show why cached hints or resolver calls are different observations. The raw report requires independent provenance for the supplied root and pair, exact path consistency, and a later UI/event/current-metadata join. Without independent provenance it retains only association with a declared directory. The adapter alternative names the missing manager fields and remains unselected. This survived; parent discovery is not promoted into active selection.

### 4. Small retained output might conceal broader acquisition

The process table enumerates named hook values, whole bounded stat records, executable-link text and target metadata, and one whole 243,059,896-byte executable read plus an overflow byte. The optional registry route selects exactly one PID-derived file from an independently supplied root, with up to two 256 KiB-plus-overflow acquisitions. Code RC `[200583000,200588300)` confirms broader serialized registry contents and updates; `[199163300,199164750)` confirms the source reader's ceiling. The report separately retains the accepted one-directory, 128-entry-plus-overflow and three-file, 1 MiB-plus-overflow metadata limits. Parent listings and config reads are explicit additional scopes. This survived: hashing or projecting fields is not described as reducing acquired contents.

### 5. Registry association or event-time endpoint might imply current-peer admission

I tried to treat a registry host/session/socket match as sufficient execution or send evidence. The candidate requires the executable witness independently, treats optional host identity as corroboration, and describes registry timestamps as different from hook production time. It forbids scan/cleanup helpers and fallback enumeration. The outcome facets preserve UI/Code association, supplied-directory binding, event-time endpoint, executable identity, lifecycle recheck, and restoration separately. A socket observation does not establish a current query or admitted peer. This survived the required separation.

### 6. The witness might inherit a deadline or turn-wide invariant

The raw report's supported join disclaims unchanged execution throughout the turn, same-PID exec detection, and complete module identity. Its ordering section records separate intervals and leaves the maximum join age and concrete recheck for the later packet. The synthesis explicitly identifies the executable read's unmeasured cost and separates it from the collector's stdin timeout. Neither the old receipt's deadline nor restart allowance carries over. Failures retain useful partial evidence without another setup turn. This survived the lifecycle, cost, and partial-result contract.

### 7. Research completion might weaken qualification or authorize integration

I compared the synthesis's remaining preparation choices with the frozen qualification clarification and published collector/procedure. The synthesis keeps full-state qualification separate and says the current collector does not implement this witness. It requires the preparer to consume reviewed revisions, select the mechanism, bind acquisition and lifecycle details, implement and review the chosen integration, and return remaining decisions before live authorization. Its numerical caps are proposals, not accepted privacy or control authority. This survived: source publication is a preparation input, not route qualification or a live grant.

## Scope and residual limits

This was one ordinary native-child intent execution. I inspected frozen source and retained vendor artifacts as data; I ran no vendor code, tests, private receiver observations, process scans, sockets, hooks, UI actions, or mutations. I did not adjudicate or edit. The coordinator retains responsibility for dispatch provenance, report-byte verification, publication, and the complete review result.

The process witness and adapter remain unimplemented and unobserved. Directory provenance, mechanism selection, exact launcher/environment, observation-stage deadline, join age, lifecycle recheck, integration, cleanup, and restoration remain preparation inputs. Relevant security/private-data review and later live observations are separate gates. This clean intent result does not certify those properties.
