# run inside $FX after mkfix: build a ready publication plan for pushing ivan/fixture-feature to origin from $FX/$REPO_SUBDIR (default work)
set -euo pipefail
repo=$FX/${REPO_SUBDIR:-work}
start=$(git -C $repo rev-parse main); src=$(git -C $repo rev-parse ivan/fixture-feature)
python3 - "$start" "$src" > $FX/request.json <<'PY'
import json,sys
start,src=sys.argv[1:3]
print(json.dumps({"schema_version":2,"start_head":start,"source_sha":src,"task_owned_commits":[src],"adopted_commits":[],"removal_authorized_commits":[],"explicit_destination":{"remote":"origin","ref":"refs/heads/ivan/fixture-feature"},"default_branch_policy":None,"allow_create":True,"creation_base_ref":"refs/heads/main"}))
PY
python3 $VK/plan_git_publication.py --repo $repo --request $FX/request.json > $FX/plan.json
python3 -c "import json;p=json.load(open('$FX/plan.json'));assert p['status']=='ready',p"
sha256sum $FX/plan.json | cut -d' ' -f1 > $FX/plan.sha256
