#!/usr/bin/env bash
# mkfix.sh DIR : create a throwaway repo DIR/work whose origin is the local bare DIR/remote.git, with an unpushed feature branch.
set -euo pipefail
dir=$1; rm -rf "$dir"; mkdir -p "$dir"
git init -q --bare "$dir/remote.git"
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
