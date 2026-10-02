import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { inspectRecords } from './reader.mjs';

const at = n => new Date(n).toISOString();
export function sample() {
  return {
    metadata: { sessionId: 'desktop-fixture', cliSessionId: 'code-fixture' },
    expected: { desktopId: 'desktop-fixture', codeId: 'code-fixture' },
    request: { correlationId: 'notice-1', senderTaskId: 'sender-fixture',
      noticeText: 'Notification notice-1: context changed.', ackText: 'ACK notice-1', since: 1000 },
    capture: { startedAt: 2000, finishedAt: 2010 }, now: 2020, maxAgeMs: 100,
    transcript: [
      { uuid: 'incoming-1', sessionId: 'code-fixture', type: 'user', timestamp: at(1100),
        origin: { kind: 'peer', senderTaskId: 'sender-fixture' },
        message: { role: 'user', content: 'Notification notice-1: context changed.' } },
      { uuid: 'reply-1', sessionId: 'code-fixture', type: 'assistant', timestamp: at(1200),
        message: { role: 'assistant', content: 'ACK notice-1' } },
    ].map(row => JSON.stringify(row) + '\n').join(''),
  };
}

test('explicit receiver records yield candidates without qualifying the notification', () => {
  const result = inspectRecords(sample());
  assert.equal(result.status, 'candidate_pair');
  assert.equal(result.qualification, 'unqualified');
  assert.equal(result.compatibility.status, 'unassessed');
  assert.deepEqual(result.notices.map(x => x.id), ['incoming-1']);
  assert.deepEqual(result.acknowledgments.map(x => x.id), ['reply-1']);
  assert.deepEqual(result.notices[0].origin, { kind: 'peer', senderTaskId: 'sender-fixture' });
});

test('a different selected Code identity cannot contribute candidates', () => {
  const input = sample();
  input.metadata.cliSessionId = 'another-code-task';
  const result = inspectRecords(input);
  assert.equal(result.status, 'unknown');
  assert.equal(result.notices.length + result.acknowledgments.length, 0);
  assert.ok(result.gaps.includes('identity_mismatch'));
});

test('a partial JSONL read returns an evidence gap instead of a parse exception or prefix success', () => {
  const input = sample();
  input.transcript += '{"type":"assistant"';
  const result = inspectRecords(input);
  assert.equal(result.status, 'unknown');
  assert.equal(result.notices.length + result.acknowledgments.length, 0);
  assert.ok(result.gaps.includes('incomplete_transcript'));
});

test('a fresh read does not make old records or old captures current', () => {
  const oldRecords = sample();
  oldRecords.request.since = 1500;
  assert.equal(inspectRecords(oldRecords).status, 'unknown');
  const oldCapture = sample();
  oldCapture.now = 5000;
  const result = inspectRecords(oldCapture);
  assert.equal(result.status, 'unknown');
  assert.ok(result.gaps.includes('stale_capture'));
});

test('inconsistent selected-session records invalidate the candidate set', () => {
  for (const alter of [
    rows => { rows[1].sessionId = 'other-code-task'; },
    rows => { rows[1].message.role = 'user'; },
    rows => { rows[1].uuid = rows[0].uuid; },
    rows => { rows[1] = null; },
  ]) {
    const input = sample();
    const rows = input.transcript.trim().split('\n').map(JSON.parse);
    alter(rows);
    input.transcript = rows.map(x => JSON.stringify(x) + '\n').join('');
    const result = inspectRecords(input);
    assert.equal(result.status, 'unknown');
    assert.deepEqual([result.notices, result.acknowledgments], [[], []]);
  }
});

test('an earlier ACK or a quoted line cannot form a notification pair', () => {
  const input = sample();
  const rows = input.transcript.trim().split('\n').map(JSON.parse);
  input.transcript = rows.reverse().map(x => JSON.stringify(x) + '\n').join('');
  assert.equal(inspectRecords(input).status, 'unpaired_candidates');
  rows[0].message.content = '> ACK notice-1';
  input.transcript = rows.map(x => JSON.stringify(x) + '\n').join('');
  const quoted = inspectRecords(input);
  assert.equal(quoted.status, 'partial_candidates');
  assert.deepEqual(quoted.acknowledgments, []);
});

test('unassessed compatibility remains distinct from demonstrated incompatibility', () => {
  const input = sample();
  input.compatibility = { status: 'unassessed', build: 'new-build' };
  assert.equal(inspectRecords(input).status, 'candidate_pair');
  input.compatibility = { status: 'incompatible', evidence: 'synthetic-schema-mismatch' };
  const result = inspectRecords(input);
  assert.equal(result.status, 'unsupported');
  assert.deepEqual([result.notices, result.acknowledgments], [[], []]);
});

