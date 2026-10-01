#!/usr/bin/env node
"use strict";

// Node-only synthetic test/eval support. The governed binding owns transitions,
// state association, argv construction, and the public classification channel.
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const {spawnSync} = require("node:child_process");
const ROOT = path.resolve(__dirname, "..");
const SKILL = "plugins/praxis/skills/aeon-bell";
const KEYS = Object.freeze({source: "binding-source", entry: "monitor-entry", run: "monitor-run"});
const PINNED = {
  "plugins/praxis/skills/aeon-bell/scripts/monitor_binding.js": "a85478740c9544544baf47ac87fec6a27ac6aeb194039ceac19a3a7f618f3b5d",
  "plugins/praxis/skills/aeon-bell/scripts/aeon_bell.py": "1320c472965ab968da0aaaa8c71f56cbad9da2d79670c9bab5ca7749c7cc8b95",
  "evals/praxis/fixtures/adapter-failure.json": "4b6dc23d804d7fd187ad44f42f620f9708e504d28ed8ab7ab19e4fcf3b28899c",
  "evals/praxis/fixtures/cached-closed.json": "bc25beb8f0456b6736726cf1fc16c1fec80d836226cbee961746386c92b843da",
  "evals/praxis/fixtures/cached-open.json": "a9dba6fe6b1686626c86cc3b907540a7722bcdbcb553a3ef181a41cb5fef5f0f",
  "evals/praxis/fixtures/due-closed.json": "cbc3956fa2cd22d165eb416df0f7e93c0973f3275162f5e3ae1f6e00da8858e5",
  "evals/praxis/fixtures/due-open.json": "9b296c6f295cc4bb54f8a32a55896d828fc210e1359f39aecbc2d95450dcc39a",
  "evals/praxis/fixtures/empty.json": "9f641f8af1164c334f6932277aebce12546cc9b51f1af4ad9234c45906b05b1a",
  "evals/praxis/fixtures/held.json": "d2fafeef127e2b1c258b6e50faf3301c57b7259030959d9724c94bc1f8196e04",
  "evals/praxis/fixtures/missing-binding-repeat.json": "78246a33bfd3525c9913f25608668097d7b443737d2a208667a42dacad002282",
  "evals/praxis/fixtures/missing-binding.json": "10f946e72bc45bb34b34a0d9feea5670784344b1c16d634c486bd255826d749e",
  "evals/praxis/fixtures/partial-observation.json": "46adbadc72ce836da3dc3972a8f5e523b9c632995f9a88cc51112b3ce93cf737",
  "evals/praxis/fixtures/paused-expired.json": "c6c44c61b6066c8e81055fae9a43db81b43d8bbb258a73ea4d2f28eeee4a1827",
  "evals/praxis/fixtures/pending.json": "3bd1d9cf1556e579dec1f4c9ba425b8fc22a29bfb8d5ea15f642d58209599e16",
  "evals/praxis/fixtures/restart-notice.json": "c4376be34d204ecd7c883219de0105471a6821ac85e7b201058aa57248c3e24d",
  "evals/praxis/fixtures/restart-send.json": "0fd9c36fcece3e86d59a188cc13fc3ae3dc28380135bd4bec3abe9c43fe18a3f",
  "evals/praxis/fixtures/schedule-unavailable.json": "0ddaa98551619bbf5210bb7cf2759bf33d27484c6b29078808dce1b8931cdb29",
  "evals/praxis/fixtures/shared-gate-single-wake.json": "93e4185c03e923806779c04d5d016b607ab25d483e67c8e1dbec17eb3ec6314e"
};
const copy = value => JSON.parse(JSON.stringify(value));
const digest = bytes => crypto.createHash("sha256").update(bytes).digest("hex");

