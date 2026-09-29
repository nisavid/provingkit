import test from 'node:test';
import assert from 'node:assert/strict';
import { createObserver, inspectEnvelope } from './observer.mjs';
import { createFixture } from './fixture.mjs';

test('an existing receiver yields selected partial observations, never qualification', async () => {
  const f = createFixture();
  const result = await createObserver({ selectReceiver: f.selectReceiver }).observeReceiver(f.binding);
  assert.equal(result.collection.state, 'collected');
  assert.equal(result.fields.model.value, 'fixture-model-a');
  assert.equal(result.fields.account.freshness, 'initialization-cache');
  assert.equal(result.fields.hostBefore.value.harnessCwd, '/fixture/worktree');
  assert.equal(result.qualification, 'unqualified');
  assert.equal(result.fields.model.completeness, 'partial');
  assert.ok(result.gaps.includes('current-account-route'));
  assert.ok(!JSON.stringify(result).includes('omit me'));
});

test('a missing, parked, or differently bound receiver supplies no observations or read attempts', async () => {
  for (const change of [f => { f.record = null; }, f => { f.record.query = null; },
    f => { f.record.codeSessionId = 'other-code'; }, f => { f.record.appStartId = 'new-boot'; }]) {
    const f = createFixture(); change(f);
    const result = await createObserver({ selectReceiver: f.selectReceiver }).observeReceiver(f.binding);
    assert.equal(result.collection.state, 'unavailable');
    assert.deepEqual(result.fields, {});
    assert.deepEqual(f.queryCalls, []);
  }
});

test('replacement during collection discards every field from the old query', async () => {
  const f = createFixture();
  f.record.query.getContextUsage = async () => { f.replaceQuery(); return { model: 'old-query-model' }; };
  const result = await createObserver({ selectReceiver: f.selectReceiver }).observeReceiver(f.binding);
  assert.equal(result.collection.state, 'discarded');
  assert.equal(result.collection.reason, 'binding-changed-during-read');
  assert.deepEqual(result.fields, {});
});

test('the deadline returns unknown and a late reply cannot change the exported result', async () => {
  const f = createFixture(); f.delayModel();
  const release = setTimeout(f.releaseLate, 50);
  try {
    const result = await createObserver({ selectReceiver: f.selectReceiver }).observeReceiver(f.binding, { timeoutMs: 5 });
    assert.equal(result.fields.model.state, 'unknown');
    assert.equal(result.fields.model.reason, 'deadline');
    const exported = JSON.stringify(result);
    f.releaseLate(); await new Promise(resolve => setTimeout(resolve, 0));
    assert.equal(JSON.stringify(result), exported);
  } finally { clearTimeout(release); f.releaseLate(); }
});

test('rules retain ignored entries and skipped-setting evidence without implying complete permissions', async () => {
  const f = createFixture();
  f.record.query.listPermissionRules = async () => ({ state: {
    rules: [{ behavior: 'allow', source: 'userSettings', rule: 'Read(/fixture/**)', editability: 'persistent', notInEffect: true }],
    workspaceDirectories: [{ path: '/fixture', source: 'session' }],
    originalCwd: '/fixture/original', managedOnly: true, errors: [{ message: 'fixture parse error' }],
  } });
  const result = await createObserver({ selectReceiver: f.selectReceiver }).observeReceiver(f.binding);
  assert.equal(result.fields.rules.value.rules[0].notInEffect, true);
  assert.equal(result.fields.rules.value.settingsErrorCount, 1);
  assert.equal(result.fields.rules.value.originalCwd, '/fixture/original');
  assert.equal(result.fields.rules.completeness, 'partial');
  assert.ok(result.gaps.includes('complete-applied-permissions'));
});

test('unsupported and malformed controls leave local gaps without suppressing other observations', async () => {
  const f = createFixture();
  f.record.query.getContextUsage = async () => ({});
  f.record.query.listPermissionRules = async () => { throw new Error('unsupported control'); };
  const result = await createObserver({ selectReceiver: f.selectReceiver }).observeReceiver(f.binding);
  assert.equal(result.fields.model.state, 'unknown');
  assert.equal(result.fields.model.reason, 'malformed-response');
  assert.equal(result.fields.rules.state, 'unavailable');
  assert.equal(result.fields.rules.reason, 'unsupported-control');
  assert.equal(result.fields.account.state, 'observed');
});

