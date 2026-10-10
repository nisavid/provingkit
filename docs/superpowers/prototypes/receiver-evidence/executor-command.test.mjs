import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn, spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdtemp, mkdir, writeFile, readFile, rm, symlink, open } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const command = fileURLToPath(new URL('./collector.mjs', import.meta.url));
const executable = Buffer.from('\x7fELFsynthetic-native-executable');
const digest = createHash('sha256').update(executable).digest('hex');
const event = { hook_event_name: 'Stop', session_id: 'fixture-code',
  last_assistant_message: 'FIXTURE run-1' };
function statLine(pid, parent, start = '12345') {
  const fields = Array(20).fill('0');
  fields[0] = 'S'; fields[1] = String(parent); fields[19] = start;
  return `${pid} (test ) command) ${fields.join(' ')}\n`;
}
async function fixture(t, changes = {}, env = {}, configChanges = {}) {
  const dir = await mkdtemp(join(tmpdir(), 'executor-command-'));
  t.after(() => rm(dir, { recursive: true, force: true }));
  const procRoot = join(dir, 'proc'); await mkdir(procRoot);
  const config = { schema: 1, runId: 'run-1', expectedCodeId: 'fixture-code',
    expectedFinalText: 'FIXTURE run-1', since: Date.now() - 10000,
    maxInputBytes: 65536, inputTimeoutMs: 1000,
    executorObservation: { processRoot: procRoot, maxExecutableBytes: 1024,
      timeoutMs: 2000, expectedSha256: digest, executorKind: 'native', ...changes }, ...configChanges };
  await writeFile(join(dir, 'config.json'), JSON.stringify(config));
  const child = spawn(process.execPath, [command, '--config', join(dir, 'config.json'),
    '--output', join(dir, 'result.json')], { env: {
      CLAUDE_PID: '1001', CLAUDE_CODE_SESSION_ID: 'fixture-code', ...env },
    stdio: ['pipe', 'pipe', 'pipe'] });
  child.stdin.on('error', () => {});
  let stderr = ''; child.stderr.on('data', x => { stderr += x; });
  const done = new Promise((resolve, reject) => {
    child.on('error', reject); child.on('close', code => resolve({ code, stderr }));
  });
  async function processFile(pid, parent, start) {
    await mkdir(join(procRoot, String(pid)), { recursive: true });
    await writeFile(join(procRoot, String(pid), 'stat'), statLine(pid, parent, start));
  }
  await processFile(child.pid, 1001);
  await processFile(1001, 1);
  const binary = join(dir, 'binary'); await writeFile(binary, executable);
  await symlink(binary, join(procRoot, '1001', 'exe'));
  async function finish(input = event) {
    child.stdin.end(JSON.stringify(input)); const result = await done;
    const record = result.code === 0 ? JSON.parse(await readFile(join(dir, 'result.json'), 'utf8')) : null;
    return { ...result, record };
  }
  return { dir, procRoot, child, binary, processFile, finish };
}

test('the command observes its claimed ancestor and the opened executable near Stop', async t => {
  const f = await fixture(t); const { code, record } = await f.finish();
  assert.equal(code, 0);
  assert.equal(record.qualification, 'unqualified');
  assert.equal(record.executorObservation.status, 'observed');
  assert.equal(record.executorObservation.comparison, 'matches_configured_identity');
  assert.equal(record.executorObservation.executable.sha256, digest);
  assert.equal(record.executorObservation.executable.bytesObserved, executable.length);
  assert.deepEqual(record.executorObservation.processes.map(x => x.pid), [f.child.pid, 1001]);
  assert.equal(record.responseCandidate.text, 'FIXTURE run-1');
  assert.deepEqual(record.hostTaskNomination, { status: 'unknown', gap: 'host_id_missing' });
});

test('a PID outside the collector ancestry leaves the Stop response intact', async t => {
  const f = await fixture(t); await f.processFile(f.child.pid, 1);
  const { code, record } = await f.finish();
  assert.equal(code, 0);
  assert.equal(record.executorObservation.status, 'incomplete');
  assert.equal(record.executorObservation.reason, 'claimed_pid_not_ancestor');
  assert.equal(record.executorObservation.executable, undefined);
  assert.equal(record.responseCandidate.text, 'FIXTURE run-1');
});

test('only an admitted Stop with consistent hook identity starts process acquisition', async t => {
  for (const [env, input, hostStatus] of [
    [{ CLAUDE_PID: '' }, event, 'candidate'],
    [{ CLAUDE_PID: '1001x' }, event, 'candidate'],
    [{ CLAUDE_CODE_SESSION_ID: 'other' }, event, 'unknown'],
    [{}, { ...event, session_id: 'other' }, 'unknown'],
    [{}, { ...event, hook_event_name: 'Notification' }, 'unknown'],
    [{}, { ...event, last_assistant_message: 'unrelated response' }, 'unknown'],
  ]) {
    const f = await fixture(t, {}, { CLAUDE_CODE_HOST_SESSION_ID: 'desktop-local-7', ...env });
    await rm(f.procRoot, { recursive: true });
    const { code, record } = await f.finish(input);
    assert.equal(code, 0);
    assert.equal(record.executorObservation.status, 'not_admitted');
    assert.equal(record.executorObservation.processes, undefined);
    assert.equal(record.hostTaskNomination.status, hostStatus);
  }
});