function loadBytes(filename, expected) {
  const bytes = fs.readFileSync(filename);
  const sha256 = digest(bytes);
  if (expected && sha256 !== expected) throw new Error("Configured source identity mismatch");
  // Reject malformed UTF-8 before evaluating or parsing the same read bytes.
  const source = new TextDecoder("utf-8", {fatal: true}).decode(bytes);
  return {bytes, source, sha256};
}
function writeJSON(filename, value) {
  const temporary = filename + ".pending";
  fs.writeFileSync(temporary, JSON.stringify(value, null, 2) + "\n");
  fs.renameSync(temporary, filename);
}
function record(directory, event) {
  fs.appendFileSync(path.join(directory, "events.jsonl"), JSON.stringify(event) + "\n");
}
function execute(argv, cwd) {
  const process = spawnSync(argv[0], argv.slice(1), {
    cwd, encoding: "utf8", timeout: 20000, maxBuffer: 4 * 1024 * 1024,
    env: {...global.process.env, PYTHONDONTWRITEBYTECODE: "1"},
  });
  if (process.error || !Number.isInteger(process.status)) {
    return {kind: "unknown", stdout: process.stdout || "", stderr: process.stderr || ""};
  }
  return {kind: "completed", exit_code: process.status,
          stdout: process.stdout, stderr: process.stderr};
}
function successfulJSON(outcome) {
  if (outcome.kind !== "completed" || outcome.exit_code !== 0) {
    throw new Error("Synthetic fixture subprocess did not complete successfully");
  }
  return JSON.parse(outcome.stdout);
}
function readJSON(filename) { return JSON.parse(fs.readFileSync(filename, "utf8")); }
function prepare(caseId, directory) {
  const recipe = "evals/praxis/fixtures/" + caseId + ".json";
  if (!Object.hasOwn(PINNED, recipe)) throw new Error("Unknown synthetic recipe");
  const sources = [SKILL + "/scripts/monitor_binding.js", SKILL + "/scripts/aeon_bell.py",
                   "tests/praxis_fixture.py", recipe, "tests/praxis_actor_runner.js"];
  // Read and hash source bytes together; prepare copies before invoking setup.
  const loaded = sources.map(relative => ({relative, ...loadBytes(path.join(ROOT, relative), PINNED[relative])}));
  fs.mkdirSync(directory); // Existing directories are never reused by setup.
  const identities = {};
  for (const item of loaded) {
    const target = path.join(directory, item.relative);
    fs.mkdirSync(path.dirname(target), {recursive: true});
    fs.writeFileSync(target, item.bytes);
    loadBytes(target, item.sha256);
    identities[item.relative] = item.sha256;
  }
  record(directory, {type: "setup_start", identities});
  const setup = execute(["python3", "-B", path.join(directory, "tests/praxis_fixture.py"),
                         "setup", caseId, "--directory", directory,
                         "--engine", path.join(directory, SKILL, "scripts/aeon_bell.py"),
                         "--defer-enter"], directory);
  record(directory, {type: "setup_transport", outcome: setup});
  const entry = successfulJSON(setup);
  const fixture = readJSON(path.join(directory, "control-state.json"));
  if (entry.initial !== null) throw new Error("Fixture entered the final generation during setup");
  for (const event of readJSON(path.join(directory, "setup-transcript.json"))) {
    record(directory, {type: "setup_event", event});
  }
  record(directory, {type: "setup_complete", outcome: setup});
  const state = {slots: {[KEYS.source]: loaded[0].source, [KEYS.entry]: entry.entry_ref}, latest_reply: null};
  writeJSON(path.join(directory, "binding-state.json"), state);
  const config = {keys: KEYS, logical_now: entry.now,
                  skill_cwd: path.join(directory, SKILL), identities,
                  fixture_identity: fixture.identity};
  writeJSON(path.join(directory, "runner-config.json"), config);
  return {status: "ready", keys: KEYS,
          advance_command: ["node", path.join(directory, "tests/praxis_actor_runner.js"),
                            "advance", "--directory", directory]};
}

