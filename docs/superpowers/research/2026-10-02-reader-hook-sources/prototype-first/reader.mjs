// Synthetic/source experiment. The caller supplies all binding and timing evidence.
export function inspectRecords(input) {
  input ??= {};
  const bounded = (x, max) => typeof x === 'string' && x.length > 0 && x.length <= max;
  const assessment = input.compatibility;
  const compatibility = { status: ['unassessed', 'assessed', 'incompatible'].includes(assessment?.status) ? assessment.status : 'unassessed' };
  for (const key of ['build', 'evidence']) if (bounded(assessment?.[key], 1024)) compatibility[key] = assessment[key];
  const result = {
    status: 'unknown', qualification: 'unqualified',
    compatibility,
    notices: [], acknowledgments: [], gaps: [],
  };
  if (result.compatibility.status === 'incompatible') {
    return { ...result, status: 'unsupported', gaps: ['incompatible_interpretation'] };
  }
  if (![input.expected?.desktopId, input.expected?.codeId, input.request?.senderTaskId,
    input.request?.correlationId].every(x => bounded(x, 256))
      || ![input.request?.noticeText, input.request?.ackText].every(x => bounded(x, 4096))) {
    return { ...result, gaps: ['invalid_binding_or_rule'] };
  }
  if (typeof input.transcript === 'string' && new TextEncoder().encode(input.transcript).length > 1048576) {
    return { ...result, gaps: ['interpretation_limit'] };
  }
  if (!input.capture || ![input.capture.startedAt, input.capture.finishedAt,
    input.now, input.maxAgeMs, input.request?.since].every(Number.isFinite)
      || input.capture.startedAt > input.capture.finishedAt
      || input.capture.finishedAt > input.now || input.maxAgeMs < 0) {
    return { ...result, gaps: ['invalid_capture'] };
  }
  if (input.now - input.capture.finishedAt > input.maxAgeMs) {
    return { ...result, gaps: ['stale_capture'] };
  }
  result.capture = { startedAt: input.capture.startedAt, finishedAt: input.capture.finishedAt };
  if (input.metadata?.sessionId !== input.expected?.desktopId
      || input.metadata?.cliSessionId !== input.expected?.codeId) {
    return { ...result, gaps: ['identity_mismatch'] };
  }
  if (typeof input.transcript !== 'string'
      || (input.transcript && !input.transcript.endsWith('\n'))) {
    return { ...result, gaps: ['incomplete_transcript'] };
  }
  let rows;
  try {
    rows = input.transcript ? input.transcript.slice(0, -1).split('\n').map(JSON.parse) : [];
  } catch {
    return { ...result, gaps: ['malformed_transcript'] };
  }
  const seen = new Set();
  for (const row of rows) {
    if (!row || Array.isArray(row) || row.sessionId !== input.expected.codeId
        || !bounded(row.uuid, 256) || seen.has(row.uuid)
        || !['user', 'assistant'].includes(row.type) || row.message?.role !== row.type) {
      return { ...result, gaps: ['inconsistent_records'] };
    }
    seen.add(row.uuid);
  }
  for (const [index, row] of rows.entries()) {
    if (row.isMeta || row.isCompactSummary || row.isSidechain || row.parent_tool_use_id) {
      if (!result.gaps.includes('non_main_record_excluded')) result.gaps.push('non_main_record_excluded');
      continue;
    }
    const timestamp = Date.parse(row.timestamp);
    if (!bounded(row.timestamp, 64) || !Number.isFinite(timestamp) || timestamp < input.request.since
        || timestamp > input.capture.finishedAt) {
      if (!result.gaps.includes('record_time_missing_or_outside_window')) result.gaps.push('record_time_missing_or_outside_window');
      continue;
    }
    const content = row.message.content;
    const text = typeof content === 'string' ? content
      : Array.isArray(content) && content.every(b => b?.type === 'text' && typeof b.text === 'string')
        ? content.map(b => b.text).join('\n') : undefined;
    const candidate = { id: row.uuid, index, timestamp: row.timestamp, text };
    if (row.type === 'user' && row.origin?.kind === 'peer'
        && row.origin.senderTaskId === input.request.senderTaskId
        && text === input.request.noticeText) {
      result.notices.push({ ...candidate, origin: {
        kind: row.origin.kind, senderTaskId: row.origin.senderTaskId,
      } });
    }
    if (row.type === 'assistant' && text === input.request.ackText) {
      result.acknowledgments.push(candidate);
    }
  }
  if (result.notices.length && result.acknowledgments.length) {
    result.status = result.acknowledgments.some(a => result.notices.some(n => n.index < a.index
      && Date.parse(n.timestamp) <= Date.parse(a.timestamp))) ? 'candidate_pair' : 'unpaired_candidates';
  } else if (result.notices.length || result.acknowledgments.length) result.status = 'partial_candidates';
  else result.gaps.push('no_matching_records');
  return result;
}
