# Desktop observer experiment

This prototype makes the proposed observer concrete: it collects selected facts
from one existing synthetic query, exports a bounded observation envelope, and
reads that envelope without turning cached or missing facts into preservation
claims. Open `demo.html` to explore it. The file is self-contained and makes no
network requests.

The experiment answers [Prototype the Desktop runtime observer with synthetic
inputs](https://github.com/nisavid/provingkit/issues/277). Its source input is the
[reviewed observer design](https://github.com/nisavid/provingkit/blob/049017077b46247095e9d24015edc1c94e9110b7/docs/superpowers/specs/2026-09-29-desktop-runtime-observer-design.md).
The question is whether this mechanism and its app-change cost are concrete
enough to prepare a disposable probe. Every prototype result is unqualified.

## What to try

1. **Existing task:** observe idle and busy fake turns, then park the query.
   Absence produces no fallback task or prompt.
2. **Permission gaps:** change a host grant while Code rules stay equal; queue
   and fail a synthetic permission push. The false pending marker still leaves
   pending/failed coverage unknown. A retained Code mode event and a manager
   selection can disagree.
3. **Races and stale files:** replace the query during collection, miss the
   deadline, expire an export, or truncate it. The reader leaves those results
   unknown; old values are not presented as usable evidence.
4. **Compatibility:** an unassessed dependency permits partial read-only
  observations in this synthetic experiment. Carry prior rule evidence forward,
  or mark a demonstrated model dependency failure. Only the affected read is
  disabled. None of these settings supplies initial live qualification.

Host spawn account, permission mode, cwd, grants, and pending-change projections
have separate assessments. A failed mode dependency leaves cwd and grants
available. Export compatibility is separate from collection; the reader also
accepts its own assessment and a current export assessment, so a previously
written file cannot override a known dependency failure. External message
representation has no producer in this prototype and remains an explicit gap.

The free-play actions persist until Reset. Walkthrough tabs reset the fixture.
The fixture panel shows constructed state, while the reader panel shows only
what the exported observation supports. No control changes a real application.

## Executable boundaries

| File | Purpose |
| --- | --- |
| `observer.mjs` | `createObserver({selectReceiver, now})` and `inspectEnvelope(bytes, expectedBinding, options)`, shared by tests and demo |
| `fixture.mjs` | Fake manager, existing query, delayed response, and replacement behavior |
| `export.mjs` | Same-directory temporary write and atomic rename; tests use a newly created private temporary directory |
| `observer.test.mjs`, `export.test.mjs` | Contract tests with synthetic inputs; no Desktop imports or private data |
| `demo-shell.html`, `build-demo.mjs`, `demo.html` | Human experiment, with the portable modules embedded verbatim except their export declarations |
| `insertion-points.json`, `verify-source.mjs` | Static source fingerprints and 14 unique anchors; no patch is applied |
| `integration-plan.md` | Concrete app insertion, field mapping, lifecycle, maintenance, and probe prerequisites |

From the repository root, using Node 24:

```sh
node --test docs/superpowers/prototypes/desktop-runtime-observer/*.test.mjs
node docs/superpowers/prototypes/desktop-runtime-observer/build-demo.mjs --check
node docs/superpowers/prototypes/desktop-runtime-observer/verify-source.mjs <extracted-build-directory>
git diff --check
```

The source check reads only the two named extracted JavaScript files. Follow the
source-only inspection procedure in the retained [receiver-evidence report](https://github.com/nisavid/provingkit/blob/9ae77ba3f3e62bda941d328b58bce1f3e8aea7ef/docs/superpowers/research/2026-09-28-claude-desktop-receiver-evidence.md)
to obtain them as data. A fingerprint mismatch requests assessment; it does not
declare a new build incompatible. Rebuild the HTML with `build-demo.mjs` after
changing either module or the shell. The `--check` verifies the generated file.

## What the result establishes

The supported input is a fake record bound by Desktop task ID, Code session ID,
app-start ID, and generation, with one existing query and the selected host
projection. Collection captures the record/query/input-stream identities, reads
three getters, and rejects a changed binding afterward. A caller deadline stops
waiting and ignores a late result; it does not cancel the underlying request.
One observer instance owns the sequence for one app start. Each replacement or
relevant identity transition requires a generation bump in the proposed adapter.

Each exported field has its own interval and origin. Host values have before and
after snapshots; spawn identity and Code mode events remain retained facts.
The cwd's event provenance is explicitly unavailable; the host snapshot time
does not date the underlying cwd report. Code
rules include inactive markers and a count of settings errors. The prototype
omits error text, unselected response fields, raw manager objects, and tokens.
The reader checks binding, schema, field shape, expiry, and optional sequence
freshness. Atomic rename demonstrates complete-file replacement under ordinary
execution; it does not establish crash durability or authenticate a producer.

Equal endpoints cannot exclude an intervening change. A successful getter does
not prove a fresh effective account, model, mode, or cwd. Host snapshots expose
selected grants and update markers; they do not exhaust the applied permission
configuration. Delivery, acknowledgment, native address binding, and executor
process identity remain outside the demonstrated mechanics.

## Procedure capture and next consumer

This is a retained experiment on a throwaway branch, outside installed
Rolecasting equipment. It proposes a future maintained observer adapter beside
its Desktop patch/build integration, with the stable reader and notification
procedure owned by Rolecasting. The app integration's owning repository and
packaging authority remain a decision before mutation there.

[Prepare and review the disposable observer probe](https://github.com/nisavid/provingkit/issues/278)
must load this README and `integration-plan.md`, record the published revision,
reproduce the synthetic checks, and specify the actual patch, arm configuration,
approved data, installation/restart/restoration effects, and unresolved
observations before its independent review. Invoke `capturing-agent-procedures`
to carry any approved method into [Capture the Rolecasting peer-notification
skill and invocation](https://github.com/nisavid/provingkit/issues/216). Feed
source corrections back to the adapter producer; do not install this unsettled
proposal as standing instructions. [Implement the exact-peer notification
actuator](https://github.com/nisavid/provingkit/issues/215) consumes only the
subsequently adopted contract and qualified producers.

Accepting this experiment resolves its usefulness for planning. Installing an
app change, reading a private fixture, and sending messages retain their separate
review and authority gates. The first live notification route remains blocked
on the full observation and acknowledgment requirements.
