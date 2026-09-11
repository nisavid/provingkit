# Two indistinguishable current-effective-unknown intents

Two independently admitted inline-source intents A and B target verified
`example/widgets` pull request 418. They use `create_inline_reply`, response
object kind `PullRequestReviewComment`, placement
`review_thread:PRRT_thread7:61`, expected actor `review-bot`, and the same exact
opaque UTF-8 body wrapper. Each current attempt crossed `write_started`, and
each operation-produced outcome is `unknown`. Neither attempt retained a
response identity.

In the first variant, their complete validated bindings have the same head and
base. In the second variant, B has a different head, base, repository display
name, and permalink, but both bindings retain the same stable repository
database/node identities, pull-request database/node identities, and pull
request number.

A later authorized collection exposes one stable exact
`PullRequestReviewComment:901:PRRC_901` whose actor, placement, and body match
both possible writes. Reconcile A, then B, then A again. No other retained
identity distinguishes which intent created the object.

Separately, intent D is current effective unknown but differs in one
provider-observable correlation field. Its binding and epoch pass the normal
full validation.

Give the closed decisions, provider actions, durable identity effects, and
stopping state for both variants and for D's independent group.
