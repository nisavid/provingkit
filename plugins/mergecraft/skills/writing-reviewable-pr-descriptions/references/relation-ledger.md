# Exact relation-ledger edits

Use `scripts/validate_relation_ledger.py` to prove an approved span replacement
in the complete body of an OPEN, CLOSED, or MERGED pull request. The existing PR
writer supplies the full candidate title and body. The title stays unchanged;
every body byte outside the authorized span stays unchanged. This path needs no
surviving branch, checkout, diff, or rebuilt change navigation.

The relation coordinator owns contribution decisions, Issue policy, and the
authorized replacement. This validator proves text and identity bindings; it
does not decide whether an Issue/PR relationship is warranted. It neither
creates native Development links nor changes Issue or PR lifecycle state.

## Bind the complete candidate

Retain the current exact title/body and stable repository/PR IDs. Write the
complete candidate title and body to literal UTF-8 files. Do not add a terminal
newline to the title, normalize line endings, trim whitespace, or reconstruct a
bot suffix. Reuse `writing-github-issue-and-pr-markdown` for the replacement's
Markdown and the existing PR writer for reviewer-facing wording.

The JSON manifest has exactly these fields. This synthetic example replaces
`Related: #4\n` with `Contributes to #4.\n`; its body input is
`Summary.\n\nContributes to #4.\n` and its title input has no trailing newline.
Replace the example identity with the independently observed target before use.

```json
{
  "schema_version": 1,
  "operation": "pr-relation-ledger-write",
  "target": {
    "host": "github.com",
    "repository": "example/project",
    "repository_id": "R_example",
    "entity_id": "PR_example",
    "number": 17
  },
  "preimage": {
    "title": "docs: link related issue",
    "body": "Summary.\n\nRelated: #4\n",
    "state": "MERGED",
    "is_draft": false
  },
  "authorized_span": {
    "start_utf8": 10,
    "end_utf8": 22,
    "replacement": "Contributes to #4.\n"
  },
  "candidate": {
    "title_sha256": "43f04d9a0ce2bde7e8166bceef86bca3d8a571fd979d0a6fdf961d5da75eeada",
    "body_sha256": "414646c7b913d780c79e6224eb298e9c01151d079583e5056dd2434050c62bd0"
  },
  "review": {
    "mode": "not-required",
    "selected_specialists": []
  }
}
```

`start_utf8` and `end_utf8` are half-open byte offsets in the original UTF-8
body, not character offsets. Both must fall on character boundaries. An
insertion uses equal offsets. The validator recomputes both candidate digests
and proves the entire replacement. It reuses the existing secret detector and
bot-tail recognizer; a span cannot overlap a recognized bot suffix. Unknown
fields, duplicate JSON keys, unsupported hosts, and mismatched review choices
block publication.

Review selection is an explicit caller decision made before invoking the
writer. Carry the same mode and sorted specialist inventory in the writer
request, candidate manifest, and publication handoff. Both commands require
`--review-mode` and `--selected-specialists`; they must match the manifest.
`not-required` requires an empty specialist array. `required` accepts the
recorded selection during text validation but the publisher blocks it because
this historical path has no Task Witness integration. Never change a required
review decision to make the helper proceed.

## Validate and publish

From the package repository, with the three file variables containing absolute
paths, validate the complete pair:

```sh
python plugins/mergecraft/skills/writing-reviewable-pr-descriptions/scripts/validate_relation_ledger.py \
  --manifest "$manifest_file" --title-file "$title_file" --body-file "$body_file" \
  --review-mode not-required --selected-specialists '[]'
```

The publication owner invokes the body-only actuator with the same inputs:

```sh
python plugins/mergecraft/skills/publishing-reviewable-prs/scripts/publish_relation_ledger.py \
  --manifest "$manifest_file" --title-file "$title_file" --body-file "$body_file" \
  --review-mode not-required --selected-specialists '[]'
```

