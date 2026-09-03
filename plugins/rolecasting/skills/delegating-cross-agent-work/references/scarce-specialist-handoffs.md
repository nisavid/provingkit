# Scarce-specialist handoffs

Use a scarce specialist for one bounded decision horizon over the smallest
content-addressed frozen input packet that can support the decision. The packet
states the exact question, authority, acceptance boundary, output contract, and
stop condition. Discovery and open-ended context gathering stay outside the
specialist dispatch.

Require the specialist to return one exact byte-stable artifact, its artifact
identity and SHA-256 digest, its assumptions and remaining fog. The returned
bytes are the specialist's decision record. A summary is not
a substitute for that artifact.

The cheaper coordinator owns discovery, setup, status, context assembly,
waiting, exact-byte relay or separately authorized publication,
post-verification, byte-preserving placement or integration, and tracker work.
Rolecasting allocates that lifecycle work; it does not grant publication
authority or decide a finding's disposition. Integration that changes meaning,
supported inputs, or evidence bytes returns to the specialist.

The coordinator must relay the returned artifact byte for byte. It may verify
the identity and attach transport metadata, but it cannot paraphrase, reformat,
or make a semantic choice on the specialist's behalf. Any semantic change or
evidence-byte change invalidates the handoff and sends a newly frozen packet
back to the specialist. Keep no coordinator or adjacent work assigned to the
scarce specialist after its decision horizon closes.
