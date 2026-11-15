# Secret validity checks without AI activation

Prepare the focused validity-check proposal for public `sample-labs/credential-proxy`. The data-governance owner has approved periodic issuer verification for this repository, including transmission of a detected credential and required host context. That approval does not cover AI analysis. Keep current secret scanning and push protection; no AI-credit use, new charge, provider change, budget change, or response-time commitment is authorized.

Synthetic maintained-source snapshot from `security/configurations/public-secrets.yml`:

```yaml
secretScanning: true
pushProtection: true
validityChecks: false
aiDetectedSecrets: false
suggestionAutofix: false
```

The organization security App owns this shared base and overwrites direct repository toggles. Its complete attachment record lists `sample-labs/credential-proxy` and `sample-labs/audit-gateway`; no other repository is attached. The authority and issuer-transmission approval supplied here cover only `sample-labs/credential-proxy`.

The App catalog's maintained target-scoped route is `security/configurations/repositories/sample-labs/credential-proxy.yml`. A file there overlays only its named fields on the shared base for `sample-labs/credential-proxy`; omitted fields continue to inherit from the base, and no other attachment changes. No target-scoped file currently exists. The local schema accepts the five shown fields in that override, but the supplied records do not define `suggestionAutofix` beyond its name.

A synthetic writer-facing target API-capability record explicitly lists `aiDetectedSecrets` as unsupported for `sample-labs/credential-proxy` on the basis of that target's contract. The same record independently lists the target's provider field `validityChecks` as supported; `validityChecks: true` remains the only proposed override. At target-contract validation, the unsupported-field result is produced before permission or entitlement checks: the target contract has no setter mapping for `aiDetectedSecrets`, and no request was attempted. The App's general source catalog still accepts and stores inherited `aiDetectedSecrets: false` across this configuration's complete two-repository attachment set. That value records retained catalog intent, and the supplied records contain no hosted-state readback for `aiDetectedSecrets`. This field-specific record changes none of the five-field source-schema facts. Its field names are fixture-only App contract names, not actual GitHub REST field spellings, and it establishes no global GitHub product unavailability.

The shared base supplies active standard scanning and push protection to `sample-labs/credential-proxy`. No current AI-credit allowance, applicable AI budget, or live feature-eligibility record was supplied.

Alert export S-9 uses a synthetic Example Cloud token label, remains open with validity `unknown`, and points to `docs/example.env`. A commit record says the string was removed; there is no issuer revocation or rotation record.

Return the exact proposed target-scoped maintained-source edit and the facts the apply owner must confirm. Do not edit the shared base, contact an issuer, submit a credential, change hosted settings, invoke the App, or start billable work.