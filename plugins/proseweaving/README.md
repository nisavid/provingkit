# Proseweaving plugin

Proseweaving is an Agent Plugins v1 plugin for prose that agents write to
people: the register a reader should meet, the evidence discipline behind
every claim in that prose, the post-draft edit passes that enforce style as
actions rather than preferences, and the adversarial pass that reads a finished
draft as its recipient before it ships. Claude Code uses a native manifest
projected from the same canonical plugin identity.

Writing standards are portable equipment here, not personal taste: a consumer
without the author's own global instructions still receives the mechanics.
Personal voice composes on top through consumer-global instructions and never
lives in this plugin.

Proseweaving owns generic human-facing prose mechanics, including selection of
register for a publication, document, or conversation. Its general writing
skill applies to authored PR and Issue prose as well as other human-facing
text; conversational openings and reply etiquette live in a conditional
reference. Surface owners keep their content and format contracts: Mergecraft
owns reviewer-facing pull-request text and review-specific framing, and
Tricritical owns review findings and their structural output contract. Compose
those contracts with Proseweaving while preserving their retained-text and
publication boundaries; projections do not cross plugin boundaries.

Claude Code also discovers the native `proseweaver` agent alias. It is a thin
forwarder to the public skill, so the skill remains the portable policy owner.
Codex consumes the standard skill surface and does not load this Claude-native
agent definition.

## Public skills

<!-- BEGIN GENERATED SKILL ROSTER -->
| Skill | Owns | Calls |
| --- | --- | --- |
| `writing-for-people` | human-facing-register, evidence-in-prose, post-draft-edit-pass | - |
<!-- END GENERATED SKILL ROSTER -->

## Developing this plugin

This section is for people who want to contribute to Proseweaving, fork it, or
work with its internals. An installed copy leaves out the topology
(`topology.json`), the content lock, the evaluation corpus and its delivery
contract, the validator, and the tests; they stay in the source repository.
The
[developer page](https://github.com/nisavid/provingkit/blob/main/plugins/proseweaving/DEVELOPING.md)
describes the adapter boundary, the generated roster, and repository
validation.
