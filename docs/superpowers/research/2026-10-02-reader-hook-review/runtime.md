# Findings

No actionable findings in the frozen runtime scope. The current reader and Stop projector implement the documented restricted specimen, keep results unqualified, and preserve the stated acquisition, timing, and producer limits. I found no current-contract contradiction requiring correction.

Candidate identity is the 28-file manifest SHA-256 `cbf10611c5c592426b4e01b3a343a2ce4c00a15e6f2c82ebcac45551228cc53b`. All 28 file digests matched before and after review. All three frozen requirement digests matched both times. Both nested archive manifests also matched. Review-input SHA-256 remained `5669be780326056b9866abd392e6ef2e6093aedbf14521df5186ea21f4b5fa55`. I independently confirmed that all 28 paths are absent at comparison base `b8760030957fefa1bc9c21bd6052373674d1971d`.

# Falsification attempts

I ran the candidate's named command:

```sh
node --test docs/superpowers/prototypes/receiver-evidence/reader.test.mjs docs/superpowers/prototypes/receiver-evidence/hook.test.mjs
```

All 20 tests passed, with zero failures, skips, or cancellations. The file tests created and removed their own invented temporary files. They demonstrated two explicit selections, missing-file failure, a 257-byte overflow read at a 256-byte limit, and no candidate evidence from that prefix. Those observations establish synthetic acquisition behavior only.

Ten additional in-memory probes passed:

- A later inconsistent record invalidated an otherwise matching prefix.
- Timestamp order conflicting with record order could not form a pair.
- Records later than capture completion were excluded.
- An exact user echo could not supply an assistant acknowledgment.
- Missing decoded peer body was not reconstructed from exact outer text.
- An extra unsupported record invalidated the restricted specimen.
- Multibyte text exceeding 1 MiB triggered the UTF-8 interpretation limit.
- Missing optional Stop fields retained an ACK candidate with explicit gaps and empty event fields.
- Padded Stop text did not match the exact supplied ACK rule.
- A recent Stop receipt retained producer-time uncertainty and unqualified status.

These attempts attacked prefix success, conflicting time, echo attribution, native-envelope guessing, schema widening, and optional-field handling. The candidate survived them within its claimed specimen. The retained named tests additionally exercise wrong identities, duplicate IDs, inner-role mismatches, quoted text, sidechain/summary exclusions, collector discontinuity, bounded projection, and compatibility distinctions.

I reconstructed `demo.html` entirely in memory using the documented assembly rule and canonical modules. It matched byte for byte. The page embeds the tested pure reader, projector, and fixtures, and invokes no filesystem adapter. I did not operate a browser or independently repeat the coordinator's DOM observations.

## Source evidence

I recomputed all six supplied source-member digests; they matched the identities recorded in the candidate. The engine was `dee301c3e248c62137cc15aafc2781bd5316c66720dd890d72e0054a024ce7d9`, 243,059,896 bytes. The stable SDK was `32d062c37b03e10870fbf839f54694545ee01bc0ec719e47078fbed76e30ef71`. Vendor members were inspected as data only.

Bounded primary-source checks supported the operative report:

- RC peer schema `[199623000,199627050)`, ingress `[221431000,221432900)`, forwarding `[221007150,221009550)`, user construction `[213089150,213090300)` and `[208923600,208925500)`, and persistence `[209117400,209119500)` and `[209129150,209130050)` support the corrected peer-origin and `isMeta` treatment. They do not authenticate sender-reported routing fields.
- Stop construction `[207307589,207308700)`, common fields `[207318493,207319450)`, last-assistant selection `[208919865,208919995)`, and text extraction `[208970859,208971099)` support normalized final-text matching and whole-event input exposure.
- Socket encoding/parser spans `[199156500,199157050)` and `[199159618,199160150)`, export `[221457200,221459450)`, and native send `[229205200,229209300)` support the source-target address path. The send call does not supply the transport's optional expected-process values.
- Getter and builder spans `[221193767,221194400)`, `[221225050,221226950)`, `[231927050,231928958)`, `[232758900,232759575)`, and `[198480300,198481700)` support applicable Code rules, named applied values, formatted status, and cwd fallback limits.
- Credential projection `[200803900,200805150)`, attempt fallback `[213024300,213027950)`, UI StatusLine construction `[226603350,226605900)`, and headless adapter `[221137250,221138350)` support the account, model, and StatusLine qualifications.
- Desktop serializer `[503942,509796)` and Manager initialization `[1520176,1521750)` support persisted Desktop/Code association without serialized `unarchivedCliSessionId`. Manager worktree resolution `[508311,511400)`, completed permission pushes `[1333100,1336850)`, and Desktop grant evaluators `[3692500,3693350)` support the remaining worktree, permissions, and expiry distinctions.

## Classification and residual limits

Selected-executor identity, independent selected-task witness, actual hook loading, native delivery, intentional correlated ACK, authenticated account route, complete effective permissions, and selected-query access remain future qualification gaps. The current increment explicitly retains them and does not depend on their fulfillment for its source/synthetic claims. No correction is required for those stronger guarantees within this review.

I did not reacquire public archives, execute or import vendor code, read private receiver state, use memory, inspect another critic's report, or perform live activity. Static checks were bounded source spot checks, not a new exhaustive producer inventory. Hostile-path containment, authorized-disclosure acceptance, and security-property acceptance remain outside this review. This report supplies runtime-review evidence to the coordinator; it does not adjudicate overall completion or qualify the live route.