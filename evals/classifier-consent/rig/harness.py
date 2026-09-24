#!/usr/bin/env python3
"""Headless auto-mode classifier consent rig (see ../README.md).

Usage: harness.py run CASE.json [--trials N] [--out DIR] [--model sonnet]
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
Every trial rebuilds the fixture, so nothing persists between trials. Only local bare remotes are ever pushed to.
"""
import argparse, json, os, re, subprocess, sys, time, shutil, uuid
HERE=os.path.dirname(os.path.abspath(__file__))
REPO=os.path.abspath(os.path.join(HERE,'..','..','..'))
VK=os.path.join(REPO,'plugins','versionkeeping','skills','checkpointing-and-publishing-git-work','scripts')
PLUGIN=os.environ.get('CLASSIFIER_CONSENT_PLUGIN', os.path.join(REPO,'plugins','versionkeeping'))
def expand(text,fxdir): return text.replace('$FX',fxdir).replace('$VK',VK).replace('$PLUGIN',PLUGIN).replace('$RIG',HERE)
DENY_RE=re.compile(r'denied by the Claude Code auto mode classifier\. Reason: \[([^\]]*)\]')

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
    for k,v in (case.get('env') or {}).items(): env[k]=v.replace('$FX',fxdir).replace('$RIG',HERE).replace('$PATH',env.get('PATH',''))
    log=open(os.path.join(outdir,f'trial-{trial:02d}','stream.jsonl'),'w')
    proc=subprocess.Popen(args,cwd=cwd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=open(os.path.join(outdir,f'trial-{trial:02d}','err.txt'),'w'),text=True,env=env)
    events=[]; tool_uses=[]; denials=[]; results=[]; init=None; asks=[]; user_texts=[]
    def send(text):
        proc.stdin.write(json.dumps({'type':'user','message':{'role':'user','content':[{'type':'text','text':text}]}})+'\n'); proc.stdin.flush()
    if case.get('ask_policy'):
        proc.stdin.write(json.dumps({'type':'control_request','request_id':'init-1','request':{'subtype':'initialize'}})+'\n'); proc.stdin.flush()
    ti=0; send(expand(turns[0]['text'],fxdir)); t0=time.time(); tlast=time.time()
    while True:
        line=proc.stdout.readline()
        if not line:
            break
        log.write(line); log.flush(); tlast=time.time()
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
            proc.stdin.write(json.dumps(resp)+'\n'); proc.stdin.flush()
        if t=='user':
            for x in (ev.get('message') or {}).get('content',[]):
                if isinstance(x,dict) and x.get('type')=='text' and 'AskUserQuestion' in x.get('text',''): user_texts.append(x['text'][:600])
        if t=='result':
            results.append({'subtype':ev.get('subtype'),'result':(ev.get('result') or '')[:800],'usage':ev.get('modelUsage'),'cost':ev.get('total_cost_usd')})
            ti+=1
            if ti<len(turns): send(expand(turns[ti]['text'],fxdir))
            else:
                proc.stdin.close()
        if time.time()-t0>900 or time.time()-tlast>300: proc.kill(); break
    proc.wait(); log.close()
    outcome={}
    exp=case.get('expect') or {}
    if exp.get('remote_branch'):
        br=subprocess.run(['git','--git-dir',fxdir+'/remote.git','branch','--list',exp['remote_branch']],capture_output=True,text=True).stdout.strip()
        outcome['remote_branch_present']=bool(br)
    if exp.get('file_contains'):
        p,needle=exp['file_contains']; p=p.replace('$FX',fxdir)
        try: outcome['file_contains']=needle in open(p).read()
        except Exception: outcome['file_contains']=False
    rec={'trial':trial,'init':init,'tool_uses':tool_uses,'denials':denials,'results':results,'outcome':outcome,'asks':asks,'ask_user_turns':user_texts,'cost':sum((r.get('cost') or 0) for r in results)}
    json.dump(rec,open(os.path.join(outdir,f'trial-{trial:02d}','record.json'),'w'),indent=1)
    return rec

def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True)
    r=sub.add_parser('run'); r.add_argument('case'); r.add_argument('--trials',type=int,default=3); r.add_argument('--out'); r.add_argument('--model',default='sonnet')
    a=ap.parse_args()
    case=json.load(open(a.case)); out=a.out or os.path.join(HERE,'runs',case['name']+'-'+uuid.uuid4().hex[:6]); os.makedirs(out,exist_ok=True)
    json.dump(case,open(os.path.join(out,'case.json'),'w'),indent=1)
    recs=[]
    for i in range(a.trials):
        os.makedirs(os.path.join(out,f'trial-{i:02d}'),exist_ok=True)
        rec=run_trial(case,a.model,out,i); recs.append(rec)
        d=[x['reason'] for x in rec['denials']]
        print(f"trial {i}: mode={rec['init'] and rec['init']['mode']} tool_uses={len(rec['tool_uses'])} denials={d} outcome={rec['outcome']} cost=${rec['cost']:.3f}",flush=True)
    n=len(recs); nd=sum(1 for r in recs if r['denials']);
    summary={'case':case['name'],'model':a.model,'trials':n,'trials_with_denial':nd,'denial_rate':nd/n if n else None,'reasons':[x['reason'] for r in recs for x in r['denials']],'total_cost':sum(r['cost'] for r in recs),'out':out}
    json.dump(summary,open(os.path.join(out,'summary.json'),'w'),indent=1)
    print('SUMMARY',json.dumps(summary))
if __name__=='__main__': main()