test('ancestry stops at six processes and never follows a cycle', async t => {
  const f = await fixture(t); await f.processFile(f.child.pid, 2001);
  for (let pid = 2001; pid <= 2005; pid++) await f.processFile(pid, pid === 2005 ? 1001 : pid + 1);
  const limited = await f.finish();
  assert.equal(limited.code, 0);
  assert.equal(limited.record.executorObservation.reason, 'ancestry_limit');
  assert.equal(limited.record.executorObservation.processes.length, 6);
  assert.equal(limited.record.executorObservation.executable, undefined);
  const cycle = await fixture(t); await cycle.processFile(cycle.child.pid, 2001);
  await cycle.processFile(2001, cycle.child.pid);
  const cyclic = await cycle.finish();
  assert.equal(cyclic.record.executorObservation.reason, 'ancestry_cycle');
  assert.equal(cyclic.record.executorObservation.processes.length, 2);
});

test('malformed or oversized process records cannot establish identity', async t => {
  for (const [line, reason] of [
    [statLine(999, 1), 'invalid_process_record'],
    ['1001 (short) S 1 0\n', 'invalid_process_record'],
    ['x'.repeat(8193), 'process_record_over_limit'],
  ]) {
    const f = await fixture(t); await writeFile(join(f.procRoot, '1001', 'stat'), line);
    const { code, record } = await f.finish();
    assert.equal(code, 0);
    assert.equal(record.executorObservation.reason, reason);
    assert.equal(record.executorObservation.executable, undefined);
  }
});

test('executable overflow retains partial acquisition without publishing a digest', async t => {
  for (const ceiling of [1, 2, 8]) {
    const f = await fixture(t, { maxExecutableBytes: ceiling });
    const { code, record } = await f.finish();
    assert.equal(code, 0);
    assert.equal(record.executorObservation.status, 'incomplete');
    assert.equal(record.executorObservation.reason, 'executable_over_limit');
    assert.equal(record.executorObservation.executable.bytesObserved, ceiling + 1);
    assert.equal(record.executorObservation.executable.sha256, undefined);
    assert.equal(record.responseCandidate.text, 'FIXTURE run-1');
  }
});

test('a replaced process identity invalidates the observation after acquisition', async t => {
  const f = await fixture(t); const path = join(f.procRoot, '1001', 'stat');
  await rm(path); assert.equal(spawnSync('mkfifo', [path]).status, 0);
  const replacement = (async () => {
    const writer = await open(path, 'w');
    await writer.writeFile(statLine(1001, 1, '12345'));
    await rm(path); await writeFile(path, statLine(1001, 1, '67890'));
    await writer.close();
  })();
  const { code, record } = await f.finish(); await replacement;
  assert.equal(code, 0);
  assert.equal(record.executorObservation.status, 'incomplete');
  assert.equal(record.executorObservation.reason, 'process_identity_changed');
  assert.equal(record.executorObservation.executable, undefined);
  assert.equal(record.responseCandidate.text, 'FIXTURE run-1');
});

test('the observation deadline preserves Stop and ends the owned reader', async t => {
  const f = await fixture(t, { timeoutMs: 100 });
  const path = join(f.procRoot, '1001', 'stat'); await rm(path);
  assert.equal(spawnSync('mkfifo', [path]).status, 0);
  const emergency = setTimeout(() => f.child.kill('SIGKILL'), 2000);
  const { code, record } = await f.finish(); clearTimeout(emergency);
  assert.equal(code, 0);
  assert.equal(record.executorObservation.status, 'incomplete');
  assert.equal(record.executorObservation.reason, 'observation_timeout');
  assert.equal(record.executorObservation.worker.cleanup, 'exit_observed');
  assert.throws(() => process.kill(record.executorObservation.worker.pid, 0), /ESRCH/);
  assert.equal(record.responseCandidate.text, 'FIXTURE run-1');
});

test('interpreter and non-ELF inputs remain gaps while changed native bytes are unassessed', async t => {
  const interpreter = await fixture(t, { executorKind: 'interpreter' });
  const ignored = await interpreter.finish();
  assert.equal(ignored.record.executorObservation.reason, 'interpreter_executor_unsupported');
  const script = await fixture(t); await writeFile(script.binary, '#!/bin/sh\n');
  const rejected = await script.finish();
  assert.equal(rejected.record.executorObservation.reason, 'native_executable_required');
  const changed = await fixture(t); await writeFile(changed.binary, Buffer.concat([executable, Buffer.from('new build')]));
  const observed = await changed.finish();
  assert.equal(observed.record.executorObservation.status, 'observed');
  assert.equal(observed.record.executorObservation.comparison, 'unassessed');
  assert.equal(observed.record.qualification, 'unqualified');
});

