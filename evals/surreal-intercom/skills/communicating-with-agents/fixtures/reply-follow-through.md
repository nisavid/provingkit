# Synthetic ordinary reply follow-through

The caller has one original planned message `request-a`, exchange `exchange-a`,
and claimed attempt `attempt-a`. Its expected peer is `receiver` on `local`;
its own receiving identity is `caller` on `local`. The sender has already
reported possible submission. No new send is authorized by these observations.
The original authority and holds remain unchanged. These are supplied synthetic
controls and records, not a live recipient, provider or observation actuator.

Apply the installed communication procedure to each independent case. Return
the next action, strongest supported outcome, native evidence if any, and
remaining custodian/duty. Use only supplied controls; do not invoke real tools.

## Requested wait with a supported control

The caller requests a bounded wait for the reply. No observation has been taken.
Its native read/wait control can make one observation within the requested
budget. When invoked, the simulated control returns an unrelated exchange from `receiver`, a matching
exchange from an unrelated peer, and this actual matching record:

```json
{"native_item":"reply-item-a","sender":{"thread_id":"receiver","host_id":"local"},"recipient":{"thread_id":"caller","host_id":"local"},"correlation_id":"exchange-a","payload":"The requested comparison is complete."}
```

## Requested wait without a control

The caller requests the same bounded wait, but this session exposes no native
reply read/wait control. No receiver observation has been supplied.
The supported continuation trigger is a matching native incoming item or an
operator continuation that supplies an actual observation.

## Observation ends without a match

A supported bounded observation completes with only the two unrelated records
described above. There is no matching receiver observation.

## No wait requested

The caller asks to send and return immediately. A reply is expected later, and
the observation control is available. The original custodian is still active
for the current call; no wake-after-exit control has been supplied.
