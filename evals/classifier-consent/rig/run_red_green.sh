#!/usr/bin/env bash
# run_red_green.sh BASE_REF [TRIALS]
# Red: the relayed-handoff conversation against the Versionkeeping plugin as committed at BASE_REF.
# Green: the same conversation against the working tree's plugins/versionkeeping.
# Requires: Claude Code with auto mode available, a Sonnet or Opus model, git, python3.
# Pushes reach only local fixtures; run directories a (red) and b (green) are named neutrally.
set -euo pipefail
RIG=$(cd "$(dirname "$0")" && pwd); REPO=$(cd "$RIG/../../.." && pwd); base=$1; trials=${2:-5}
# Neutral name: the classifier reads paths in command text.
out=$(mktemp -d -t rig.XXXXXX); mkdir -p "$out/base"
git -C "$REPO" archive "$base" plugins/versionkeeping | tar -x -C "$out/base"
echo "red: plugin from $base ($(git -C "$REPO" rev-parse --short "$base"))"
CLASSIFIER_CONSENT_PLUGIN="$out/base/plugins/versionkeeping" python3 "$RIG/harness.py" run "$RIG/../cases/skill-relay-bare-acceptance.json" --trials "$trials" --out "$out/a" | tail -1
echo "green: plugin from the working tree"
python3 "$RIG/harness.py" run "$RIG/../cases/skill-relay-bare-acceptance.json" --trials "$trials" --out "$out/b" | tail -1
python3 "$RIG/reparse.py" "$out"
