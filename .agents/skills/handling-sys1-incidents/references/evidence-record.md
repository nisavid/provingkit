# Evidence Record

Keep a bounded record with these fields. Use unknown for information that was
not retained, inaccessible for information outside the allowed read boundary,
and not applicable only when the field has no role in this occurrence.

| Field | Retain |
| --- | --- |
| Question and scope | Witnessed effect, intended outcome, current claim, supported inputs |
| Case and occurrence | Existing case if any; distinct occurrence identity and event order |
| Accountable owner | Person or task responsible for the investigation, or unknown; a case identifier does not establish ownership |
| Action and authority | Exact retained proposal; relevant operator words, scope, and intent amendments |
| Intervention | Hook or service stage; emitted bytes, verdict, score, and stated reason when available |
| Identities | Installed source, candidate, harness, model, configuration, and relevant dependencies actually observed |
| Effects | Attempted action, observed execution or nonexecution, and resulting artifacts |
| Evidence | Explicit file/log selections or reviewable links, digests where retained bytes matter |
| Provenance | Witness report, source fact, authored fixture, model response, native observation, or inference |
| Unknowns | Missing facts that could change the current conclusion; smallest useful next observation |
| Handling | Permitted readers, transfer/publication limits, and omitted or transformed content |
| Procedure | Reviewed source revision loaded by the consumer; candidate revision for producer self-use |

An event's score does not identify the command body or prove that approval
context reached the model. A source adapter's behavior does not prove that a
particular runtime used that adapter. Record those links only when observed.

For duplicate intake, retain one case owner and separate occurrence records.
A repeated intervention after approval is another observation, even when the
proposed action bytes match. If ownership is unresolved, return a draft
handback instead of inventing a tracker convention.

For public evidence, retain the original privately within its existing access
boundary. Review the proposed public bytes, including embedded and encoded
payloads, and record transformations and both identities when available.
A digest supports byte identity; it does not establish truth or permission.

The handback states what the evidence establishes, what remains unknown, the
selected next action and owner, and which execution or publication decisions
remain separate.
