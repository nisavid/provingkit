# Source corrections for the lane handoff

These corrections govern the current interpretation alongside the final lane
reports. The coordinator reconciled findings from the separately frozen
follow-ups against source before final review.

## Task creation returns the Desktop session ID

`LocalSessions.start` returns `{sessionId: d}` on its normal successful path,
whether or not `typedText` is present. The conditional text-binding call is the
left operand of a comma expression; the object on the right is the return
value. An exception can still reject the call.

This corrects the branch interpretation in the earlier
[native source delta](../2026-10-01-observer-scope-review/native-source-delta.md).
That report remains a historical artifact at its published revision. Consumers
of the new comparison must use this correction and the current lane reports.

The existing-interface worker found the error independently. The coordinator
checked UTF-8 bytes 27800–28640 of the retained
`.vite/build/index.chunk-COPWZCsC.js` on 2026-10-02. Its full-member SHA-256 is
`b22a9dc34684cef348f9c0e72abe88c433bbfc2d350d9a3e61faf7ae22858950`.
This was source inspection, with no app execution or private receiver read.

The result corrects an internal function contract. It supplies no external
client connection to the renderer IPC and no demonstrated UI exposure of the
returned ID. Fixture acquisition still needs a concrete, authorized access path.

## An explicit SDK directory is not an exact-file read boundary

The existing-interface final report adds a source finding that the hooks
follow-up had not yet seen. Passing `dir` to SDK `getSessionMessages` avoids the
all-project fallback, but its lookup can still enumerate directories and inspect
other transcript candidates. The hooks report's narrower-search statement must
not be used to authorize exact-file-only acquisition through that SDK helper.

The coordinator independently retrieved SDK 0.3.284 as data and traced `GD`
through `Vo`, `kn`, `Vfe`, and the `Aa` long-path fallback. In `sdk.mjs`, the
relevant UTF-8 byte spans are 404100–405100, 405187–406290, 406645–407800, and
530964–531650. The archive SHA-256 is
`4550e830246026133fc1802a2208dd0f3a785cae1eec83f261d114c33d797771`;
the member SHA-256 is
`32d062c37b03e10870fbf839f54694545ee01bc0ec719e47078fbed76e30ef71`.
No package code was executed. See the
[versioned public archive](https://registry.npmjs.org/@anthropic-ai/claude-agent-sdk/-/claude-agent-sdk-0.3.284.tgz).

A later reader must separate acquisition from interpretation: either acquire
approved exact-file bytes through a bounded reader or assess and authorize the
SDK's actual lookup footprint. Filtering returned fields cannot narrow bytes
already read.

## Prototype reuse leaves specific implementation choices open

The follow-ups improve their first-round blanket prototype conclusion. Hook
projection, host completed-push projection, and explicit endpoint collection
have meaningful source/synthetic test seams. They can test a selected interface;
they cannot establish missing runtime producers.

No new prototype is needed to substantiate this handoff's source findings or
partial-coverage claims. The design choices those seams implement remain open:
which observations to retain, which acquisition scope to use, and when samples
must be requested. Implementing one now would select part of that contract
before the component decision. The join must carry these concrete candidates
into the decision, then obtain the required test-boundary agreement for any
selected implementation. The retained prototypes provide prior demonstrations;
their tests were not rerun during these lanes.
