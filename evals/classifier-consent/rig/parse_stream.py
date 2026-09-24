#!/usr/bin/env python3
"""Summarize a claude -p stream-json run: tool calls, tool results (head), permission_denied system events, final result."""
import json,sys
for line in open(sys.argv[1],errors='replace'):
    line=line.strip()
    if not line: continue
    try: d=json.loads(line)
    except: print('UNPARSED',line[:200]); continue
    t=d.get('type')
    if t=='system':
        st=d.get('subtype');
        if st=='init': print('INIT mode=',d.get('permissionMode'),'model=',d.get('model'),'tools=',len(d.get('tools',[])),'mcp=',len(d.get('mcp_servers',[])),'plugins=',d.get('plugins'))
        else: print('SYSTEM',st,json.dumps({k:v for k,v in d.items() if k not in ('type','session_id','uuid')})[:900])
    elif t=='assistant':
        for x in (d.get('message') or {}).get('content',[]):
            if x.get('type')=='text': print('ASSISTANT:',x['text'][:500].replace('\n','⏎ '))
            elif x.get('type')=='tool_use': print('TOOL_USE',x.get('name'),json.dumps(x.get('input'))[:600])
    elif t=='user':
        for x in (d.get('message') or {}).get('content',[]):
            if isinstance(x,dict) and x.get('type')=='tool_result':
                c=x.get('content'); s=c if isinstance(c,str) else json.dumps(c)
                print('TOOL_RESULT:',s[:700].replace('\n','⏎ '))
    elif t=='result':
        print('RESULT subtype=',d.get('subtype'),'denials=',json.dumps(d.get('permission_denials'))[:500]); print('FINAL:',(d.get('result') or '')[:400].replace('\n','⏎ '))
        mu=d.get('modelUsage',{}); print('USAGE:',{m:{k:v for k,v in u.items() if 'Tokens' in k or k=='costUSD'} for m,u in mu.items()})
