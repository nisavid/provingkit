# Evidence In Prose

## Gather The Facts First

Most invented details come from a thin brief. Before drafting, gather:

- What was run, on what, and what it returned.
- What was decided, by whom, and what is still open.
- What the reader asked, in their words.
- What the reader already knows, so the draft neither repeats it nor
  assumes more.

Say what you did not check, and let the reader look up what the draft
does not carry. Before asking for a fact, check the transcript and the
artifacts you already have; ask only for what they cannot tell you.

## Guards

### Distinguish Source Findings From Observed Outcomes

State behavior established by inspected source as such: "`parse_limit` rejects
negative values" can follow from its guard without a runtime experiment.
Keep the claim within what that source establishes. A report that a test or
command passed, a deployment completed, or a live system behaved a certain way
needs a recorded run and result. Attach the observation where it matters:
"`make check` exits 1 on the fixture branch". Use a condition or modal for an
unverified prediction, such as "this should fail once the cache is wired up".

### Never Commit To An Undecided Position

Do not commit yourself, or the people you write for, to a position,
threshold, offer, deadline, or concession that is not in the brief.
Offer options, ask the question, or name the decision as open and say
who holds it.

### Write The Observation, Not The Story

Report the observation accurately: "the config record hasn't changed since
June 2" does not by itself establish that the update silently failed. Include
an inference when it helps, identifying it as a judgment and giving its basis
and remaining uncertainty.

### Leave Out Social Facts You Do Not Have

Who asked, what happened, when, and why someone acted are facts like any
other. When one is not in evidence, ask or leave it out. Do not supply a
plausible actor or motive to make a sentence flow.

### Separate The System From The Setup

When reporting a check you ran, separate what the real system does from
conditions you constructed to run it. "The endpoint returns 429 after
the tenth request in a minute" and "I hit it with a loop of twelve
requests against a local build" are different facts; give the reader
both when the second changes how far the first can be trusted.

## Qualify Only Real Uncertainty

State a confident finding as a plain declarative. Qualify a claim only
when it is genuinely uncertain, and say what makes it so ("my best
guess from the current API shape; I couldn't find a direct caller").
When every claim carries a hedge, the reader cannot tell which one needs
it.