async function advance(directory, classification) {
  const config = readJSON(path.join(directory, "runner-config.json"));
  const filename = path.join(directory, "binding-state.json");
  const privateState = readJSON(filename);
  const loaded = loadBytes(path.join(directory, SKILL, "scripts/monitor_binding.js"),
                           PINNED[SKILL + "/scripts/monitor_binding.js"]);
  if (privateState.slots[config.keys.source] !== loaded.source) throw new Error("Stored binding source differs from verified bytes");
  // Verify copied engine, fixture, and recipe identities before entering/continuing.
  for (const [relative, expected] of Object.entries(config.identities)) loadBytes(path.join(directory, relative), expected);
  const fixture = readJSON(path.join(directory, "control-state.json"));
  const factory = (0, eval)(loaded.source);
  const state = {
    get: key => privateState.slots[key],
    put: (key, value) => {
      privateState.slots[key] = copy(value);
      writeJSON(filename, privateState);
      record(directory, {type: "state", key, value});
    },
  };
  let transitions = 0;
  const engineTransport = async argv => {
    if (++transitions > 64) throw new Error("Synthetic advance exceeded 64 engine transitions");
    const outcome = execute(argv, config.skill_cwd);
    let reply = null;
    if (outcome.kind === "completed" && outcome.exit_code === 0) {
      try { reply = JSON.parse(outcome.stdout); } catch (_) { /* Binding handles malformed replies. */ }
    }
    if (reply !== null) {
      privateState.latest_reply = reply;
      writeJSON(filename, privateState);
    }
    record(directory, {type: "engine", argv, cwd: config.skill_cwd, outcome, reply});
    return outcome;
  };
  const controller = (kind, input) => {
    const reply = privateState.latest_reply;
    if (!reply || !reply.action || reply.action.kind !== kind) throw new Error("Synthetic control has no matching issued action");
    const arguments_ = reply.action.arguments;
    let expected;
    if (kind === "task_read") expected = {host: arguments_.host, task_id: arguments_.task_id, episode: arguments_.episode};
    if (kind === "send") expected = {host: arguments_.host, task_id: arguments_.task_id, message: arguments_.message};
    if (kind === "observe") expected = {argv: arguments_.argv, cwd: arguments_.cwd};
    if (kind === "emit") expected = arguments_.text;
    if (kind === "heartbeat_set") expected = {
      engine: {registry_id: reply.registry_id, invocation_id: reply.invocation_id, generation: reply.generation},
      action: reply.action,
    };
    if (JSON.stringify(input) !== JSON.stringify(expected)) throw new Error("Synthetic native control shape differs from issued action");
    const replyFile = path.join(directory, "controller-reply.json");
    writeJSON(replyFile, reply);
    const controllerArgv = ["python3", "-B", path.join(directory, "tests/praxis_fixture.py"),
                            "control", "--directory", directory, "--reply", replyFile];
    record(directory, {type: "controller_start", kind, input, argv: controllerArgv, cwd: directory});
    const outcome = execute(controllerArgv, directory);
    record(directory, {type: "controller_transport", kind, outcome});
    const actualResult = successfulJSON(outcome);
    const nativeOutcome = {kind: "completed", actual_result: actualResult};
    if (kind === "task_read") {
      // The fixture registrations model the observed synthetic latest wait.
      // Keep relation evidence explicit; no native episode field is invented.
      const registration = fixture.registrations.find(item => item.host === input.host && item.task_id === input.task_id);
      nativeOutcome.summary = {task_status: actualResult.status,
        episode_context: registration ? "Synthetic latest wait: " + registration.episode : "Synthetic latest wait unavailable",
        episode_matches: Boolean(registration && registration.episode === input.episode)};
    }
    if (kind === "send") nativeOutcome.summary = {
      transport_status: actualResult.outcome,
      evidence_summary: actualResult.evidence.mode,
    };
    const artifactRecords = fs.readFileSync(path.join(directory, "control-transcript.jsonl"), "utf8").trim().split("\n");
    record(directory, {type: "control", kind, input, outcome: nativeOutcome,
                       controller_outcome: outcome, controller_record: JSON.parse(artifactRecords[artifactRecords.length - 1])});
    return nativeOutcome;
  };
  const nativeAdapters = factory.createNativeAdapters({
    taskRead: input => controller("task_read", input),
    send: input => controller("send", input),
    runArgv: input => controller("observe", input),
    emit: input => controller("emit", input),
    heartbeatSet: input => controller("heartbeat_set", input),
  });
  const binding = factory.createStructuredMonitorBinding({state, engineTransport, nativeAdapters});
  record(directory, {type: "advance_start", classification: classification === undefined ? null : classification});
  const result = await binding.advance({runKey: config.keys.run, entryKey: config.keys.entry,
                                         now: config.logical_now, classification});
  record(directory, {type: "advance_result", result});
  return result;
}

async function main(argv) {
  const command = argv.shift();
  let caseId;
  if (command === "setup") caseId = argv.shift();
  if (!["setup", "advance"].includes(command)) throw new Error("Use setup CASE or advance");
  const options = {};
  for (let index = 0; index < argv.length; index += 2) {
    const name = argv[index];
    if (!["--directory", "--classification"].includes(name) || Object.hasOwn(options, name) || argv[index + 1] === undefined) throw new Error("Invalid runner arguments");
    options[name] = argv[index + 1];
  }
  if (!options["--directory"]) throw new Error("--directory is required");
  if (command === "setup" && options["--classification"] !== undefined) throw new Error("setup does not accept classification");
  const directory = path.resolve(options["--directory"]);
  const classification = options["--classification"] === undefined ? undefined : JSON.parse(options["--classification"]);
  // Serialize separate advance calls; this is synthetic correctness plumbing.
  const lock = directory + ".runner-lock";
  const descriptor = fs.openSync(lock, "wx");
  try {
    const result = command === "setup" ? prepare(caseId, directory) : await advance(directory, classification);
    process.stdout.write(JSON.stringify(result) + "\n");
  } finally { fs.closeSync(descriptor); fs.unlinkSync(lock); }
}
main(process.argv.slice(2)).catch(error => { process.stderr.write(error.message + "\n"); process.exitCode = 1; });
