import { open, writeFile, link, unlink } from 'node:fs/promises';
import { writeSync } from 'node:fs';
import { Socket } from 'node:net';
import { projectStop } from './hook.mjs';
import { observeExecutor } from './executor.mjs';

const text = (value, max) => typeof value === 'string' && value.length > 0 && value.length <= max;

async function readConfig(path) {
  const file = await open(path, 'r');
  try {
    if (!(await file.stat()).isFile()) throw new Error('config_not_regular');
    const buffer = Buffer.alloc(32769);
    let size = 0;
    while (size < buffer.length) {
      const { bytesRead } = await file.read(buffer, size, buffer.length - size, null);
      if (!bytesRead) break;
      size += bytesRead;
    }
    if (size > 32768) throw new Error('config_oversized');
    const c = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(buffer.subarray(0, size)));
    if (!c || Array.isArray(c) || c.schema !== 1 || !text(c.runId, 256)
        || !(c.expectedCodeId === null || text(c.expectedCodeId, 256))
        || !text(c.expectedFinalText, 4096) || !Number.isSafeInteger(c.since) || c.since < 0
        || !Number.isInteger(c.maxInputBytes) || c.maxInputBytes < 1 || c.maxInputBytes > 1048576
        || !Number.isInteger(c.inputTimeoutMs) || c.inputTimeoutMs < 10 || c.inputTimeoutMs > 60000
        || Object.keys(c).some(key => !['schema', 'runId', 'expectedCodeId', 'expectedFinalText',
          'since', 'maxInputBytes', 'inputTimeoutMs', 'executorObservation'].includes(key))) throw new Error('invalid_config');
    if (c.executorObservation !== undefined) {
      const x = c.executorObservation;
      if (!x || Array.isArray(x) || typeof x.processRoot !== 'string' || !x.processRoot.startsWith('/')
          || !Number.isInteger(x.maxExecutableBytes) || x.maxExecutableBytes < 1 || x.maxExecutableBytes > 268435456
          || !Number.isInteger(x.timeoutMs) || x.timeoutMs < 10 || x.timeoutMs > 30000
          || !/^[a-f0-9]{64}$/.test(x.expectedSha256) || !['native', 'interpreter'].includes(x.executorKind)
          || Object.keys(x).some(key => !['processRoot', 'maxExecutableBytes', 'timeoutMs', 'expectedSha256', 'executorKind'].includes(key))) {
        throw new Error('invalid_executor_config');
      }
    }
    return c;
  } finally { await file.close(); }
}

async function publish(path, record) {
  const bytes = Buffer.from(JSON.stringify(record) + '\n');
  if (bytes.length > 65536) throw new Error('output_oversized');
  const partial = path + '.partial';
  const file = await open(partial, 'wx', 0o600);
  try {
    await file.writeFile(bytes);
    await file.sync();
    await file.close();
    // link publishes completed bytes without replacing an existing record.
    await link(partial, path);
  } finally {
    await file.close();
    await unlink(partial);
  }
}

function readInput(limit, timeoutMs) {
  const bytes = Buffer.alloc(limit + 1);
  return new Promise(resolve => {
    let size = 0, done = false;
    const finish = (status, eof = false) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      socket.destroy();
      resolve({ bytes: Buffer.from(bytes.subarray(0, size)), acquisition: {
        bytesObserved: size, byteLimit: limit, eof, status } });
    };
    // Wrap this command's inherited pipe, without connecting to any endpoint.
    // onread supplies the actual read buffer, including the one overflow byte.
    const socket = new Socket({ fd: 0, readable: true, writable: false,
      onread: {
        buffer: () => bytes.subarray(size, Math.min(bytes.length, size + 4096)),
        callback: count => {
          size += count;
          if (size > limit) { finish('over_limit'); return false; }
          return true;
        },
      } });
    const timer = setTimeout(() => finish('timeout'), timeoutMs);
    socket.on('end', () => finish('complete', true));
    socket.on('error', () => finish('input_error'));
    socket.on('close', () => finish('input_error'));
    socket.resume();
  });
}