The actuator revalidates the files, takes the canonical per-PR publication
lease, and checks live type, stable IDs, repository/name/number, title, full
body, state, and draft state. After durably recording the attempt it reads the
preimage again immediately before one GraphQL mutation containing only the
PR ID and complete replacement body. It then independently rereads the target.
Any GraphQL errors invalidate a response even when it contains data.

A matching existing candidate produces an observation-only no-op. A successful
write requires a valid mutation acknowledgement, matching live postimage, and
a durable receipt. Other actors do not share the local lease, and GitHub offers
no body compare-and-swap in this path; drift caught after sending remains
`unknown`. No blind mutation retry occurs.

## Consume results and recover uncertain attempts

The publisher emits one JSON result with `schema_version: 1`,
`operation: "pr-relation-ledger"`, all five target fields,
`before_body_sha256`, `after_body_sha256`, `title_sha256`, `state`, `is_draft`,
`status`, `no_op`, `receipt_id`, and `receipt_sha256`. Hash/state fields bind the
requested transition; only a `verified` result attests a matching observation.
Invalid manifests cannot supply trusted bindings and return only the operation,
version, status, and a redacted reason.

| Result | Meaning | Exit code |
| --- | --- | --- |
| `verified`, `wrote-and-verified` | This invocation sent one acknowledged body update and verified it. | 0 |
| `verified`, `observed-existing` | Candidate already matched; this invocation made no forge mutation. | 0 |
| `verified`, `observed-after-uncertain` | Reconciliation observed the bound candidate; it does not establish which actor wrote it. | 0 |
| `blocked` | No mutation was sent by this invocation; read `reason`. | 1 |
| `unknown` | An attempt may have written, or its unresolved state prevents another write. | 2 |

Use the result only for coordination. The relation coordinator must
independently reread the live title/body/state and match the stable IDs and
digests. These receipts establish neither navigation completeness nor PR
readiness, review approval, merge authority, or Issue completion.

For an `unknown` attempt, retain the exact original manifest and candidate
files. Invoke the same publisher command with `--reconcile`. This mode only
reads the forge. A matching candidate receives `observed-after-uncertain`
provenance and resolves the pending guard. A matching original preimage gets
an `observed-preimage` receipt with `status: "blocked"`, `no_op: true`, and
`renewal_required: true`; the guard remains. Neither observation proves a
previous request could never finish later.

If another write is explicitly chosen after that preimage observation, invoke
the original command with `--renew-after-receipt "$receipt_sha256"`. This is a
new publication decision, not an automatic retry. The helper requires the
receipt for that exact unresolved attempt and manifest, rereads the preimage,
and applies the ordinary single-write guards. A receipt from an earlier attempt
cannot renew a later one. `--reconcile` and `--renew-after-receipt` are mutually
exclusive. When neither bound body matches, retain the evidence and resolve
the conflicting live change before planning another edit.

Receipts contain identities, digests, review selection, and observation
provenance, never title/body text or arbitrary transport errors. They live in
the canonical private publication state root's separate `relation-ledger/`
directory; ordinary publication chains and readiness readers do not consume
them. The CLI has no receipt-root override. The Python API permits an injected
temporary root and forge only for isolated tests.

Journals and immutable receipts are serialized and synchronized in private
staging files before atomic installation. Initial installation cannot replace
an existing file; renewal rechecks its bound predecessor under the publication
lease. An interrupted staging file is never treated as a journal or receipt,
and later invocations leave that retained evidence alone.

## Verification boundary

Run `python -m unittest tests.test_mergecraft_pr_relation_ledger` to exercise
the public validator, publisher, actual CLI argument/transport boundary with an
isolated fake `gh`, canonical lease interoperability, historical states,
Unicode/CRLF preservation, bot drift, unknown outcomes, and recovery. These
tests establish the helper's behavior; real forge qualification must separately
establish supported historical body-edit behavior and permissions. Preserve
that distinction when reporting a platform result.
