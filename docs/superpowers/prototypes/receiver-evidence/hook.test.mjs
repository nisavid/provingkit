import test from 'node:test';
import assert from 'node:assert/strict';
import { projectStop } from './hook.mjs';

import { eventSample } from './fixtures.mjs';

test('a Stop event projects an ACK candidate without inventing incoming delivery or full state', () => {
  const result = projectStop(eventSample());
  assert.equal(result.status, 'candidate');
  assert.equal(result.qualification, 'unqualified');
  assert.deepEqual(result.acknowledgment, { text: 'ACK notice-1', correlationId: 'notice-1' });
  assert.deepEqual(result.eventFields, { cwd: '/synthetic/project', permissionMode: 'default' });
  assert.ok(result.gaps.includes('incoming_delivery_unobserved'));
  assert.ok(result.gaps.includes('full_runtime_state_unobserved'));
  assert.ok(!JSON.stringify(result).includes('must-not-open'));
});

test('another task or event cannot produce the selected receiver ACK candidate', () => {
  for (const change of [{ session_id: 'other-task' }, { hook_event_name: 'UserPromptSubmit' }]) {
    const input = eventSample(); Object.assign(input.event, change);
    const result = projectStop(input);
    assert.equal(result.status, 'unknown');
    assert.equal(result.acknowledgment, null);
    assert.deepEqual(result.eventFields, {});
  }
});

test('missing final text and missing binding stay unknown rather than matching absent values', () => {
  const input = eventSample(); delete input.event.last_assistant_message;
  assert.equal(projectStop(input).status, 'unknown');
  assert.ok(projectStop(input).gaps.includes('final_text_missing'));
  delete input.ackText; delete input.expectedCodeId; delete input.event.session_id;
  const missing = projectStop(input);
  assert.equal(missing.status, 'unknown');
  assert.equal(missing.acknowledgment, null);
  assert.ok(missing.gaps.includes('invalid_binding_or_rule'));
  assert.equal(projectStop(undefined).status, 'unknown');
});

test('capture age and collector discontinuity prevent a recently captured ACK candidate', () => {
  for (const change of [
    input => { input.capture.now = 5000; },
    input => { input.capture.receivedAt = 3000; },
    input => { input.capture.receivedAt = 500; },
    input => { input.collector.interrupted = true; },
    input => { delete input.collector; },
  ]) {
    const input = eventSample(); change(input);
    const result = projectStop(input);
    assert.equal(result.status, 'unknown');
    assert.equal(result.acknowledgment, null);
  }
  assert.ok(projectStop(eventSample()).gaps.includes('producer_event_time_unobserved'));
});

test('the hook retains bounded fields and reports omitted oversized observations', () => {
  const input = eventSample();
  input.event.cwd = 'x'.repeat(4097);
  input.event.permission_mode = 'x'.repeat(129);
  input.capture.unrelated = 'PRIVATE EXTRA';
  input.event.background_tasks = [{ description: 'PRIVATE EXTRA' }];
  const result = projectStop(input);
  assert.deepEqual(result.eventFields, {});
  assert.ok(result.gaps.includes('optional_fields_oversized'));
  assert.ok(!JSON.stringify(result).includes('PRIVATE EXTRA'));
  input.ackText = input.event.last_assistant_message = 'x'.repeat(4097);
  assert.equal(projectStop(input).status, 'unknown');
});
