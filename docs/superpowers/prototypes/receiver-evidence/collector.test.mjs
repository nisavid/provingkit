import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdtemp, writeFile, readFile, readdir, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const command = fileURLToPath(new URL('./collector.mjs', import.meta.url));
const event = () => ({ hook_event_name: 'Stop', session_id: 'fixture-code',
  cwd: '/invented/project', permission_mode: 'default',
  last_assistant_message: 'FIXTURE run-1', transcript_path: '/never-open',
  background_tasks: [{ command: 'PRIVATE INPUT' }] });

async function fixture(t, changes = {}) {
  const dir = await mkdtemp(join(tmpdir(), 'receiver-collector-test-'));
  t.after(() => rm(dir, { recursive: true, force: true }));
  const config = { schema: 1, runId: 'run-1', expectedCodeId: 'fixture-code',
    expectedFinalText: 'FIXTURE run-1', since: Date.now() - 10000,
    maxInputBytes: 65536, inputTimeoutMs: 1000, ...changes };
  await writeFile(join(dir, 'config.json'), JSON.stringify(config));
  return { dir, config, output: join(dir, 'result.json') };
}

function start(f, extraEnvironment = {}, fileSizeLimit = null) {
  const args = [command, '--config', join(f.dir, 'config.json'), '--output', f.output];
  const executable = fileSizeLimit === null ? process.execPath : '/usr/bin/prlimit';
  const invocation = fileSizeLimit === null ? args
    : [`--fsize=${fileSizeLimit}:${fileSizeLimit}`, '--core=0:0', '--', process.execPath, ...args];
  const child = spawn(executable, invocation, { cwd: f.dir,
    env: { CLAUDE_CODE_MESSAGING_SOCKET: '/invented/peer.sock', ...extraEnvironment },
    stdio: ['pipe', 'pipe', 'pipe'] });
  let stdout = '', stderr = '';
  child.stdout.on('data', chunk => { stdout += chunk; });
  child.stderr.on('data', chunk => { stderr += chunk; });
  child.stdin.on('error', () => {});
  const done = new Promise((resolve, reject) => {
    child.on('error', reject);
    child.on('close', (code, signal) => resolve({ code, signal, stdout, stderr }));
  });
  return { child, done };
}

async function collect(f, input = JSON.stringify(event()), extraEnvironment = {}) {
  const run = start(f, extraEnvironment);
  run.child.stdin.end(input);
  const result = await run.done;
  const bytes = await readFile(f.output, 'utf8');
  return { ...result, bytes, record: JSON.parse(bytes) };
}

test('the command publishes a bounded record for the configured synthetic receiver', async t => {
  const f = await fixture(t);
  const result = await collect(f, JSON.stringify(event()), { UNRELATED_PRIVATE_VALUE: 'NEVER RETAIN' });
  assert.equal(result.code, 0);
  assert.equal(result.stdout, '');
  assert.equal(result.stderr, '');
  assert.equal(result.record.schema, 1);
  assert.equal(result.record.runId, 'run-1');
  assert.equal(result.record.qualification, 'unqualified');
  assert.equal(result.record.binding, 'configured_code_id_only');
  assert.equal(result.record.projection.status, 'candidate');
  assert.deepEqual(result.record.responseCandidate,
    { text: 'FIXTURE run-1', runId: 'run-1' });
  assert.equal(result.record.endpoint, '/invented/peer.sock');
  assert.equal(result.record.acquisition.eof, true);
  assert.ok(result.bytes.endsWith('\n'));
  assert.ok(!/PRIVATE INPUT|NEVER RETAIN|never-open/.test(result.bytes));
  assert.deepEqual((await readdir(f.dir)).sort(), ['config.json', 'result.json', 'result.json.claim']);
});

test('initial acquisition retains a matching setup token without deriving identity from itself', async t => {
  const f = await fixture(t, { expectedCodeId: null });
  const result = await collect(f);
  assert.equal(result.code, 0);
  assert.equal(result.record.binding, 'unbound');
  assert.equal(result.record.projection.status, 'unknown');
  assert.equal(result.record.responseCandidate, null);
  assert.deepEqual(result.record.unbound,
    { observedHookSessionId: 'fixture-code', matchingFinalText: 'FIXTURE run-1',
      eventFields: { cwd: '/invented/project', permissionMode: 'default' }, gaps: [] });
  assert.ok(result.record.gaps.includes('independent_task_binding_required'));
});

