#!/usr/bin/env bash
# mkfix.sh DIR : create a throwaway repo DIR/work whose origin is the local bare DIR/remote.git, with an unpushed feature branch.
set -euo pipefail
dir=$1; rm -rf "$dir"; mkdir -p "$dir"
# Build with no inherited GIT_* variable and without the host's global or system Git configuration (Git 2.32 or
# later) or templates, so no host hook, fsmonitor, filter, or other configured program runs here, including in the
# push's receive-pack. The harness sets the same environment for every fixture it builds; these lines keep it when
# the script runs alone. The bare remote also turns hooks off in its own config, so a trial's push into it runs none
# of the host's; the working repository keeps no such setting, because the publication planner refuses one.
for v in $(compgen -e); do case $v in GIT_*) unset "$v";; esac; done
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 GIT_TEMPLATE_DIR=
git init -q --bare -b main "$dir/remote.git"; git --git-dir "$dir/remote.git" config core.hooksPath /dev/null
git init -q -b main "$dir/work"
cd "$dir/work"
git config user.name "Harness Fixture"; git config user.email "harness@example.invalid"
git config commit.gpgsign false
printf '# fixture\n' > README.md; git add README.md; git commit -q -m "chore: initial fixture"
git remote add origin "$dir/remote.git"; git push -q -u origin main
git checkout -q -b ivan/fixture-feature
printf 'feature line\n' > feature.txt; git add feature.txt; git commit -q -m "feat: add fixture feature"
git checkout -q main; git checkout -q ivan/fixture-feature
echo "fixture ready: $(git rev-parse --short HEAD) on $(git branch --show-current), origin=$dir/remote.git"
