# Two Issues

Bug report facts: Export stalls after a connection reset. The writer reproduced it on version 2.4 using a local CSV export, interrupting the connection, and restoring it. The expected result is either completion or a bounded failure. The observed export remained pending for ten minutes. The cause is not established.

Proposal facts: The team is considering a configurable retry limit. There are two open decisions: whether the default should be three or five attempts, and whether the final failure should offer a manual retry. No owner has chosen either. The proposal should explain the idea and present both decisions for discussion.