test('a different task cannot supply the configured receiver projection or endpoint', async t => {
  const f = await fixture(t);
  const input = event(); input.session_id = 'different-code';
  const { record } = await collect(f, JSON.stringify(input));
  assert.equal(record.binding, 'mismatch');
  assert.equal(record.projection.status, 'unknown');
  assert.equal(record.responseCandidate, null);
  assert.equal(record.endpoint, null);
  assert.equal(record.unbound, null);
});

test('input beyond the byte ceiling produces an unknown record after one overflow byte', async t => {
  const f = await fixture(t, { maxInputBytes: 256 });
  const input = JSON.stringify({ ...event(), extra: 'x'.repeat(4096) });
  const { code, record } = await collect(f, input);
  assert.equal(code, 0);
  assert.equal(record.acquisition.status, 'over_limit');
  assert.equal(record.acquisition.bytesObserved, 257);
  assert.equal(record.acquisition.eof, false);
  assert.equal(record.projection.status, 'unknown');
  assert.equal(record.endpoint, null);
  assert.equal(record.unbound, null);
});

test('incomplete JSON and invalid event shapes remain explicit unknown input', async t => {
  for (const input of ['{"hook_event_name":', 'null', '[]', Buffer.from([0xff])]) {
    const f = await fixture(t);
    const { code, record } = await collect(f, input);
    assert.equal(code, 0);
    assert.equal(record.acquisition.eof, true);
    assert.equal(record.projection.status, 'unknown');
    assert.ok(record.gaps.includes('invalid_event_input'));
    assert.equal(record.endpoint, null);
  }
});

test('a stalled input closes with an unknown record without claiming unread bytes', async t => {
  const f = await fixture(t, { inputTimeoutMs: 50, maxInputBytes: 256 });
  const run = start(f);
  run.child.stdin.write('{');
  const watchdog = setTimeout(() => run.child.kill('SIGKILL'), 1500);
  t.after(() => clearTimeout(watchdog));
  const result = await run.done;
  assert.equal(result.code, 0);
  const record = JSON.parse(await readFile(f.output, 'utf8'));
  assert.equal(record.acquisition.status, 'timeout');
  assert.equal(record.acquisition.eof, false);
  assert.equal(record.acquisition.bytesObserved, 1);
  assert.equal(Object.hasOwn(record.acquisition, 'pendingBytesAtStop'), false);
  assert.equal(record.projection.status, 'unknown');
  assert.equal(record.endpoint, null);
});

test('missing final text and an oversized environment field remain gaps', async t => {
  const f = await fixture(t);
  const input = event(); delete input.last_assistant_message; delete input.permission_mode;
  const { record } = await collect(f, JSON.stringify(input), { CLAUDE_CODE_MESSAGING_SOCKET: 'x'.repeat(4097) });
  assert.equal(record.projection.status, 'unknown');
  assert.ok(record.projection.gaps.includes('final_text_missing'));
  assert.ok(record.projection.gaps.includes('permission_mode_missing'));
  assert.equal(record.endpoint, null);
  assert.ok(record.gaps.includes('endpoint_missing_or_oversized'));
});

test('invalid configuration stops the command without publishing a result', async t => {
  for (const change of [{ schema: 2 }, { maxInputBytes: 0 }, { inputTimeoutMs: -1 },
    { expectedFinalText: 'x'.repeat(4097) }, { expectedCodeId: '' }, { since: null }]) {
    const f = await fixture(t, change);
    const run = start(f); run.child.stdin.end(JSON.stringify(event()));
    const result = await run.done;
    assert.equal(result.code, 1);
    assert.equal(result.stdout, '');
    assert.equal(result.stderr, 'Collector did not confirm completion; inspect the run files.\n');
    assert.deepEqual(await readdir(f.dir), ['config.json']);
  }
});

test('a consumed output slot prevents a later invocation from waiting for another event', async t => {
  const f = await fixture(t);
  const first = await collect(f);
  const run = start(f);
  const watchdog = setTimeout(() => run.child.kill('SIGKILL'), 500);
  t.after(() => clearTimeout(watchdog));
  const result = await run.done;
  assert.equal(result.code, 1);
  assert.equal(await readFile(f.output, 'utf8'), first.bytes);
  assert.deepEqual((await readdir(f.dir)).sort(), ['config.json', 'result.json', 'result.json.claim']);
});

