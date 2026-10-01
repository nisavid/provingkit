---
name: writing-for-people
description: Use when asked to write, draft, rewrite, edit, or polish text for people, including PRs, Issues, documentation, reports, posts, chat replies, and review comments.
---

# Writing For People

## Scope

Own generic prose mechanics: grounding, register, organization, clarity,
evidence, and editing. The caller supplies personal voice. Surface owners
retain their content and format contracts: compose this guidance with the
applicable PR, Issue, or review writer, preserve retained text as its contract
requires, and leave publication and other actions to their authorized owners.

## Ground The Draft

Gather the source material, verified observations, decisions, open questions,
and the reader's purpose. Recover context from the available conversation and
artifacts before asking for discoverable facts. Distinguish what you know about
the audience from what you infer. Write a standalone artifact for a reader
arriving fresh; fold revision feedback into its substance.

Treat an operator's brief as compressed input. Unpack it into what this reader
needs to understand or do; preserve its facts and decisions without carrying
the operator's internal roles, powers, or work sequence into the message's
frame. Include that context only when it helps the reader use the piece.

## Choose The Register

Choose phrasing and structure for the medium, purpose, and audience. Lead the
piece and its sections with the subject the reader came for: the change,
finding, capability, question, or decision. Use first-person experience,
actions, judgments, and uncertainty where they help the reader assess that
subject. In publications and documents, these are usually supporting
statements; prefer subject-led openings. Let first person lead when the
writer's perspective is itself the subject, as in a personal account or a
reply about what the writer tried.

A publication explains its subject to readers beyond the exchange that
produced it. A conversation responds to what someone just said. A report,
proposal, guide, and reference document each need the organization their reader
will use. A public register can stay plain and approachable without turning
the artifact into a chat update or adopting an academic tone.

For chat, threaded comments, review replies, and status exchanges, read
[threaded-conversation.md](references/threaded-conversation.md). Apply those
exchange-specific rules only to that surface; a document requested in chat
still uses the document's register. Specialized writers own narrower
conventions, such as how a PR summarizes the change it applies.

## Build From Common Ground

Start from the context and language shared with the reader, giving enough
orientation for what follows. Explain a necessary unfamiliar term where it
appears; otherwise use plain words. Use technical precision where it changes
the reader's understanding or decision and everyday verbs elsewhere. When a
reader shows that an explanation did not land, recover the missing common
ground and explain more simply.

Use meaningful names for workflow stages and activities. Never use opaque
project-local alphanumeric workflow codes in committed or published
documentation, posts, descriptions, comments, or other durable/public prose.
A legend does not make those codes suitable for that prose.

Avoid those codes in communication with the operator or agents in other
projects unless their shorthand benefit outweighs the overhead of a legend
and a legend alongside the message defines every referenced code. Do not
assume humans or project-colocated agents remember a code catalog; shorthand
usually loses its value once a feature stabilizes.

Before asking for a decision, identify the system, purpose, and interface
whenever these are not established in the shared context. Distinguish an
existing interface from a proposed one: an unbuilt command-line tool is a
design option, not a command the reader can already run. Recover missing
context from verified inputs; ask for a material fact only when it cannot be
recovered. Workflow codes are distinct from literal commands, code symbols,
versions, revision identifiers, and ticket references that identify the subject.

## Make References Usable

When a reference helps the reader find work, evidence, or a resource, give it a
usable destination for this audience and venue. Link the verified title or a
clear description of the resource rather than leaving a known destination
behind a bare name or opaque identifier. In a client conversation that supports
chat links, use the chat's current verified title as the clickable label.

Resolve available identities through the client's supported lookup and link
contract. Match each title and destination to the same resource; a matching
title alone cannot distinguish two chats. Recover available context to resolve
ambiguity, and ask only for a material distinction that remains unknown. When a
destination cannot be recovered, give the useful known information and state
the narrow gap without inventing a link or claiming it was verified.

Use a public issue, PR, document, or other accessible reference when the audience
cannot use a private client link. A document delivered in chat still follows its
own audience's access and medium. If no accessible reference is available, keep
the supported information and state the access limitation where the reader
needs the source; do not invent a public equivalent or imply access.

## Let Content Pick The Shape

Make the central point easy to find, then supply the motivation, evidence, and
detail needed to assess or act on it. Use headings, lists, tables, examples,
and conclusions when they serve the artifact's purpose. A short answer needs
little scaffolding; a procedure may need several steps, and a proposal may
need several decisions. Keep useful structure consistent across related
documents.

Spend emphasis in proportion to stakes. Give dense, important claims a
concrete instance, mention material caveats briefly, and keep each detail for
what it helps the reader understand or do. Describe verification in terms of
what it establishes, naming the machinery when readers need to rerun or audit
it. Credit a real strength when it helps explain the judgment.

## Bind Claims To Evidence

Distinguish behavior established from source from outcomes observed in a run.
A source-supported finding can be a plain declarative; an assertion that a
check passed needs the recorded observation. Separate the real system from
conditions constructed to test it. Identify an inference as an inference and
qualify only the uncertainty that remains, saying what causes it.

Read [evidence-in-prose.md](references/evidence-in-prose.md) when the draft
describes system behavior, reports an outcome, makes a commitment, or states
what someone did. Keep claims within the evidence and decisions supplied or
verified for the task.

## Edit Before Delivery

Run [edit-pass.md](references/edit-pass.md) on the finished draft. Check its
register against the intended surface, its structure against the reader's
purpose, and every factual claim against the evidence after rewriting. For
text going to a reviewer, a shared channel, or a customer, make a second pass
for distracting mannerisms and factual drift.
