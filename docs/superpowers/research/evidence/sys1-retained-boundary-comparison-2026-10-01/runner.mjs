import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync,mkdirSync,openSync,writeSync,fsyncSync,closeSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {pathToFileURL} from 'node:url';

export const sha = bytes => createHash('sha256').update(bytes).digest('hex');
export const MODEL = 'jev-1.13.0';
export const ORDER = ['B10','C10','C20','B20','B30','C30','C40','B40'];
export const KEYS = ['meaningful_progress','worker_stuck','work_off_track','needs_human'];
export const SDK_SHA = 'bbb851dfe375c586c5bee3c082a04ab71882813dde39df0e95eaa23f30ec7012';
export const ENDPOINT = 'https://api.typesafe.ai/v1/systemone';

export async function loadSdk(path) {
  const bytes=readFileSync(path);
  assert.equal(sha(bytes),SDK_SHA,'SDK source changed');
  // The reviewed SDK is one self-contained ESM file. Import the verified bytes.
  return import(`data:text/javascript;base64,${bytes.toString('base64')}`);
}

export function buildArms(capture) {
  const b = capture.bookkeeping, hook = capture.raw_hook;
  assert.equal(b.cadence_eligible, true);
  assert.equal(typeof hook.tool_response, 'string');
  const records = capture.context.primary.records;
  const completed = records.flatMap((r,index) => r.type === 'event_msg' && r.payload?.type === 'item_completed' ? [{index,item:r.payload.item}] : []);
  const users = completed.filter(r=>r.item.type === 'UserMessage');
  assert.ok(users.length);
  const requests = users.map(({item}) => {
    assert.equal(item.content.length,1);
    assert.equal(item.content[0].type,'text');
    assert.equal(typeof item.content[0].text,'string');
    return item.content[0].text.trim();
  });
  const matches = completed.filter(r=>r.item.id === hook.tool_use_id);
  assert.equal(matches.length,1);
  assert.equal(matches[0].item.type,'CommandExecution');
  assert.equal(matches[0].item.aggregated_output,hook.tool_response);
  const baseline = structuredClone(b.current_observation);
  const last = baseline.state.events.at(-1);
  assert.equal(last.tool,hook.tool_name);
  // These four current inputs/results require no redaction; fail any changed join.
  assert.equal(last.input,JSON.stringify(hook.tool_input).slice(0,400));
  assert.equal(last.result,hook.tool_response.slice(-400));
  assert.deepEqual(last,b.after.events.at(-1));
  const context = structuredClone(baseline);
  context.state.job = requests.join('\n\n');
  context.state.events.at(-1).result = hook.tool_response;
  return {baseline,context,provenance:{
    count:b.after.count,user_records:users.map(r=>({index:r.index,id:r.item.id})),
    current_record:matches[0].index,current_id:hook.tool_use_id,
    result_utf16_units:hook.tool_response.length,result_utf8_bytes:Buffer.byteLength(hook.tool_response),
  }};
}

// Worker-only PostToolUse policy, transcribed from the pinned jev-axi source.
export function projectResponse(data) {
  assert.ok(data && typeof data === 'object' && data.answers);
  assert.deepEqual(Object.keys(data.answers).sort(), [...KEYS].sort());
  const raw = Object.fromEntries(KEYS.map(k=>[k,data.answers[k]?.noul]));
  assert.ok(Object.values(raw).every(n=>typeof n === 'number' && Number.isFinite(n) && n>=0 && n<=1));
  assert.ok(data.model === undefined || data.model === MODEL, 'returned model mismatch');
  const scores = Object.fromEntries(KEYS.map(k=>[k,Math.round(raw[k]*100)/100]));
  const raw_flags = Object.fromEntries(KEYS.map(k=>[k,raw[k]>=0.7]));
  const rounded_flags = Object.fromEntries(KEYS.map(k=>[k,scores[k]>=0.7]));
  let verdict='continue',reason='no worker concern above threshold';
  if (rounded_flags.needs_human) {verdict='escalate';reason=`a person may be needed to unblock this (needs_human ${scores.needs_human})`;}
  else if (rounded_flags.worker_stuck) {verdict='steer';reason=`the recent tool calls look stuck in a loop (worker_stuck ${scores.worker_stuck}); try a different approach`;}
  else if (rounded_flags.work_off_track) {verdict='steer';reason=`the recent tool calls look unrelated to the job (work_off_track ${scores.work_off_track})`;}
  const action=verdict==='steer'?'note':'none';
  const output=action==='note'?JSON.stringify({hookSpecificOutput:{hookEventName:'PostToolUse',additionalContext:`jev-axi supervision: ${reason}. Reconsider the approach against the original request; ignore this note if it is wrong.`}}):'';
  const usage=data.usage && ['input_tokens','output_tokens'].every(k=>Number.isSafeInteger(data.usage[k]) && data.usage[k]>=0)?data.usage:null;
  return {raw,scores,raw_flags,rounded_flags,verdict,reason,action,output,masked_steering:verdict==='escalate'&&(rounded_flags.worker_stuck||rounded_flags.work_off_track),returned_model:data.model??null,usage};
}

