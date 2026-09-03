# Review output contract

Every finding must state:

- one stable evidenced cause and the reviewer scope that found it
- direct evidence from the frozen input
- the affected contract and causal path where applicable
- whether it contradicts the current contract, creates material risk within a
  current claim or supported input, or concerns a stronger future guarantee,
  unsupported-input defense, or hypothetical extension
- whether the current increment explicitly depends on that broader behavior
- realistic impact and severity, calibrated by impact, likelihood, recoverability, and detectability, never by fix size
- the smallest actionable direction
- tests or proof needed to establish the correction
- known limitations and residual risk

A current-contract contradiction or material risk within a current claim or
supported input blocks done until resolved or explicitly decided. A stronger
future guarantee, unsupported-input defense, or hypothetical extension is
recorded as fog or `follow-up outside scope` unless the current increment
claims or depends on it. Never discard a valid in-scope finding because time or
an execution budget ran out.

Separate findings from falsification attempts and other non-findings. Label
purely cosmetic preferences as `nitpick`; do not promote them into substantive
findings. Preserve uncertainty rather than manufacturing confidence.
