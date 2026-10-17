# Capability-Scoped Signing and Custody Mechanisms

**Date:** 2026-09-16
**Status:** Public-source feasibility candidate for [provingkit#44][P44]; not an accepted decision, implementation design, qualification result, or provider choice

## Answer

Two small mechanism combinations are credible enough to carry into the next decision round:

1. a Task Witness signing adapter using one OpenBao Transit key path per capability authority, one Transit key version per authority generation, an explicitly bound derivation mode and (when derivation is enabled) context-derived key identity, path-scoped authenticated access, an enabled audit device, and an immutably retained public key; and
2. a Task Witness signing adapter using one Google Cloud KMS `CryptoKey` per capability authority, one `CryptoKeyVersion` per authority generation, a workload principal with key-scoped IAM, Data Access audit logging, and an immutably retained public key.

Both can produce signatures that remain verifiable offline after routine credential rotation. Neither mechanism understands a Task Witness claim: the Task Witness adapter must first construct the accepted canonical typed preimage and must bind the exact authority, capability set, implementation, Q8 binding core and payload, applicable Q9 host materialization, and Q10 attempt. The external signer should receive only those exact bytes or their contract-selected digest.

Both combinations are feasible only at the documented mechanism and pinned public-source layers. This research did not authenticate to either product, create or import a key, sign or verify data, inspect a host, test a runner, or qualify custody, recovery, availability, concurrency, audit completeness, or platform behavior. The public evidence therefore supports comparison, not adoption or production readiness.

The two combinations differ materially. OpenBao exposes a public, pinnable implementation and can run locally or at a separately chosen hosted boundary, but its storage, seal, recovery, availability, and audit operations become operator responsibilities. Google Cloud KMS removes the signing service and key-storage build from the hosts and gives each key version an explicit lifecycle, but the service implementation and build are not publicly pinnable, IAM cannot be granted to an individual key version, and the signing API has no caller-supplied attempt or idempotency field. Those differences are decision inputs, not a recommendation.

## Authority and current source boundary

The live public tracker state at dispatch matched the gate: #44 was open, assigned only to `nisavid`, contained one exact public claim, and named two native predecessors; both [agents#42][A42] and [agents#46][A46] were closed as completed. The claim grants this public-source report, not key, account, hosted-service, host, implementation, qualification, release, or publication authority beyond root's separately owned workflow.

The parallel invocation-evidence study in #43 remains independent and supplies no premise or conclusion to this signing-custody comparison. [P44]

The accepted #8 decisions remain fixed:

- Producer, issuer, validator, and consuming-workflow duties stay distinct. Task Witness validation does not grant workflow authority, and resistance to compromise of the shared Task Witness runtime/control domain is explicitly outside the required guarantee. [P8-Q1Q6]
- Authorities are capability-scoped program authorities, not a Provingkit-wide signer or persona identity. Receipts use a closed value-free binding core with typed payloads, bind platform-specific materialization where applicable, and retain immutable linked attempts and honest non-success states. [P8-Q7Q10]
- Authentication uses asymmetric signatures. One authority generation binds one exact verification key and scheme to the authority ID, evidence contract, reviewed implementation, and allowed capabilities. Rotation creates a new immutable trust context; the old generation becomes historical-only. Suspected compromise revokes the generation and reopens dependent evidence. Receipts are never rewritten or re-signed. [P8-Q11]

The artifact baseline also narrows what this report can claim. At [`8783281f165676d5202c455efc10018fb3b4ec07`][PK-BASE], Task Witness is optional future equipment outside the current Slate. The Rolecasting and Tricritical provider declarations still contain validators but empty `producers` and `issuers` arrays. [PK-CONTEXT] [PK-ROLE] [PK-TRI] The retained canonical design describes a cooperative current-EUID boundary and an immutable trust-context shape, but it is not an active production signer. [PK-DESIGN] No candidate below changes that status or places Task Witness into the preview slate.

The historical harness inventory establishes documentary host context only: a then-observed CachyOS x86_64 system and a then-observed macOS arm64 system. It is not current available-host evidence and is not used as qualification. [A-INVENTORY] The Base/Host composition contract keeps credential requirements, opaque secret bindings, and injection projections value-free and explicitly leaves custody products, key delivery, and signing algorithms outside that contract. [A-COMPOSITION]

## Method and evidence layers

I used only public primary sources: public issue records, immutable repository revisions, official product source and release metadata, official API documentation, and a pinned public API definition. Moving documentation was retrieved on 2026-09-16 and is hashed in the companion manifest. Pinned source was preferred wherever the owner publishes it.

I also consumed a public Context7 discovery pass after drafting. Its OpenBao result resolved the official `/openbao/openbao` corpus and corroborated current documentation for path ACLs, key configuration and trimming, and audit behavior. Its Google lookups did not resolve a dedicated Cloud KMS API corpus; the selected official Cloud SDK snippets were treated only as locators and not as evidence of KMS API coverage or absence. These results changed no factual conclusion or source coverage: every candidate claim remains grounded in the direct pinned or dated-and-hashed primary sources in the companion manifest.

Every conclusion is limited to one of these layers:

1. **Decision or contract:** accepted public requirements and repository source shape.
2. **Documented mechanism:** the owner documents an interface or behavior.
3. **Pinned implementation/API source:** exact public source contains the described fields or control.
4. **Platform applicability:** the mechanism has a public distribution or network interface plausibly usable from the target platform.
5. **Credentialed operation:** an authenticated real product call works with a selected identity and key.
6. **Qualification:** the exact reviewed implementation, route, platform, cases, and retained evidence meet an accepted policy.

This report reaches layers 1–4 only. Applicability is not credentialed operation, and neither is qualification.

## Smallest credible combinations

Each combination includes a narrow Task Witness adapter because neither signing product enforces Task Witness's canonical evidence semantics. That adapter can remain in the accepted shared runtime/control domain. The accepted compromise exclusion means this study does not require a second compromise-resistant runtime; it also means the external signer cannot be advertised as protecting against compromise that can use the same admitted caller credential.

| Required field | Combination A: OpenBao Transit | Combination B: Google Cloud KMS |
| --- | --- | --- |
| Mechanism boundary | Self-operated or separately hosted OpenBao server; signing occurs behind the Transit HTTP API. Minimal credible set: adapter, authenticated machine identity/token, exact path policy, asymmetric Transit key with an explicitly bound derivation mode, audit device, and retained public key. A derivation-enabled Ed25519 branch additionally requires a bound context-derived identity and caller-context control. | Managed Cloud KMS service; signing occurs through the version-addressed REST/gRPC API. Minimal credible set: adapter, authenticated workload principal, key-scoped IAM, asymmetric `CryptoKeyVersion`, Data Access audit log, retained public key. |
| Signature scheme and stable identifier | Transit supports Ed25519, ECDSA, and RSA signing. This report selects none. The native signature prefix carries a key version but not the complete authority meaning. A retained generation identifier must bind authority ID, Transit mount and key identity, exact key version, key type, the key's `derived` mode, hash, `prehashed`, RSA/ECDSA options where applicable, and the verification-key digest. When Ed25519 derivation is enabled, it must also bind the exact decoded context bytes or a collision-resistant digest of them; one Transit version can otherwise identify multiple effective verification keys. [O-TRANSIT] [O-SOURCE] | An asymmetric-signing algorithm is fixed on each key version. This report selects none. The retained generation identifier must bind the full `CryptoKeyVersion` resource name, returned algorithm, public-key format and digest, and authority ID. The API response returns the exact version name used. [G-ALGORITHMS] [G-PROTO] |
| Canonical message and prehash | Task Witness must canonicalize first. Transit accepts base64 input and can hash internally, or accepts a prehash when `prehashed=true`; Ed25519 has its own hashing behavior, while RSA exposes padding and salt choices and ECDSA exposes marshaling. The generation must freeze every signing parameter and every identity-changing derivation parameter to prevent double hashing, key-identity ambiguity, or verifier disagreement. [O-TRANSIT] [O-SOURCE] | `AsymmetricSign` accepts either `digest` or `data`, never both; the key algorithm controls which form and digest are valid. CRC32C fields protect transport integrity but do not replace the signed-domain or canonical-message contract. [G-SIGN] [G-PROTO] |
| Key generation, import, export, and public material | Transit can generate keys or import wrapped private key material. `derived` defaults false. If an Ed25519 key is derivation-enabled, the sign request requires a base64 context, different decoded contexts under one version can produce different public keys, and the sign response returns the effective derived public key. `exportable` and plaintext-backup enablement default false and become irreversible when enabled. The generation must retain the exact effective public key and its digest before later disablement or deletion; for derived Ed25519 it must use the public key returned by the admitted signing response rather than treating the version's base public metadata as sufficient. [O-TRANSIT] [O-SOURCE] | Cloud KMS can generate an asymmetric key version or import one through an import job. `GetPublicKey` returns version name, algorithm, protection level, public key, and integrity metadata. The cited API exposes public-key retrieval; this evidence establishes no private-key export path. Imported source material may still exist at its origin and therefore has a different custody claim. [G-PUBLIC] [G-IMPORT] [G-PROTO] |
| Exact interface and support evidence | `POST /v1/transit/sign/:name(/:hash_algorithm)` with `key_version`, `input` or `batch_input`, and scheme parameters; `GET /v1/transit/keys/:name` for public metadata. The pinned source is OpenBao v2.6.2 at `dd9c19c37a878cf4a81b18efb8d6f0599c7da923`. [O-RELEASE] [O-TRANSIT] [O-SOURCE] | `POST https://cloudkms.googleapis.com/v1/{name=projects/*/locations/*/keyRings/*/cryptoKeys/*/cryptoKeyVersions/*}:asymmetricSign` and `GET .../{cryptoKeyVersion}/publicKey`; the pinned public contract is the `googleapis` proto at `5f61cd5a991506c795a2b0a3639eb5e1b0cb6b27`. [G-SIGN] [G-PUBLIC] [G-PROTO] |
| Local or hosted execution | The client and server may be colocated or separated, but the deployment, storage, TLS, seal/unseal, recovery, and availability boundary must be selected later. Local placement does not make Transit part of ordinary plugin lifecycle. | Signing and private-key operations are hosted. The Task Witness adapter and offline verifier remain local to their selected execution cells. Network and provider availability enter the evidence path. |
| Capability and caller controls | OpenBao policy is deny-by-default and path-based. One Transit key path per capability authority lets a token receive only the sign operation for that path; broader globs or policy unions would widen authority. The adapter must submit the generation's exact explicit `key_version`; omitting it resolves the current latest version and can change the effective key. Path policy also does not constrain a sign request's derivation context. An admitted derived-Ed25519 caller could therefore select multiple effective keys under the same path and version unless an independently reviewed adapter enforces the generation's exact decoded context before every single request and for every batch item. A non-derived generation instead requires `derived=false` and forbids context in both forms. Policy does not inspect Task Witness claim semantics, so the adapter and retained trust context remain mandatory. [O-POLICY] [O-TRANSIT] [O-SOURCE] | `cloudkms.cryptoKeyVersions.useToSign` can be granted at the `CryptoKey` level but not at an individual version. One `CryptoKey` per capability authority is therefore required for external capability separation; a version can represent a generation only while every historical version that must not sign is disabled. The predefined signer role's lowest grantable resource is `CryptoKey`. [G-IAM] |
| Product authentication | OpenBao authentication yields a token whose policies control API access. AppRole is documented for automated machines and services and can constrain token/SecretID lifetime, uses, and source CIDRs. The chosen auth method, credential delivery, and token lifecycle remain undecided. [O-APPROLE] | Google APIs authenticate separately from KMS authorization. ADC can obtain credentials from several sources; Workload Identity Federation can exchange an external workload identity for short-lived access and can grant a federated principal direct access to a resource. The identity provider, credential source, and host binding remain undecided. [G-ADC] [G-WIF] |
| Unattended and interactive behavior | AppRole explicitly supports automated workflows; interactive operator authentication is not required by the mechanism. Setup, unseal, recovery, and some policy operations may still require operator action depending on the deployment, which this report does not choose. | Workload and attached-service identities support unattended calls. User ADC is a distinct interactive/development path and is not implied for production. No authentication path was exercised. |
| Authority-generation identity | Map exactly one Transit key version, `derived` mode, and effective verification key to one immutable Task Witness authority generation. For `derived=false`, context is forbidden. For derivation-enabled Ed25519, the generation also binds the exact decoded context bytes or their collision-resistant digest, the adapter enforces that context, and retained public material comes from the signing response. Rotation or a change to any identity-changing input creates a new retained generation before new evidence is admitted. A key path or version alone is insufficient. Exact retained-public-key matching still rejects a signature under an unregistered derived key; the missing context contract would be an identity/admission defect, not by itself a demonstrated forgery or custody compromise. [O-TRANSIT] [O-SOURCE] | Map exactly one full `CryptoKeyVersion` name and verification key to one immutable Task Witness authority generation. A `CryptoKey` alone is insufficient because it can contain multiple versions and IAM applies across those versions. |
| Rotation, disablement, revocation, historical verification | Transit rotation creates a new key version. `min_encryption_version` controls the oldest version allowed to sign; `min_decryption_version` controls the oldest version the Transit verify endpoint accepts. Soft deletion blocks signing and verification for the whole key and can be restored. Task Witness revocation remains the authoritative evidence decision, while the immutably retained public key permits offline historical verification independently of Transit. [O-TRANSIT] | Cloud KMS does not automatically rotate asymmetric keys. Rotation requires a new version and public-key distribution. Old versions remain enabled until explicitly disabled; disabled versions can be re-enabled. Destruction eventually removes key material and public-key download, so Task Witness must retain the public key and metadata first. Provider disablement stops new signing; Task Witness compromise revocation separately reopens dependent evidence. [G-ROTATION] [G-STATES] |
| Audit and invocation correlation | Enabled audit devices log API requests, responses, and errors; request and response records share a unique request identifier and most strings are HMACed. Auditing is not enabled by default, and OpenBao can block service when no audit device can record. The adapter must retain the provider request ID or a verified mapping; the single-sign request has no caller-supplied Task Witness attempt field. [O-AUDIT] | `AsymmetricSign` is a Data Access audit event. The sign request/response proto has no caller-supplied attempt or idempotency field. The adapter must bind Q10 attempt identity inside the signed preimage and retain a qualified mapping to provider audit metadata; public source does not yet prove a lossless one-to-one correlation recipe. [G-AUDIT] [G-PROTO] |
| Concurrency, failure, retry, and recovery | Batch signing preserves input order, supports per-item errors, and offers a caller `reference` only for batch correlation. There is no documented idempotency token or signature-operation readback. A lost response remains indeterminate unless qualified audit evidence narrows it; a retry is a new Q10 attempt. Server concurrency and recovery depend on the unselected storage/HA/seal design. Plaintext backup and soft-delete restore exist but are not an accepted recovery policy. [O-TRANSIT] [O-AUDIT] | Calls are quota-governed and can fail for resource exhaustion or service/network conditions. CRC32C mismatch guidance permits only bounded retries. There is no signature-operation readback or idempotency token in the pinned request. A lost response therefore remains indeterminate; a retry is a new Q10 attempt. Recovery can re-enable a disabled version or restore a destruction-scheduled version; a destroyed generated version is not recoverable, while eligible imported material may be re-imported. [G-QUOTAS] [G-PROTO] [G-STATES] [G-IMPORT] |
| Source and build dependencies | The server implementation, API documentation, and sign/verify handler are pinnable at v2.6.2; `go.mod` declares Go 1.25.8. Official release metadata lists `darwin_arm64` and `linux_amd64` artifacts. A selected deployment would also need pinned server configuration, storage, seal, TLS, auth, audit, adapter, and verifier identities. [O-RELEASE] [O-SOURCE] [O-BUILD] | The public API schema is pinnable, but the managed service implementation and build are not. A selected implementation would need a pinned Task Witness adapter, authentication library or direct protocol implementation, transport/TLS trust, chosen algorithm verifier, API contract, and provider assurance inputs. No client library or framework is selected here. [G-PROTO] |
| Platform and execution boundary | Published artifacts make native OpenBao execution documentary-applicable to macOS arm64 and Linux x86_64. That does not show CachyOS compatibility, GitHub runner behavior, installed state, custody behavior, or qualification. A remote Transit server would reduce client-platform dependence but add a network boundary. | REST/gRPC makes the signer client independent of a local KMS binary. That supports documentary applicability from Linux x86_64 and a GitHub-hosted macOS arm64 runner with a suitable authenticated client, but no exact client, runner image, credentials, request, or verifier were tested. Hosted key custody itself is outside runner control. |
| Operational tradeoff | Strong public source transparency and flexible placement; larger operator-owned state, availability, seal, recovery, and audit burden. Parameter-rich signing API creates more configuration that the generation must freeze. | Smaller host footprint and explicit version lifecycle; provider/service dependence, network availability, opaque service build, key-level rather than version-level IAM, and weaker native attempt correlation. |

## Cross-candidate findings

### Capability scope needs both an external resource boundary and a Task Witness binding

Neither product authorizes the semantic statement “issue only a Tricritical terminal observation for this exact contract.” OpenBao authorizes a path and operation. Cloud KMS authorizes a principal to sign with a key. The narrowest credible shape is therefore:

```text
authenticated caller
  -> one externally isolated key per capability authority
  -> one exact key version plus all identity-changing parameters per authority generation
  -> signature over the Task Witness canonical typed preimage
  -> offline validation against an immutable retained generation
```

The external key boundary limits which authenticated callers can use which key. The retained trust context limits what that key is allowed to mean. Omitting either layer broadens authority.

OpenBao can place each authority on a distinct sign path. Cloud KMS IAM cannot target a key version, so each capability authority needs a distinct `CryptoKey`; version state then controls which generation can still sign. In both cases, a compromised shared Task Witness runtime that holds or can invoke the admitted credential may still sign. That condition is the accepted Q2 exclusion, not a hidden mechanism guarantee.

For OpenBao, the path boundary alone is incomplete when Ed25519 derivation is enabled. The same path and Transit version can accept different contexts and return different public keys. An admissible generation must either bind `derived=false` and reject context or bind one exact decoded context (or its collision-resistant digest), enforce it before every single call and for every batch item, and retain the effective public key returned by signing. Exact verification-key matching prevents a receipt signed under any other derived public key from being accepted as that generation.

### Product authentication is not signing identity

An AppRole/token or Google workload principal proves who may call the product. The receipt's portable signing identity is the Task Witness authority generation: exact public key, scheme, authority ID, contract, implementation digest, and capabilities. Product credential rotation may leave that generation unchanged; signing-key rotation always creates a new generation. Keeping these identities separate avoids treating a token, account, role, or service name as portable cryptographic authority.

### Offline verification requires retaining more than a signature

Each immutable generation must retain at least:

- the exact public verification bytes and their digest;
- the complete scheme/prehash/marshaling identifier;
- every identity-changing key configuration and request input, including OpenBao `derived` mode and, when enabled for Ed25519, the exact decoded context bytes or their collision-resistant digest;
- the authority ID, allowed capabilities, evidence contract, and reviewed adapter implementation digest;
- the external resource/version identity and its documented protection/origin metadata;
- activation, historical-only, and compromise-revoked status as immutable trust-context generations; and
- the canonical preimage contract and all Q8/Q9/Q10 bindings needed to reconstruct or validate the signed bytes.

Provider lifecycle state cannot replace Task Witness revocation. Disabling a key prevents new provider operations but does not make old signatures invalid. Destroying a provider key can also remove later public-key retrieval. Historical verification therefore depends on public material retained before lifecycle changes.

### Neither API supplies exactly-once signing

Neither pinned signing request carries an idempotency token or a Task Witness attempt ID, and neither product exposes a signature-operation readback endpoint. OpenBao supplies a service-generated audit request ID; Cloud KMS supplies audit events and returns the used version name. Those can support correlation only after an exact retention and mapping contract is qualified.

The accepted Q10 model is therefore necessary for both candidates: an ambiguous response produces `indeterminate`; retry uses a new attempt identity linked to the first; identical receipt bytes remain the same observation; and audit readback narrows uncertainty only to what it actually proves. Randomized signature schemes may also produce different signature bytes for the same preimage, so signature equality cannot be used as request deduplication.

## Infeasible or incomplete alternatives

These are not padded into the credible set:

- **Shared-secret MAC:** rejected by accepted Q11 because every verifier that holds the secret could mint indistinguishable evidence. It does not provide the required verifier/issuer separation. [P8-Q11]
- **A delegating certificate root as the authority:** rejected by accepted Q11 because it grants broader delegation than the exact capability-scoped generation. A certificate may carry metadata, but a general issuing root cannot replace direct pinning of the exact verification key without reopening the decision. [P8-Q11]
- **One Provingkit-wide key, one persona key, or one product-account key:** rejected by Q7. Those identities can authenticate unrelated claims and do not follow the exact program/observation capability. [P8-Q7Q10]
- **A raw private-key file, desktop keychain item, hardware token, or PKCS #11 object used directly by the shared runtime:** incomplete on the allowed public evidence. Custody alone does not establish canonical-message enforcement, one key per capability authority, caller-scoped admission, generation disablement, audit correlation, or Q10 recovery. A new broker could add those properties, but no reviewed broker is an input to this study, and inventing a general signing framework is out of scope.
- **OpenBao without a configured audit device or with one broadly shared sign path:** incomplete. OpenBao starts without auditing, while broad path policy would collapse capability separation. [O-AUDIT] [O-POLICY]
- **Cloud KMS with one `CryptoKey` shared by multiple capability authorities or with historical versions left enabled:** incomplete. IAM cannot be granted per version, and every enabled version of the permitted key remains signable. [G-IAM] [G-STATES]

These dispositions do not claim global impossibility. They state why the supplied public evidence does not meet this contract without additional mechanism or a reopened decision.

## Platform assurance and qualification boundary

The current portfolio policy makes the live CachyOS x86_64 environment the Linux subject and limits macOS assurance to what GitHub-hosted macOS CI can establish. Personal-Mac access is neither required nor authorized. Runner-inaccessible hardware, desktop, provider, persistence, and custody behavior remains explicitly unqualified and nonblocking for macOS. Fixtures and mocks prove only their exercised behavior. [D258]

For a later exact candidate, Linux qualification must bind the reviewed adapter, chosen client/runtime, actual CachyOS platform and architecture, exact external route, authentication identity class, key generation, canonical/prehash cases, positive and negative signing cases, audit correlation, disablement, rotation, retry, failure, and recovery evidence. This report supplies none of those observations.

GitHub-hosted macOS qualification can cover build/installability of the public client pieces, deterministic canonicalization and offline verification, disposable authenticated calls only if separately authorized with non-production material, negative cases, and retained runner metadata. It cannot qualify a personal keychain, physical token, persistent host deployment, provider custody administration, or any hardware interaction the runner cannot reach. CI receives no production signing or custody material under the platform-assurance contract.

OpenBao's published `darwin_arm64` and `linux_amd64` artifacts establish distribution applicability only. Cloud KMS's network API establishes protocol applicability only. Neither is passing macOS or Linux evidence.

## Static validation assessment

The security-validation path was static because the task expressly forbids every dynamic signing, key, account, service, credential, runner, and host action. I applied five criteria: exact interface/generation representation; separate capability, authentication, and custody controls; coherent rotation/revocation/historical verification; honest attempt/audit/failure behavior; and correctly bounded two-platform applicability.

| Candidate | Public-mechanism disposition | Evidence that survives | Proof gaps that remain |
| --- | --- | --- | --- |
| OpenBao Transit combination | **Credible with mandatory conditions** | Exact public sign/read/rotate/config interfaces; pinned server handler and v2.6.2 source; path ACL and machine authentication; versioned keys; derivation mode/context behavior and returned effective public key; audit request IDs; target-architecture release artifacts. | Exact algorithm and prehash; `derived=false` with forbidden context versus derived Ed25519 with one bound, adapter-enforced decoded context and response public key; deployment/storage/seal/TLS; auth and secret handoff; audit configuration and retention; single-attempt mapping; HA/concurrency; backup/recovery; CachyOS and runner execution; credentialed operation; qualification. |
| Google Cloud KMS combination | **Credible with mandatory conditions** | Exact version-addressed sign/get-public-key API; pinned proto; key-scoped IAM; workload identity options; explicit version states; manual asymmetric rotation; Data Access audit classification; quotas and bounded CRC retry guidance. | Provider and protection-level choice; service build transparency; exact algorithm/prehash; principal and credential binding; log enablement/retention and single-attempt mapping; network failure/readback; client/runtime build; credentialed operation; platform qualification. |

Both candidates pass only the stated public-mechanism rubric. A change to either candidate shape, its API/source evidence, or the accepted #8 contract makes this pass stale and requires a new whole-candidate review.

## Assumptions and unresolved decision inputs

The comparison assumes that Q2's shared-runtime compromise exclusion remains accepted, that each adapter can be reviewed and content-pinned, that one external key resource may be allocated per exact capability authority, and that offline validators can retain public, value-free generation data. None of those assumptions authorizes implementation.

The following inputs remain unresolved and can change feasibility or tradeoffs:

- exact signature algorithm, key size/variant, signature encoding, prehash rule, and domain-separated canonical preimage;
- whether the authority uses generated or imported key material, and the required custody/protection, export, backup, destruction, and recovery claim;
- self-operated versus hosted execution, including availability, network, storage, seal, TLS, and service-build assurance;
- exact product authentication and value-free Host Binding, credential lifetime, principal scope, and recovery path;
- mapping of capability sets to external key resources and of key versions plus every effective-verification-key input to immutable Task Witness generations, including OpenBao derivation mode and any exact decoded Ed25519 context;
- audit enablement, integrity, retention, access, request/attempt correlation, and the evidence that can safely enter a portable receipt;
- concurrency limits, bounded retry policy, lost-response handling, provider readback, and recovery tests;
- exact adapter and offline-verifier source/build closure for Linux x86_64 and GitHub-hosted macOS arm64; and
- qualification policy, cases, independent review owner, and acceptance authority.

No public source established credentialed operation, a live compatible CachyOS client, a working GitHub-hosted macOS cell, an accepted recovery ceremony, or a production authority generation. The managed-service backend build is not publicly pinnable. OpenBao's public implementation is pinnable, but no selected deployment or protected storage boundary exists in this evidence set.

## Exact next frontier for #8

The next #8 decision round can now ask one bounded question:

> For each accepted capability-scoped producer or issuer authority, should an authority generation use the self-operated Transit combination, the managed KMS combination, or neither—and what exact scheme/prehash, external resource-to-capability mapping, effective-verification-key parameters, caller authentication, custody/origin, historical-key retention, disable/revoke, attempt/audit correlation, retry/recovery, and platform-qualification contract makes that choice admissible?

The decision must then freeze the selected adapter and verifier source/build ownership, trust-root and generation record, value-free Host Binding inputs, Linux and macOS CI qualification cells, and independent security-review boundary before creating the already-required implementation, independent security-review, and host-qualification tickets. If neither combination's remaining proof gaps can be closed within the accepted boundary, #8 should reject both rather than weaken Q7–Q11.

This frontier concerns evidence-receipt signing only. Release-artifact signatures, whole-release composition, provider descriptors, and evidence rebinding remain owned by #3. This report grants no adoption, signer, stakeholder, deployment, release, preview, or production authority.

## Procedure-capture proposal

This correction exposes a reusable review gap, but it does not authorize an installed or shared procedure edit. The procedure owner should add one conditional-identity-parameter gate to the maintained public-source signing-custody research/review procedure: enumerate every product configuration and request parameter that can change the effective verification key; for each parameter, record the owning primary source, require it to be disabled or bind its exact normalized value (or a collision-resistant digest) into the immutable authority generation, identify the admission control that enforces that value, and verify that retained public material matches the effective key returned or used by the signer.

The OpenBao regression case includes the named mount/key resource, an explicit `key_version` rather than the moving latest-version default, `derived`, and decoded Ed25519 `context`: the resource and version are bound; `derived=false` makes context forbidden; `derived=true` requires one bound context, an independently reviewed pre-invocation check over single requests and every batch item, and the response public key. Future signing-custody researchers must invoke this gate while drafting stable-identifier, public-material, caller-control, and authority-generation rows. Independent reviewers must rerun it against the complete pinned key-configuration and sign-request schemas before accepting those rows. Canonical placement and installation remain an operator decision; this report changes no shared equipment.

[P44]: https://github.com/nisavid/provingkit/issues/44
[A42]: https://github.com/nisavid/agents/issues/42
[A46]: https://github.com/nisavid/agents/issues/46
[P8-Q1Q6]: https://github.com/nisavid/provingkit/issues/8#issuecomment-5565178275
[P8-Q7Q10]: https://github.com/nisavid/provingkit/issues/8#issuecomment-5567698314
[P8-Q11]: https://github.com/nisavid/provingkit/issues/8#issuecomment-5568191158
[A-INVENTORY]: https://github.com/nisavid/agents/blob/3e30fec6f0379b15ded9ba71fbd83114872390a7/docs/superpowers/research/2026-09-07-live-harness-inventory.md
[A-COMPOSITION]: https://github.com/nisavid/agents/blob/537ff5d38b334598aab8c8abec092dbd7e827c7a/docs/superpowers/specs/2026-09-08-base-host-loadout-composition.md#secret-handoff
[D258]: https://github.com/nisavid/dotfiles/issues/258#platform-assurance
[PK-BASE]: https://github.com/nisavid/provingkit/commit/8783281f165676d5202c455efc10018fb3b4ec07
[PK-CONTEXT]: https://github.com/nisavid/provingkit/blob/8783281f165676d5202c455efc10018fb3b4ec07/CONTEXT.md
[PK-ROLE]: https://github.com/nisavid/provingkit/blob/8783281f165676d5202c455efc10018fb3b4ec07/plugins/rolecasting/task-witness-provider.json
[PK-TRI]: https://github.com/nisavid/provingkit/blob/8783281f165676d5202c455efc10018fb3b4ec07/plugins/tricritical/task-witness-provider.json
[PK-DESIGN]: https://github.com/nisavid/provingkit/blob/8783281f165676d5202c455efc10018fb3b4ec07/docs/superpowers/specs/2026-07-27-task-witness-canonical-client-design.md
[O-RELEASE]: https://github.com/openbao/openbao/releases/tag/v2.6.2
[O-TRANSIT]: https://github.com/openbao/openbao/blob/dd9c19c37a878cf4a81b18efb8d6f0599c7da923/website/content/docs/api/secret/transit.mdx
[O-POLICY]: https://github.com/openbao/openbao/blob/dd9c19c37a878cf4a81b18efb8d6f0599c7da923/website/content/docs/concepts/policies.mdx
[O-APPROLE]: https://github.com/openbao/openbao/blob/dd9c19c37a878cf4a81b18efb8d6f0599c7da923/website/content/docs/auth/approle.mdx
[O-AUDIT]: https://github.com/openbao/openbao/blob/dd9c19c37a878cf4a81b18efb8d6f0599c7da923/website/content/docs/audit/index.mdx
[O-SOURCE]: https://github.com/openbao/openbao/blob/dd9c19c37a878cf4a81b18efb8d6f0599c7da923/builtin/logical/transit/path_sign_verify.go
[O-BUILD]: https://github.com/openbao/openbao/blob/dd9c19c37a878cf4a81b18efb8d6f0599c7da923/go.mod
[G-SIGN]: https://cloud.google.com/kms/docs/reference/rest/v1/projects.locations.keyRings.cryptoKeys.cryptoKeyVersions/asymmetricSign
[G-PUBLIC]: https://cloud.google.com/kms/docs/reference/rest/v1/projects.locations.keyRings.cryptoKeys.cryptoKeyVersions/getPublicKey
[G-ALGORITHMS]: https://cloud.google.com/kms/docs/algorithms
[G-IAM]: https://cloud.google.com/iam/docs/roles-permissions/cloudkms
[G-ADC]: https://cloud.google.com/docs/authentication/application-default-credentials
[G-WIF]: https://cloud.google.com/iam/docs/workload-identity-federation
[G-ROTATION]: https://cloud.google.com/kms/docs/key-rotation
[G-STATES]: https://cloud.google.com/kms/docs/key-states
[G-AUDIT]: https://cloud.google.com/kms/docs/audit-logging
[G-QUOTAS]: https://cloud.google.com/kms/quotas
[G-IMPORT]: https://cloud.google.com/kms/docs/importing-a-key
[G-PROTO]: https://github.com/googleapis/googleapis/blob/5f61cd5a991506c795a2b0a3639eb5e1b0cb6b27/google/cloud/kms/v1/service.proto