async function main() {
  const [, , configFlag, configPath, outputFlag, outputPath] = process.argv;
  if (process.argv.length !== 6 || configFlag !== '--config' || outputFlag !== '--output' || !configPath || !outputPath) {
    throw new Error('invalid_command');
  }
  const config = await readConfig(configPath);
  // Keep this one-shot claim through success or failure. Reuse requires a new
  // reviewed run slot; automatic retries must not acquire another whole event.
  await writeFile(outputPath + '.claim', JSON.stringify({ runId: config.runId, pid: process.pid }) + '\n',
    { flag: 'wx', mode: 0o600 });
  const receivedAt = Date.now();
  const { bytes, acquisition } = await readInput(config.maxInputBytes, config.inputTimeoutMs);
  let event = {}, invalidInput = false;
  if (acquisition.status === 'complete') {
    try {
      event = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
      if (!event || typeof event !== 'object' || Array.isArray(event)) throw new Error('event_shape');
    } catch { event = {}; invalidInput = true; }
  }
  const completedAt = Date.now();
  const validWindow = receivedAt >= config.since && completedAt >= receivedAt;
  const served = typeof event.session_id === 'string' && event.session_id.startsWith('served:');
  const { acknowledgment: matchingText, ...projection } = projectStop({ event: served ? {} : event, expectedCodeId: config.expectedCodeId,
    ackText: config.expectedFinalText, correlationId: config.runId,
    since: config.since, capture: { receivedAt, now: completedAt, maxAgeMs: config.inputTimeoutMs },
    collector: { interrupted: acquisition.status !== 'complete' } });
  const record = { schema: 1, runId: config.runId, qualification: 'unqualified',
    binding: config.expectedCodeId === null ? 'unbound' : 'configured_code_id_only', projection,
    purpose: 'fixture_stop_check',
    responseCandidate: matchingText ? { text: matchingText.text, runId: matchingText.correlationId } : null,
    endpoint: process.env.CLAUDE_CODE_MESSAGING_SOCKET ?? null,
    acquisition,
    capture: { startedAt: receivedAt, completedAt, notBefore: config.since },
    gaps: ['independent_task_binding_required', 'selected_executor_unobserved'],
    unbound: null };
  if (typeof record.endpoint !== 'string' || record.endpoint.length === 0 || record.endpoint.length > 4096) {
    record.endpoint = null; record.gaps.push('endpoint_missing_or_oversized');
  }
  if (invalidInput) record.gaps.push('invalid_event_input');
  if (config.expectedCodeId !== null && (served || event.session_id !== config.expectedCodeId || event.hook_event_name !== 'Stop')) {
    record.binding = 'mismatch'; record.endpoint = null;
  }
  if (!validWindow) record.gaps.push('invalid_capture_window');
  if (served) record.gaps.push('served_session_not_fixture');
  if (config.expectedCodeId === null && !served && validWindow && acquisition.status === 'complete'
      && event.hook_event_name === 'Stop'
      && typeof event.session_id === 'string' && event.session_id.length > 0
      && event.session_id.length <= 256 && event.last_assistant_message === config.expectedFinalText) {
    record.unbound = { observedHookSessionId: event.session_id, matchingFinalText: config.expectedFinalText,
      eventFields: {}, gaps: [] };
    for (const [key, output, max] of [['cwd', 'cwd', 4096], ['permission_mode', 'permissionMode', 128]]) {
      if (text(event[key], max)) record.unbound.eventFields[output] = event[key];
      else record.unbound.gaps.push(`${key}_${typeof event[key] === 'string' && event[key].length > max ? 'oversized' : 'missing'}`);
    }
  }
  if (!validWindow || (config.expectedCodeId === null && !record.unbound)) record.endpoint = null;
  const admittedStop = validWindow && acquisition.status === 'complete' && !served
    && event.hook_event_name === 'Stop' && (!!record.responseCandidate || !!record.unbound)
    && record.binding !== 'mismatch' && text(event.session_id, 256)
    && process.env.CLAUDE_CODE_SESSION_ID === event.session_id;
  record.hostTaskNomination = { status: 'unknown', gap: 'matching_stop_and_hook_identity_required' };
  if (admittedStop) {
    const hostId = process.env.CLAUDE_CODE_HOST_SESSION_ID;
    record.hostTaskNomination = hostId === undefined
      ? { status: 'unknown', gap: 'host_id_missing' }
      : hostId.length > 250
        ? { status: 'unknown', gap: 'host_id_oversized' }
        : !/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(hostId)
          ? { status: 'unknown', gap: 'host_id_invalid' }
          : { status: 'candidate', desktopSessionId: hostId,
            filename: `${hostId}.json`, source: 'CLAUDE_CODE_HOST_SESSION_ID' };
  }
  if (config.executorObservation) {
    const claimedPid = process.env.CLAUDE_PID;
    const admitted = admittedStop
      && typeof claimedPid === 'string' && /^[1-9][0-9]{0,9}$/.test(claimedPid)
      && Number.isSafeInteger(Number(claimedPid)) && Number(claimedPid) !== process.pid;
    record.executorObservation = admitted
      ? await observeExecutor(config.executorObservation, process.pid, Number(claimedPid))
      : { status: 'not_admitted', reason: 'matching_stop_and_hook_identity_required' };
  }
  await publish(outputPath, record);
}

main().catch(() => {
  try { writeSync(2, 'Collector did not confirm completion; inspect the run files.\n'); } catch {}
  process.exitCode = 1;
});
