# Cross-harness coordination catalog

The catalog records candidate communication routes, their evidence, and what
remains to be proved. The atlas consumes generated graph and matrix data from
the same record. GitHub remains the source for operator decisions, claims, and
blocking relationships in the [portfolio map](https://github.com/nisavid/provingkit/issues/533).

`catalog.json` is the maintained source. Its first snapshot preserves the
[reviewed inventory and comparison](https://github.com/nisavid/provingkit/blob/61b99e73ebedf8afb33b28a531daea8089504394/docs/superpowers/research/2026-10-11-peer-portfolio-comparison.md).
Those findings describe interfaces and eligible populations; they establish no
live-qualified direction. The accepted operation outcomes come from
[Choose Wave 1 operation and evidence contracts](https://github.com/nisavid/provingkit/issues/538#issuecomment-6112579765).
The [granular coverage investigation](https://github.com/nisavid/provingkit/issues/560)
will refine the endpoint inventory. Current counts describe this dated
snapshot, rather than an exhaustive support promise.

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
