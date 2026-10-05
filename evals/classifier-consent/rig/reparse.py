#!/usr/bin/env python3
"""Re-derive trial judgments from saved stream.jsonl files. Usage: reparse.py RUNS_DIR [more dirs]
Each RUNS_DIR is one harness --out directory (case.json, or trial-*/stream.jsonl, at its root) or holds several; one
yielding no runs is reported on stderr. Validity, denials, text mismatches, and buckets come from the harness's own
assess() and bucket(); the run's case.json gives the turn count (without it, at least one result) and its expect, and each
trial's record.json gives the expected-effect outcome and any watchdog kill, noted only when one fired. A valid,
denial-free trial whose expect names an effect but whose record.json is missing or unreadable is no-record, not
no-effect. When case.json is missing or unreadable, or its expect names an effect the harness cannot check, the expected
effects are unknown: stderr says so, and every valid, denial-free trial of that run is unjudged, never clean. No-record
and unjudged trials are listed, left out of no_effect, clean, and effects, and counted when any occur, so
any_denial+no_effect+clean+no_record+unjudged=trials. Counts cover valid trials only; invalid trials are listed with
their reason and observed permission mode."""
import json,glob,os,sys,collections
from harness import EFFECTS,assess,bucket,unknown_effects
def load(stream):
    evs=[]
    for line in open(stream,errors='replace'):
        try: evs.append(json.loads(line))
        except ValueError: continue
    return evs
def cmd(d):
    inp=d.get('input'); c=inp.get('command') if isinstance(inp,dict) else None
    return (c or json.dumps(inp)[:200]).replace('\n',' ')
for root in sys.argv[1:]:
    rname=os.path.basename(os.path.abspath(root)); runs=0; g=glob.escape(root)
    direct=os.path.exists(os.path.join(root,'case.json')) or glob.glob(os.path.join(g,'trial-*','stream.jsonl'))  # one --out dir
    for cdir in [root] if direct else sorted(glob.glob(os.path.join(g,'*'))):
        if not os.path.isdir(cdir): continue
        streams=sorted(glob.glob(os.path.join(glob.escape(cdir),'trial-*','stream.jsonl')))
        try: case=json.load(open(os.path.join(cdir,'case.json'))); case=case if isinstance(case,dict) else None
        except Exception: case=None
        exp=(case or {}).get('expect') or {}; rows=[]
        u=unknown_effects(exp); unknown='case.json missing or unreadable' if case is None else ('expect names '+', '.join(u) if u else None)
        if unknown and streams: print(f"reparse: {cdir}: {unknown}; expected effects unknown, so denial-free trials are unjudged",file=sys.stderr)
        for st in streams:
            tdir=os.path.dirname(st)
            try: rec=json.load(open(os.path.join(tdir,'record.json'))); outcome=rec.get('outcome') or {}; killed=rec.get('killed')
            except Exception: outcome=None; killed=None  # no readable record: the expected-effect outcome is unknown
            a=assess(load(st),len((case or {}).get('turns') or [None])); bk=bucket(a,outcome or {},exp)
            if unknown and bk in ('no-effect','clean'): bk='unjudged'  # valid and denial-free, but the expected effects are unknown
            elif outcome is None and bk=='no-effect': bk='no-record'  # valid, denial-free, and expect names an effect
            rows.append((os.path.basename(tdir),a,outcome,bk,killed))
        if not rows: continue
        runs+=1
        valid=[r for r in rows if not r[1]['invalid']]; b=collections.Counter(r[3] for r in rows)
        classifier=sum(1 for r in valid if any(d['source']=='classifier' for d in r[1]['denials']))
        kinds=collections.Counter(d['kind'] for r in valid for d in r[1]['denials'])
        effects={o:sum(1 for r in valid if r[3]!='unjudged' and (r[2] or {}).get(o)) for e,o in EFFECTS.items() if exp.get(e)}
        modes=collections.Counter(str(r[1]['mode']) for r in rows); errors=collections.Counter(e for r in valid for e in r[1]['errors'])
        mismatched=sum(1 for r in valid if r[1]['mismatch']); kills=collections.Counter(r[4] for r in rows if r[4])
        print(f"{rname if direct else rname+'/'+os.path.basename(cdir)}: trials={len(valid)} invalid={b['invalid']} any_denial={b['denied']} classifier_denial={classifier} no_effect={b['no-effect']} clean={b['clean']}"
              +(f" no_record={b['no-record']}" if b['no-record'] else '')+(f" unjudged={b['unjudged']}" if b['unjudged'] else '')+f" kinds={dict(kinds)} effects={effects} modes={dict(modes)}"
              +(f" errors={dict(errors)}" if errors else '')+(f" mismatch={mismatched}" if mismatched else '')+(f" killed={dict(kills)}" if kills else ''))
        for name,a,outcome,bk,killed in rows:
            notes=[f"INVALID ({a['invalid']}) mode={a['mode']}" if a['invalid'] else '',
                   f"NO-EFFECT outcome={outcome}" if bk=='no-effect' else '',
                   'NO-RECORD (record.json missing or unreadable)' if bk=='no-record' else '',
                   f"UNJUDGED ({unknown})" if bk=='unjudged' else '',
                   '; '.join(f"{d['kind']}<{d['tool']}> {cmd(d)[:60]}" for d in a['denials']) if bk=='denied' else '',
                   f"errors={a['errors']}" if a['errors'] and not a['invalid'] else '',
                   f"MISMATCH text vs structured: {a['mismatch']}" if a['mismatch'] else '',
                   f"killed={killed}" if killed else '']
            if any(notes): print(f"    {name}: "+' '.join(n for n in notes if n))
    if not runs: print(f"reparse: no runs in {root}",file=sys.stderr)
