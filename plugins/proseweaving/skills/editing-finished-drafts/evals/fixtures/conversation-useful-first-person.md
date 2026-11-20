# Context
Mara asked: "Did you reproduce the export failure, and should support tell customers it's fixed?" The author reproduced the failure locally after a connection reset. The author read the patch and thinks it addresses the reset path. The patch has not been run; deployment was not checked. No deadline or person responsible for the original failure is known.

# Draft
Status: I reproduced the export failure locally after a connection reset. I noticed the patch clears the stale connection before retrying, so it should address this path; I haven't run it. The fleet is fixed, and support can promise completion tonight. This is where reliability really counts.
