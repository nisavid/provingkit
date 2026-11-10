# Receive a companion migration

Use this procedure when a verified companion installation or deployment changes
a skill name or path referenced by Provingkit. The deployment owner supplies
the installed source and version, affected names or paths, its deployment
record, and the migration issue. An archive or release alone does not establish
an installed update.

1. Find the existing migration issue, or follow the repository's issue tracker
   procedure to create one. Link the deployment record and identify the affected
   active references, their owning sources, and any intentional historical or
   separately owned references. Keep the deployment handoff pending while the
   issue or an accountable recipient is missing.
2. Provingkit Orchestrator names the recipient. In the migration issue, record
   that recipient's acceptance and first action, or that recipient's concrete
   deferral and the condition that restarts it. Give the entry link to the
   deployment owner, who maintains the deployment record and its pending state.
   Verify its backlink. A sent notice or an unanswered assignment remains
   pending; neither is the recipient's acceptance or deferral.
3. Bind checks to the changed references and their actual active source files.
   Show that the old reference is rejected there and the replacement is
   accepted. Verify separately that intentional historical evidence and
   independently owned references remain intact. Reuse #793's compatibility
   work where it applies; names and paths alone do not prove behavioral
   compatibility.
4. Record the checked files, commands, version and source used, results, and
   any unverified surfaces in the migration issue. Apply the owning sources'
   review, validation and publication requirements to changes. The deployment
   owner's pending record can be resolved when step 2 and its backlink are
   recorded; completing the migration remains separate work.

## October reference migration

The [deployment receipt](https://github.com/nisavid/real-skills/issues/8#issuecomment-6094893049)
identified the installed plugin. The subsequent [migration readback](https://github.com/nisavid/provingkit/issues/477#issuecomment-6598066393)
still called for an owner and source reconciliation. Under this procedure that
handoff stays pending until the named recipient records an acceptance and first
action, or a deferral and restart condition; the deployment owner then links it.
This walkthrough is a check of the intended procedure, not a claim that the
historical handoff was recorded that way.

From the repository root, this bounded check covers the two active domain
instruction files from that migration. The first command must exit 1 (no match)
and each remaining command must exit 0. Any other status is a failed check.

```sh
rg -n -F 'CONTEXT.md' AGENTS.md docs/agents/domain.md
rg -n -F 'GLOSSARY.md' AGENTS.md
rg -n -F 'GLOSSARY.md' docs/agents/domain.md
```

The [merged migration](https://github.com/nisavid/provingkit/pull/966) retained
the hash-pinned historical research record and the independently owned
Versionkeeping conflict-resolution skill. Compare those paths across the merge
to check that migration did not change them:

```sh
git diff --exit-code e4b82f875981c58caa2d4c697e4b2dd64e243225^ e4b82f875981c58caa2d4c697e4b2dd64e243225 -- docs/superpowers/research/2026-09-17-mergecraft-relation-inventory.md plugins/versionkeeping/skills/resolving-merge-conflicts/SKILL.md
```

These checks cover the named files and that historical migration only. For a
later update, select and test its own active sources and preserved references.
