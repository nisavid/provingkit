# Fresh evidence for the narrower judgments

The corpus supplies 24 assertions across six synthetic source families. Each assertion has its complete three-line draft context and two complete sources. The cases distinguish missing support, an explicit incompatible fact, unresolved disagreement, material ambiguity, and ambiguity or disagreement that does not affect the assertion.

`construction.json` binds the draft coordinates, ordered sources, and original neutral labeling packet for each case. `labeler-packets/` preserves those complete packets. The producer reads the committed drafts and sources, writes a clean `inference.json`, and retains Git identity, raw source bytes, and receipts separately. Before execution, compare every inference object's assertion, context, and sources with its labeled packet; encoding whitespace may differ, but the field values and source bytes must not. Use the producer's frozen bytes for every condition and treatment.

Two isolated labelers independently assigned all 24 final relations and component answers. They agreed on every assignment, and their quoted evidence was present in the supplied sources. A separate adjudicator checked both reports against the complete packets and selected definitions, accepted all 24 cases, and found no source or definition defect. `label-provenance.json` records the input and report identities and the limits of that observation. Agreement prepares an evaluator key; it establishes no candidate-model accuracy.

The key contains six cases per final relation. Of the six unresolved cases, four have a material missing referent and two have conflicting independent accounts. Sources recur within families, so the 24 outcomes are not independent population samples. The source families and their dates, people, and activities are invented diagnostic examples. No retained development example or earlier experiment packet is reused.

Only `assertion`, `draft_context`, and the ordered `sources` entries (`id`, `text`) go to inference. Keep constructor notes, filenames, commits, labeler reports, key, rationale, and other model answers outside requests. Preserve evaluator files separately even when publishing them in the same research directory.

Add c25 only during preparation as a copy of c01 with one source selected and controlled unavailable. It must be non-ready, with no inference file or semantic slot. It tests the preparation boundary and is not a twenty-fifth semantic case.