test('absent binding or an oversized specimen cannot produce candidates', () => {
  const input = sample(); input.expected = {}; input.metadata = {};
  assert.ok(inspectRecords(input).gaps.includes('invalid_binding_or_rule'));
  assert.equal(inspectRecords(undefined).status, 'unknown');
  const large = sample(); large.transcript = 'x'.repeat(1048577);
  assert.ok(inspectRecords(large).gaps.includes('interpretation_limit'));
});

test('summary and sidechain records do not impersonate the main receiver response', () => {
  for (const flag of ['isMeta', 'isCompactSummary', 'isSidechain']) {
    const input = sample(), rows = input.transcript.trim().split('\n').map(JSON.parse);
    rows[1][flag] = true;
    input.transcript = rows.map(x => JSON.stringify(x) + '\n').join('');
    assert.deepEqual(inspectRecords(input).acknowledgments, []);
  }
  const input = sample(), rows = input.transcript.trim().split('\n').map(JSON.parse);
  delete rows[1].timestamp;
  input.transcript = rows.map(x => JSON.stringify(x) + '\n').join('');
  assert.ok(inspectRecords(input).gaps.includes('record_time_missing_or_outside_window'));
});

test('text-only blocks are interpretable but another sender or mixed content cannot form the pair', () => {
  const input = sample(), rows = input.transcript.trim().split('\n').map(JSON.parse);
  rows[1].message.content = [{ type: 'text', text: 'ACK notice-1' }];
  input.transcript = rows.map(x => JSON.stringify(x) + '\n').join('');
  assert.equal(inspectRecords(input).status, 'candidate_pair');
  rows[0].origin.senderTaskId = 'wrong-sender';
  input.transcript = rows.map(x => JSON.stringify(x) + '\n').join('');
  assert.deepEqual(inspectRecords(input).notices, []);
  rows[1].message.content.push({ type: 'tool_use', name: 'invented-tool' });
  input.transcript = rows.map(x => JSON.stringify(x) + '\n').join('');
  assert.deepEqual(inspectRecords(input).acknowledgments, []);
});

test('file acquisition uses the two explicit files and never searches for a missing selection', async () => {
  const { readSelectedFiles } = await import('./files.mjs');
  const dir = await mkdtemp(join(tmpdir(), 'reader-evidence-synthetic-'));
  try {
    const input = sample();
    const metadataPath = join(dir, 'selected.json');
    const transcriptPath = join(dir, 'selected.jsonl');
    await writeFile(metadataPath, JSON.stringify({ ...input.metadata, transcriptPath: 'unrelated.jsonl' }));
    await writeFile(transcriptPath, input.transcript);
    await writeFile(join(dir, 'unrelated.jsonl'), 'UNRELATED FILE MUST NOT BECOME EVIDENCE');
    const result = await readSelectedFiles({ ...input, metadataPath, transcriptPath }, { clock: () => 2010 });
    assert.equal(result.status, 'candidate_pair');
    assert.deepEqual(result.acquisition.files.map(f => f.path), [metadataPath, transcriptPath]);
    assert.equal(result.acquisition.coherence, 'unverified');
    const missing = await readSelectedFiles({ ...input, metadataPath, transcriptPath: join(dir, 'missing.jsonl') }, { clock: () => 2010 });
    assert.equal(missing.status, 'unknown');
    assert.ok(missing.gaps.includes('acquisition_failed'));
    assert.deepEqual(missing.notices, []);
  } finally { await rm(dir, { recursive: true, force: true }); }
});

test('an oversized selected file yields only a bounded prefix and no candidate evidence', async () => {
  const { readSelectedFiles } = await import('./files.mjs');
  const dir = await mkdtemp(join(tmpdir(), 'reader-evidence-limit-'));
  try {
    const input = sample(), metadataPath = join(dir, 'selected.json'), transcriptPath = join(dir, 'selected.jsonl');
    await writeFile(metadataPath, JSON.stringify(input.metadata));
    await writeFile(transcriptPath, input.transcript.repeat(10));
    const result = await readSelectedFiles({ ...input, metadataPath, transcriptPath }, { clock: () => 2010, limitBytes: 256 });
    assert.equal(result.status, 'unknown');
    assert.equal(result.error, 'acquisition_limit');
    assert.equal(result.acquisition.files[1].bytesRead, 257);
    assert.equal(result.acquisition.files[1].complete, false);
    assert.deepEqual([result.notices, result.acknowledgments], [[], []]);
  } finally { await rm(dir, { recursive: true, force: true }); }
});
