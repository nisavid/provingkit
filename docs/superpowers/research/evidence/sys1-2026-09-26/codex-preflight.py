#!/usr/bin/env python3
import hashlib, json, pathlib, subprocess, sys
root=pathlib.Path(sys.argv[1]).resolve() / "codex-preflight"
root.mkdir(exist_ok=False)
for name in ("project","allowed","excluded"):
    (root/name).mkdir()
(root/"project/local.txt").write_text("synthetic local canary\n")
(root/"allowed/sibling.txt").write_text("synthetic sibling canary\n")
(root/"excluded/retained.txt").write_text("synthetic excluded canary; preserve\n")
(root/"project/excluded-link.txt").symlink_to(root/"excluded/retained.txt")
codex_binary=str(pathlib.Path(sys.argv[2]).resolve())
loader="/usr/lib/ld-linux-x86-64.so.2"
grants={str(root/"project"):"write",str(root/"allowed"):"write",codex_binary:"read",loader:"read","/usr/lib/libc.so.6":"read"}
for cmd in ("true","cat","tee"):
    grants["/usr/bin/"+cmd]="read"
profile="permissions.sys1_fixture_probe={filesystem={"+",".join(json.dumps(k)+"="+json.dumps(v) for k,v in grants.items())+"},network={enabled=false}}"
base=["codex","--disable","hooks","-c",profile,"sandbox","--permission-profile","sys1_fixture_probe","--include-managed-config","--cd",str(root/"project"),"--",loader,"--inhibit-cache","--library-path","/usr/lib"]
cases=[("runtime_launch",["/usr/bin/true"],"",True),
       ("local_read",["/usr/bin/cat",str(root/"project/local.txt")],"",True),
       ("sibling_read",["/usr/bin/cat",str(root/"allowed/sibling.txt")],"",True),
       ("excluded_read",["/usr/bin/cat",str(root/"excluded/retained.txt")],"",False),
       ("symlink_read",["/usr/bin/cat",str(root/"project/excluded-link.txt")],"",False),
       ("sibling_write",["/usr/bin/tee",str(root/"allowed/output.txt")],"synthetic codex output\n",True),
       ("excluded_write",["/usr/bin/tee",str(root/"excluded/output.txt")],"synthetic excluded output\n",False),
       ("symlink_write",["/usr/bin/tee",str(root/"project/excluded-link.txt")],"synthetic link output\n",False)]
manifest={"kind":"standalone sandbox canaries; no model or agent tools","codex_version":subprocess.check_output(["codex","--version"],text=True).strip(),"grants":grants,"network":{"configured":False,"socket_test_run":False},"managed_requirements":"included","ordinary_hooks":"disabled only for each child invocation","cases":[{"case":c,"argv":a,"expected_success":e} for c,a,_,e in cases]}
(root/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
results=[]
for name,args,stdin,expected in cases:
    r=subprocess.run(base+args,input=stdin,text=True,capture_output=True,timeout=15)
    record={"case":name,"argv":args,"exit_code":r.returncode,"stdout":r.stdout,"stderr":r.stderr,"expected_success":expected}
    results.append(record)
    (root/"results.json").write_text(json.dumps(results,indent=2)+"\n")
    print(json.dumps(record),flush=True)
    if (r.returncode==0)!=expected:
        raise RuntimeError("Unexpected result; stop remaining canaries")
assert (root/"excluded/retained.txt").read_text()=="synthetic excluded canary; preserve\n"
assert not (root/"excluded/output.txt").exists()
assert (root/"allowed/output.txt").read_text()=="synthetic codex output\n"
(root/"effects.json").write_text(json.dumps({"retained_unchanged":True,"excluded_output_absent":True,"allowed_output_sha256":hashlib.sha256((root/"allowed/output.txt").read_bytes()).hexdigest()},indent=2)+"\n")
