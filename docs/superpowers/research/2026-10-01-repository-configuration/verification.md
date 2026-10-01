# Research acceptance evidence

The substantive research candidate is [the 55-file manifest](reviews/research-candidate-1.json), SHA-256 `351a79780102e27bfd96285fd00b7d102c03ce11999be7da66a6a18b8d57dd5c`. Both independent reviewers consumed those same bytes and returned no material findings in their selected scopes:

- [Intent, coverage, provenance, and architecture handoff](reviews/intent.md).
- [Facts, citations, evidence limits, and security claims](reviews/evidence.md).

The [review contract](reviews/research-review-requirements.json) states the supported inputs, claims, acceptance, and exclusions. The reports describe their actual checks and limits. The separate [history recovery review](reviews/history-recovery.md) verifies the recovered follow-up and its sole citation correction; it does not reconstruct the interrupted worker's complete execution history.

The coordinator independently verified the retained first-report, exchange, and follow-up digests; all relative Markdown file destinations; absence of machine-local paths in the publication; and whitespace with `git diff --check` after staging. The live native map read found all six expected children, completed child and blocker pagination, and confirmed that the three research tickets block the architecture comparison and two human decisions. Resolution comments, map-pointer readback, and closing each research ticket follow publication; their live state remains on [the map](https://github.com/nisavid/provingkit/issues/366).

The reviewed candidate remains unchanged. The review reports, their input copies, and this acceptance record are appended evidence outside its manifest. These checks accept research for the separate design panel. They do not qualify platform enforcement, select architecture or policy, establish reusable panel conformance, or demonstrate installation.
