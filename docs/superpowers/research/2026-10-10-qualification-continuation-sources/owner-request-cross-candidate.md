# Request for passive state from an existing Claude Code query

I'm preparing two state observations of one normal Claude Desktop conversation, before and after a separate operation. Desktop already holds the Claude Code query serving that conversation. I need to compare the model configuration applied at each point, the query's effective account, organization, and authentication route, applicable Code permission state, and the conversation's current working directory. Observed model fallbacks are recorded separately.

Can a supported passive Code or Agent SDK interface answer these questions through that existing query, without starting or reinitializing another query or consuming its message stream?

- Does an applicable context layer change the model or permission mode for the selected main conversation beyond the session settings? How can a caller tell whether that layer applies, and what state remains available between turns?
- Which account, organization, credential source, and authentication route are effective for the query? Can the response distinguish an established route from one not yet established, without returning credentials, refreshing authentication, constructing a client, or making an inference request?
- What Code permission mode, rules, runtime inputs, and pending applications apply to that conversation? I will assess Desktop's own grants and pending decisions separately.
- What is the raw current directory of the selected main conversation, and did its read succeed or fall back to a presentation value?

If no supported interface covers these fields, is there an owner-supported editable source, build, load, and version-support path for a narrow diagnostic producer exposed through the SDK? Please identify any existing equivalent, the full reads and effects of the suggested interface, and its query-lifecycle limits.
