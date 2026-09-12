# Exclusive identity and conservative crash recovery

Inline intents A and B address different source comments in one thread with the
same exact response bytes and actor. A has `write_started` but no result identity
and remains unknown. Independent B then succeeds with full typed response
identity `PullRequestReviewComment:901:PRRC_901`. A later listing exposes only
that same object as an otherwise exact candidate for A.

Separately, intent D gets a verified response and the immediate check observes a
new head. Publishing D's atomic attempt resolution fails, leaving only its
durable `write_started`. After restart, the head happens to match D's admitted
head again, and D's response is uniquely visible.

Before rereading a newly discovered candidate for D, one reconciliation round
has no candidate and a successor round selects identity
`PullRequestReviewComment:902:PRRC_902`. Another intent attempts to select the
same identity by recording it as an observation. A later D round selects
identity 903 instead. The resolution that selects 903 also carries several
valid observations before a final identity effect conflicts with another
intent.

Describe how A, B, and D are credited or reconciled, including their response
identity ownership and historical drift state. State what the fold commits when
the final identity conflict occurs.
