# Change brief

A reconnect attempt previously retried indefinitely after a connection reset. The change adds a configurable attempt limit, with a default of three, and returns RetryExhausted when that limit is reached. The implementation and default are established by inspected source. The focused reconnect tests ran and all 12 passed. The full suite was not run. There is no deployment result.

The operator asks in chat: "Were you able to reproduce it, and what did you change?" The writer did reproduce the endless retry locally before changing it. Write the PR summary for repository readers and the separate answer to that operator.
