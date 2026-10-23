# Specify consumer behavior and develop one verified slice

Use this method when adding or correcting software behavior in Provingkit. It connects the consumer's intended result to executable examples, a protocol driver, and a test-first repair. The first supported application is offline Python CLI compatibility; agent behavior and other runtime surfaces need their own discovery and qualification.

## Establish the consumer contract

Identify who consumes the operation, the outcome they need, and the assurances they rely on. Read the applicable domain language, maintained interface, existing tests, and current source before choosing examples. Record supported inputs, consequences of failure, and what the proposed observation cannot establish.

Choose the smallest existing specification language that expresses those distinctions clearly. Compare applicable alternatives with a concrete example before adding a framework. Python functions, values, and assertions can form a small embedded DSL when the consumer concepts remain legible; a list of flags or a snapshot of the implementation is not a consumer contract.

Separate semantic requirements from adapter details. A specification says which member's evidence can be inspected and which review requirements publishing preserves. Its driver knows how the maintained generator and parser represent that operation. Change the driver when an implementation route changes, keeping the consumer assertion stable unless the intended behavior changes.

## Bind the observation

Confirm the public test boundary before writing a test. State what real component executes, which external effects are replaced, and what those replacements prevent the result from proving. Use independently specified outcomes; deriving the expected result from the generated command cannot reveal a generator error.

Exercise the actual consuming interface. A mocked successful subprocess result does not show that the command it received is accepted. Distinguish parser rejection, entry into an inert operation handler, and completion of a live operation.

Qualify the driver on its claimed observation: deliberately wrong expected identities and outcomes must fail, and invalid inputs must remain distinguishable from successful operation entry. Isolate live effects without replacing the behavior under test. These controls qualify only the selected driver and seam, not every future use of the method.

## Develop and refine

Load this procedure, fixtures, driver, and implementation from the same committed candidate. A producer may validate its own draft, but independent consumer acceptance must identify the reviewed revision it actually loaded.

1. Write one semantic example at the confirmed boundary. Run it against unchanged behavior and preserve the failure, source identity, command, original output, and exit. Verify that it fails for the intended reason; an import error or unavailable environment is not the causal RED.
2. Make the smallest behavior change that satisfies that example. Run the same assertion and retain its GREEN result. Preserve original failures; do not replace them with a later successful record.
3. Add the next needed example as another RED–GREEN slice. Cover misleading successes and relevant refusal branches without writing a horizontal catalogue of speculative tests.
4. Review the resulting design and refactor where it reduces cost or clarifies responsibility. Rerun the same consumer assertions after refactoring. A simpler driver must still detect the original defect and wrong expectations.

Keep runs bounded under the owning resource policy. Preserve failures and unknown outcomes; use the task's retry policy rather than replaying an operation automatically.

## Complete the delivery

Run the touched surface's owning checks, update governed identities through their documented writers, and obtain clean independent review on the final revision and evidence dependencies. Capture the actual source and consumer result through the owning task. Publish and adopt only through their existing gates.

For the first Graphite consumer, a generated inspection command must reach the real auditor parser and the correct inert audit handler, while publishing commands retain their selected review requirements. That demonstrates offline command compatibility. Receipt access, forge mutation, aggregate repair, installation, and live acceptance remain separate.
