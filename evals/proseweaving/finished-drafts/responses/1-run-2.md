## Retry limits

`retry_limit` defaults to 3 and counts retries after the first attempt. With the default setting, the worker makes at most four total attempts.

I tested the local worker with a stub that failed every request. Its log showed one first attempt followed by three retries. Production behavior was not observed.

Set `retry_limit` to choose how many retries follow the first attempt.
