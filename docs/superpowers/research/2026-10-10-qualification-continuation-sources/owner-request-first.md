# Request for a passive selected-query diagnostic

I am preparing before/after qualification observations for one ordinary Claude Desktop task. The observations need the model configuration applied to that task, the effective account/organization/authentication route of its existing Code query, applicable permission state and pending changes, and the task's current working directory. Observed model fallbacks are recorded separately. The available query getters appear to cover only part of that state.

Is there a supported passive Code or Agent SDK API for the already owned query that can report the following, with an explicit unavailable state where a value has not been established?

- Whether a main-task context layer changes the model used by the selected task beyond the session setting, including what remains available while the task is idle.
- The effective query route and account/organization provenance without returning credentials, refreshing authentication, constructing a new client, or making an inference request.
- The applicable permission mode, rules, runtime inputs, and pending applications for that ordinary task, rather than only a represented rule list.
- The raw current directory from the selected main-task scope, including read failure or fallback provenance.

If no such API exists, what owner-supported editable source, build, load, and version-support path would permit a narrow diagnostic producer and expose it through the SDK to the existing query? I would also appreciate the complete read/effect footprint and lifecycle limits of any recommended interface. A pointer to an existing equivalent for any of these fields would be useful.

