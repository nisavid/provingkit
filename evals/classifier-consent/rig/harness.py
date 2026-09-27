#!/usr/bin/env python3
"""Headless auto-mode classifier consent rig (see ../README.md).

Usage: harness.py run CASE.json [--trials N] [--out DIR] [--model sonnet]
--trials N asks for N valid trials and attempts at most 2N. A trial is invalid when any turn ends in an API error
(for example an exhausted session limit) or lacks its result event; invalid trials are kept on disk and reported
separately, never counted as clean. A watchdog bounds every trial by TRIAL_TOTAL_LIMIT (900 s) and TRIAL_IDLE_LIMIT (300 s
without a stream line), killing the claude process group; the kill is recorded as the trial's `killed` diagnostic
('total-limit' or 'idle-limit') while `invalid` stays derived from the stream alone.
CASE.json fields:
  name            label
  fixture         "push" | "push-worktree" | "none" | path to a shell script taking DIR (default "push")
  cwd             relative dir inside the fixture to start the session in (default "work")
  setup           optional shell snippet run in the fixture dir after the fixture is built (env FX=<fixture dir>)
  turns           list of {"text": "...", "max_turns": K} user turns sent one after another; each waits for the result event
  settings        optional JSON object passed via --settings (e.g. {"autoMode": {"environment": [...]}})
  setting_sources default "local"
  plugin_dirs     list of --plugin-dir paths
  append_system   optional --append-system-prompt text
  extra_args      list of extra CLI args
  env             dict of environment overrides for the claude process; $FX and $PATH expand
  expect          optional {"remote_branch": "ivan/fixture-feature"} checked after the run
  ask_policy      optional {"select": "affirmative"}: enables the stdio permission-prompt surface and auto-answers each AskUserQuestion with the first affirmative-reading option label; only "affirmative" is supported
Every trial rebuilds the fixture, so nothing persists between trials. Pushes reach only the fixture's local bare remote, and every case
runs with the recording gh stub first on PATH, logging to <fixture>/gh-stub.log. Without --out, runs go to a new temporary
directory outside the checkout, named neutrally because the classifier reads paths in
command text. The rig does not otherwise sandbox the agent.
"""
import argparse, json, os, re, signal, subprocess, sys, tempfile, threading, time, shutil, uuid
HERE=os.path.dirname(os.path.abspath(__file__))
REPO=os.path.abspath(os.path.join(HERE,'..','..','..'))
VK=os.path.join(REPO,'plugins','versionkeeping','skills','checkpointing-and-publishing-git-work','scripts')
PLUGIN=os.environ.get('CLASSIFIER_CONSENT_PLUGIN', os.path.join(REPO,'plugins','versionkeeping'))
def expand(text,fxdir): return text.replace('$FX',fxdir).replace('$VK',VK).replace('$PLUGIN',PLUGIN).replace('$RIG',HERE)
DENY_RE=re.compile(r'denied by the Claude Code auto mode classifier\. Reason: \[([^\]]*)\]')
TRIAL_TOTAL_LIMIT=900  # seconds per trial before the watchdog kills the claude process group
TRIAL_IDLE_LIMIT=300   # seconds without a stream line before the watchdog kills it
WATCHDOG_POLL=2        # longest pause between watchdog checks; it wakes sooner when a limit is nearer

def check_ask_policy(case):
    """Exit before any run directory, trial directory, or fixture exists when ask_policy asks for an unsupported selection."""
    pol=case.get('ask_policy')
    if pol and (not isinstance(pol,dict) or pol.get('select')!='affirmative'):
        sys.exit(f"harness: unsupported ask_policy {json.dumps(pol)}; only {{\"select\": \"affirmative\"}} is supported")

def build_fixture(kind, fxdir):
    if os.path.exists(fxdir): shutil.rmtree(fxdir)
    if kind=='none':
        os.makedirs(fxdir+'/work'); subprocess.run(['git','init','-q',fxdir+'/work'],check=True); return
    script = kind if os.path.exists(kind) else os.path.join(HERE,'mkfix.sh')
    subprocess.run(['bash',script,fxdir],check=True,stdout=subprocess.DEVNULL)
    if kind=='push-worktree':
        # move the feature branch into a sibling linked worktree; main checkout stays on main
        w=fxdir+'/work'
        subprocess.run(['git','-C',w,'checkout','-q','main'],check=True)
        os.makedirs(fxdir+'/work.wt',exist_ok=True)
        subprocess.run(['git','-C',w,'worktree','add','-q',fxdir+'/work.wt/fixture-feature','ivan/fixture-feature'],check=True)

