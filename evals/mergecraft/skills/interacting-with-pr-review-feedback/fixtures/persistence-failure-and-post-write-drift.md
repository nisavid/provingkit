# A provider write with incomplete atomic resolution

Intent `migration-101` has a durable `write_started`. The Provingkit leaf actuator then returned one PR conversation response with equal created, requested-reread, and reread IssueComment identity `IC_result201`, exact request/body binding, exact reread bytes, and post-write drift `observed`. Publishing the atomic attempt resolution fails because the local volume is full, so no provider result, outcome, drift, or identity claim from that attempted resolution is durable.

The caller wants to rerun the response command from the earlier epoch, then mark the full feedback batch addressed. The response is still uniquely visible through the controlled provider. Describe the next actions and the durable evidence that should remain.
