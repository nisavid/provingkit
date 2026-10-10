# Passive state observations through an existing Claude Code query

I'm designing before/after state observations of one ordinary Claude Desktop-hosted Code task. I need a supported way to read the model configuration applied to that task, its effective account/organization/authentication route, Code-owned permission state, and raw current directory through Desktop's already-held Agent SDK query. Observed model fallbacks would be recorded separately.

Which supported passive Code or Agent SDK interface can supply those observations without starting or reinitializing another query, adding another consumer to its message stream, or making an inference request?

- **Model and context lifetime:** Can a tool-produced context change the model or permission mode for a later iteration of the same main turn? Does any owner retain an applicable context between turns or change the session setting, and how can an interface report that distinction at an idle observation point?
- **Effective route:** Which account, organization, credential source, provider, and authentication route are effective for this query at the observation point? Can the interface distinguish established, unestablished, and pending-update states without returning credentials, refreshing authentication, or constructing a new client?
- **Code-owned permissions:** What mode, rules, runtime inputs, tool availability, and pending applications apply to the selected main context? Desktop-owned grants and broker decisions are separate observations.
- **Raw cwd:** Can the interface read the selected ordinary main scope's raw cwd and distinguish success, read failure, and a substituted presentation value? What scope remains observable while the task is idle?

I'm asking for supported ingress to the query Desktop already holds, rather than assuming an external attach API. Please identify support/error states, the full reads and effects, query-lifecycle limits, and how late control replies remain correlated with the original query.

For any missing equivalent, is there a canonical editable Code source, build, load, and version-support route for a narrow SDK-exposed diagnostic producer, including how it reaches the intended Desktop/Code pairing?
