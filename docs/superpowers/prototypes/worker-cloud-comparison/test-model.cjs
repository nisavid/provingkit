const fs = require('node:fs');
const vm = require('node:vm');
const test = require('node:test');
const assert = require('node:assert/strict');
const html = fs.readFileSync(__dirname + '/demo.html', 'utf8');
const source = html.match(/<script id="trace-model">([\s\S]*?)<\/script>/)[1];
const box = {}; vm.runInNewContext(source, box);
const run = input => JSON.parse(JSON.stringify(box.WorkerCloudModel.evaluate(input)));
function fixture(change = {}) {
  return {
    caller: 'chatgpt-codex', fabric: 'python-app-server', operation: 'work',
    target: {population:'controlled', nativeId:'native-a', ownerId:'owner-a', observedOwnerId:'owner-a', exactReferenceMatched:true},
    consent: {verified:true, taskId:'native-a', purpose:'no-edit arithmetic', priorGrants:['grant-original','grant-transitive']},
    access: true, requestId:'request-a', correlation:'correlation-a', purpose:'no-edit arithmetic',
    settings: {requested:'read-only', appliedNoEdit:true},
    checks: {numbers:[12,-4,7,7]}, events:[], ...change
  };
}
function event(type, extra={}) {
  return {type, nativeId:'native-a', ownerId:'owner-a', requestId:'request-a', correlation:'correlation-a', origin:'receiver', ...extra};
}
const answer = '{"ascending":[-4,7,7,12],"sum":22}';
test('a captured request keeps task-scoped prior grants without creating authority', () => {
  const result = run(fixture());
  assert.deepEqual(result.request.priorGrants, ['grant-original','grant-transitive']);
  assert.equal(result.authorityCreated, false);
  assert.equal(result.qualified, false);
});

test('a mismatched owning server blocks request construction', () => {
 const input=fixture(); input.target.observedOwnerId='other-owner';
 const result=run(input);
 assert.equal(result.request, null);
 assert.ok(result.gaps.includes('owner mismatch'));
});

test('task, purpose, consent and caller access must all be admitted', () => {
 for(const mutate of [x=>x.consent.verified=false,x=>x.consent.taskId='other-task',x=>x.consent.purpose='other-purpose',x=>x.access=false,x=>x.target.exactReferenceMatched=false]) {
   const input=fixture();mutate(input);const result=run(input);
   assert.equal(result.request,null);assert.ok(result.gaps.length>0);
 }
});

test('a queued client response establishes submission only', () => {
 const result=run(fixture({fabric:'cloud-cli-reader',events:[event('submission',{origin:'client',status:'queued'})]}));
 assert.deepEqual(result.stages,['submission']);
 assert.equal(result.outcome,'queued');assert.equal(result.next,'read');
});

test('early receiver evidence survives a later queued response; wrong correlations do not count', () => {
 const result=run(fixture({events:[event('receipt'),event('submission',{origin:'client',status:'queued'})]}));
 assert.ok(result.stages.includes('receipt'));
 for(const bad of [{ownerId:'other-owner'},{nativeId:'other-task'},{correlation:'other-correlation'},{requestId:'other-request'},{origin:'client'}]) {
  assert.ok(!run(fixture({events:[event('receipt',bad)]})).stages.includes('receipt'));
 }
});

test('addressability needs an independent read rather than a returned ID', () => {
 const returned=run(fixture({events:[event('created',{source:'creation-response'})]}));
 assert.ok(!returned.stages.includes('creation'));
 const observed=run(fixture({events:[event('addressable',{source:'independent-read'})]}));
 assert.ok(observed.stages.includes('creation'));
});

test('a complete bound result passes declared arithmetic checks only after successful completion', () => {
 const result=run(fixture({events:[event('addressable',{source:'independent-read'}),event('receipt'),event('execution'),event('output',{text:answer,complete:true,source:'independent-read'}),event('terminal',{status:'success'})]}));
 assert.equal(result.checks.state,'passed');
 assert.deepEqual(result.terminal,['success']);
 assert.ok(result.stages.includes('fulfillment'));
});

