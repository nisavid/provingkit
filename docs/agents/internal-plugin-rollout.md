# Verify an internal plugin rollout

Use this procedure when an accepted Provingkit release or change includes
installation and use by the project's own agents. The rollout owner binds the
selected revision and the intended accounts and Codex and Claude surfaces from
the actual assignment. For Provingkit dogfood, cover all of the operator's
Codex and Claude accounts, on desktop and cloud, by default; an incomplete
account list is not a scoped exception.
An assignment may explicitly select a narrower rollout. A release that does not
select internal rollout does not acquire it merely from publication.

Use the installation owner's current inventory to map accounts to actual client
installation scopes. A verified shared local installation can cover mapped
accounts; account-specific cloud installations need their own evidence. A saved
cache or inventory seed alone does not establish current completeness.

For every intended account and surface, identify the receiving account and
workspace, expected per-plugin artifact identity, enabled installation, and
plugin and component identities actually present. A version string alone is
weaker than artifact or reviewed content identity. Reconcile newer accepted fixes before
choosing the revision; preserve them rather than overwriting them with an older
release. A missing account, unsupported route, or conflicting installed version
is an owned gap, not evidence that the other accounts failed. Continue the
independent eligible account and surface rows while that gap is resolved.

After saving and enabling a plugin update used in Claude Desktop Code, run
`/reload-plugins` in the affected Code session. Compare the loaded version or
a changed file from the loaded plugin with the reviewed release. Keep the check
read-only. Inspect the version or file directly, or use a skill that sends
nothing and changes nothing. Record the saved and loaded identities separately.

If the loaded copy matches, continue. If the check identifies the previous
release, [refresh Claude Desktop](../install-and-update.md#refresh-claude-desktop-after-an-update)
and record the loaded identity again. If you cannot identify the loaded release,
stop. Report the expected release, the observed difference, and any reload error
to the installation owner. Do not restart on that basis alone.

If you restarted Desktop, verify each peer route tied to the old connection
reaches its intended recipient before sending on it. Do not send on a route
whose recipient cannot be confirmed.
Reconcile an uncertain send with its original attempt before retrying it or
switching its route. Verify fresh-session discovery and useful use separately
from the recovery of a session whose transcript survived the restart.

After installation or update, complete any required restart or sync for that
surface and record its result. Then open a genuine fresh session on each intended
surface. Verify that the intended plugin and its components load and that an
appropriately assigned Worker can discover and use the relevant capability for
useful work. Record the account, surface, session, loaded identity, useful
action and result, and any uncertainty. An installed manifest, a copied file,
or a prior session is not a fresh-session loading or Worker-use observation.
Preserve the supplied discovery observation before adding manual pointers, and
retain unknown account binding when the evidence does not establish it.
Use an existing authorized task where it supplies the evidence; do not create
artificial work merely to produce a marker.

Report publication, installation, enabled state, discovery and loading,
qualification, and adoption separately. Compare the observed evidence with
the selected rollout's acceptance criteria, retain each uncovered account or
surface with its owner and next action, and return the outcome to the
commissioning outcome owner. When a release owner invoked this procedure, it
uses the result in its existing tracker reconciliation; a standalone rollout
does not require a release.
Keep operation-specific qualification in its own contract: discovering a plugin
does not establish that its transport, recovery, or other operations work.
Neither this procedure nor a successful rollout authorizes publication, account
changes, installations, or other operations beyond the existing assignment.
