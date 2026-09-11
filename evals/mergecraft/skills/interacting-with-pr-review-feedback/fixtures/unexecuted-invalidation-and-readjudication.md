# Unexecuted invalidation and fresh adjudication

An ordinary inline intent owns exact source revision `revision-44`. Its
atomic ordinary admission and `prewrite_validation_started` records committed.
The validation read found a new pull request head, and terminal
`prewrite_invalidated` committed before `write_started`. The bundle contains no
`write_started`, provider identity, unknown provider evidence, or response for
this owner.

A caller has the predecessor epoch and decision artifacts, can rename their
evidence IDs, and can restore the provider to the predecessor head. No
`replacement_basis` exists yet. The caller asks what must happen before a new
classification, adjudication, authority decision, and exact writer result can
be authored, and which fields the eventual successor may supply.

Describe the permitted transition, its durable links, and the next provider
boundary.