def run_trial(case, model, outdir, trial):
    fxdir=os.path.join(outdir,f'trial-{trial:02d}','fx')
    build_fixture(case.get('fixture','push'), fxdir)
    if case.get('setup'):
        subprocess.run(['bash','-c',expand(case['setup'],fxdir)],cwd=fxdir,check=True,env=dict(os.environ,FX=fxdir,VK=VK,RIG=HERE))
    cwd=os.path.join(fxdir,case.get('cwd','work'))
    args=['claude','-p','--input-format','stream-json','--output-format','stream-json','--verbose','--permission-mode','auto','--permission-prompts',('host' if case.get('ask_policy') else 'none'),*(['--permission-prompt-tool','stdio'] if case.get('ask_policy') else []),'--model',model,'--setting-sources',case.get('setting_sources','local'),'--strict-mcp-config','--no-session-persistence']
    if case.get('settings'): args+=['--settings',json.dumps(case['settings'])]
    for p in case.get('plugin_dirs',[]): args+=['--plugin-dir',expand(p,fxdir)]
    if case.get('append_system'): args+=['--append-system-prompt',expand(case['append_system'],fxdir)]
    args+=case.get('extra_args',[])
    turns=case['turns']
    args+=['--max-turns',str(sum(int(t.get('max_turns',6)) for t in turns))]
    env=dict(os.environ); env.pop('CLAUDECODE',None); env.pop('CLAUDE_CODE_ENTRYPOINT',None)
    env['PATH']=os.path.join(HERE,'stub')+os.pathsep+env.get('PATH',''); env['GH_STUB_LOG']=os.path.join(fxdir,'gh-stub.log')
    for k,v in (case.get('env') or {}).items(): env[k]=v.replace('$FX',fxdir).replace('$RIG',HERE).replace('$PATH',env.get('PATH',''))
    log=open(os.path.join(outdir,f'trial-{trial:02d}','stream.jsonl'),'w')
    proc=subprocess.Popen(args,cwd=cwd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=open(os.path.join(outdir,f'trial-{trial:02d}','err.txt'),'w'),text=True,env=env,start_new_session=True)
    events=[]; tool_uses=[]; denials=[]; results=[]; init=None; asks=[]; user_texts=[]
    def write_line(obj):
        try: proc.stdin.write(json.dumps(obj)+'\n'); proc.stdin.flush()
        except BrokenPipeError: pass  # the child exited or was killed; the read loop ends at stdout EOF
    def send(text): write_line({'type':'user','message':{'role':'user','content':[{'type':'text','text':text}]}})
    if case.get('ask_policy'):
        write_line({'type':'control_request','request_id':'init-1','request':{'subtype':'initialize'}})
    ti=0; send(expand(turns[0]['text'],fxdir)); t0=time.time(); tlast={'t':t0}; killed={'v':None}; finished=threading.Event()
    def kill_group(reason):
        killed['v']=reason
        try: os.killpg(proc.pid,signal.SIGKILL)  # the whole session, so a grandchild cannot keep stdout open
        except ProcessLookupError: pass
        proc.kill()
    def watchdog():
        while True:
            now=time.time(); total_left=TRIAL_TOTAL_LIMIT-(now-t0); idle_left=TRIAL_IDLE_LIMIT-(now-tlast['t'])
            if total_left<=0: kill_group('total-limit'); return
            if idle_left<=0: kill_group('idle-limit'); return
            if finished.wait(max(0.05,min(WATCHDOG_POLL,total_left,idle_left))): return
    threading.Thread(target=watchdog,daemon=True).start()
    while True:
        line=proc.stdout.readline()
        if not line:
            break
        log.write(line); log.flush(); tlast['t']=time.time()
        try: ev=json.loads(line)
        except: continue
        events.append(ev); t=ev.get('type')
        if t=='system' and ev.get('subtype')=='init': init={'mode':ev.get('permissionMode'),'model':ev.get('model')}
        if t=='assistant':
            for x in (ev.get('message') or {}).get('content',[]):
                if x.get('type')=='tool_use': tool_uses.append({'id':x.get('id'),'name':x.get('name'),'input':x.get('input')})
        if t=='user':
            for x in (ev.get('message') or {}).get('content',[]):
                if isinstance(x,dict) and x.get('type')=='tool_result':
                    c=x.get('content'); s=c if isinstance(c,str) else json.dumps(c)
                    m=DENY_RE.search(s)
                    if m or 'Permission for this tool use was denied' in s:
                        tu=next((u for u in tool_uses if u['id']==x.get('tool_use_id')),None)
                        denials.append({'reason':m.group(1) if m else 'prompt-fallback','tool':tu['name'] if tu else None,'input':tu['input'] if tu else None,'text':s[:400]})
        if t=='control_request':
            req=ev.get('request') or {}; rid=ev.get('request_id')
            if req.get('subtype')=='can_use_tool' and req.get('tool_name')=='AskUserQuestion':
                inp=req.get('input') or {}; answers={}
                import re as _re
                neg=_re.compile(r"\b(no|skip|hold|don't|do not|cancel|not now|later|decline)\b",_re.I); pos=_re.compile(r"\b(yes|confirm|proceed|go ahead|push|file|open|publish|create)\b",_re.I)
                for q in inp.get('questions',[]):
                    opts=q.get('options') or []; labels=[o.get('label','') for o in opts]
                    pick=next((l for l in labels if pos.search(l) and not neg.search(l)),None) or next((l for l in labels if not neg.search(l)),None) or (labels[0] if labels else 'Yes')
                    answers[q.get('question','')]=pick
                asks.append({'questions':inp.get('questions'),'answers':answers})
                resp={'type':'control_response','response':{'subtype':'success','request_id':rid,'response':{'behavior':'allow','updatedInput':{'questions':inp.get('questions',[]),'answers':answers}}}}
            elif req.get('subtype')=='can_use_tool':
                denials.append({'reason':'prompt-fallback','tool':req.get('tool_name'),'input':req.get('input'),'text':'host denied: no approval surface'})
                resp={'type':'control_response','response':{'subtype':'success','request_id':rid,'response':{'behavior':'deny','message':'Permission for this tool use was denied. It requires approval, and this session has no approval surface; the action was NOT performed. Do not retry it.'}}}
            else:
                resp={'type':'control_response','response':{'subtype':'success','request_id':rid,'response':{}}}
            write_line(resp)
        if t=='user':
            for x in (ev.get('message') or {}).get('content',[]):
                if isinstance(x,dict) and x.get('type')=='text' and 'AskUserQuestion' in x.get('text',''): user_texts.append(x['text'][:600])
        if t=='result':
            results.append({'subtype':ev.get('subtype'),'is_error':ev.get('is_error'),'terminal_reason':ev.get('terminal_reason'),'result':(ev.get('result') or '')[:800],'usage':ev.get('modelUsage'),'cost':ev.get('total_cost_usd')})
            ti+=1
            if ti<len(turns): send(expand(turns[ti]['text'],fxdir))
            else:
                try: proc.stdin.close()
                except BrokenPipeError: pass
    proc.wait(); finished.set(); log.close()
    outcome={}
    exp=case.get('expect') or {}
    if exp.get('remote_branch'):
        br=subprocess.run(['git','--git-dir',fxdir+'/remote.git','branch','--list',exp['remote_branch']],capture_output=True,text=True).stdout.strip()
        outcome['remote_branch_present']=bool(br)
    if exp.get('file_contains'):
        p,needle=exp['file_contains']; p=p.replace('$FX',fxdir)
        try: outcome['file_contains']=needle in open(p).read()
        except Exception: outcome['file_contains']=False
    invalid=None
    if len(results)<len(turns): invalid='missing-result'
    elif any(r.get('is_error') or r.get('terminal_reason')=='api_error' for r in results):
        invalid=next((r.get('terminal_reason') or r.get('subtype') or 'error') for r in results if r.get('is_error') or r.get('terminal_reason')=='api_error')
    rec={'trial':trial,'invalid':invalid,'killed':killed['v'],'init':init,'tool_uses':tool_uses,'denials':denials,'results':results,'outcome':outcome,'asks':asks,'ask_user_turns':user_texts,'cost':sum((r.get('cost') or 0) for r in results)}
    json.dump(rec,open(os.path.join(outdir,f'trial-{trial:02d}','record.json'),'w'),indent=1)
    return rec

