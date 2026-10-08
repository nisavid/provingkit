// Source/synthetic prototype. Witnesses are supplied assertions, not authenticated evidence.
const text = (value, limit) => typeof value === 'string' && value.length > 0 && value.length <= limit && !value.includes('\0');
export function metadataComplete(metadata, projectField) {
  return text(metadata?.sessionId, 250) && text(metadata?.cliSessionId, 256) && text(metadata?.[projectField], 4096);
}
export function admitFixtureWitness(request, now) {
  const ui = request.uiWitness;
  if (!ui || ui.runId !== request.runId || ui.selectedTask !== true
      || !['cwd', 'originCwd'].includes(ui.projectField)
      || !text(ui.projectPath, 4096) || !ui.projectPath.startsWith('/')
      || !text(ui.setupText, 4096) || !text(ui.displayedText, 4096)) return ['ui_witness_incomplete'];
  const stop = request.stopRecord;
  if (!stop || stop.schema !== 1 || stop.runId !== request.runId || stop.purpose !== 'fixture_stop_check'
      || stop.binding !== 'unbound' || stop.acquisition?.status !== 'complete' || stop.acquisition.eof !== true
      || typeof stop.unbound?.observedHookSessionId !== 'string' || !stop.unbound.observedHookSessionId
      || stop.unbound.observedHookSessionId.length > 256 || stop.unbound.observedHookSessionId.startsWith('served:')) {
    return ['stop_record_incomplete'];
  }
  const u = ui.capture, s = stop.capture;
  if (!u || !s || ![request.since, request.maxJoinAgeMs, u.startedAt, u.finishedAt,
    s.startedAt, s.completedAt, s.notBefore, now].every(Number.isSafeInteger)
      || request.since < 0 || request.maxJoinAgeMs < 0 || u.startedAt < request.since
      || u.finishedAt < u.startedAt || u.finishedAt > now || s.startedAt < request.since
      || s.notBefore < 0 || s.startedAt < s.notBefore || s.completedAt < s.startedAt || s.completedAt > now) {
    return ['invalid_join_window'];
  }
  if (!Number.isSafeInteger(ui.recheckedAt) || ui.recheckedAt < Math.max(u.finishedAt, s.completedAt)
      || ui.recheckedAt > now) return ['selection_recheck_incomplete'];
  if (now - Math.min(u.startedAt, s.startedAt) > request.maxJoinAgeMs) return ['stale_evidence'];
  if (ui.displayedText !== ui.setupText || ui.setupText !== stop.unbound.matchingFinalText) return ['setup_response_mismatch'];
  return [];
}
export function associateSnapshots(request, snapshots, now) {
  const admission = admitFixtureWitness(request, now);
  if (admission.length) return { status: 'unknown', gaps: admission, association: null };
  const ui = request.uiWitness;
  if (snapshots.some(({ metadata }) => !metadataComplete(metadata, ui.projectField))) {
    return { status: 'unknown', gaps: ['metadata_incomplete'], association: null };
  }
  const codeId = request.stopRecord.unbound.observedHookSessionId;
  const matches = snapshots.filter(({ name, metadata }) => text(metadata.sessionId, 250) && metadata.sessionId + '.json' === name
    && metadata.cliSessionId === codeId && metadata[ui.projectField] === ui.projectPath);
  return { status: matches.length === 1 ? 'association_candidate' : 'unknown',
    gaps: matches.length === 1 ? [] : ['no_unique_match'],
    association: matches.length === 1 ? { desktopId: matches[0].metadata.sessionId, codeId,
      filename: matches[0].name, project: { field: ui.projectField, value: ui.projectPath },
      uniqueness: 'acquired_candidates_only' } : null };
}
