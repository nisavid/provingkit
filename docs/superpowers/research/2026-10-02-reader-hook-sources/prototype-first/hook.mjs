// Pure projection of supplied hook input; no hooks, environment, or transcript access.
export function projectStop(input) {
  input ??= {};
  const result = {
    status: 'unknown', qualification: 'unqualified',
    acknowledgment: null,
    eventFields: {},
    gaps: ['incoming_delivery_unobserved', 'native_peer_binding_unqualified', 'full_runtime_state_unobserved', 'producer_event_time_unobserved'],
  };
  const text = (x, max) => typeof x === 'string' && x.length > 0 && x.length <= max;
  if (!text(input.expectedCodeId, 256) || !text(input.ackText, 4096) || !text(input.correlationId, 256)) {
    result.gaps.push('invalid_binding_or_rule'); return result;
  }
  if (input.event?.hook_event_name !== 'Stop' || input.event?.session_id !== input.expectedCodeId) {
    result.gaps.push('identity_or_event_mismatch'); return result;
  }
  const c = input.capture;
  if (!c || ![c.receivedAt, c.now, c.maxAgeMs, input.since].every(Number.isFinite)
      || c.maxAgeMs < 0 || c.receivedAt < input.since || c.receivedAt > c.now) {
    result.gaps.push('invalid_capture'); return result;
  }
  result.capture = { receivedAt: c.receivedAt, now: c.now, maxAgeMs: c.maxAgeMs };
  if (c.now - c.receivedAt > c.maxAgeMs) { result.gaps.push('stale_capture'); return result; }
  if (input.collector?.interrupted !== false) { result.gaps.push('collector_discontinuity'); return result; }
  result.codeId = input.event.session_id;
  let oversized = false;
  for (const [key, output, max] of [['cwd', 'cwd', 4096], ['permission_mode', 'permissionMode', 128]]) {
    const value = input.event[key];
    if (text(value, max)) result.eventFields[output] = value;
    else if (typeof value === 'string' && value.length > max) oversized = true;
    else result.gaps.push(`${key}_missing`);
  }
  if (oversized) result.gaps.push('optional_fields_oversized');
  if (input.event?.last_assistant_message === input.ackText) {
    result.status = 'candidate';
    result.acknowledgment = { text: input.ackText, correlationId: input.correlationId };
  } else result.gaps.push(typeof input.event?.last_assistant_message === 'string' ? 'final_text_not_matching' : 'final_text_missing');
  return result;
}
