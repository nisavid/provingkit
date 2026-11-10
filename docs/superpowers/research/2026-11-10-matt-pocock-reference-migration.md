# Matt Pocock skill reference migration

The repository's active domain instructions use `GLOSSARY.md` and `GLOSSARY-MAP.md`, matching the deployed `mattpocock-skills` 1.3.1 plugin. Its manifest identifies Skills for Real Engineers and its installed skill directory contains 27 skills. The deployed manifest SHA-256 is `00a28c3d7f89beafde6314ab72d97b6de756fd44671b3f1ec01b536abf37ff93`; the installed setup skill's domain template SHA-256 is `593a7042218689f1d24df89df14eaf0a20e19e0d0a7d479a01947ac78f0784b9`.

The installed inventory contains `to-spec`, `to-tickets`, `writing-for-agents`, `wayfinder`, and `diagnosing-bugs`. The former Matt Pocock names `to-prd`, `to-plan`, `to-issues`, `writing-great-skills`, and `decision-mapping` do not occur in the current repository instructions or maintained plugin sources. Ordinary uses of “diagnose” and independently owned skills and resource names are not aliases for an upstream skill and remain unchanged.

The old root `CONTEXT.md` is a link-only compatibility pointer to the sole maintained glossary. A hash-pinned historical research record still links to that location, and a Proseweaving evaluation receipt names `CONTEXT.md` at its recorded source revision. Those historical records are not current discovery instructions and remain unchanged. Current guidance, the repository's identity validator, and its regression tests use the new glossary path.

This inventory verifies names and discovery paths for the deployed plugin; it does not establish behavioral equivalence of every renamed skill, a future version's compatibility, installation in another harness, or downstream repository migration. The deployment and source-inventory records remain linked from [the migration issue](https://github.com/nisavid/provingkit/issues/477).
