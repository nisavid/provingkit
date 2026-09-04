# Tidesmith plugin

Tidesmith is an Agent Plugins v1 plugin for prose that agents write to
people: the register a reader should meet, the evidence discipline behind
every claim in that prose, the post-draft edit passes that enforce style as
actions rather than preferences, and the adversarial pass that reads a finished
draft as its recipient before it ships. Claude Code uses a native manifest
projected from the same canonical plugin identity.

Writing standards are portable equipment here, not personal taste: a consumer
without the author's own global instructions still receives the mechanics.
Personal voice composes on top through consumer-global instructions and never
lives in this plugin.

Tidesmith owns generic human-facing prose mechanics only. Surface owners keep
their surface contracts: Mergecraft owns reviewer-facing pull-request text and
the review-voice reference that applies this register to review threads, and
Tricritical owns review findings and their structural output contract. A caller
can explicitly compose those surface contracts with Tidesmith when prose
mechanics also apply; projections do not cross plugin boundaries.

## Public skills

<!-- BEGIN GENERATED SKILL ROSTER -->
| Skill | Owns | Calls |
| --- | --- | --- |
| `writing-for-people` | human-facing-register, evidence-in-prose, post-draft-edit-pass | - |
<!-- END GENERATED SKILL ROSTER -->

## Adapter boundary

Root `plugin.json` and `skills/` are the canonical Agent Plugins plugin root;
`.claude-plugin/plugin.json` is a projection of the same identity. Skill-to-skill
edges use literal public identities linked to sibling `SKILL.md` files. Codex
adapters and each skill's `agents/openai.yaml` use `$tidesmith:<skill>` targets.
The roster projection above is generated from `topology.json` by the content-lock writer.

## Validation

`python -m unittest tests.test_validate_tidesmith` exercises the focused
contract suite. `python3 scripts/validate_tidesmith.py .` validates the plugin from the
repository root: manifest identity and projection, topology, skill contracts,
the generated roster projection, inventory, portability, and the semantic content lock.
`--write-content-lock` regenerates the roster projection and the lock after an
authored change. `evals/delivery.json` governs plugin delivery, while
`skills/writing-for-people/evals/evals.json` carries the skill behavior corpus.
The plugin declares no Task Witness provider yet; publication eligibility and
inclusion in a release slate is decided outside this plugin.
