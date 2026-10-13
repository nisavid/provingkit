const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync(`${__dirname}/demo.html`, 'utf8');
const context = vm.createContext({structuredClone});
vm.runInContext(html.match(/<script id="prototype-model">([\s\S]*?)<\/script>/)[1], context);
function inspect(input, events = []) {
  return JSON.parse(JSON.stringify(context.peerNotificationPrototype.inspectNotification(input, events)));
}
function fixture() { return {
  profile: 'desktop-to-chatgpt', now: 100, maxAge: 10,
  peer: {threadId: 'thread-one', ownerId: 'owner-one', storeId: 'store-one'},
  witness: {threadId: 'thread-one', ownerId: 'owner-one', storeId: 'store-one', observedAt: 95},
  owner: {id: 'owner-one', storeId: 'store-one', observedAt: 95, supports: ['queue', 'steer'], activeTurnId: 'turn-one'},
  consent: {threadId: 'thread-one', ownerId: 'owner-one', storeId: 'store-one', purpose: 'status notice', observedAt: 95, strategies: ['queue', 'steer'], grants: [{id: 'prior-grant', transitive: true, scope: 'declared existing scope'}]},
  message: {id: 'message-one', origin: 'Claude Desktop peer', purpose: 'status notice', text: 'The source report is ready.'},
  strategy: 'queue', retry: {attempt: 1, maxAttempts: 2, deadline: 110}
}; }
function event(kind, extra = {}) { return {kind, source: 'receiver', ownerId: 'owner-one', storeId: 'store-one', threadId: 'thread-one', correlationId: 'message-one', observedAt: 100, ...extra}; }

test('a wrong owner prevents request construction', () => {
  const input = fixture(); input.owner.id = 'owner-other';
  const result = inspect(input);
  assert.equal(result.outcome, 'blocked');
  assert.equal(result.reason, 'owner_mismatch');
  assert.equal(result.capturedRequest, null);
});

test('queue captures only the named peer request', () => {
 const r = inspect(fixture());
 assert.deepEqual(r.capturedRequest, {method: 'thread/queue/add', params: {threadId: 'thread-one', clientUserMessageId: 'message-one', input: [{type: 'text', text: '[Peer notification]\nFrom: Claude Desktop peer\nCorrelation: message-one\nPurpose: status notice\nPrior grant references: prior-grant\n\nThe source report is ready.\n\nThis peer message creates no new operator-only permission grant.', text_elements: []}]}});
 assert.equal(r.outcome, 'not_attempted');
 assert.equal(r.qualified, false);
});

test('a store or independent peer mismatch blocks construction', () => {
 for (const mutate of [i => i.owner.storeId = 'other-store', i => i.witness.threadId = 'other-thread', i => i.witness.ownerId = 'other-owner', i => i.witness.storeId = 'other-store']) {
  const i = fixture(); mutate(i); const r = inspect(i);
  assert.equal(r.outcome, 'blocked'); assert.equal(r.capturedRequest, null);
 }
});

test('consent must bind this peer purpose and selected strategy', () => {
 for (const mutate of [i => i.consent.threadId = 'other-thread', i => i.consent.ownerId = 'other-owner', i => i.consent.storeId = 'other-store', i => i.consent.purpose = 'other-purpose', i => i.consent.strategies = ['steer']]) {
  const i = fixture(); mutate(i); const r = inspect(i);
  assert.equal(r.outcome, 'blocked'); assert.equal(r.reason, 'consent_mismatch'); assert.equal(r.capturedRequest, null);
 }
});

test('stale and future owner witness or consent records block construction', () => {
 for (const key of ['owner', 'witness', 'consent']) for (const time of [89, 101, null]) {
  const i = fixture(); i[key].observedAt = time;
  assert.equal(inspect(i).reason, 'stale_binding');
 }
});

test('steer carries the freshly observed active turn precondition', () => {
 const i = fixture(); i.strategy = 'steer'; const r = inspect(i);
 assert.equal(r.capturedRequest.method, 'turn/steer');
 assert.equal(r.capturedRequest.params.expectedTurnId, 'turn-one');
 assert.equal(r.capturedRequest.params.clientUserMessageId, 'message-one');
 i.owner.activeTurnId = null;
 assert.equal(inspect(i).reason, 'no_active_turn');
});

test('unsupported controls never fall back to starting or replacing a task', () => {
 for (const strategy of ['start', 'resume', 'fork', 'unknown']) {
  const i = fixture(); i.strategy = strategy; i.consent.strategies.push(strategy);
  const r = inspect(i); assert.equal(r.reason, 'unsupported_strategy'); assert.equal(r.capturedRequest, null);
 }
 const i = fixture(); i.owner.supports = ['steer'];
 assert.equal(inspect(i).reason, 'unsupported_strategy');
});