test('busy receivers expose changing host grants and uncertain pending work even with equal Code rules', async () => {
  const f = createFixture(); f.record.turn = 'busy';
  f.record.host.unselected = 'do not export';
  f.record.host.permissionMode = 'default';
  f.record.host.modeEvent = { mode: 'plan', at: 900, generation: 1 };
  f.record.host.flagScopeSyncPending = true;
  f.record.query.getContextUsage = async () => {
    f.record.host.alwaysAllowedReasons.push('fixture-grant');
    f.record.host.flagScopeSyncPending = false;
    return { model: 'fixture-model-a' };
  };
  const result = await createObserver({ selectReceiver: f.selectReceiver }).observeReceiver(f.binding);
  assert.equal(result.collection.hostChangedDuringRead, true);
  assert.deepEqual(result.fields.hostBefore.value.alwaysAllowedReasons, []);
  assert.deepEqual(result.fields.hostAfter.value.alwaysAllowedReasons, ['fixture-grant']);
  assert.equal(result.fields.hostAfter.value.pendingCoverage, 'unknown');
  assert.equal(result.fields.hostAfter.value.permissionMode, 'default');
  assert.equal(result.fields.hostAfter.value.modeEvent.mode, 'plan');
  assert.ok(!JSON.stringify(result).includes('do not export'));
  assert.equal(result.fields.rules.state, 'observed');
});

test('unassessed builds remain distinct from incompatible dependencies and failed dependencies disable only their reads', async () => {
  const f = createFixture();
  const observer = createObserver({ selectReceiver: f.selectReceiver });
  const first = await observer.observeReceiver(f.binding);
  assert.equal(first.compatibility.model.state, 'unassessed');
  assert.equal(first.fields.model.state, 'observed');
  f.queryCalls.length = 0;
  const second = await observer.observeReceiver(f.binding, { compatibility: {
    model: { state: 'incompatible', basis: 'Synthetic contract failure: model producer absent.' },
    rules: { state: 'carried-forward', basis: 'Synthetic unchanged producer comparison.' },
  } });
  assert.equal(second.fields.model.reason, 'incompatible-dependency');
  assert.ok(!f.queryCalls.includes('getContextUsage'));
  assert.equal(second.fields.rules.state, 'observed');
  assert.equal(second.qualification, 'unqualified');
});

test('the reader accepts fresh partial evidence and rejects stale, restarted, replayed, and malformed exports', async () => {
  const f = createFixture();
  const result = await createObserver({ selectReceiver: f.selectReceiver, now: () => 1000 }).observeReceiver(f.binding, { ttlMs: 50 });
  const bytes = JSON.stringify(result);
  const read = (input = bytes, options = {}, expected = f.binding) => inspectEnvelope(input, expected, { now: 1020, ...options });
  assert.equal(read().state, 'usable-partial');
  assert.equal(read().envelope.qualification, 'unqualified');
  assert.equal(read(bytes, { now: 1050 }).reason, 'expired');
  assert.equal(read(bytes, { afterSequence: result.sequence }).reason, 'not-newer');
  assert.equal(read(bytes, {}, { ...f.binding, appStartId: 'restarted' }).reason, 'binding-mismatch');
  assert.equal(read(bytes.slice(0, -3)).reason, 'invalid-envelope');
  for (const change of [e => { e.fields.model.value = null; }, e => { e.gaps = []; },
    e => { e.qualification = 'qualified'; }, e => { e.fields.model.endedAt = 999999; },
    e => { delete e.fields.rules; }, e => { e.collection.expiresAt = -1; },
    e => { delete e.fields.hostAfter.value.harnessCwd; },
    e => { e.fields.hostAfter.value.modeEvent = {mode:'plan',at:900,generation:99}; },
    e => { e.fields.rules.value.unselected = 'extra data'; }]) {
    const broken = JSON.parse(bytes); change(broken);
    assert.equal(read(JSON.stringify(broken)).reason, 'invalid-envelope');
  }
});
