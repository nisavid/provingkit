# Receive a companion migration

Use this procedure when a verified companion installation or deployment changes
a skill name or path referenced by Provingkit. The deployment owner supplies
the installed source and version, affected names or paths, its deployment
record, and the migration issue if one exists. If no issue exists, the notice
identifies that gap so Provingkit Orchestrator can route its creation. An
archive or release alone does not establish an installed update.

1. Find the existing migration issue, or follow the repository's issue tracker
   procedure to create one. Link the deployment record and identify the affected
   active references, their owning sources, and any intentional historical or
   separately owned references. Keep the deployment handoff pending while the
   issue or an accountable recipient is missing.
2. Provingkit Orchestrator names the recipient. The recipient posts a comment
   on the migration issue identifying itself and recording acceptance and a
   first action, or a concrete deferral and the condition that restarts it.
   Give that comment's permalink to the deployment owner, who verifies the
   response, maintains the deployment record and its pending state, and links
   the comment. Verify the backlink. An unanswered assignment, a secondhand
   entry, or inaccessible or ambiguous evidence leaves the handoff pending.
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

From the repository root, run each command separately. Both old-name searches
must exit 1 (no match), and each instruction check must exit 0. Any other
status fails the walkthrough.

The positive checks cover every instruction line whose filenames #966 changed
in the two active domain instruction files. They match the migration's wording.
The old-name searches also scan the illustrative file trees, but this
walkthrough does not check the layout or replacement names in those trees.

```sh
# Obsolete names in either active file
rg -n -F 'CONTEXT.md' AGENTS.md docs/agents/domain.md
rg -n -F 'CONTEXT-MAP.md' AGENTS.md docs/agents/domain.md

# AGENTS.md: single-context layout and required reading
rg -n -x -F 'This is a single-context repository with root `GLOSSARY.md` and system-wide' AGENTS.md
rg -n -x -F 'Read `GLOSSARY.md` before planning or editing, and use its canonical language' AGENTS.md

# docs/agents/domain.md: root glossary, map and per-context glossary, multi-context criterion, and vocabulary
rg -n -x -F -- '- **`GLOSSARY.md`** at the repo root, or' docs/agents/domain.md
rg -n -x -F -- '- **`GLOSSARY-MAP.md`** at the repo root if it exists: it points at one `GLOSSARY.md` per context. Read each one relevant to the topic.' docs/agents/domain.md
rg -n -x -F 'Multi-context repo (presence of `GLOSSARY-MAP.md` at the root):' docs/agents/domain.md
rg -n -x -F "When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in \`GLOSSARY.md\`. Don't drift to synonyms the glossary explicitly avoids." docs/agents/domain.md
```

The [merged migration](https://github.com/nisavid/provingkit/pull/966) retained
the hash-pinned historical research record, the independently owned
Versionkeeping conflict-resolution skill, and Mergecraft's reference to that
skill. Compare those paths across the merge to check that migration did not
change them:

```sh
git diff --exit-code e4b82f875981c58caa2d4c697e4b2dd64e243225^ e4b82f875981c58caa2d4c697e4b2dd64e243225 -- docs/superpowers/research/2026-09-17-mergecraft-relation-inventory.md plugins/versionkeeping/skills/resolving-merge-conflicts/SKILL.md plugins/mergecraft/skills/resuming-reviewed-prs/SKILL.md
```

These checks cover the named files and that historical migration only. For a
later update, select and test its own active sources and preserved references.
