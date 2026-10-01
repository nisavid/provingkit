import test from 'node:test';
import assert from 'node:assert/strict';
import { buildArms, projectResponse, loadSdk, assessCell, runBatch, preparePacket, sha, ORDER, KEYS } from './runner.mjs';
import {mkdtempSync,readFileSync,writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';

const event = (item) => ({type:'event_msg', payload:{type:'item_completed', item}});
function capture() {
  const result = 'x'.repeat(401) + '😀';
  const recent = {tool:'Bash',input:'{"command":"make test"}',result:result.slice(-400)};
  return {
    raw_hook:{tool_name:'Bash',tool_input:{command:'make test'},tool_response:result,tool_use_id:'current'},
    context:{primary:{records:[
      event({type:'UserMessage',id:'u1',content:[{type:'text',text:'  CSV\n'}]}),
      event({type:'UserMessage',id:'u2',content:[{type:'text',text:'\u00a0JSON\n'}]}),
      event({type:'CommandExecution',id:'current',aggregated_output:result}),
    ]}},
    bookkeeping:{cadence_eligible:true,after:{count:10,events:[recent]},current_observation:{
      state:{job:'CSV only',events:[recent]},questions:{worker_stuck:{type:'noul',question:'Stuck?'}},
    }},
  };
}

test('preparation retains baseline values and adds only ordered requests and the current full result', () => {
  const source = capture(); const before = JSON.stringify(source);
  const {baseline,context,provenance} = buildArms(source);
  assert.deepEqual(baseline, source.bookkeeping.current_observation);
  assert.equal(context.state.job, 'CSV\n\nJSON');
  assert.equal(context.state.events.at(-1).result, 'x'.repeat(401)+'😀');
  assert.deepEqual(context.questions, baseline.questions);
  assert.equal(provenance.result_utf16_units, 403);
  assert.equal(provenance.result_utf8_bytes, 405);
  assert.equal(JSON.stringify(source), before);
});

test('preparation freezes the eight requests and rejects changed source captures',()=>{
  const root=mkdtempSync(join(tmpdir(),'boundary-prepare-'));
  const captures=[10,20,30,40].map(count=>{
    const source=capture();source.bookkeeping.after.count=count;
    source.bookkeeping.current_observation.questions=Object.fromEntries(KEYS.map(k=>[k,{type:'noul',question:k}]));
    const bytes=JSON.stringify(source);writeFileSync(join(root,`${count}.json`),bytes);
    return {count,file:`${count}.json`,sha256:sha(bytes)};
  });
  const ready=preparePacket({captures},root);
  assert.deepEqual(ready.cells.map(c=>c.id),['B10','C10','C20','B20','B30','C30','C40','B40']);
  assert.equal(JSON.parse(ready.cells[0].body).state.job,'CSV only');
  assert.equal(JSON.parse(ready.cells[1].body).state.job,'CSV\n\nJSON');
  writeFileSync(join(root,'10.json'),'{}');
  assert.throws(()=>preparePacket({captures},root));
});

function packet() {
  const questions=Object.fromEntries(KEYS.map(k=>[k,{type:'noul',question:k}]));
  const body=JSON.stringify({state:{job:'Synthetic',events:[]},questions,model:'jev-1.13.0'});
  return {cells:ORDER.map(id=>({id,body,sha256:sha(body)}))};
}
test('a failed first response stops the batch, preserves its attempt, and prevents reuse',async()=>{
  const {TypeSafeClient}=await loadSdk(process.env.TYPESAFE_SDK_FILE);
  const out=mkdtempSync(join(tmpdir(),'boundary-test-'));let calls=0;
  const options={TypeSafeClient,apiKey:'synthetic',fetch:async()=>{calls++;return new Response('{"answers":{}}');}};
  const result=await runBatch(packet(),out,options);
  assert.equal(calls,1);assert.equal(result.cells[0].status,'failed');
  assert.equal(result.cells.filter(c=>c.status==='unattempted').length,7);
  const saved=readFileSync(join(out,'attempts','B10-terminal.json'),'utf8');
  await assert.rejects(()=>runBatch(packet(),out,options));
  assert.equal(calls,1);assert.equal(readFileSync(join(out,'attempts','B10-terminal.json'),'utf8'),saved);
});

test('SDK retains failure for 529, malformed JSON, and a stalled response body without a second request',async()=>{
  const {TypeSafeClient}=await loadSdk(process.env.TYPESAFE_SDK_FILE);
  for (const kind of ['529','malformed','body-timeout','connection']) {
    let calls=0; const events=[];
    const result=await assessCell(packet().cells[0],{TypeSafeClient,apiKey:'synthetic',timeoutMs:25,emit:e=>events.push(e),fetch:async(url,init)=>{
      calls++;
      if(kind==='connection') throw new TypeError('synthetic network failure');
      if(kind==='529') return new Response('overloaded',{status:529});
      if(kind==='malformed') return new Response('{');
      return new Response(new ReadableStream({start(controller){init.signal.addEventListener('abort',()=>controller.error(new Error('aborted')),{once:true});}}));
    }});
    assert.equal(calls,1);assert.equal(result.status,'failed');
    if(kind==='body-timeout') {assert.equal(result.error_type,'APITimeoutError');assert.ok(events.some(e=>e.kind==='response_headers'));assert.ok(!events.some(e=>e.kind==='response_body'));}
  }
});

test('failed attempts retain diagnostic causes and invariant names without the authentication value',async()=>{
  const {TypeSafeClient}=await loadSdk(process.env.TYPESAFE_SDK_FILE);
  const key='synthetic-secret-for-error-test';
  const failed=await assessCell(packet().cells[0],{TypeSafeClient,apiKey:key,emit:()=>{},fetch:async()=>{
    throw Object.assign(new TypeError(`synthetic connection problem; Bearer ${key}`),{code:'SYNTHETIC_CONNECTION'});
  }});
  assert.equal(failed.status,'failed');
  assert.ok(failed.error.message.includes('synthetic connection problem'));
  assert.equal(failed.error.cause.name,'TypeError');
  assert.equal(failed.error.cause.code,'SYNTHETIC_CONNECTION');
  assert.equal(JSON.stringify(failed).includes(key),false);
  const wrong={...packet().cells[0],sha256:'0'.repeat(64)};
  const invalid=await assessCell(wrong,{TypeSafeClient,apiKey:key,emit:()=>{},fetch:async()=>assert.fail('must not dispatch')});
  assert.equal(invalid.fetch_invocations,0);
  assert.ok(invalid.error.message.includes('request digest changed'));
});

test('all eight synthetic successes preserve order, literal zero-call omission, and independent records',async()=>{
  const {TypeSafeClient}=await loadSdk(process.env.TYPESAFE_SDK_FILE);
  let calls=0;
  const out=mkdtempSync(join(tmpdir(),'boundary-complete-'));
  const result=await runBatch(packet(),out,{TypeSafeClient,apiKey:'synthetic',fetch:async()=>{calls++;return new Response(JSON.stringify({...answer(),usage:{input_tokens:11,output_tokens:0}}));}});
  assert.equal(calls,8);assert.equal(result.status,'complete');assert.equal(result.omission.assessment_requests,0);
  assert.deepEqual(result.cells.map(c=>c.id),['B10','C10','C20','B20','B30','C30','C40','B40']);
  assert.equal(result.cells.every(c=>c.projection.output===''),true);
  assert.equal(result.cells.reduce((n,c)=>n+c.projection.usage.input_tokens,0),88);
  const drifted=packet();drifted.cells[7].body='{}';let driftCalls=0;
  await assert.rejects(()=>runBatch(drifted,mkdtempSync(join(tmpdir(),'boundary-drift-')),{TypeSafeClient,apiKey:'synthetic',fetch:async()=>{driftCalls++;}}));
  assert.equal(driftCalls,0);
});

test('context extraction rejects duplicate or mismatched current items and preserves empty ordered task entries',()=>{
  const ambiguous=capture();ambiguous.context.primary.records.push(ambiguous.context.primary.records.at(-1));
  assert.throws(()=>buildArms(ambiguous));
  const mismatch=capture();mismatch.raw_hook.tool_response+='changed';assert.throws(()=>buildArms(mismatch));
  const empty=capture();empty.context.primary.records[0].payload.item.content[0].text=' ';assert.equal(buildArms(empty).context.state.job,'\n\nJSON');
});

test('pinned SDK sends exact bytes once, records the complete response, and does not retry a 429', async () => {
  const {TypeSafeClient} = await loadSdk(process.env.TYPESAFE_SDK_FILE);
  const body=JSON.stringify({...buildArms(capture()).baseline,model:'jev-1.13.0'});
  const cell={id:'B10',body,sha256:sha(body)};
  for (const status of [200,429]) {
    let calls=0;const events=[];
    const result=await assessCell(cell,{TypeSafeClient,apiKey:'synthetic-not-a-credential',emit:e=>events.push(e),fetch:async(url,init)=>{
      calls++;assert.equal(String(url),'https://api.typesafe.ai/v1/systemone');assert.equal(init.body,body);assert.equal(init.redirect,'error');
      return new Response(JSON.stringify(status===200?answer():{error:'synthetic limited'}),{status,headers:{'x-typesafe-request-id':'synthetic-id'}});
    }});
    assert.equal(calls,1);
    assert.equal(result.status,status===200?'assessed':'failed');
    assert.equal(events.find(e=>e.kind==='response_body').body,status===200?JSON.stringify(answer()):'{"error":"synthetic limited"}');
    assert.equal(JSON.stringify(events).includes('synthetic-not-a-credential'),false);
  }
});

const answer = (stuck=0.1,off=0.1,human=0.1) => ({model:'jev-1.13.0',answers:{
  meaningful_progress:{noul:0.8},worker_stuck:{noul:stuck},work_off_track:{noul:off},needs_human:{noul:human},
}});
test('projected notes follow source rounding and precedence without hiding masked concerns', () => {
  const note = projectResponse(answer(0.695));
  assert.equal(note.verdict,'steer');
  assert.equal(note.raw_flags.worker_stuck,false);
  assert.equal(note.rounded_flags.worker_stuck,true);
  assert.deepEqual(JSON.parse(note.output),{hookSpecificOutput:{hookEventName:'PostToolUse',additionalContext:'jev-axi supervision: the recent tool calls look stuck in a loop (worker_stuck 0.7); try a different approach. Reconsider the approach against the original request; ignore this note if it is wrong.'}});
  const quiet = projectResponse(answer(0.9,0.8,0.695));
  assert.equal(quiet.verdict,'escalate');
  assert.equal(quiet.output,'');
  assert.equal(quiet.masked_steering,true);
  assert.equal(quiet.usage,null);
  for (const bad of [null,{answers:{}},answer(NaN),answer(1.1),{...answer(),answers:{...answer().answers,extra:{noul:0.2}}}]) assert.throws(()=>projectResponse(bad));
});
