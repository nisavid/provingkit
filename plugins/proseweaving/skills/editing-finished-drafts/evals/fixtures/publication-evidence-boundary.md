# Context
The section is for maintainers reading the export guide. The supplied code inspection establishes that `retry_limit` defaults to 3 and counts retries after the first attempt. A local test used a stub that failed every request; its log contains one first attempt and three retries. Production was not observed. Nobody supplied a rollout date or customer-loss measurements.

# Draft
## Retry limits
It's worth noting that `retry_limit` defaults to 3. This isn't about waiting longer—it's about reliable exports. The worker makes at most three total attempts. I tested the local worker with a stub that failed every request and saw three retries after the first attempt. Production now recovers without losing any exports. That said, the change goes live for all customers on Friday.

Set `retry_limit` to choose how many retries follow the first attempt.
