# Public-comment publication needs a separate payload-context comparison

Two retained safety records identify exfiltration as the leading hazard and
record an `ask` decision. The installed Codex adapter converts that decision
to denial. The available records do not establish that either judgment
considered the proposed comment body or its authorization.

The originating closeout task reported two commands blocked before execution
while trying to publish a prepared public comment. After checking that the
JSON body matched its reviewed Markdown, it tried a narrower POST command,
then reported stopping retries and choosing its accepted reply-through-operator route.
Execution blocking and publication authority remain witness evidence; the
safety records establish judgments, not subsequent command execution.

| Recorded UTC time on September 26 | Exfiltration probability | Risk, 0–2 | Decision |
| --- | --- | --- | --- |
| 20:58:30.282 | 0.47 | 0.82 | Ask |
| 20:59:27.946 | 0.53 | 0.53 | Ask |

Both probabilities exceed the installed ask threshold of 0.45 and remain
below the deny threshold of 0.8. The displayed risks of 0.8 and 0.5 are
consistent with rounding.

The reviewed JSON contained only a body field, exactly matching the named
Markdown. Inspection found operational instructions, hexadecimal identifiers,
and a GitHub review link, without a credential value or private-key material.
That check does not independently prove publication authority or exclude
arbitrary encoded secrets.

## Evidence boundary

Each safety record retains only 200 redacted command characters, rounded
scores, working directory, and decision. Neither contains complete tool
arguments, serialized evaluator state, returned model identity, or payload
digest. The second prefix identifies the intended POST and JSON input, but
its suffix is missing. The first command is likewise incomplete.

In installed Jev 0.7.2, `readCall` retains tool name, tool input, and cwd,
omitting task authorization, approval history, and transcript context. For
Bash, `buildSafetyState` includes the redacted command and, for recognized
scripts inside cwd, bounded script contents. It does not load arbitrary
`gh api --input` bodies or scan neighboring directory contents.

Missing body or approval evidence is therefore a supported hypothesis, not
an established cause of these judgments. Directory-name wording may affect
the command description; influence from neighboring sensitive files' contents
is not supported by the inspected builder. The incident remains a possible
false positive, not a settled diagnosis.

## Controlled follow-up

Compare synthetic public operational prose with the same prose plus an inert,
fabricated token-shaped canary. For each, compare installed command-only state
with explicitly bounded payload evidence. Keep the command, path, destination,
and public-only authorization constant; put expected classifications in
separate evaluator records.

First inspect serialized inputs locally. If changing the file body leaves
installed state identical, record that information loss rather than treating
repeated judgments as a body comparison. Preserve the redaction result so the
canary's presence is not erased without a marker. Any simulated publication
must end in a local fake sink; use no real credentials, sensitive artifacts,
or actual POST. Test directory-name sensitivity separately with identical
payload bytes. This intake performed no judge calls or publication.

The witness report hash is
`02031428b274b858363f689312231a3a4b939e20be064ca54e4ed3e964be9681`.
The Markdown and JSON payload hashes are
`b64037f4a3ffa852bbe43522c4ca5c3ee9d4486878e9a0ea26d1dba0bc2cc0b5`
and `9de85021c68d8bd26740996a7ce43db35bf74fb6a5ee4e041fbba8cec4b1064d`.
The matching log-line hashes, including newlines, are
`24eed4c5b3a47f58e31a1bd85e1feab4e38de39802145d9e68eb4cb534960b36`
and `33459f714501ff3e9bed651d0e9b8b3abba1cae63539250e47a41c05b94018e9`.
These identify retained local evidence; they are not public payload copies or
independent attestations. The full blocked requests were not recovered.
