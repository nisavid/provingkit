## Retry limits

`retry_limit` defaults to 3. With this setting, the worker makes at most four total attempts: the first attempt and up to three retries.

I tested the local worker with a stub that failed every request. The log showed one first attempt and three retries. Production behavior was not observed.

Set `retry_limit` to choose how many retries follow the first attempt.
