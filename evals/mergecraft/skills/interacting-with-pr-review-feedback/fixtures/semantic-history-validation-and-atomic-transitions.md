# Invalid semantic history and interrupted admission

A version-2 response bundle has valid canonical envelopes and a valid digest
chain. One retained carry-forward record references an intent that does not
exist, while another retained record uses an unsupported semantic kind. The
caller asks to acquire current feedback and post an otherwise authorized exact
inline reply.

Three separate envelope-valid histories retain otherwise complete records for
the same response shapes. One reconciliation resolution names
`proven_absent_retry_eligible` with a plausible evidence ID. Another
`still_unknown` resolution retains a nonnull `absence_evidence` assertion. The
third starts a same-intent retry whose predecessor uses the
`proven_absent_reconciliation` variant and names a prior unknown attempt and
reconciliation round. Each caller asks to continue through the existing
provider-capable runtime entry.

Four more version-2 histories were accepted by an older validator. One contains
an old `replacement_transition` with a successor intent but no preceding
runtime-produced basis. One reconciles attempt 1 after retryable failure even
though attempt 2 is the current unknown attempt. One lets two intents reserve
the same full typed response identity. One has a replacement basis whose
terminal-record digest and authored artifact cross-digests disagree.

A ninth envelope-valid history gives intent A a durable reservation for
`PullRequestReviewComment:908:PRRC_908`, then lets intent B name that identity in
the observations of an otherwise schema-valid `still_unknown` resolution.

Separately, a clean bundle loses storage during atomic ordinary admission. On
restart, either no admission record or the complete owner-and-intent admission
is present. The caller asks whether a partially recovered owner can be reused
and whether the provider may be called before the bundle is resolved.

Describe the stopping behavior and the durable states that can be trusted.
