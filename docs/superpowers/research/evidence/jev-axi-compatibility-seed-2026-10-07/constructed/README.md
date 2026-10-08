# Constructed compatibility contrasts

These patches isolate proposed compatibility differences around the same JSON addition. This is preparation and evaluation information; do not include it in a native seed or model judgment packet. Apply each patch independently to an unchanged copy of `seed/`.

| Candidate | Construction | Expected observation to verify |
| --- | --- | --- |
| `c01` | Shared collection with opt-in JSON; text remains the default. | Existing text and consumer behavior remains available; JSON preserves warehouse identity and zero-stock records. |
| `c02` | The same addition, with JSON as the default. | The omitted-format report becomes JSON. Low-stock forwards that JSON successfully, including a quantity above its threshold; archive rejects it. |
| `c03` | The same addition, with zero-stock rows removed in shared collection. | Both renderers omit the zero-stock record, and the consumer observations expose the lost record. |
| `c04` | The same addition, with formatting moved to another module and text rows reversed. | Supported records remain unchanged despite a different implementation and row order. |

The construction tests inspect actual CLI output after applying each patch. Before using these candidates in an experiment, retain the full before/after comparison on the declared cases and verify every claimed effect. A label or a patch's appearance alone cannot establish its behavior. The default-change and zero-stock patches deliberately violate the amended request; they are not proposed production fixes.

These fixtures do not establish how frequently ordinary development produces either defect, whether an added assessment improves completed work, or whether it saves model or operator effort. Native success and missing intervention opportunities remain valid outcomes.
