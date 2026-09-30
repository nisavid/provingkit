# Effort Eligibility

Apply this policy at every selection, dispatch, continuation, fallback, and review, including Jev and Daybreak routes. Capability and eligibility are separate gates.

## Minimum Effort

For the OpenAI and Anthropic genius and workhorse families (Astra/Fable and Sol/Opus), `medium` is the minimum reasoning effort. Reject explicit, inherited, fixed, and executor-default `low` for those named families and their successors. Omitted selection fields do not waive the floor: establish the fixed family and effort from current target evidence before dispatch. An unknown default or a scale without a proven medium-or-higher equivalent cannot establish eligibility for those families. Select a contract-preserving eligible alternative when authorized; otherwise report `NEEDS_CONTEXT` for missing evidence or `BLOCKED` for an unavailable route.

Other models, including Sonnet, Haiku, Luna, Grok, Jev, and Daybreak, are outside this named-family floor. Their occasional `low` routes still require a suitable task role, adequate outcome quality and judgment margin, current capabilities, and their applicable policies. Do not raise them to medium merely to import this floor, or assume low is suitable merely because it is advertised. A service such as Jev that exposes no reasoning-effort scale needs proof of its own complete-operation capability and suitability, not an invented medium equivalence. An unknown fixed binding remains unproven wherever the missing fact can change suitability or a required policy gate.

## Max Effort

For OpenAI and Anthropic models, select `max` only when **every** gate holds:

1. **Model and role:** Astra or Fable in the exceptional cognitive role assigned by the applicable routing policy; Sol or Opus for other work. Other OpenAI or Anthropic named families, including Luna, Sonnet, Haiku, and Daybreak, are ineligible for `max`. Preserve all applicable security, exceptional-tier, Fable-proof, and authority gates.
2. **Problem:** extremely challenging **and** extremely complex **and** at the frontier, with no known prior solution or closely related solution. Record evidence for each condition; any missing or unproven condition fails this gate.
3. **Workflow:** a loop involving adjudicated or reconciled collaborative or competitive panels of max-effort ideators, researchers, planners, implementers, or communicators; or a `tricritical:loop` workflow using max-effort `tricritical:review` reviewer panels. Prefer cross-harness panels where authorized and capable. A lone worker, an unlooped panel, or a loop without adjudication or reconciliation does not qualify.
4. **Capability:** the exact model-effort pair is supported by the target's fresh catalog and executor schema, with any required model proof. Sol and Opus are policy-eligible in their roles; an executor that lacks `max` remains incapable of that pair.

Record these gates in the selection record for OpenAI or Anthropic max requests. High stakes, cost of failure, risky unknowns, and model availability alone satisfy none of the missing problem or workflow conditions. If a gate fails, select a supported eligible lower effort preserving the contract, or report an unavailable route when a fixed request cannot be met. Other effort labels retain their documented target meaning; a renamed or aliased OpenAI or Anthropic `max` still requires these gates.

This max restriction does not govern other providers. Their own capability, suitability, and policy gates still apply; being outside this restriction neither grants invocation authority nor recommends or establishes eligibility for their max effort.
