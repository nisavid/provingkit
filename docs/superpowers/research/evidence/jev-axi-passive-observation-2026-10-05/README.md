# Prepare passive observations of ordinary work

This packet provides a bounded local evidence importer and a proposal for observing real work already in progress. The operator selected passive observation, a brief voluntary effort record, and tests through the import command and its resulting files. The [observation contract](observation-contract.md) is a proposal awaiting execution acceptance.

The three consumers remain separate: [completion evidence](https://github.com/nisavid/provingkit/issues/430), [genuine resumption](https://github.com/nisavid/provingkit/issues/432), and [task-relevant discovery](https://github.com/nisavid/provingkit/issues/434). They consume the [published input and measurement preparation](../jev-axi-consumer-observation-preparation-2026-10-05/README.md). The maintained method is [handling-sys1-incidents](../../../../../.agents/skills/handling-sys1-incidents/SKILL.md) and its [comparison contract](../../../../../.agents/skills/handling-sys1-incidents/references/comparison-contract.md). This research packet installs no skill or live hook.

## Import an explicit selection

```sh
python docs/superpowers/research/evidence/jev-axi-passive-observation-2026-10-05/import_records.py selection.json new-evidence-directory
```

The manifest is a JSON object with `version: 1`, nonempty `episode` and `purpose` strings, and a `sources` list. Each source names `label`, `path`, `start`, `length`, `sha256`, and `format` (`bytes` or `jsonl`). Offsets and lengths are nonnegative byte counts; the lowercase SHA-256 covers exactly that span. Relative source paths resolve beside the manifest. The producer supplies the intended order and declares that JSONL spans begin at record boundaries. The importer does not discover sources or infer chronology.

An invocation accepts at most 128 spans totaling 8 MiB and a manifest of at most 1 MiB. Its structural index contains at most 10,000 records. These are supported-input limits, not experimental success criteria. Manifests and source files must be regular files. The producer selects permitted material and records omissions before import; the command is not a privacy filter or an access-control mechanism.

A new directory contains the exact `selection.json`, numbered `.source` files, a structural `index.json` when indexing finishes, and `receipt.json`. JSONL records retain byte positions, field names, parsing status, and exact-byte duplicate references. Duplicate references do not establish that two occurrences are the same event; every occurrence remains present. Unterminated final lines remain uninterpreted, even if they might parse as standalone JSON.

Exit 0 means every selected span was imported and its requested index parsed within the limits. It says nothing about history completeness, human origin, model context, delivery, consumption, task quality, or cost savings. Exit 2 retains a partial index because of malformed or unterminated records or the index limit. Exit 1 reports invalid input, missing or changed bytes, an existing output directory, or an I/O failure. Existing output is never reused. A failed attempt remains incomplete; a missing or unreadable receipt is never success. Storage failure can prevent an error receipt from being written.

The receipt measures elapsed importer time through index writing, excluding final receipt serialization and process startup/shutdown. Selection, acquisition, interpretation, operator effort, and whole-task costs require separate observations. Unknown or estimated fields supplied in the manifest remain unchanged and are not converted into totals.

Raw evidence stays local. Public results require a reviewed projection; this source packet contains no chat transcript. The importer launches no agent, model, hook, network call, or monitor and never interferes with the observed task.

## Local verification

```sh
python -m unittest discover -s docs/superpowers/research/evidence/jev-axi-passive-observation-2026-10-05 -p 'test_*.py' -v
```

Eleven synthetic CLI checks cover exact span/order preservation, changed input, missing files, existing-result preservation, partial/malformed JSONL, duplicate occurrences, input/index bounds, deeply nested manifests, line-feed record boundaries, and unknown/estimated costs. Tests use real temporary files and subprocess invocation. They establish importer behavior only; no native observation or Jev request has run under this proposal.