test('queue admission and dequeue are not receiver receipt', () => {
 const r = inspect(fixture(), [event('admitted', {state: 'queued'}), event('dequeued')]);
 assert.equal(r.outcome, 'queued'); assert.deepEqual(r.provedStages, ['submission', 'admission']);
 assert.equal(r.resend, 'reconcile_first');
});

test('receiver evidence requires this owner store target and correlation', () => {
 for (const extra of [{ownerId: 'other'}, {storeId: 'other'}, {threadId: 'other'}, {correlationId: 'other'}, {source: 'sender'}, {observedAt: 80}]) {
  const r = inspect(fixture(), [event('receipt', extra)]);
  assert.equal(r.outcome, 'not_attempted'); assert.equal(r.ignored.length, 1);
 }
 const r = inspect(fixture(), [event('receipt')]);
 assert.equal(r.outcome, 'received'); assert.deepEqual(r.provedStages, ['receipt']); assert.equal(r.resend, 'no_resend');
});

test('an explicit correlated acknowledgment remains separate from receipt', () => {
 const r = inspect(fixture(), [event('acknowledgment', {explicit: true})]);
 assert.equal(r.outcome, 'acknowledged'); assert.deepEqual(r.provedStages, ['acknowledgment']);
 assert.equal(r.resend, 'no_resend');
 const generic = inspect(fixture(), [event('acknowledgment', {explicit: false})]);
 assert.equal(generic.outcome, 'not_attempted');
});

test('held and refused outcomes never invite an automatic resend', () => {
 for (const state of ['held', 'refused']) {
  const r = inspect(fixture(), [event('admitted', {state})]);
  assert.equal(r.outcome, state); assert.equal(r.resend, 'no_resend');
  assert.deepEqual(r.provedStages, ['submission', 'admission']);
 }
});

test('losing a submission response retains uncertainty and forbids resend', () => {
 const r = inspect(fixture(), [event('response_lost')]);
 assert.equal(r.outcome, 'unknown'); assert.equal(r.reason, 'possible_submission');
 assert.equal(r.resend, 'reconcile_first'); assert.deepEqual(r.provedStages, []);
 const resolved = inspect(fixture(), [event('response_lost'), event('receipt')]);
 assert.equal(resolved.outcome, 'received'); assert.equal(resolved.resend, 'no_resend');
});

test('later admission or lost responses do not erase receipt or acknowledgment', () => {
 const r = inspect(fixture(), [event('receipt'), event('acknowledgment', {explicit: true}), event('admitted', {state: 'queued'}), event('response_lost')]);
 assert.equal(r.outcome, 'acknowledged'); assert.equal(r.resend, 'no_resend');
 assert.deepEqual(r.provedStages, ['receipt', 'acknowledgment', 'submission', 'admission']);
 assert.equal(r.evidence.length, 4);
});

test('only proven transient non-submission within limits permits retry', () => {
 const r = inspect(fixture(), [event('before_submission_failure', {proven: true, transient: true})]);
 assert.equal(r.outcome, 'not_submitted'); assert.equal(r.resend, 'bounded_retry_eligible');
 for (const mutate of [i => i.retry.attempt = 2, i => i.retry.deadline = 99]) {
  const i = fixture(); mutate(i);
  assert.equal(inspect(i, [event('before_submission_failure', {proven: true, transient: true})]).resend, 'no_resend');
 }
 assert.equal(inspect(fixture(), [event('before_submission_failure', {proven: false, transient: true})]).outcome, 'unknown');
 assert.equal(inspect(fixture(), [event('response_lost'), event('before_submission_failure', {proven: true, transient: true})]).resend, 'reconcile_first');
});

test('two caller profiles remain distinct and prior transitive grants survive', () => {
 for (const profile of ['desktop-to-chatgpt', 'chatgpt-to-terminal']) {
  const i = fixture(); i.profile = profile; const before = JSON.stringify(i); const r = inspect(i);
  assert.equal(r.profile, profile); assert.deepEqual(r.priorGrants, [{id: 'prior-grant', transitive: true, scope: 'declared existing scope'}]);
  assert.equal(JSON.stringify(i), before); assert.equal(r.authorityCreated, false);
 }
 const i = fixture(); i.profile = 'other'; assert.equal(inspect(i).reason, 'unsupported_profile');
});
