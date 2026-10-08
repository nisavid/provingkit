# Associate selected fixture metadata with supplied task evidence

`fixture-metadata.mjs` lists one declared folder or acquires up to three nominated
files and compares their saved identities with supplied UI and Stop evidence.
It produces an **unqualified conditional association candidate**, or an explicit
gap. Desktop's active account/organization directory remains unproved in every
result. This source experiment is not an installed operating reader.

The [accepted method](https://github.com/nisavid/provingkit/issues/476#issuecomment-6065165501)
and [prototype increment](https://github.com/nisavid/provingkit/issues/490)
control its claim. The [maintained fixture procedure](fixture-check-procedure.md)
is its downstream entrypoint. Private reads, hooks, fixture creation, prompts,
installation, restarts, and sends require their separately reviewed grants.

## Public command and supported inputs

Invoke the selected Node executable with `fixture-metadata.mjs --request` and one
explicit request-file path. The command emits one JSON line on stdout. Exit 0
means it produced an evidence record, including `unknown`; it does not mean a
match, authorization, or live qualification. Exit 1 emits no evidence record
and the fixed stderr message `Metadata command did not complete.`. Retain any
existing source records rather than retrying or interpreting absence as success.

This prototype targets Linux regular files and UTF-8 JSON. The request file is
read with a 128 KiB ceiling plus one overflow byte. It must contain:

| Field | Meaning |
| --- | --- |
| `schema` | Exactly `1` |
| `runId` | 1–128 ASCII letters, digits, hyphen, or underscore; starts with a letter or digit |
| `directory` | Explicit absolute folder path, at most 4096 characters, without NUL |
| `operation` | `list` or `associate` |

`list` reads names and entry types nonrecursively. It retains at most 128 entries
and observes at most one further entry to detect overflow. Overflow gives
`unknown` with `listing_overflow`; no file contents are acquired. Directory order
is not a selection rule. A listing is neither a coherent directory snapshot nor
proof of current Desktop selection.

`associate` additionally requires:

| Field | Meaning |
| --- | --- |
| `candidates` | 1–3 distinct objects with explicit `name`; no automatic search or selection |
| `candidates[].name` | ASCII JSON basename, at most 255 characters; starts with a letter or digit and then uses letters, digits, `.`, `_`, or `-`, ending in `.json` |
| `candidates[].expectedIdentity` | Optional caller-supplied selection sample: decimal-string `dev`, `ino`, `size`, `mtimeNs`, and `ctimeNs` |
| `since` | Nonnegative epoch milliseconds for the setup window beginning |
| `maxJoinAgeMs` | Nonnegative integer age limit; the later proposal must choose it |
| `uiWitness` | Supplied assertion of this run's selected disposable task, project relation, displayed whole response, and observation/recheck times |
| `stopRecord` | This run's complete, unbound `fixture_stop_check` collector record with EOF, current hook Code ID, matching whole text, and receipt times |

The UI witness fields are `runId`, `selectedTask: true`, `projectField` (`cwd` or
`originCwd`), `projectPath` (absolute, at most 4096 characters), `setupText`,
`displayedText` (each nonempty, at most 4096 characters),
`capture: { startedAt, finishedAt }`, and `recheckedAt`. Paths and text exclude
NUL. The supplied record's `unbound.observedHookSessionId` must be nonempty,
at most 256 characters, and not a `served:` identity. Acquisition must be
`{status: "complete", eof: true}`. Its capture has `startedAt`, `completedAt`,
and `notBefore`.

All times are integer epoch milliseconds. UI and Stop samples must begin no
earlier than `since`, finish in order, and not lie in the future. Stop must also
begin after its own `notBefore`. The supplied selection recheck must follow both
completed samples and precede the current check. Age is measured from the earlier
source start, before file reads and again when joining completed acquisitions.
A fresh read or recheck cannot make old source evidence fresh. These endpoint
times do not establish continuous selection, producer authenticity, or an atomic
snapshot.

Unsupported command inputs fail before metadata acquisition. Missing, stale,
unordered, cross-run, or mismatched witnesses yield `unknown` without candidate
reads. A supplied witness is an assertion: the helper does not observe the UI,
verify the collector's producer, or authenticate a grant.

## Acquisition and association

For each nominated candidate, in declared order:

1. Sample the named path and opened regular file. Reject a nonregular final
   component, including a symlink. Compare identity with any supplied selection
   sample. A changed or unavailable sample remains unknown.
2. Acquire at most 1 MiB plus one overflow byte. EOF at or below the ceiling
   completes acquisition; an overflow byte prevents association.
3. Compare opened-file and named-path identity samples after reading. Parse
   complete UTF-8 object JSON. Every nominee must supply nonempty string
   `sessionId` (at most 250 characters), current `cliSessionId` (at most 256),
   and the chosen project field (at most 4096), without NUL. Missing or invalid
   fields give `metadata_incomplete`, including when another file matches.
   This conservative rule does not exclude a nominee on only one known mismatch.
   Overflow, invalid data, incomplete fields, or changed observations
   stop further acquisition and retain the acquired prefix in the result.
4. Match filename against the string `sessionId` plus `.json`, current
   `cliSessionId` against the admitted hook Code ID, and the explicitly selected
   saved project field against the UI project path. Prior Code lineage never
   substitutes. Require exactly one match across all acquired candidates.

Zero or multiple matches give `no_unique_match`. A match retains only Desktop
ID, current Code ID, filename, saved project relation, and
`uniqueness: "acquired_candidates_only"`. It proves no global uniqueness outside
that set. Saved project fields do not establish current engine cwd/worktree or
full runtime preservation. No path found inside metadata is opened.

Per-file records retain bytes acquired, EOF completion, identity endpoint
samples, and read intervals. `complete` concerns acquired bytes, not valid JSON
or association. Source UI/Stop times remain separate from command/read times.
Every output has `qualification: "unqualified"` and
`activeDirectory: "unproved"`; association output also has
`witnessEvidence: "caller_supplied"`.

The complete files are acquired, including private fields discarded from output.
The request file itself may contain private witness data. Final-component checks
do not protect against hostile ancestors, authorize access, or certify
private-data containment. Matching identity samples cannot rule out every
intervening mutation or establish a writer has finished. This command has byte
and entry ceilings, **no filesystem deadline** and no installation, UI,
settings, or run-file cleanup actuator. The eventual launcher and grant must
bind those effects, interruptions, retention, and failure handling.

## Source basis, demo, and verification

The retained [directory comparison](../../research/2026-10-07-selected-directory-binding-comparison.md)
and [cross-examination](../../research/2026-10-07-fixture-observation-cross-examination.md)
establish the conditional method's remaining evidence limits. The inspected
Desktop serializer emits `sessionId`, current `cliSessionId`, `cwd`, and
`originCwd`; the source member digest is
`dad88ac66fe13f72d0225c49d48e124d238ff643ff96426c4a2020482621e62d`.
This is saved metadata source evidence, not observation of a live task.

[The self-contained demo](metadata-demo.html) uses invented in-memory witnesses
and candidates. Its portable association functions are copied from
`fixture-association.mjs`; file acquisition and changes in the page are explicitly
simulated. It opens without a server and makes no private reads.

Run the agreed command-boundary checks with:

```sh
node --test docs/superpowers/prototypes/receiver-evidence/fixture-metadata.test.mjs
```

These use invented directory/file fixtures and supplied witness inputs, checking
acquisition records, association results, and exit status. They do not certify
private-data protection, actual task selection, hook activation, Desktop
behavior, or the full notification route. Preparation must consume the reviewed
published helper and procedure revision and record that invocation before
proposing live access.
