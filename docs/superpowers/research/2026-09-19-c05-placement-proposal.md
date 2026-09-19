# Revised bounded placement: migrate C05 only

## Decision horizon

Propose one placement change inside the accepted four-method, 12-case cohort: move only C05 `single-quoted-backslash` from its full-CLI fixture to the accepted production file-identity interface, and add a focused repository-stage owner for C05. Keep C04 `canonical-repository` on its exact original `assert_identity_fixture(..., accepted=True, extension="yaml")` route. Keep C01–C04 and C06–C12 on their original full-CLI routes. This is the smallest positive split: 12 original full-CLI executions become 11; it does not attempt the larger set of removals that source decomposition might later make plausible.

This design preserves all seven adversarial rejection cases at their exact full-CLI owners. It also gives the one removed success assertion an executable repository-composition owner, rather than treating a direct False result or a prose reassignment as repository acceptance.

This is a source-only design proposal. It is not an implementation instruction, test result, runtime qualification, measured saving, migration recommendation, or approval of its own replacement.

## Bound evidence

All values listed by the supplied migration manifest were recomputed and matched.

- Migration packet `manifest.json` SHA-256: `345d338c63dcb4e27d25b1b5a8060beffaf6b990c3718d76d9fb71af0a14a49a`
- Embedded prior packet manifest SHA-256: `6c05a9170caf3407bf7ab61d1cdde2484482d0387bbb75a5be7ac46091995ce6`
- Current design boundary SHA-256: `ec65d9171f83ba4086bd70b0fe498ef30d4a00e27f39ba7d03bb93f857a85452`
- Prior independent review SHA-256: `0f81973b70dd2e9718d7ec2e40118e4f8a7ff102bc0b458af61f0f5ad71b3b58`
- [Published source commit](https://github.com/nisavid/provingkit/commit/89d895269db5652aafa9ff9a642114585e7bb709): `89d895269db5652aafa9ff9a642114585e7bb709`
- Prepared interface source identity: `5eb0f1df86e4e7407acda909905b3fe0c3f5cfd0`
- [Published `scripts/validate_provingkit.py`](https://github.com/nisavid/provingkit/blob/89d895269db5652aafa9ff9a642114585e7bb709/scripts/validate_provingkit.py) SHA-256: `3fe9ce6082134c766609fdf923f22c0b4476cef63588594f0ee8446f0d1fa03b`
- Prepared `scripts/validate_provingkit.py` SHA-256: `75a2143882118a233745dfa3548cb0e17e510283b599e9475a86f8057e1e6cd9`
- Published and prepared [`tests/test_validate_provingkit.py`](https://github.com/nisavid/provingkit/blob/89d895269db5652aafa9ff9a642114585e7bb709/tests/test_validate_provingkit.py) SHA-256: `33e6366e05c7d46ba4a7d1162fca63e5630eed90fee32cb62f33bbbc6a8c8d11`
- [Accepted issue criteria](https://github.com/nisavid/provingkit/issues/134) packet SHA-256: `917c4824990f603339af175678b1db0a0b041e64af3c0a321b0fbd4f1c54209f`
- Supplied interface patch SHA-256: `a362a00b3e115c9e94ca26172d9bebbfd545009843abf1b1dee99a0635e61326`
- Supplied 12-case matrix SHA-256: `d8bd721fc3a072d6a394193e7e28c769e6af23e80aa1bf937cd0e57d0d8c42d3`

The exact case bytes remain bound by the matrix hashes below and by the immutable [source-bound case inventory](https://github.com/nisavid/provingkit/blob/1494a78f2025544db0511c2909344973331d07e7/docs/superpowers/research/2026-09-18-file-identity-cases.json).

## Proposed executable shape

In `test_legitimate_yaml_semantics_remain_accepted`:

1. Leave the original `yaml.safe_load(document) == expected` assertion unchanged for C04, C05, and C06.
2. Leave C04 and C06 on the original full-CLI helper.
3. For C05 only, call `contains_historical_identity(Path("release/provingkit/unexpected-identity.yaml"), document.encode("utf-8"))` and require the singleton result `False`.
4. For C05 only, add a focused repository-stage owner. It must:
   - create the same repository fixture used by `assert_identity_fixture`;
   - write C05 with its exact matrix bytes at `release/provingkit/unexpected-identity.yaml`, preferably with `write_bytes` so encoding is not reinterpreted;
   - wrap `contains_historical_identity` while delegating to the real function, run `_validate_historical_identities(repository)`, and require normal completion;
   - assert that the scanner invoked the accepted interface exactly once for the target path with the exact C05 bytes;
   - run `_validate_release_boundary(repository)` on the same repository and require normal completion, because that is the other source-visible stage after the identity scanner that traverses arbitrary repository files.

That focused stage check is the concrete replacement owner for the content-sensitive portion of C05-CLI-1. The retained C04 and C06 full-CLI successes remain executable owners for `main` orchestration and zero-status conversion on the same YAML path. The prepared source shows that the other `main` stages load fixed contract paths, plugin membership, or Git history rather than interpret the arbitrary C05 fixture. If that dependency shape changes, this placement is stale and must be reviewed again.

## Placement matrix

“Original → proposed CLI” counts subprocess executions through the existing `validate` helper. Direct interface calls and the new repository-stage check are counted separately.

| Case | Exact input binding | Final direct owner | Final integration owner(s) | Original → proposed CLI | Unchanged assertions and preserved CLI obligation | New required checks and counterexample control |
| --- | --- | --- | --- | ---: | --- | --- |
| C01 | `release/provingkit/unexpected-identity.yaml`; `79dc64e925367703db334bb93c4b5f75871a125764b1fa0fcd4f9b8314248432`; reject | Original C01-YAML parse equality | Original C01 full CLI | 1 → 1 | C01-YAML and C01-CLI-1/2/3 remain byte-for-byte at the original owner: nonzero status, rejection diagnostic, and exact path | None. A hex escape that parses to the legacy repository but evades normalization, status mapping, or path reporting still fails the retained call. |
| C02 | `release/provingkit/unexpected-identity.yml`; `f3c3cf5dd4fef8857d07f485952498f77b9ab86ce82d03c2cf303916fd627a8c`; reject | Original C02-YAML parse equality | Original C02 full CLI | 1 → 1 | C02-YAML and C02-CLI-1/2/3 remain at the original owner | None. A `.yml` dispatch or escaped-line-break regression remains observable through exact status, diagnostic, and path assertions. |
| C03 | `release/provingkit/unexpected-identity.yaml`; `1a1b6811777be752ff602c9f753d5df8ec69733d89568b6e75f9bd86fbde0d2a`; reject | Original C03-YAML parse equality | Original C03 full CLI | 1 → 1 | C03-YAML and C03-CLI-1/2/3 remain at the original owner | None. A YAML-decode-then-percent-decode composition bypass remains caught by the exact original CLI. |
| C04 | `release/provingkit/unexpected-identity.yaml`; `246fcfa0e8c1b684e20b1ab225cba29681aa59cb03398b46e80dde47e812f2a5`; accept | Original C04-YAML parse equality | Exact original C04 full CLI | 1 → 1 | C04-YAML and C04-CLI-1 remain at the exact original owner, as required | None. A canonical-YAML-only detector, scanner, allowlist-composition, later repository-scan, or status regression remains caught by C04 itself. |
| C05 | `release/provingkit/unexpected-identity.yaml`; `6f93f721b84364e1286a811a0540e7738e1326f22e24f8d20c521323daeaf21f`; accept | Original C05-YAML parse equality plus new exact-path/exact-byte `contains_historical_identity(...) is False` | New exact C05 repository-stage owner; retained C04 and C06 full CLI for orchestration and zero-status mapping | 1 → 0 | C05-YAML is unchanged. C05-CLI-1’s effective zero-status obligation is decomposed into an exact content-sensitive stage check plus retained executable CLI status owners; it is not assigned to those owners by prose alone. | Require the five stage-owner checks above. Direct False alone would miss scanner bypass, normalized-byte delivery, allowlist-set failure, or release-wide scanning rejection; the stage owner catches each. A generic `main` status regression is caught by retained C04/C06. A newly added arbitrary-file consumer elsewhere in `main` invalidates this source proof and requires remapping. |
| C06 | `release/provingkit/unexpected-identity.yaml`; `bb90ab778f0de0f19150d7c674730e631675462146501a7e88264b089700538a`; accept | Original C06-YAML parse equality | Original C06 full CLI | 1 → 1 | C06-YAML and C06-CLI-1 remain at the original owner | None. The closest sibling to C05 stays end to end, so a double-quoted escaped-backslash acceptance regression still reaches the full validator. |
| C07 | `release/provingkit/unexpected-identity.md`; `512d00e79a123dfc828ea4efc41a560a1e1ec3c23e454f67d44faf1418c2d310`; reject | No separate direct owner; the file decision remains integrated | Original C07 full CLI | 1 → 1 | C07-CLI-1/2/3 remain at the original owner | None. Frontmatter extraction with LF and no BOM, rejection status, diagnostic, and path remain one exact executable claim. |
| C08 | `release/provingkit/unexpected-identity.md`; `13fefa0d04d753ffa265d67e3926598734d27ec37b5b925b38879be9f2d6ad0b`; reject | No separate direct owner; the file decision remains integrated | Original C08 full CLI | 1 → 1 | C08-CLI-1/2/3 remain at the original owner | None. A CRLF-specific frontmatter regression remains caught end to end. |
| C09 | `release/provingkit/unexpected-identity.md`; `3ea9a41365ed6c76d7d7a0328abd7e40e6da50b35f3728f3c14d0a0069bafc74`; reject | No separate direct owner; the file decision remains integrated | Original C09 full CLI | 1 → 1 | C09-CLI-1/2/3 remain at the original owner | None. A BOM-plus-LF regression remains caught end to end and retains the bytes used by the separate allowlist-hash test. |
| C10 | `release/provingkit/unexpected-identity.md`; `743e883b2faaf4d3cbe42abe10367dec207ed912c25045810f348df7bd87f4ec`; reject | No separate direct owner; the file decision remains integrated | Original C10 full CLI | 1 → 1 | C10-CLI-1/2/3 remain at the original owner | None. The combined BOM-plus-CRLF partition remains exact; neither C08 nor C09 substitutes for it. |
| C11 | `release/provingkit/unexpected-identity.md`; `df3b142ce6dff027bce34d9e3d03aea0fc3c22ad5a08bbec19762b359c63a46f`; accept | No separate direct owner; the file decision remains integrated | Original C11 full CLI | 1 → 1 | C11-CLI-1 remains at the original owner | None. Canonical metadata in BOM frontmatter and the non-YAML Markdown body remain accepted by the full validator. |
| C12 | `release/provingkit/unexpected-identity.md`; `b6cfd9e5833402aef16c0268051ab6225d7b9e84fef32a0d5c01431ca29417fb`; accept | No separate direct owner; the file decision remains integrated | Original C12 full CLI | 1 → 1 | C12-CLI-1 remains at the original owner | None. Literal-backslash metadata in BOM frontmatter remains accepted end to end. |

Totals: all 12 exact paths and byte sequences remain; all six YAML assertions remain at their original cases; 25 of the 26 CLI assertions remain at their exact original full-CLI owners; C05-CLI-1 is carried by the new exact C05 stage owner plus retained same-path full-CLI status owners. Full-CLI executions are 12 originally and 11 proposed. The proposal adds one direct predicate assertion and one focused repository-stage execution.

## Composition obligations outside the migrated row

The proposed change does not move or weaken these existing executable owners:

- all seven rejection statuses and all fourteen rejection diagnostic/path assertions in C01–C03 and C07–C10;
- `test_malformed_bom_frontmatter_reports_its_path` and `test_invalid_yaml_identity_source_fails_closed` for their exact malformed-input contexts;
- `test_repository_identity_scan_rejects_symbolic_links` for symlink handling;
- the active guidance and tracker-reference exemption tests for their exact special paths;
- `test_frontmatter_exception_binds_original_bytes_including_bom` for whole-file hashing of original BOM and non-BOM bytes, including matching and mismatching digests; and
- `test_historical_identity_allowlist_binds_the_delta_bundle` for its one entry and 31-entry count.

The source supplies more composition detail than those focused assertions prove. In the prepared candidate, `_validate_historical_identities` sorts `rglob` results, excludes `.git`, `__pycache__`, and the allowlist file, rejects symlinks, reads each file once, calls `contains_historical_identity(relative_path, content)`, stores the same original `content` only when detection is True, checks the observed and allowed path sets, and hashes the stored original bytes. The proposed C05 stage owner executes that scanner with the exact C05 file present, so traversal, interface wiring, path delivery, format dispatch, and allowlist-set acceptance are executable for C05. Original-byte hashing is meaningful only for detected allowlisted files; its explicit BOM/no-BOM owner remains unchanged.

## Evidence classification

### Proven by supplied source

- The accepted interface performs active-path handling, YAML or frontmatter extraction, normalization, and token detection.
- The production scanner calls that interface with repository-relative `Path` plus bytes read from the file, and retains the original bytes for allowlist hashing.
- The scanner’s post-predicate behavior branches on the Boolean result, not on C05’s YAML quoting form.
- `_validate_release_boundary` is the other post-scanner stage that traverses and reads arbitrary repository files.
- The remaining `main` stages read fixed contract paths, plugin membership, or Git history; the retained full-CLI cases continue to exercise their orchestration and status behavior.
- The published test file contains 12 cohort subprocess calls, 26 CLI assertions, and six YAML assertions.

### Proposed to be tested on a frozen candidate

- C05 returns exactly False through the accepted interface for its exact path and bytes.
- The production scanner actually calls that interface exactly once for C05 with those exact inputs.
- `_validate_historical_identities` and `_validate_release_boundary` both accept the repository containing exact C05.
- The retained 11 cohort CLI calls, all owning focused checks, and the complete suite pass on the same final revision.
- An independent security-routed reviewer accepts the concrete final replacement mapping after inspecting its exact bytes and source revision.

### Unsupported in this round

- That the proposed code compiles or passes.
- That one fewer full-CLI subprocess makes the complete suite faster in elapsed or runner time.
- Any amount or repeatability of savings.
- Runtime, hosted-run, deployment, or production qualification.
- Exhaustive security coverage of the validator or allowlist.
- Any placement change beyond C05.

## Required qualification before replacement

Freeze the concrete C05-only candidate and rebind its source, test, and patch hashes. Run the direct C05 check, the new C05 repository-stage owner, every retained owning check, and the complete suite on that same revision. Then obtain an independent review of the exact candidate; any change in the candidate or an evidence dependency makes the pass stale. Only after coverage review is clean should matched repeated complete-suite measurements decide whether the one-call reduction provides a positive practical saving. If it does not, the accepted result is to retain the current placement rather than widen the cohort or weaken acceptance.
