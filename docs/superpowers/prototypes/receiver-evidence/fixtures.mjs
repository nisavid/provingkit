// Invented records only. Shared by tests and the standalone demonstration.
const at = n => new Date(n).toISOString();
export function sample() {
  return {
    metadata: { sessionId: 'desktop-fixture', cliSessionId: 'code-fixture' },
    expected: { desktopId: 'desktop-fixture', codeId: 'code-fixture' },
    request: { correlationId: 'notice-1', senderAddress: 'uds:/synthetic/sender.sock',
      noticeText: 'Notification notice-1: context changed.', ackText: 'ACK notice-1', since: 1000 },
    capture: { startedAt: 2000, finishedAt: 2010 }, now: 2020, maxAgeMs: 100,
    transcript: [
      { uuid: 'incoming-1', sessionId: 'code-fixture', type: 'user', timestamp: at(1100),
        isMeta: true,
        origin: { kind: 'peer', from: 'uds:/synthetic/sender.sock', fromSession: 'local_sender',
          msg_id: 'transport-1', body: 'Notification notice-1: context changed.' },
        message: { role: 'user', content: 'Notification notice-1: context changed.' } },
      { uuid: 'reply-1', sessionId: 'code-fixture', type: 'assistant', timestamp: at(1200),
        message: { role: 'assistant', content: 'ACK notice-1' } },
    ].map(row => JSON.stringify(row) + '\n').join(''),
  };
}

export function eventSample() {
  return {
    expectedCodeId: 'code-fixture', correlationId: 'notice-1', ackText: 'ACK notice-1', since: 1000,
    capture: { receivedAt: 2000, now: 2020, maxAgeMs: 100 },
    collector: { interrupted: false },
    event: { hook_event_name: 'Stop', session_id: 'code-fixture',
      last_assistant_message: 'ACK notice-1', cwd: '/synthetic/project',
      permission_mode: 'default', transcript_path: '/synthetic/must-not-open.jsonl' },
  };
}
