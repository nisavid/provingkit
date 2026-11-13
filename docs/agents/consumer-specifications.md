# Specify consumer behavior and develop one verified slice

Use this method when specifying, developing, or reviewing behavior at any layer of a component within Provingkit or a component built by Provingkit. It connects the consumer's intended result to executable examples, a separate protocol driver, and a verified development slice. Apply the rule to each relevant component boundary, including agent behavior and downstream construction.

The existing qualified application is offline Python CLI compatibility. Universal applicability of the rule does not qualify every driver or runtime surface. Agent behavior, user interfaces, installed use, and other seams need their own discovery and qualification; preserve the existing CLI evidence within its supported inputs and observations.

## Establish the consumer contract

Identify who consumes the behavior at each relevant boundary, the outcome they need, and the assurances they rely on. The consumer may be a person, another component, or an agent carrying out its task; an internal mechanism can itself serve another consumer at a different layer. Read the applicable domain language, maintained interface, existing tests, and current source before choosing examples. Record supported inputs, consequences of failure, and what the proposed observation cannot establish.

State acceptance in that consumer's terms before choosing the driver. For example, a caller needs the selected member's evidence to be inspectable; a command's exit status alone does not establish that result. Materialize the accepted criteria as executable specifications. Requirements, development, and review use the same behavioral assertions rather than replacing them with the implementation's steps.

Choose the smallest existing specification language that expresses those distinctions clearly. Compare applicable alternatives with a concrete example before adding a framework. Python functions, values, and assertions can form a small embedded DSL when the consumer concepts remain legible; a list of flags or a snapshot of the implementation is not a consumer contract.

Separate semantic requirements from adapter details. A specification says which member's evidence can be inspected and which review requirements publishing preserves. Its driver knows how the maintained generator and parser represent that operation. Change the driver when an implementation route changes, keeping the consumer assertion stable unless the intended behavior changes.

## Bind the observation

Confirm the public test boundary before writing a test. State what real component executes, which external effects are replaced, and what those replacements prevent the result from proving. Use independently specified outcomes; deriving the expected result from the generated command cannot reveal a generator error.

Exercise the actual consuming interface. A mocked successful subprocess result does not show that the command it received is accepted. Distinguish parser rejection, entry into an inert operation handler, and completion of a live operation.

Qualify the driver on its claimed observation: deliberately wrong expected identities and outcomes must fail, and invalid inputs must remain distinguishable from successful operation entry. Include a control in which the mechanism appears successful while the consumer's required result is absent or wrong; the semantic assertion must reject it. Isolate live effects without replacing the behavior under test. These controls qualify only the selected driver and seam, not every future use of the method.

## Develop and refine

Start from one committed candidate for the procedure, fixtures, driver, and implementation. Keep task-owned TDD changes together in that worktree and retain the diff and input identities for each run; preparation tools and fixtures must not come from another revision. A producer may validate its own draft; independent consumer acceptance identifies the reviewed method revision it actually loaded.

1. Write one semantic example at the confirmed boundary. Run it against unchanged behavior and preserve the failure, source identity, command, original output, and exit. Verify that it fails for the intended reason; an import error or unavailable environment is not the causal RED.
2. Make the smallest behavior change that satisfies that example. Run the same assertion and retain its GREEN result. Preserve original failures; do not replace them with a later successful record.
3. Add the next needed example as another RED–GREEN slice. Cover misleading successes and relevant refusal branches without writing a horizontal catalogue of speculative tests.
4. Review the resulting design and refactor where it reduces cost or clarifies responsibility. Rerun the same consumer assertions after refactoring. A simpler driver must still detect the original defect and wrong expectations.

Keep runs bounded under the owning resource policy. Preserve failures and unknown outcomes; use the task's retry policy rather than replaying an operation automatically.

## Complete the delivery

Run the touched surface's owning checks, update governed identities through their documented writers, and obtain clean independent review on the final revision and evidence dependencies. Review completion against the consumer assertions and the observation's limits; source existence, passing tests, or successful delivery alone do not establish installed use or the consumer's outcome. Capture the actual source and consumer result through the owning task. Publish and adopt only through their existing gates.

A downstream consumer loads this maintained procedure at the reviewed revision before applying it, records that revision with `capturing-agent-procedures`, and identifies the assertions, driver, actual result, and remaining qualification gaps. A source-only change supplies guidance for that application; it does not itself prove discovery, loading, or adoption. Retrospective conversion of unrelated components and tests is not required to introduce the rule in the current slice.

For the first Graphite consumer, a generated inspection command must reach the real auditor parser and the correct inert audit handler, while publishing commands retain their selected review requirements. That demonstrates offline command compatibility. Receipt access, forge mutation, aggregate repair, installation, and live acceptance remain separate.