test('the observed result retains both endpoint samples and rejects an empty image', async t => {
  const f = await fixture(t); const { record } = await f.finish();
  assert.equal(record.executorObservation.afterProcesses.length, 2);
  assert.equal(record.executorObservation.afterProcesses[1].startTimeTicks, '12345');
  assert.ok(record.executorObservation.processes[1].completedAt <= record.executorObservation.afterProcesses[1].startedAt);
  assert.equal(record.executorObservation.executable.before.ino, record.executorObservation.executable.after.ino);
  const empty = await fixture(t); await writeFile(empty.binary, '');
  const result = await empty.finish();
  assert.equal(result.record.executorObservation.reason, 'native_executable_required');
});

test('initial unbound collection may observe the executor without binding the task', async t => {
  const f = await fixture(t, {}, { CLAUDE_CODE_HOST_SESSION_ID: 'desktop-local-7' }, { expectedCodeId: null });
  const { code, record } = await f.finish();
  assert.equal(code, 0);
  assert.equal(record.executorObservation.status, 'observed');
  assert.equal(record.binding, 'unbound');
  assert.equal(record.responseCandidate, null);
  assert.equal(record.unbound.observedHookSessionId, 'fixture-code');
  assert.equal(record.hostTaskNomination.filename, 'desktop-local-7.json');
  assert.equal(record.hostTaskNomination.status, 'candidate');
  assert.ok(record.gaps.includes('independent_task_binding_required'));
});

test('the public command acquires the ancestry and image of a controlled Linux child', async t => {
  const dir = await mkdtemp(join(tmpdir(), 'executor-owned-linux-'));
  t.after(() => rm(dir, { recursive: true, force: true }));
  const expectedSha256 = createHash('sha256').update(await readFile(process.execPath)).digest('hex');
  const configPath = join(dir, 'config.json'), outputPath = join(dir, 'result.json');
  await writeFile(configPath, JSON.stringify({ schema: 1, runId: 'run-1', expectedCodeId: null,
    expectedFinalText: 'FIXTURE run-1', since: Date.now() - 10000, maxInputBytes: 65536,
    inputTimeoutMs: 1000, executorObservation: { processRoot: '/proc', maxExecutableBytes: 268435456,
      timeoutMs: 30000, expectedSha256, executorKind: 'native' } }));
  // This owned native Node image exercises /proc mechanics, not Code role classification.
  const wrapper = spawn(process.execPath, ['--input-type=module', '--eval', `
    import { spawn } from 'node:child_process';
    const [command, config, output, input] = process.argv.slice(1);
    const child = spawn(process.execPath, [command, '--config', config, '--output', output], {
      env: { CLAUDE_PID: String(process.pid), CLAUDE_CODE_SESSION_ID: 'fixture-code' },
      stdio: ['pipe', 'ignore', 'inherit'] });
    child.stdin.end(input);
    child.on('close', code => { console.log(JSON.stringify({ code, pid: process.pid, collectorPid: child.pid })); });
  `, command, configPath, outputPath, JSON.stringify(event)], { env: {}, stdio: ['ignore', 'pipe', 'pipe'] });
  t.after(() => { if (wrapper.exitCode === null && wrapper.signalCode === null) wrapper.kill('SIGKILL'); });
  let stdout = '', stderr = ''; wrapper.stdout.on('data', x => { stdout += x; });
  wrapper.stderr.on('data', x => { stderr += x; });
  await new Promise((resolve, reject) => { wrapper.on('error', reject); wrapper.on('close', resolve); });
  const result = JSON.parse(stdout); assert.equal(result.code, 0, stderr);
  const record = JSON.parse(await readFile(outputPath, 'utf8'));
  assert.equal(record.executorObservation.status, 'observed');
  assert.equal(record.executorObservation.executable.sha256, expectedSha256);
  assert.deepEqual(record.executorObservation.processes.map(x => x.pid), [result.collectorPid, result.pid]);
  assert.equal(record.executorObservation.comparison, 'matches_configured_identity');
  assert.equal(record.binding, 'unbound');
});

test('a vanished process preserves the complete Stop as partial evidence', async t => {
  const f = await fixture(t); await rm(join(f.procRoot, '1001', 'stat'));
  const { code, record } = await f.finish();
  assert.equal(code, 0);
  assert.equal(record.executorObservation.status, 'incomplete');
  assert.equal(record.executorObservation.reason, 'process_or_executable_unavailable');
  assert.equal(record.responseCandidate.text, 'FIXTURE run-1');
});

test('configuration cannot widen the accepted executable or deadline ceilings', async t => {
  for (const changes of [{ maxExecutableBytes: 268435457 }, { timeoutMs: 30001 },
    { maxExecutableBytes: 0 }, { processRoot: 'relative' }, { extra: true }]) {
    const f = await fixture(t, changes); const { code } = await f.finish();
    assert.equal(code, 1);
    await assert.rejects(readFile(join(f.dir, 'result.json.claim')), { code: 'ENOENT' });
  }
});
