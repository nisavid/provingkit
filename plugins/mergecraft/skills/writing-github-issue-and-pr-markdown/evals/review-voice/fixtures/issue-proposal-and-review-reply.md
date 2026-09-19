# Two GitHub fields with different purposes

Draft an Issue proposal body and a reply to a review comment as separate JSON string values named issue and reply. Neither may be posted.

Issue proposal: exports need a clear destination policy. Present two open decisions: whether an existing destination should fail or be replaced, and whether canceled exports should remove partial files or retain them for diagnosis. The operator has not chosen either policy. Give the reader enough context to decide both.

Review reply: the maintainer asked whether retry-limit coverage was added. The focused reconnect test was added, ran, and passed; it verifies the configured limit is used after reconnect. The author may report that observation. No request for another action is needed.

The request arrived in a chat whose old writing instructions said every message should sound like a conversation. The Issue is intended as a standalone proposal.
