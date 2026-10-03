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
- `hook.mjs`: pure Stop projection.
- `collector.mjs`: one bounded stdin-pipe event and a task-owned output slot;
  see the [command contract](collector-contract.md) and
  [fixture-check procedure](fixture-check-procedure.md).
- `fixtures.mjs`: invented examples shared by tests and the demonstration.
- `demo-source.html` and `build-demo.mjs`: presentation source and deterministic
  single-file assembly. Change the pure modules first, then regenerate.

```sh
node --test docs/superpowers/prototypes/receiver-evidence/reader.test.mjs docs/superpowers/prototypes/receiver-evidence/hook.test.mjs docs/superpowers/prototypes/receiver-evidence/collector.test.mjs
node docs/superpowers/prototypes/receiver-evidence/build-demo.mjs
git diff --check
```

The tests exercise the operator-agreed reader, projector, and command boundaries with invented
inputs. File tests create and remove their own temporary directory. They do not
qualify native files, authenticate peers, test containment of hostile paths,
or demonstrate applied runtime state.

## Collector and fixture preparation

The collector implements acquisition, projection, output, exit status, and
one-shot file lifecycle with synthetic inputs. It keeps initial Code identity,
setup text, optional cwd/mode, and the endpoint observation unbound until the
procedure's independent selection/metadata checks can be evaluated. It does
not open metadata, configure hooks, or invoke the sender.

The proposed fixture procedure still needs exact project/profile paths,
selected-executor evidence, launcher/environment, settings pre-state,
restoration, and a reviewed live grant. Receiving a hook event acquires its
complete serialized contents before projection. Reading fewer output fields
does not reduce that footprint. The browser demonstration exercises only the
pure reader/projector and does not run the collector.

## Use in the next decision

Read the [reconciled source findings](../../research/2026-10-02-reader-hook-findings.md)
before carrying these components forward. The
[comparison join](https://github.com/nisavid/provingkit/issues/396) consumes that
report, this contract, and verification at the published revision. The
[accepted experiment decision](https://github.com/nisavid/provingkit/issues/397)
selects the source increment. The
[preparation join](https://github.com/nisavid/provingkit/issues/278) consumes the
[collector and runtime-access findings](../../research/2026-10-03-receiver-collector-findings.md)
before presenting a live proposal. Source
publication does not install a procedure or qualify the notification route.