test('correct output from failed or interrupted runs is never fulfilled', () => {
 for(const status of ['failed','interrupted']) {
  const result=run(fixture({events:[event('output',{text:answer,complete:true,source:'independent-read'}),event('terminal',{status})]}));
  assert.equal(result.checks.state,'passed');assert.deepEqual(result.terminal,[status]);
  assert.ok(!result.stages.includes('fulfillment'));assert.ok(result.gaps.includes('terminal non-success'));
 }
 const conflict=run(fixture({events:[event('output',{text:answer,complete:true,source:'independent-read'}),event('terminal',{status:'success'}),event('terminal',{status:'failed'})]}));
 assert.ok(!conflict.stages.includes('fulfillment'));assert.equal(conflict.next,'reconcile');
});

test('stream text and missing independent addressability stay below fulfillment', () => {
 for(const events of [
  [event('output',{text:answer,complete:true,source:'stream'}),event('terminal',{status:'success'})],
  [event('output',{text:answer,complete:true,source:'independent-read'}),event('terminal',{status:'success'})]
 ]) {
  const result=run(fixture({events}));assert.ok(!result.stages.includes('fulfillment'));assert.equal(result.next,'read');
 }
});

test('truncated or incomplete output is retained without a caller-check pass', () => {
 for(const extra of [{complete:false},{complete:true,truncated:true}]) {
  const result=run(fixture({events:[event('addressable',{source:'independent-read'}),event('output',{text:answer,source:'independent-read',...extra}),event('terminal',{status:'success'})]}));
  assert.equal(result.checks.state,'incomplete');assert.ok(result.stages.includes('output'));
  assert.ok(!result.stages.includes('fulfillment'));assert.equal(result.next,'read');
 }
});

test('a copied browser envelope cannot establish receipt even with matching payload IDs', () => {
 const direct=event('receipt');direct.envelope={subject:direct};
 const copied=event('receipt');copied.envelope={subject:{...copied}};
 assert.ok(run(fixture({fabric:'cloud-sse',target:{...fixture().target,population:'existing'},events:[direct]})).stages.includes('receipt'));
 const result=run(fixture({fabric:'cloud-sse',events:[copied]}));
 assert.ok(!result.stages.includes('receipt'));assert.ok(result.gaps.includes('envelope association unproved'));
});

test('continuation needs the same native task and an unrepeated prior-context marker', () => {
 const events=[event('addressable',{source:'independent-read'}),event('output',{text:answer,complete:true,source:'independent-read'}),event('terminal',{status:'success'})];
 const input=fixture({operation:'continue',priorNativeId:'native-a',checks:{numbers:[12,-4,7,7],marker:'prior-amber'},events});
 const missing=run(input);assert.equal(missing.checks.state,'failed');assert.ok(!missing.stages.includes('continuation'));
 const matching=structuredClone(input);matching.events[1].text='{"ascending":[-4,7,7,12],"sum":22,"marker":"prior-amber"}';
 assert.ok(run(matching).stages.includes('continuation'));
 const replaced=structuredClone(matching);replaced.priorNativeId='former-native';replaced.wrapperId='same-wrapper';
 const result=run(replaced);assert.equal(result.request,null);assert.ok(result.gaps.includes('native task replacement'));
});

test('requested read-only settings are not treated as applied no-edit controls', () => {
 const input=fixture({settings:{requested:'read-only'},events:[event('addressable',{source:'independent-read'}),event('output',{text:answer,complete:true,source:'independent-read'}),event('terminal',{status:'success'})]});
 const result=run(input);assert.equal(result.checks.state,'passed');assert.ok(!result.stages.includes('fulfillment'));
 assert.ok(result.gaps.includes('applied no-edit evidence missing'));
 assert.deepEqual(result.request.settings,{requested:'read-only'});
});

