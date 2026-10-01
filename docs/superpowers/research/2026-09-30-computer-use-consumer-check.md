# Computer Use consumer check

The local repair correctly replaces selected text on Programmer Dvorak through
the public MCP interface. Adoption for the observer workflow awaits a decision
about an incidental full-desktop screenshot request during targeted typing.

This check serves [local adoption](https://github.com/nisavid/provingkit/issues/302)
under [the first directed notification map](https://github.com/nisavid/provingkit/issues/212).
The existing v0.7.6 AT-SPI text-entry workaround remains selected. No Claude
interaction, observer installation, or persistent tool configuration changed.

## Candidate and evidence

I verified the [producer's handoff](https://github.com/nisavid/computer-use-linux/issues/16#issuecomment-5917624979)
and loaded its maintained `computer-use-linux` skill and input-verification
reference. Published source `b1db8ef70449a54e899193309493497198af02be` has the
same tree as reviewed source `3436cda38d1f6ce1e777186b99c99edbf98aa133`.
The executable was tested from `a9967f5e8f15a3faa1e45959f623ee2a51e5c03d`;
only the skill text differs between that revision and the published source.
The executable SHA-256 is
`05754d622928c2be3e36d42343fbad01b4271d88c5f3fa7ff488ef1d4e74c5d9`.

The comparison used pristine upstream v0.7.7 source
`418892f10e6840c45d92e4911f499f2e33994c94`, executable SHA-256
`f6b5d8bacfcb64cacb0c4e8f2f93689db51f53d3e192bb4ce5d6087e6c1cd363`.
This control is distinct from the currently selected v0.7.6 fallback.

Each executable ran in a fresh private display, bus, configuration, runtime,
and input session. The driver resolved the disposable Qt window and PID,
requested scoped accessibility state with screenshots disabled, checked the
selection through Qt's own getters, activated the window, and verified focus.
It then issued one targeted `type_text` request to replace `OLD` in
`LEFT_OLD_RIGHT` with `LAYOUT_PROBE_PASTE`.

| Executable | Qt key symbols | Qt and scoped MCP readback |
| --- | --- | --- |
| Pristine control | Control_L + k | `LEFT_OLD` |
| Local repair | Control_L + v | `LEFT_LAYOUT_PROBE_PASTE_RIGHT` |

Both tools reported successful dispatch. The control reproduced the failure;
the repair preserved both neighboring text segments. Both final trials verified
normal private input consent, denied the subsequent screenshot request, completed
scoped readback, preserved frozen input hashes, and left no fixture processes.
Earlier attempts and their failures remain retained. No ambiguous input was
replayed in the same fixture.

The [evidence record](2026-09-30-computer-use-consumer-check.json) binds the
executables, fixture, final results, and retained raw evidence by digest. The
final independent security review passed the supplied fixture and observations;
it did not qualify Claude or real-desktop use.

## Incidental screenshot request

After input, both executables opened the private portal's “Allow Apps to Take
Screenshots?” dialog. With that dialog unanswered, a subsequent scoped state
request timed out while its diagnostics probed the Screenshot portal interface.
Declining the request through its normal `Deny` button let both final checks
finish. This establishes the observed sequence, not a general diagnosis of
portal behavior or proof that every capture backend respects that denial.

The published source explains the request:
[`type_text`](https://github.com/nisavid/computer-use-linux/blob/b1db8ef70449a54e899193309493497198af02be/src/server.rs#L1845)
adds input feedback through `input_landing_notes`. Its optional off-screen
warning calls `capture_space_rect`, which can take a full-frame screenshot when
dimensions are not cached. Disabling screenshots on `get_app_state` does not
control this separate input path. The pristine source also contains this path;
the observation does not establish a regression introduced by the repair.

## Adoption decision

I recommend returning this finding to the repair effort before selecting the
candidate. Non-screenshot input actions should obtain geometry without capture
or omit the optional warning when geometry is unavailable. Consumer verification
should then repeat the affected check and require no screenshot request.

The alternative is an explicit decision accepting the broader observation scope
and its operational cost, followed by a revised observer authorization packet.
The private test's portal denial is not a maintained real-desktop workaround.

Until that decision and its resulting work are complete, retain the pinned
v0.7.6 procedure's verified AT-SPI text entry and application readback. Local
repair adoption and the later upstream-release transition remain separate from
the observer's fixture-identity decision, quiet window, and final live grant.