export async function assessCell(cell,{TypeSafeClient,apiKey,emit,fetch:transport=globalThis.fetch,timeoutMs=6000}) {
  const started=performance.now();let invocations=0;
  try {
    assert.equal(sha(cell.body),cell.sha256,'request digest changed');
    const request=JSON.parse(cell.body);
    assert.equal(request.model,MODEL);
    const client=new TypeSafeClient({apiKey,baseURL:'https://api.typesafe.ai',defaultModel:MODEL,logLevel:'off',timeout:timeoutMs,retry:{maxRetries:0},fetch:async(url,init)=>{
      invocations++;assert.equal(invocations,1,'unexpected retry');
      assert.equal(String(url),ENDPOINT);assert.equal(init.method,'POST');assert.equal(init.body,cell.body);
      emit({kind:'fetch_started',request_sha256:sha(init.body),at:new Date().toISOString()});
      const response=await transport(url,{...init,redirect:'error'});
      emit({kind:'response_headers',status:response.status,request_id:response.headers.get('x-typesafe-request-id'),content_type:response.headers.get('content-type'),at:new Date().toISOString()});
      const read=response.text.bind(response);
      response.text=async()=>{const body=await read();emit({kind:'response_body',body,sha256:sha(body),bytes:Buffer.byteLength(body),at:new Date().toISOString()});return body;};
      return response;
    }});
    const {data,requestId}=await client.systemOne(request,{timeout:timeoutMs,retry:{maxRetries:0}}).withResponse();
    const projection=projectResponse(data);
    return {status:'assessed',fetch_invocations:invocations,duration_ms:performance.now()-started,request_id:requestId??null,response:data,projection};
  } catch(error) {
    return {status:'failed',fetch_invocations:invocations,duration_ms:performance.now()-started,error_type:error.name,error:diagnostic(error,apiKey),http_status:Number.isInteger(error.status)?error.status:null,request_id:error.requestId??null};
  }
}

function diagnostic(error,apiKey,depth=0) {
  const clean=value=>{
    if(typeof value!=='string') return null;
    for(const key of new Set([apiKey,apiKey?.trim()])) if(key) value=value.replaceAll(key,'[REDACTED]');
    return value.replace(/\b(Bearer|Basic)\s+\S+/gi,'$1 [REDACTED]').slice(0,2000);
  };
  return {name:clean(error?.name),message:clean(error?.message),code:clean(error?.code),
    cause:depth<2 && error?.cause?diagnostic(error.cause,apiKey,depth+1):null};
}

export function saveExclusive(path,value) {
  const fd=openSync(path,'wx',0o600);
  try {writeSync(fd,JSON.stringify(value,null,2)+'\n');fsyncSync(fd);} finally {closeSync(fd);}
}

export function validatePacket(packet) {
  assert.deepEqual(packet.cells.map(c=>c.id),ORDER);
  for (const cell of packet.cells) {
    assert.equal(sha(cell.body),cell.sha256);
    const request=JSON.parse(cell.body);
    assert.deepEqual(Object.keys(request),['state','questions','model']);
    assert.deepEqual(Object.keys(request.questions),KEYS);
    assert.equal(request.model,MODEL);
  }
}

