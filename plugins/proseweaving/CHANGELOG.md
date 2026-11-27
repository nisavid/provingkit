# Changelog

## 0.1.0-trunk

- Align the source and Claude adapter versions with the Kit's synchronized
  `0.1.0-trunk` development identity.
- Add `editing-finished-drafts` to check an existing draft against its
  evidence and intended reader. Its evaluation bundle includes the writing
  skill it calls. Twelve behavior cases cover revisions, and 22 discovery
  inputs distinguish editing a finished draft from related requests.
- Choose prose register and organization for the medium, purpose, and audience,
  with subject-led publication openings and useful first-person evidence.
- Apply conversational reply and status guidance through a conditional reference;
  leave PR change phrasing and review-specific ask forms with their surface owners.
- Expand the writing corpus from seven to 28 cases covering publications,
  documentation, personal accounts, source and runtime evidence, workflow
  names, support requests, and links readers can follow.

## Historical source changes (mistakenly labeled 1.0.0)

- Add the Claude-native `proseweaver` agent alias as a thin forwarder to the
  portable `writing-for-people` skill.
- Publish `writing-for-people`: the generic mechanics for prose an agent writes
  to a person (grounding first, one graded ask, evidence as a hard constraint, a
  post-draft edit pass with a usage-judged dash rule) with seven behavior evals
  and their fixtures.
- Bootstrap the Proseweaving plugin: canonical Agent Plugins manifest with its
  Claude projection, the `writing-for-people` skill topology, the generated public-skill
  roster projection, the eval delivery contract, and the semantic content lock.