test('an interrupted output write leaves no published record', async t => {
  const f = await fixture(t, { expectedFinalText: 'x'.repeat(2048) });
  const run = start(f, {}, 1024);
  run.child.stdin.end(JSON.stringify({ ...event(), last_assistant_message: f.config.expectedFinalText }));
  const result = await run.done;
  assert.ok(result.code !== 0 || result.signal !== null);
  assert.equal(result.stdout, '');
  const files = await readdir(f.dir);
  assert.ok(!files.includes('result.json'));
  assert.ok(files.includes('result.json.claim'));
});

test('unbound collection retains receipt times but rejects events outside its setup rule', async t => {
  for (const change of [{ hook_event_name: 'UserPromptSubmit' }, { session_id: '' },
    { last_assistant_message: 'a different response' }]) {
    const f = await fixture(t, { expectedCodeId: null });
    const { record } = await collect(f, JSON.stringify({ ...event(), ...change }));
    assert.equal(record.unbound, null);
    assert.equal(record.endpoint, null);
    assert.ok(record.capture.startedAt >= f.config.since);
    assert.ok(record.capture.completedAt >= record.capture.startedAt);
  }
  const f = await fixture(t, { expectedCodeId: null, since: Date.now() + 60000 });
  const { record } = await collect(f);
  assert.equal(record.unbound, null);
  assert.equal(record.endpoint, null);
  assert.ok(record.gaps.includes('invalid_capture_window'));
});

test('an occupied destination is preserved and the failed publication cleans its temporary file', async t => {
  const f = await fixture(t);
  await writeFile(f.output, 'existing observation\n');
  await writeFile(join(f.dir, 'neighbor.txt'), 'keep this\n');
  const run = start(f); run.child.stdin.end(JSON.stringify(event()));
  assert.equal((await run.done).code, 1);
  assert.equal(await readFile(f.output, 'utf8'), 'existing observation\n');
  assert.equal(await readFile(join(f.dir, 'neighbor.txt'), 'utf8'), 'keep this\n');
  assert.deepEqual((await readdir(f.dir)).sort(),
    ['config.json', 'neighbor.txt', 'result.json', 'result.json.claim']);
});

test('termination during input leaves the consumed slot without a completion record', async t => {
  const f = await fixture(t, { inputTimeoutMs: 60000 });
  const run = start(f);
  t.after(() => { if (run.child.exitCode === null) run.child.kill('SIGKILL'); });
  const deadline = Date.now() + 1000;
  while (!(await readdir(f.dir)).includes('result.json.claim') && Date.now() < deadline) {
    await new Promise(resolve => setTimeout(resolve, 10));
  }
  assert.ok((await readdir(f.dir)).includes('result.json.claim'));
  run.child.kill('SIGTERM');
  assert.equal((await run.done).signal, 'SIGTERM');
  assert.deepEqual((await readdir(f.dir)).sort(), ['config.json', 'result.json.claim']);
});

test('configuration larger than its acquisition ceiling produces no run artifacts', async t => {
  const f = await fixture(t);
  await writeFile(join(f.dir, 'config.json'), ' '.repeat(32769));
  const run = start(f); run.child.stdin.end(JSON.stringify(event()));
  assert.equal((await run.done).code, 1);
  assert.deepEqual(await readdir(f.dir), ['config.json']);
});

test('unbound optional fields preserve gaps and omit oversized values', async t => {
  const f = await fixture(t, { expectedCodeId: null });
  const input = event(); input.cwd = 'x'.repeat(4097); delete input.permission_mode;
  const { record } = await collect(f, JSON.stringify(input));
  assert.deepEqual(record.unbound.eventFields, {});
  assert.deepEqual(record.unbound.gaps, ['cwd_oversized', 'permission_mode_missing']);
  assert.equal(record.projection.status, 'unknown');
  assert.equal(record.responseCandidate, null);
});

test('a served Stop cannot supply an ordinary disposable fixture identity', async t => {
  for (const expectedCodeId of [null, 'served:caller']) {
    const f = await fixture(t, { expectedCodeId });
    const { record } = await collect(f, JSON.stringify({ ...event(), session_id: 'served:caller' }));
    assert.equal(record.unbound, null);
    assert.equal(record.responseCandidate, null);
    assert.equal(record.endpoint, null);
    assert.ok(record.gaps.includes('served_session_not_fixture'));
  }
});
