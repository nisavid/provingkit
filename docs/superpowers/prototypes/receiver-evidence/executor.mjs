import { open, stat } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { join } from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

export function observeExecutor(config, collectorPid, claimedPid) {
  const startedAt = Date.now();
  return new Promise(resolve => {
    const child = spawn(process.execPath, [fileURLToPath(new URL('./executor-worker.mjs', import.meta.url)),
      JSON.stringify({ config, collectorPid, claimedPid })], { env: {}, stdio: ['ignore', 'pipe', 'ignore'] });
    let bytes = Buffer.alloc(0), failure = null, finished = false, cleanupTimer;
    const finish = (code, signal, cleanup) => {
      if (finished) return;
      finished = true; clearTimeout(timer); clearTimeout(cleanupTimer);
      child.stdout.destroy(); child.unref();
      let result;
      if (!failure && code === 0) {
        try { result = JSON.parse(bytes.toString('utf8')); } catch { failure = 'invalid_observation_output'; }
      }
      if (!result) result = { status: 'incomplete', reason: failure ?? 'observation_worker_failed',
        startedAt, completedAt: Date.now() };
      result.worker = { pid: child.pid ?? null, cleanup, code, signal };
      resolve(result);
    };
    const stop = reason => {
      if (finished || failure) return;
      failure = reason;
      child.kill('SIGKILL');
      // Never make collector completion depend on a stuck observation reader.
      cleanupTimer = setTimeout(() => finish(null, null, 'exit_unconfirmed'), 100);
    };
    const timer = setTimeout(() => stop('observation_timeout'), config.timeoutMs);
    child.stdout.on('data', chunk => {
      if (bytes.length + chunk.length > 16384) stop('observation_output_over_limit');
      else bytes = Buffer.concat([bytes, chunk]);
    });
    child.on('error', () => { failure ??= 'observation_worker_failed'; finish(null, null, 'spawn_or_signal_error'); });
    child.on('close', (code, signal) => finish(code, signal, 'exit_observed'));
  });
}

async function readProcess(root, pid) {
  const startedAt = Date.now();
  const file = await open(join(root, String(pid), 'stat'), 'r');
  try {
    const buffer = Buffer.alloc(8193);
    let size = 0;
    while (size < buffer.length) {
      const { bytesRead } = await file.read(buffer, size, buffer.length - size, null);
      if (!bytesRead) break;
      size += bytesRead;
    }
    if (size > 8192) throw new Error('process_record_over_limit');
    const line = new TextDecoder('utf-8', { fatal: true }).decode(buffer.subarray(0, size));
    const close = line.lastIndexOf(')');
    const fields = line.slice(close + 2).trim().split(/\s+/);
    if (!line.startsWith(`${pid} (`) || close < line.indexOf('(') || line[close + 1] !== ' '
        || !/^[A-Za-z]$/.test(fields[0]) || !/^[0-9]{1,10}$/.test(fields[1])
        || !/^[0-9]{1,20}$/.test(fields[19])) throw new Error('invalid_process_record');
    return { pid, parentPid: Number(fields[1]), startTimeTicks: fields[19], bytesObserved: size,
      startedAt, completedAt: Date.now() };
  } finally { await file.close(); }
}

export async function sampleExecutor(config, collectorPid, claimedPid) {
  const startedAt = Date.now();
  const processes = [];
  try {
    if (config.executorKind === 'interpreter') throw new Error('interpreter_executor_unsupported');
    let pid = collectorPid;
    for (let count = 0; count < 6; count++) {
      if (processes.some(record => record.pid === pid)) throw new Error('ancestry_cycle');
      const record = await readProcess(config.processRoot, pid); processes.push(record);
      if (pid === Number(claimedPid)) break;
      if (record.parentPid <= 1) throw new Error('claimed_pid_not_ancestor');
      pid = record.parentPid;
    }
    if (processes.at(-1)?.pid !== claimedPid) throw new Error('ancestry_limit');
    const executablePath = join(config.processRoot, String(claimedPid), 'exe');
    const pathBefore = await stat(executablePath, { bigint: true });
    const file = await open(executablePath, 'r');
    try {
      const before = await file.stat({ bigint: true });
      if (!before.isFile()) throw new Error('native_executable_required');
      const hash = createHash('sha256'), buffer = Buffer.alloc(65536), header = Buffer.alloc(4);
      let size = 0;
      while (size <= config.maxExecutableBytes) {
        const { bytesRead } = await file.read(buffer, 0, Math.min(buffer.length, config.maxExecutableBytes + 1 - size), null);
        if (!bytesRead) break;
        if (size < 4) buffer.copy(header, size, 0, Math.min(bytesRead, 4 - size));
        size += bytesRead; hash.update(buffer.subarray(0, bytesRead));
      }
      if (size > config.maxExecutableBytes) return { status: 'incomplete', reason: 'executable_over_limit',
        startedAt, completedAt: Date.now(), processes, executable: { bytesObserved: size, eof: false } };
      if (size < 4 || !header.equals(Buffer.from('\x7fELF'))) throw new Error('native_executable_required');
      const after = await file.stat({ bigint: true });
      const pathAfter = await stat(executablePath, { bigint: true });
      const afterProcesses = [];
      for (const record of processes) {
        const observed = await readProcess(config.processRoot, record.pid);
        afterProcesses.push(observed);
        if (record.parentPid !== observed.parentPid || record.startTimeTicks !== observed.startTimeTicks) {
          throw new Error('process_identity_changed');
        }
      }
      if (['dev', 'ino', 'size', 'mtimeNs', 'ctimeNs'].some(key =>
        before[key] !== after[key] || before[key] !== pathBefore[key] || before[key] !== pathAfter[key])) {
        throw new Error('executable_identity_changed');
      }
      const sha256 = hash.digest('hex');
      const identity = value => Object.fromEntries(['dev', 'ino', 'size', 'mtimeNs', 'ctimeNs']
        .map(key => [key, String(value[key])]));
      return { status: 'observed', startedAt, completedAt: Date.now(), processes, afterProcesses,
        comparison: sha256 === config.expectedSha256 ? 'matches_configured_identity' : 'unassessed',
        executable: { bytesObserved: size, sha256, eof: true, before: identity(before), after: identity(after) } };
    } finally { await file.close(); }
  } catch (error) {
    return { status: 'incomplete', reason: ['claimed_pid_not_ancestor', 'ancestry_limit', 'ancestry_cycle',
      'invalid_process_record', 'process_record_over_limit', 'process_identity_changed',
      'executable_identity_changed', 'interpreter_executor_unsupported', 'native_executable_required'].includes(error.message)
      ? error.message : 'process_or_executable_unavailable', startedAt, completedAt: Date.now(), processes };
  }
}