export async function runBatch(packet,out,options) {
  validatePacket(packet);
  const attempts=join(out,'attempts');mkdirSync(attempts,{mode:0o700});
  const rows=[];let stopped=null;
  for (const cell of packet.cells) {
    if (stopped) {rows.push({id:cell.id,status:'unattempted',reason:stopped});continue;}
    saveExclusive(join(attempts,`${cell.id}-start.json`),{id:cell.id,request_sha256:cell.sha256,at:new Date().toISOString()});
    const journal=openSync(join(attempts,`${cell.id}-transport.jsonl`),'wx',0o600);
    let result;
    try {result=await assessCell(cell,{...options,emit:e=>{writeSync(journal,JSON.stringify(e)+'\n');fsyncSync(journal);}});}
    finally {closeSync(journal);}
    const terminal={id:cell.id,...result,ended:new Date().toISOString()};
    saveExclusive(join(attempts,`${cell.id}-terminal.json`),terminal);rows.push(terminal);
    if (result.status!=='assessed') stopped=`failed ${cell.id}`;
  }
  const result={status:stopped?'incomplete':'complete',cells:rows,omission:{assessment_requests:0,projected_output:'',native_continuation:false}};
  saveExclusive(join(out,'batch.json'),result);return result;
}

export function preparePacket(index,root) {
  assert.deepEqual(index.captures.map(c=>c.count),[10,20,30,40]);
  const cells={},inputs=[],provenance=[];
  for (const entry of index.captures) {
    assert.match(entry.file,/^[a-zA-Z0-9-]+\.json$/);
    const path=resolve(root,entry.file),bytes=readFileSync(path);
    assert.equal(sha(bytes),entry.sha256);
    const arms=buildArms(JSON.parse(bytes));assert.equal(arms.provenance.count,entry.count);
    inputs.push({path,sha256:entry.sha256});provenance.push(arms.provenance);
    for (const [letter,arm] of [['B',arms.baseline],['C',arms.context]]) {
      const body=JSON.stringify({...arm,model:MODEL}),id=letter+entry.count;
      cells[id]={id,body,sha256:sha(body),utf8_bytes:Buffer.byteLength(body),utf16_units:body.length};
    }
  }
  const packet={schema:'retained-boundary-v1',inputs,provenance,cells:ORDER.map(id=>cells[id])};
  validatePacket(packet);return packet;
}

async function main(args) {
  const [mode,...rest]=args;
  if (mode==='prepare') {
    assert.equal(rest.length,3);const [index,root,out]=rest;
    const packet=preparePacket(JSON.parse(readFileSync(index,'utf8')),root);
    saveExclusive(out,packet);
    console.log(JSON.stringify({packet_sha256:sha(readFileSync(out)),cells:packet.cells.map(({body,...metadata})=>metadata)}));
  } else if (mode==='run') {
    assert.equal(rest.length,4);const [path,expected,sdk,out]=rest;
    assert.equal(process.version,'v24.21.0','runtime changed');
    const bytes=readFileSync(path);assert.equal(sha(bytes),expected);
    const packet=JSON.parse(bytes);validatePacket(packet);
    for (const input of packet.inputs) assert.equal(sha(readFileSync(input.path)),input.sha256,'input source changed');
    const {TypeSafeClient}=await loadSdk(sdk);
    assert.ok(process.env.TYPESAFE_API_KEY?.trim(),'API key absent');
    const result=await runBatch(packet,out,{TypeSafeClient,apiKey:process.env.TYPESAFE_API_KEY});
    console.log(JSON.stringify({status:result.status,assessed:result.cells.filter(c=>c.status==='assessed').length}));
    if(result.status!=='complete') process.exitCode=1;
  } else throw new Error('expected prepare or run');
}

if (process.argv[1] && import.meta.url===pathToFileURL(resolve(process.argv[1])).href) {
  main(process.argv.slice(2)).catch(error=>{console.error(JSON.stringify({status:'failed_before_batch_or_recording',error_type:error.name}));process.exitCode=1;});
}
