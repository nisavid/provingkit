# Sys1 comparison evidence

These research fixtures preserve the actual model inputs and answers behind [First Sys1 comparisons](../../2026-09-26-sys1-first-comparisons.md), plus normalized native-harness observations. They are diagnostic artifacts, not a production hook implementation or a release gate.

## Evidence boundaries

The four `*-live.jsonl` files preserve exact SDK observation rows. State and question JSON bytes are embedded as strings and bound by SHA-256. The corresponding dry rows contain the same planned inputs without model answers. Labels remain in sidecars, outside model input. The separate `native-episode-frozen-judgment.json` contains one additional synthetic Write judgment; despite its preparatory filename, its result was allow and was not the injected ask used by the native episodes.

`claude-adapter-observations.json`, `claude-preflight-observations.json`, and `codex-preflight-observations.json` document normalization and the hashes of retained local originals. Native fixture roots become `/fixture`; Claude transcript-path fields are omitted; the local Codex binary becomes `<codex-executable>`. These are normalized observations, not byte-identical provider transcripts.

The first two preregistrations preserve the first 44-call plan. The follow-up preregistration fixes its 16 calls. Host-specific artifact references are replaced with role placeholders where needed. `artifact-identities.json` distinguishes original and portable/public hashes. A separate file inventory binds the final checked-in artifacts.

Jev questions in the records and runtime imports originate from [jev-axi 0.7.2](https://github.com/shiftynick/jev-axi/tree/v0.7.2). Its MIT license is included in [JEV-LICENSE.txt](JEV-LICENSE.txt). Installed source hashes qualify the tested distribution; they do not prove that distribution was built byte-for-byte from the upstream tag.

## Reproduce inputs before spending calls

The model runners require Node 24.21.0, Python 3 for transcript extraction, and the exact installed Jev source hashes checked by the scripts. Supply the installed package root explicitly:

```sh
node sys1-diagnostic-runner.mjs --package-root "$JEV_PACKAGE_ROOT" --mode safety
node sys1-diagnostic-runner.mjs --package-root "$JEV_PACKAGE_ROOT" --mode questions
node sys1-diagnostic-runner.mjs --package-root "$JEV_PACKAGE_ROOT" --mode supervision
node sys1-intent-followup-runner.mjs --package-root "$JEV_PACKAGE_ROOT"
```

Default execution is dry: it prints planned JSONL without contacting the model. Inspect those bytes before adding `--live`. Live calls use the existing `TYPESAFE_API_KEY` environment variable through the installed SDK, bypass client caches, and make no retries. They never execute the fixture commands. Model results may vary and `jev-latest` may resolve to a different version; retain the returned identity instead of expecting identical scores.

The safety/question runs originally used runner v2. The recorded v3 changed the supervision subprocess's stdin transport. The published runner additionally pins the questions-source digest before import; its identity is distinguished from the recorded runner. Its safety and question dry outputs are checked against the retained first-batch inputs. The failed v2 supervision dry run remains recorded in the report.

## Native experiments

The standalone preflight and adapter scripts create new named child directories below a caller-supplied scratch directory and refuse to reuse them. The Codex model script consumes an existing standalone fixture, reserves one model attempt, and refuses existing attempt records before writing or launching. Use an existing empty scratch parent. They make real model calls and disposable file effects; they do not edit installed hooks.

```sh
python native-preflight.py "$SYS1_SCRATCH"
python native-adapter-episodes.py "$SYS1_SCRATCH"
python codex-preflight.py "$SYS1_SCRATCH" "$CODEX_EXECUTABLE"
```

The Claude scripts require the documented 2.1.282 flags and an available Opus 5.5 route. They use only restricted file tools and retain native permission checks. The adapter script supplies fixture hooks through per-launch settings. Its one-shot review arm deliberately removes its signal after one denial; this is a mechanism test, not a deployable release rule.

The retained Codex standalone run used 0.157.1 and requires the actual ELF executable as a readable runtime file, not only a wrapper path. The executable argument configures that read grant; the script invokes `codex` through PATH and records its version before the standalone loop. It includes managed requirements. Its fixed runtime files match the tested Linux installation and may not match another host.

`bash-loader.c` is the fixture-only launcher used to make a standalone Bash process start with the explicit loader/library grants. It can be compiled statically into `codex-preflight/project/bash` after the standalone fixture exists. `codex-model-preflight.py` expects that launcher and takes the same scratch/executable arguments. Its recorded model run failed before task effects; do not treat the script's existence or a passing standalone canary as qualification of the model-tool route.

The portable Python copies generalize artifact-location arguments and locate the hook alongside the script. Their original and portable identities are distinct. The recorded native results came from the original versions; portability edits received syntax and diff checks, and the model-attempt guard received rejection checks, without another paid episode run.
