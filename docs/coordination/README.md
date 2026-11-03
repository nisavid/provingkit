# Cross-harness coordination catalog

The catalog records candidate communication routes, their evidence, and what
remains to be proved. The atlas consumes generated graph and matrix data from
the same record. GitHub remains the source for operator decisions, claims, and
blocking relationships in the [portfolio map](https://github.com/nisavid/provingkit/issues/533).

`catalog.json` is the maintained source. The dated first-cohort snapshot
integrates the [granular coverage investigation](https://github.com/nisavid/provingkit/issues/560)
and eight published directional preparations. It contains 23 Wave 1 operational
surface views, 28 across all waves, and 165 candidate/supporting fabric records.
All 150 seed fabrics, their distinct source cohorts, unsuccessful/unsuitable
leads, archived vectors and unresolved mappings remain discoverable.

The generated register has 756 potential directed view pairs and 26 explicit
source-candidate associations. Those counts are neither unique native
populations nor supported routes. No actual fabric operation is qualified.
Pure invented Queue/Steer and worker/Cloud state models are separate synthetic
evidence; they do not establish a working transport or backend capability.

The original [reviewed inventory and comparison](https://github.com/nisavid/provingkit/blob/61b99e73ebedf8afb33b28a531daea8089504394/docs/superpowers/research/2026-10-11-peer-portfolio-comparison.md)
remains archived in provenance. Broad legacy Desktop/SDK associations have
unresolved correspondence to narrower display views; they supply no inferred
SSH, WSL, Python, IDE, child/team or reverse caller access. Source updates do
not refresh unrelated deployed builds. The accepted operation outcomes remain
[Choose Wave 1 operation and evidence contracts](https://github.com/nisavid/provingkit/issues/538#issuecomment-6112579765).

The maintained Claude MCP sender source batch adds a mailbox-backed actuator and its required shared helper and selected-server layers. Its notification-submission path is implemented and exercised through an explicitly assisted synthetic public-command application; the initial failed caller launch remains retained. The selected server/backend and native peer remain unbound, and no actual receiver operation is qualified. See [the dated source and consumer report](batches/2026-11-03-claude-mcp-sender.md). The original first-cohort data and all unrelated records remain unchanged.

The maintained Codex IPC sender source batch adds a busy-only actuator and its required existing-owner Unix IPC backend class, reusing the unchanged mailbox/envelope helpers. Its shared notification-submission and receipt profile is implemented with partial source and synthetic command coverage; exact caller/owner/access/authority and live receipt remain unbound. That source batch added a busy-only profile and its evidence. Two ordinary synthetic procedure consumers passed; installation and adoption remain separate. See [the dated source report](batches/2026-11-03-codex-ipc-sender.md).

## Read the record

- **Endpoints** identify a host and surface. A host-owned thread, a native GUI
  task, and an SDK-owned session retain their own entries.
- **Fabrics** identify actuators, hosts, protocols, routers, observers, and
  supporting layers. Subroutes retain their parent, dependencies, and source
  crosswalk. A partial or unsuitable candidate remains in the inventory.
- **Profiles** distinguish independently existing tasks from controller-created
  lifecycles, with ownership, input semantics, consent limits, continuity, and
  operation milestones. A source assessment can be shared; qualified evidence
  belongs to one named channel.
- **Channels** record a direction's candidate association, caller access, target
  binding, gaps, and next check. Every potential ordered pair appears in the
  projections. A direction without an explicit association has no cataloged
  candidate yet; receiver capabilities do not fill it automatically.
- **Evidence** names its kind, immutable revision or content digest, observation
  date, acquisition pointer, and limits. Compatibility is assessed against the
  affected behavior. Unassessed builds differ from demonstrated incompatibility.

Each profile can have several stages at once. Creation might be qualified
while continuation has only a synthetic prototype and notification remains
unknown. Inspect the claims and their limits; a highest-stage badge or source
vector cannot summarize that combination honestly.

The [explicit idle-intent batch](batches/2026-11-03-codex-idle-catalog.md) adds a separate prototyped profile to the existing IPC fabric. The snapshot has 312 profiles and 26 evidence records; the new submission/receipt outcomes remain unknown. It does not change the busy-only profile or qualify an actual operation.

## Validate and regenerate

From the repository root:

```sh
python scripts/coordination_catalog.py validate docs/coordination/catalog.json
python scripts/coordination_catalog.py project docs/coordination/catalog.json > docs/coordination/views.json.tmp && mv docs/coordination/views.json.tmp docs/coordination/views.json
python -m unittest discover -s tests -p test_coordination_catalog.py
git diff --check
```

The command accepts local JSON and emits diagnostics or deterministic view data.
It fetches no source, authenticates no account, and acts on no harness task.
Validation checks record shape, references, and evidence metadata. Human and
independent review establish whether the cited evidence supports a claim.

`views.json` contains graph nodes/arcs, a source-by-target matrix, and shared
channel details and fabric cards. Both navigation views refer to the same
channel IDs. Generation uses the snapshot date supplied in the catalog; opening
or regenerating the view performs no new harness observation. The source digest
identifies the actual catalog bytes used. The separate
[atlas prototype](https://github.com/nisavid/provingkit/issues/553) owns visual
interaction and the operator's reaction.

## Update a producer batch

Use `updating-cross-harness-catalog` from
[the canonical repository skill](../../.agents/skills/updating-cross-harness-catalog/SKILL.md)
before integrating a coherent research, prototype, selection, implementation,
qualification, release, or deployment result. Its completion checks cover
preserving concurrent records, evidence limits, regeneration, review,
publication, and consumer pointers. An unaffected batch records why it needs
no update.

The [format reference](format.md) defines the command's supported records.
Source publication, procedure installation, prototype acceptance, live
qualification, release, and Hatchery deployment each require their own evidence.
