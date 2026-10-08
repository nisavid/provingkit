import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, rm, stat, symlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawn } from 'node:child_process';

const command = new URL('./fixture-metadata.mjs', import.meta.url).pathname;
async function fixture(t) {
  const root = await mkdtemp(join(tmpdir(), 'synthetic-fixture-metadata-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const directory = join(root, 'declared');
  await mkdir(directory);
  return { root, directory };
}
async function invoke(f, request) {
  const requestPath = join(f.root, 'request.json');
  await writeFile(requestPath, JSON.stringify({ schema: 1, runId: 'synthetic-run', directory: f.directory, ...request }));
  return new Promise(resolve => {
    const child = spawn(process.execPath, [command, '--request', requestPath], { env: {}, stdio: ['ignore', 'pipe', 'pipe'] });
    let out = '', error = '';
    child.stdout.on('data', b => { out += b; }); child.stderr.on('data', b => { error += b; });
    child.on('close', code => {
      let record; try { record = JSON.parse(out); } catch {}
      resolve({ code, record, error });
    });
  });
}
function associationRequest(names = ['desktop-a.json']) {
  const now = Date.now();
  return { operation: 'associate', candidates: names.map(name => ({ name })), since: now - 1000, maxJoinAgeMs: 10000,
    uiWitness: { runId: 'synthetic-run', selectedTask: true, projectField: 'cwd', projectPath: '/synthetic/project',
      setupText: 'FIXTURE:synthetic-run', displayedText: 'FIXTURE:synthetic-run',
      capture: { startedAt: now - 100, finishedAt: now - 50 }, recheckedAt: now - 1 },
    stopRecord: { schema: 1, runId: 'synthetic-run', purpose: 'fixture_stop_check', binding: 'unbound',
      qualification: 'unqualified', acquisition: { status: 'complete', eof: true },
      capture: { startedAt: now - 40, completedAt: now - 30, notBefore: now - 1000 },
      unbound: { observedHookSessionId: 'code-a', matchingFinalText: 'FIXTURE:synthetic-run' } } };
}
const metadata = (id = 'desktop-a', codeId = 'code-a') => ({ sessionId: id, cliSessionId: codeId,
  cwd: '/synthetic/project', title: 'private invented title', transcriptPath: '/synthetic/must-not-open' });

test('listing records names and types without acquiring candidate contents', async t => {
  const f = await fixture(t);
  await writeFile(join(f.directory, 'desktop-a.json'), 'not JSON; must not be opened during listing');
  await mkdir(join(f.directory, 'nested'));
  const result = await invoke(f, { operation: 'list' });
  assert.equal(result.code, 0, result.error);
  assert.equal(result.record.status, 'listed');
  assert.equal(result.record.qualification, 'unqualified');
  assert.deepEqual(result.record.entries.sort((a, b) => a.name.localeCompare(b.name)), [
    { name: 'desktop-a.json', type: 'file' }, { name: 'nested', type: 'directory' },
  ]);
  assert.equal(result.record.acquisition.files.length, 0);
  assert.equal(result.record.activeDirectory, 'unproved');
});

test('listing stops at one overflow entry without opening files', async t => {
  const f = await fixture(t);
  for (let i = 0; i < 140; i++) await writeFile(join(f.directory, `entry-${i}.json`), 'not a candidate');
  const { code, record } = await invoke(f, { operation: 'list' });
  assert.equal(code, 0);
  assert.equal(record.status, 'unknown');
  assert.deepEqual(record.gaps, ['listing_overflow']);
  assert.equal(record.acquisition.listing.entriesObserved, 129);
  assert.equal(record.entries.length, 128);
  assert.deepEqual(record.acquisition.files, []);
});

test('one selected metadata match yields only a conditional association candidate', async t => {
  const f = await fixture(t);
  await writeFile(join(f.directory, 'desktop-a.json'), JSON.stringify(metadata()));
  const { code, record } = await invoke(f, associationRequest());
  assert.equal(code, 0);
  assert.equal(record.status, 'association_candidate');
  assert.deepEqual(record.association, { desktopId: 'desktop-a', codeId: 'code-a', filename: 'desktop-a.json',
    project: { field: 'cwd', value: '/synthetic/project' }, uniqueness: 'acquired_candidates_only' });
  assert.equal(record.qualification, 'unqualified');
  assert.equal(record.activeDirectory, 'unproved');
  assert.equal(record.witnessEvidence, 'caller_supplied');
  assert.equal(record.acquisition.files.length, 1);
  assert.equal(record.acquisition.files[0].complete, true);
  assert.equal(JSON.stringify(record).includes('private invented title'), false);
});

test('oversized metadata stops after the one overflow byte and cannot associate', async t => {
  const f = await fixture(t);
  await writeFile(join(f.directory, 'desktop-a.json'), Buffer.alloc(1048576 + 100, 32));
  const { code, record } = await invoke(f, associationRequest());
  assert.equal(code, 0);
  assert.equal(record.status, 'unknown');
  assert.deepEqual(record.gaps, ['metadata_overflow']);
  assert.equal(record.association, null);
  assert.equal(record.acquisition.files[0].bytesRead, 1048577);
  assert.equal(record.acquisition.files[0].complete, false);
});

test('more than three nominated candidates is a command-input failure', async t => {
  const f = await fixture(t);
  const names = ['desktop-a.json', 'desktop-b.json', 'desktop-c.json', 'desktop-d.json'];
  for (const [i, name] of names.entries()) await writeFile(join(f.directory, name), JSON.stringify(metadata(name.slice(0, -5), `code-${i}`)));
  const { code, record, error } = await invoke(f, associationRequest(names));
  assert.equal(code, 1);
  assert.equal(record, undefined);
  assert.equal(error, 'Metadata command did not complete.\n');
});

test('duplicate candidate nominations are rejected rather than counted as two matches', async t => {
  const f = await fixture(t);
  await writeFile(join(f.directory, 'desktop-a.json'), JSON.stringify(metadata()));
  const { code, record } = await invoke(f, associationRequest(['desktop-a.json', 'desktop-a.json']));
  assert.equal(code, 1);
  assert.equal(record, undefined);
});

test('the displayed setup response must match the whole hook response', async t => {
  const f = await fixture(t);
  await writeFile(join(f.directory, 'desktop-a.json'), JSON.stringify(metadata()));
  const request = associationRequest();
  request.uiWitness.displayedText = 'quoted FIXTURE:synthetic-run';
  const { code, record } = await invoke(f, request);
  assert.equal(code, 0);
  assert.equal(record.status, 'unknown');
  assert.equal(record.association, null);
  assert.deepEqual(record.gaps, ['setup_response_mismatch']);
  assert.deepEqual(record.acquisition.files, []);
});

test('one malformed authorized candidate prevents a uniqueness claim', async t => {
  const f = await fixture(t);
  await writeFile(join(f.directory, 'desktop-a.json'), JSON.stringify(metadata()));
  await writeFile(join(f.directory, 'desktop-b.json'), '{unfinished');
  const { code, record } = await invoke(f, associationRequest(['desktop-a.json', 'desktop-b.json']));
  assert.equal(code, 0);
  assert.equal(record.status, 'unknown');
  assert.equal(record.association, null);
  assert.deepEqual(record.gaps, ['metadata_invalid']);
  assert.equal(record.acquisition.files.length, 2);
  assert.equal(record.acquisition.files[1].complete, true);
});

test('missing independent UI evidence yields unknown without reading candidates', async t => {
  const f = await fixture(t);
  const request = associationRequest();
  delete request.uiWitness;
  const { code, record } = await invoke(f, request);
  assert.equal(code, 0);
  assert.equal(record.status, 'unknown');
  assert.deepEqual(record.gaps, ['ui_witness_incomplete']);
  assert.deepEqual(record.acquisition.files, []);
});

test('a timed-out Stop record cannot supply the association identity', async t => {
  const f = await fixture(t);
  await writeFile(join(f.directory, 'desktop-a.json'), JSON.stringify(metadata()));
  const request = associationRequest();
  request.stopRecord.acquisition = { status: 'timeout', eof: false };
  const { code, record } = await invoke(f, request);
  assert.equal(code, 0);
  assert.equal(record.status, 'unknown');
  assert.deepEqual(record.gaps, ['stop_record_incomplete']);
  assert.deepEqual(record.acquisition.files, []);
});

test('a fresh selection recheck does not freshen old setup evidence', async t => {
  const f = await fixture(t);
  await writeFile(join(f.directory, 'desktop-a.json'), JSON.stringify(metadata()));
  const request = associationRequest(), now = Date.now();
  request.since = now - 60000;
  request.uiWitness.capture = { startedAt: now - 30000, finishedAt: now - 25000 };
  request.stopRecord.capture = { startedAt: now - 23000, completedAt: now - 22000, notBefore: request.since };
  const { code, record } = await invoke(f, request);
  assert.equal(code, 0);
  assert.equal(record.status, 'unknown');
  assert.deepEqual(record.gaps, ['stale_evidence']);
  assert.deepEqual(record.acquisition.files, []);
});

test('metadata changed since the supplied selection identity remains unknown', async t => {
  const f = await fixture(t), path = join(f.directory, 'desktop-a.json');
  await writeFile(path, JSON.stringify(metadata()));
  const original = await stat(path, { bigint: true });
  const identity = Object.fromEntries(['dev', 'ino', 'size', 'mtimeNs', 'ctimeNs'].map(key => [key, String(original[key])]));
  await writeFile(path, JSON.stringify({ ...metadata(), extra: 'changed after selection' }));
  const request = associationRequest();
  request.candidates[0].expectedIdentity = identity;
  const { code, record } = await invoke(f, request);
  assert.equal(code, 0);
  assert.equal(record.status, 'unknown');
  assert.deepEqual(record.gaps, ['metadata_changed']);
  assert.equal(record.acquisition.files[0].bytesRead, 0);
});

test('request acquisition has a separate byte ceiling', async t => {
  const f = await fixture(t);
  const { code, record, error } = await invoke(f, { operation: 'list', extra: 'x'.repeat(131072) });
  assert.equal(code, 1);
  assert.equal(record, undefined);
  assert.equal(error, 'Metadata command did not complete.\n');
});

test('unsupported command input stops before directory acquisition', async t => {
  const f = await fixture(t);
  for (const bad of [{ schema: 2 }, { operation: 'search' }, { runId: '' }, { directory: 'relative' }]) {
    const { code, record } = await invoke(f, { operation: 'list', ...bad });
    assert.equal(code, 1, JSON.stringify(bad));
    assert.equal(record, undefined);
  }
});

test('UI evidence must identify this run, selected task and a supported project relation', async t => {
  const f = await fixture(t);
  await writeFile(join(f.directory, 'desktop-a.json'), JSON.stringify(metadata()));
  for (const change of [{ runId: 'other' }, { selectedTask: false }, { projectField: 'title' },
    { projectPath: '' }, { setupText: '' }]) {
    const request = associationRequest();
    Object.assign(request.uiWitness, change);
    const { code, record } = await invoke(f, request);
    assert.equal(code, 0);
    assert.deepEqual(record.gaps, ['ui_witness_incomplete'], JSON.stringify(change));
    assert.deepEqual(record.acquisition.files, []);
  }
});

test('association requires a selection recheck after both source observations', async t => {
  const f = await fixture(t);
  for (const recheckedAt of [undefined, 0, Date.now() + 60000]) {
    const request = associationRequest();
    request.uiWitness.recheckedAt = recheckedAt;
    const { code, record } = await invoke(f, request);
    assert.equal(code, 0);
    assert.deepEqual(record.gaps, ['selection_recheck_incomplete']);
    assert.deepEqual(record.acquisition.files, []);
  }
});

test('candidate nominations are distinct regular JSON basenames with optional complete identity samples', async t => {
  const f = await fixture(t);
  for (const candidate of [{ name: '../desktop-a.json' }, { name: 'nested/desktop-a.json' },
    { name: 'desktop-a.txt' }, { name: 'desktop-a.json', expectedIdentity: { size: '0' } }]) {
    const request = associationRequest();
    request.candidates = [candidate];
    const { code, record } = await invoke(f, request);
    assert.equal(code, 1, JSON.stringify(candidate));
    assert.equal(record, undefined);
  }
});

test('two distinct current matches are ambiguous within the acquired set', async t => {
  const f = await fixture(t);
  for (const id of ['desktop-a', 'desktop-b']) await writeFile(join(f.directory, `${id}.json`), JSON.stringify(metadata(id)));
  const { code, record } = await invoke(f, associationRequest(['desktop-a.json', 'desktop-b.json']));
  assert.equal(code, 0);
  assert.equal(record.status, 'unknown');
  assert.equal(record.association, null);
  assert.deepEqual(record.gaps, ['no_unique_match']);
  assert.equal(record.acquisition.files.length, 2);
});

test('serialized identity, current Code identity and explicit project relation must all match', async t => {
  const f = await fixture(t);
  for (const candidate of [metadata('desktop-other'), { ...metadata(), cliSessionId: 'code-other', priorCliSessionIds: ['code-a'] },
    { ...metadata(), cwd: '/other/project' }]) {
    await writeFile(join(f.directory, 'desktop-a.json'), JSON.stringify(candidate));
    const { record } = await invoke(f, associationRequest());
    assert.equal(record.status, 'unknown');
    assert.equal(record.association, null);
    assert.deepEqual(record.gaps, ['no_unique_match']);
  }
});

test('an explicit originCwd relation can match without claiming current runtime cwd', async t => {
  const f = await fixture(t);
  await writeFile(join(f.directory, 'desktop-a.json'), JSON.stringify({ ...metadata(), cwd: '/worktree', originCwd: '/synthetic/project' }));
  const request = associationRequest();
  request.uiWitness.projectField = 'originCwd';
  const { record } = await invoke(f, request);
  assert.equal(record.status, 'association_candidate');
  assert.deepEqual(record.association.project, { field: 'originCwd', value: '/synthetic/project' });
});

test('missing, symlink and directory candidates produce gaps without acquiring their bytes', async t => {
  const f = await fixture(t);
  await mkdir(join(f.directory, 'directory.json'));
  await writeFile(join(f.root, 'outside.json'), JSON.stringify(metadata()));
  await symlink(join(f.root, 'outside.json'), join(f.directory, 'link.json'));
  for (const [name, gap] of [['missing.json', 'metadata_unavailable'], ['directory.json', 'metadata_not_regular'], ['link.json', 'metadata_not_regular']]) {
    const { record } = await invoke(f, associationRequest([name]));
    assert.equal(record.status, 'unknown');
    assert.deepEqual(record.gaps, [gap]);
    assert.equal(record.acquisition.files[0].bytesRead, 0);
  }
});

test('cross-run or served Stop identities and unordered capture windows are not admitted', async t => {
  const f = await fixture(t);
  for (const change of [r => r.stopRecord.runId = 'other', r => r.stopRecord.unbound.observedHookSessionId = 'served:code-a',
    r => r.stopRecord.acquisition.eof = false, r => r.stopRecord.capture.completedAt = r.stopRecord.capture.startedAt - 1]) {
    const request = associationRequest(); change(request);
    const { record } = await invoke(f, request);
    assert.equal(record.status, 'unknown');
    assert.deepEqual(record.acquisition.files, []);
  }
});

test('complete acquisition at the exact byte ceiling is allowed but invalid UTF-8 is a gap', async t => {
  const f = await fixture(t);
  const valid = JSON.stringify(metadata());
  await writeFile(join(f.directory, 'desktop-a.json'), valid + ' '.repeat(1048576 - Buffer.byteLength(valid)));
  let result = await invoke(f, associationRequest());
  assert.equal(result.record.status, 'association_candidate');
  assert.equal(result.record.acquisition.files[0].bytesRead, 1048576);
  assert.equal(result.record.acquisition.files[0].complete, true);
  await writeFile(join(f.directory, 'desktop-a.json'), Buffer.from([0xff]));
  result = await invoke(f, associationRequest());
  assert.deepEqual(result.record.gaps, ['metadata_invalid']);
});

test('records separate command and metadata acquisition intervals without refreshing source times', async t => {
  const f = await fixture(t);
  await writeFile(join(f.directory, 'desktop-a.json'), JSON.stringify(metadata()));
  const request = associationRequest(), before = Date.now();
  const { record } = await invoke(f, request);
  const after = Date.now();
  assert.ok(record.acquisition.capture.startedAt >= before);
  assert.ok(record.acquisition.capture.completedAt <= after);
  const capture = record.acquisition.files[0].capture;
  assert.ok(capture.startedAt >= record.acquisition.capture.startedAt);
  assert.ok(capture.completedAt >= capture.startedAt);
  assert.ok(capture.completedAt <= record.acquisition.capture.completedAt);
  assert.equal(record.sources.ui.startedAt, request.uiWitness.capture.startedAt);
  assert.equal(record.sources.stop.completedAt, request.stopRecord.capture.completedAt);
});

test('a numeric serialized Desktop ID cannot become a text task identity', async t => {
  const f = await fixture(t);
  await writeFile(join(f.directory, '42.json'), JSON.stringify(metadata(42)));
  const { record } = await invoke(f, associationRequest(['42.json']));
  assert.equal(record.status, 'unknown');
  assert.deepEqual(record.gaps, ['metadata_incomplete']);
});

test('a fully acquired but structurally incomplete candidate prevents a uniqueness result', async t => {
  const f = await fixture(t);
  await writeFile(join(f.directory, 'desktop-a.json'), JSON.stringify(metadata()));
  for (const incomplete of [{ sessionId: 'desktop-b' }, { cliSessionId: 'code-a', cwd: '/synthetic/project' },
    { sessionId: 'desktop-b', cliSessionId: 'code-a' }]) {
    await writeFile(join(f.directory, 'desktop-b.json'), JSON.stringify(incomplete));
    const { code, record } = await invoke(f, associationRequest(['desktop-a.json', 'desktop-b.json']));
    assert.equal(code, 0);
    assert.equal(record.status, 'unknown');
    assert.equal(record.association, null);
    assert.deepEqual(record.gaps, ['metadata_incomplete']);
    assert.equal(record.acquisition.files[1].complete, true);
  }
});