test('held and refused submissions remain distinct and never trigger resubmission', () => {
 for(const status of ['held','refused']) {
  const result=run(fixture({events:[event('submission',{origin:'client',status})]}));
  assert.equal(result.outcome,status);assert.equal(result.next,'hold');
 }
});

test('a lost response after possible submission requires reconciliation, not another send', () => {
 const result=run(fixture({events:[event('submission',{origin:'client',status:'unknown',possibleSubmission:true})]}));
 assert.equal(result.outcome,'unknown');assert.equal(result.next,'reconcile');
 assert.deepEqual(result.stages,[]);
});

test('bounded retry eligibility requires proven non-submission and no contradictory stages', () => {
 const failure=event('pre-submission-failure',{origin:'client',provenNonSubmission:true});
 const input=fixture({retry:{attempts:1,maxAttempts:2},events:[failure]});
 assert.equal(run(input).next,'eligible-bounded-retry');
 for(const change of [{retry:{attempts:2,maxAttempts:2}},{events:[event('pre-submission-failure',{origin:'client',provenNonSubmission:false})]},{events:[failure,event('receipt')]},{events:[failure,event('submission',{origin:'client',status:'unknown',possibleSubmission:true})]},{events:[failure,event('submission',{origin:'client',status:'refused'})]}]) {
   assert.notEqual(run({...input,...change}).next,'eligible-bounded-retry');
 }
});

test('merged input IDs and conflicting complete outputs keep result association unknown', () => {
 const result=run(fixture({target:{...fixture().target,population:'existing'},events:[event('receipt'),event('output',{text:answer,complete:true,source:'independent-read',inputIds:['request-a','request-b']}),event('terminal',{status:'success'})]}));
 assert.ok(!result.stages.includes('fulfillment'));assert.ok(result.gaps.includes('multiple input association'));
 const conflict=run(fixture({events:[event('addressable',{source:'independent-read'}),event('output',{text:answer,complete:true,source:'independent-read'}),event('output',{text:'{"ascending":[-4,7,7,12],"sum":23}',complete:true,source:'independent-read'}),event('terminal',{status:'success'})]}));
 assert.equal(conflict.checks.state,'incomplete');assert.equal(conflict.next,'reconcile');
});

test('an existing cloud work result needs admitted receiver input association', () => {
 const input=fixture({fabric:'cloud-sse',target:{...fixture().target,population:'existing'},events:[event('output',{text:answer,complete:true,source:'independent-read'}),event('terminal',{status:'success'})]});
 assert.ok(!run(input).stages.includes('fulfillment'));
 const receipt=event('receipt');receipt.envelope={subject:receipt};input.events.unshift(receipt);
 assert.ok(run(input).stages.includes('fulfillment'));
});

test('continuation observes addressability without declaring another creation', () => {
 const result=run(fixture({operation:'continue',priorNativeId:'native-a',checks:{numbers:[12,-4,7,7],marker:'prior-amber'},events:[event('addressable',{source:'independent-read'}),event('output',{text:'{"ascending":[-4,7,7,12],"sum":22,"marker":"prior-amber"}',complete:true,source:'independent-read'}),event('terminal',{status:'success'})]}));
 assert.ok(!result.stages.includes('creation'));assert.ok(result.stages.includes('continuation'));
});

test('a validated complete result ends the read recommendation without requesting another write', () => {
 const result=run(fixture({events:[event('submission',{origin:'client',status:'queued'}),event('addressable',{source:'independent-read'}),event('receipt'),event('output',{text:answer,complete:true,source:'independent-read'}),event('terminal',{status:'success'})]}));
 assert.ok(result.stages.includes('fulfillment'));assert.equal(result.next,'hold');
});

test('captured requests retain their caller, owner, candidate, operation and purpose', () => {
 const result=run(fixture());
 assert.equal(result.request.caller,'chatgpt-codex');assert.equal(result.request.ownerId,'owner-a');
 assert.equal(result.request.fabric,'python-app-server');assert.equal(result.request.operation,'work');
 assert.equal(result.request.purpose,'no-edit arithmetic');
});