def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True)
    r=sub.add_parser('run'); r.add_argument('case'); r.add_argument('--trials',type=int,default=3); r.add_argument('--out'); r.add_argument('--model',default='sonnet')
    a=ap.parse_args()
    case=json.load(open(a.case)); check_ask_policy(case)
    out=a.out or tempfile.mkdtemp(prefix="rig-"); os.makedirs(out,exist_ok=True)
    json.dump(case,open(os.path.join(out,'case.json'),'w'),indent=1)
    recs=[]; i=0
    while sum(1 for r in recs if not r['invalid'])<a.trials and i<2*a.trials:
        os.makedirs(os.path.join(out,f'trial-{i:02d}'),exist_ok=True)
        rec=run_trial(case,a.model,out,i); recs.append(rec)
        d=[x['reason'] for x in rec['denials']]
        print(f"trial {i}: {'INVALID('+rec['invalid']+') ' if rec['invalid'] else ''}{'killed='+rec['killed']+' ' if rec['killed'] else ''}mode={rec['init'] and rec['init']['mode']} tool_uses={len(rec['tool_uses'])} denials={d} outcome={rec['outcome']} cost=${rec['cost']:.3f}",flush=True)
        i+=1
    valid=[r for r in recs if not r['invalid']]; n=len(valid); nd=sum(1 for r in valid if r['denials'])
    summary={'case':case['name'],'model':a.model,'trials':n,'invalid_trials':len(recs)-n,'trials_with_denial':nd,'denial_rate':nd/n if n else None,'reasons':[x['reason'] for r in valid for x in r['denials']],'total_cost':sum(r['cost'] for r in recs),'out':out}
    json.dump(summary,open(os.path.join(out,'summary.json'),'w'),indent=1)
    print('SUMMARY',json.dumps(summary))
if __name__=='__main__': main()
