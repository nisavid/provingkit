# Inspect receiver evidence candidates

The [standalone demonstration](demo.html) lets you compare a selected-file reader
and a Stop-hook projection using invented records. It exposes matching text,
identity mismatches, stale observations, collector gaps, and the difference
between an unassessed build and a demonstrated incompatibility. Every result
remains unqualified.

Open `demo.html` directly in a browser. It has no external assets or dependencies.
If the host blocks local file URLs, serve this directory on loopback:

```sh
python -m http.server 8000 --bind 127.0.0.1 --directory docs/superpowers/prototypes/receiver-evidence
```

Then open `http://127.0.0.1:8000/demo.html`. Stop that server after viewing.
The page invokes the same pure functions as the tests; it never invokes the
filesystem adapter.

## Source and verification

- [Contract](contract.md): inputs, output meaning, supported specimen, and limits.
- `reader.mjs`: pure metadata/JSONL interpretation.
- `files.mjs`: two explicitly selected synthetic files, bounded acquisition,
  no directory discovery or metadata path dereferencing.
- `hook.mjs`: pure Stop projection; no hook installation, process, or log sink.
- `fixtures.mjs`: invented examples shared by tests and the demonstration.
- `demo-source.html` and `build-demo.mjs`: presentation source and deterministic
  single-file assembly. Change the pure modules first, then regenerate.

```sh
node --test docs/superpowers/prototypes/receiver-evidence/reader.test.mjs docs/superpowers/prototypes/receiver-evidence/hook.test.mjs
node docs/superpowers/prototypes/receiver-evidence/build-demo.mjs
git diff --check
```

The tests exercise the two operator-agreed public boundaries with invented
inputs. File tests create and remove their own temporary directory. They do not
qualify native files, authenticate peers, test containment of hostile paths,
or demonstrate applied runtime state.

## Proposed hook operation to assess later

A later plan could configure a command for the selected fixture project's
`Stop` event. That requires an explicit project-settings change and command
execution grant. The command would receive the full serialized hook event
before projecting it. In the inspected engine that can include transcript path,
cwd, permission mode, assistant text, agent fields, background-task descriptions
and commands, and cron prompts. Keeping fewer output fields does not reduce
the input exposure.

That plan must specify the exact settings file and merge/restoration method,
command/runtime, stdin size bound, selected fixture/executor binding, projection
fields, private output location and lifecycle, and failure behavior. Adding
socket or host-session environment observations requires an explicit field list;
this prototype does not read the environment. It must also specify how to
preserve other hooks, stop the fixture collector, restore the selected settings,
and remove its private output and temporary files. No such wrapper, settings
change, sink, or installation is delivered here.

## Use in the next decision

Read the [reconciled source findings](../../research/2026-10-02-reader-hook-findings.md)
before carrying these components forward. The
[comparison join](https://github.com/nisavid/provingkit/issues/396) consumes that
report, this contract, and verification at the published revision. The
[experiment decision](https://github.com/nisavid/provingkit/issues/397) owns the
operator's reaction and the selection of any later live proposal. Source
publication does not install a procedure or qualify the notification route.
