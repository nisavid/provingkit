#!/usr/bin/env bash
# run_red_green.sh BASE_REF [TRIALS]
# Red: the relayed-handoff conversation against the Versionkeeping plugin as committed at BASE_REF.
# Green: the same conversation against a copy of the working tree's plugins/versionkeeping.
# Requires: Claude Code with auto mode available, a Sonnet or Opus model, git, python3.
# Pushes reach only local fixtures. Each arm's plugin copy sits in its own run directory, a (red) or b (green), and
# $PLUGIN and $VK resolve inside it, so the arms' command text differs only in that neutral name.
set -euo pipefail
RIG=$(cd "$(dirname "$0")" && pwd); REPO=$(cd "$RIG/../../.." && pwd); base=$1; trials=${2:-5}
# Neutral names: the classifier reads paths in command text.
out=$(mktemp -d -t rig.XXXXXX); mkdir -p "$out/a" "$out/b/plugins"
git -C "$REPO" archive "$base" plugins/versionkeeping | tar -x -C "$out/a"
cp -R "$REPO/plugins/versionkeeping" "$out/b/plugins/"
echo "red: plugin from $base ($(git -C "$REPO" rev-parse --short "$base"))"
CLASSIFIER_CONSENT_PLUGIN="$out/a/plugins/versionkeeping" python3 "$RIG/harness.py" run "$RIG/../fixtures/skill-relay-bare-acceptance.json" --trials "$trials" --out "$out/a"
echo "green: plugin from the working tree"
CLASSIFIER_CONSENT_PLUGIN="$out/b/plugins/versionkeeping" python3 "$RIG/harness.py" run "$RIG/../fixtures/skill-relay-bare-acceptance.json" --trials "$trials" --out "$out/b"
python3 "$RIG/reparse.py" "$out"
