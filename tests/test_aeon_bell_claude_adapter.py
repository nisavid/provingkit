#!/usr/bin/env python3
"""Complete-cycle tests for the dormant Claude one-off Routine control."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "plugins/praxis/skills/aeon-bell"
BINDING = SKILL / "scripts/monitor_binding.js"
ADAPTER = SKILL / "scripts/claude_routine_adapter.js"
ENGINE = SKILL / "scripts/aeon_bell.py"
NOW = "2026-10-07T16:00:00+00:00"
TARGET = "2026-10-07T17:00:00+00:00"
NATIVE_TARGET = "2026-10-07T17:00:00Z"
ROUTINE_ID = "routine-00000000-0000-4000-8000-000000000457"
GATE = {
    "kind": "quota_recovery",
    "account": "controlled-account",
    "route": "controlled-route",
    "bucket": "weekly",
    "policy_revision": "controlled-policy-1",
}


RUNNER = r'''
"use strict";
const fs = require("node:fs");
const childProcess = require("node:child_process");
const bindingFactory = eval(fs.readFileSync(process.argv[1], "utf8"));
const claudeFactory = eval(fs.readFileSync(process.argv[2], "utf8"));
const engine = process.argv[3];
const skill = process.argv[4];
const entry = process.argv[5];
const now = process.argv[6];
const registration = JSON.parse(process.argv[7]);
const scenario = JSON.parse(process.argv[8]);
const slots = new Map([["entry", entry]]);
const engineReplies = [];
const remoteCalls = [];
const heartbeatSnapshots = [];
const responses = [...scenario.responses];
const copy = value => JSON.parse(JSON.stringify(value));

const engineTransport = async argv => {
  const result = childProcess.spawnSync(argv[0], argv.slice(1), {
    cwd: skill, encoding: "utf8", env: {...process.env, PYTHONDONTWRITEBYTECODE: "1"},
  });
  const outcome = {kind: "completed", exit_code: result.status,
    stdout: result.stdout || "", stderr: result.stderr || ""};
  if (result.status === 0) engineReplies.push(JSON.parse(result.stdout));
  return outcome;
};

const remoteTrigger = async input => {
  remoteCalls.push(copy(input));
  const response = responses.shift();
  if (response && response.throw_remote) throw new Error("controlled transport loss with account-secret");
  if (response && response.non_serializable_extra) {
    delete response.non_serializable_extra;
    response.arbitrary = 1n;
  }
  return response;
};

const claudeControls = claudeFactory.createClaudeRoutineControls({
  remoteTrigger,
  triggerId: scenario.trigger_id,
});
const nativeAdapters = bindingFactory.createNativeAdapters({
  taskRead: async () => ({
    kind: "completed",
    actual_result: {observed_at: now},
    summary: {
      task_status: "idle",
      episode_context: "controlled task observation proves the registered latest wait",
      episode_matches: true,
    },
  }),
  runArgv: async ({argv}) => {
    const requestsPath = argv[argv.indexOf("--requests") + 1];
    const outputPath = argv[argv.indexOf("--output") + 1];
    const reportPath = argv[argv.indexOf("--report") + 1];
    const requests = JSON.parse(fs.readFileSync(requestsPath, "utf8")).observation_requests;
    fs.writeFileSync(outputPath, JSON.stringify({observations: requests.map(item => ({
      gate_key: item.gate_key,
      status: "ok",
      observed_at: now,
      account: registration.gate.account,
      route: registration.gate.route,
      buckets: [{name: registration.gate.bucket, remaining_percent: 0}],
    })), task_states: []}) + "\n");
    fs.writeFileSync(reportPath, JSON.stringify({
      adapter: "praxis-aeon-bell-codex-status",
      gates: requests.map(item => ({gate_key: item.gate_key, kind: item.kind,
        outcome: "observed", reason: "typed-observation"})),
    }) + "\n");
    return {kind: "completed", actual_result: {exit_code: 0}};
  },
  emit: async () => ({kind: "completed", actual_result: {emitted: true}}),
  heartbeatSet: input => {
    if (!scenario.action_override) return claudeControls.heartbeatSet(input);
    const changed = copy(input);
    Object.assign(changed.action.arguments, scenario.action_override);
    return claudeControls.heartbeatSet(changed);
  },
});

const state = {
  get: key => slots.get(key),
  put: (key, value) => {
    const stored = copy(value);
    slots.set(key, stored);
    if (heartbeatSnapshots.length === 0 && stored.action &&
        stored.action.kind === "heartbeat_set" && stored.native_actual_result !== null) {
      heartbeatSnapshots.push(copy(stored.native_actual_result));
    }
  },
};
const binding = bindingFactory.createStructuredMonitorBinding({state, engineTransport, nativeAdapters});

(async () => {
  let classification;
  const results = [];
  for (let step = 0; step < 64; step += 1) {
    const result = await binding.advance({runKey: "run", entryKey: "entry", now, classification});
    results.push(result);
    classification = undefined;
    if (result.status === "needs_classification") {
      classification = {decision_id: result.view.decision_id, choice: "idle"};
      continue;
    }
    if (["complete", "unresolved", "unsupported", "stopped", "correction_required"].includes(result.status)) {
      const statusResult = childProcess.spawnSync("python3", [engine, "monitor", "status",
        "--entry-ref", entry, "--now", now], {
        cwd: skill, encoding: "utf8", env: {...process.env, PYTHONDONTWRITEBYTECODE: "1"},
      });
      if (statusResult.status !== 0) throw new Error(statusResult.stderr || statusResult.stdout);
      process.stdout.write(JSON.stringify({
        result, results, engineReplies, remoteCalls, heartbeatSnapshots,
        monitorStatus: JSON.parse(statusResult.stdout),
        responses_remaining: responses.length,
      }));
      return;
    }
  }
  throw new Error("cycle exceeded 64 binding advances");
})().catch(error => { process.stderr.write(error.stack + "\n"); process.exit(1); });
'''


CROSS_INVOCATION_RUNNER = r'''
"use strict";
const fs = require("node:fs");
const childProcess = require("node:child_process");
const bindingFactory = eval(fs.readFileSync(process.argv[1], "utf8"));
const claudeFactory = eval(fs.readFileSync(process.argv[2], "utf8"));
const engine = process.argv[3];
const skill = process.argv[4];
const entry = process.argv[5];
const now = process.argv[6];
const triggerId = process.argv[7];
const lateEffective = process.argv[8];
const firstMode = process.argv[9];
const slots = new Map([["entry", entry]]);
const remoteCalls = [];
const updates = [];
const pendingReadbacks = [];
let releaseFirstUpdate;
let signalFirstUpdate;
const firstUpdateStarted = new Promise(resolve => { signalFirstUpdate = resolve; });
const copy = value => JSON.parse(JSON.stringify(value));
const nativeResponse = payload => ({kind: "completed", status: 200, json: JSON.stringify(payload)});

const engineTransport = async argv => {
  const result = childProcess.spawnSync(argv[0], argv.slice(1), {
    cwd: skill, encoding: "utf8", env: {...process.env, PYTHONDONTWRITEBYTECODE: "1"},
  });
  return {kind: "completed", exit_code: result.status,
    stdout: result.stdout || "", stderr: result.stderr || ""};
};

const remoteTrigger = async input => {
  remoteCalls.push(copy(input));
  if (input.action === "get") {
    if (pendingReadbacks.length > 0) {
      return nativeResponse({id: triggerId, enabled: true,
        next_run_at: pendingReadbacks.shift()});
    }
    return nativeResponse({id: triggerId, enabled: false,
      run_once_at: "2026-10-07T15:00:00Z", cron_expression: null});
  }
  updates.push(copy(input));
  if (updates.length === 1) {
    signalFirstUpdate();
    if (firstMode === "throw") throw new Error("controlled loss after update start");
    return await new Promise(resolve => {
      releaseFirstUpdate = () => {
        pendingReadbacks.push(lateEffective);
        resolve(nativeResponse({id: triggerId, enabled: true}));
      };
    });
  }
  pendingReadbacks.push(input.body.run_once_at);
  return nativeResponse({id: triggerId, enabled: true});
};

const controls = claudeFactory.createClaudeRoutineControls({remoteTrigger, triggerId});
const adapters = bindingFactory.createNativeAdapters({
  emit: async () => ({kind: "completed", actual_result: {emitted: true}}),
  heartbeatSet: controls.heartbeatSet,
});
const binding = bindingFactory.createStructuredMonitorBinding({
  state: {get: key => slots.get(key), put: (key, value) => slots.set(key, copy(value))},
  engineTransport,
  nativeAdapters: adapters,
});

function status() {
  const result = childProcess.spawnSync("python3", [engine, "monitor", "status",
    "--entry-ref", entry, "--now", now], {
    cwd: skill, encoding: "utf8", env: {...process.env, PYTHONDONTWRITEBYTECODE: "1"},
  });
  if (result.status !== 0) throw new Error(result.stderr || result.stdout);
  return JSON.parse(result.stdout);
}

function settleLate() {
  const continuation = slots.get("run-1").continuation;
  const result = childProcess.spawnSync("python3", [engine, "monitor", "continue",
    "--continuation", continuation, "--result-json", JSON.stringify({
      applied: true, next_run_at: lateEffective,
    }), "--now", now], {
    cwd: skill, encoding: "utf8", env: {...process.env, PYTHONDONTWRITEBYTECODE: "1"},
  });
  if (result.status !== 0) throw new Error(result.stderr || result.stdout);
  return JSON.parse(result.stdout);
}

(async () => {
  const firstPromise = binding.advance({runKey: "run-1", entryKey: "entry", now});
  await firstUpdateStarted;
  const first = firstMode === "throw" ? await firstPromise : null;
  const second = await binding.advance({runKey: "run-2", entryKey: "entry", now});
  const updatesBeforeSettlement = updates.length;
  let late;
  if (firstMode === "throw") late = settleLate();
  else {
    releaseFirstUpdate();
    late = await firstPromise;
  }
  const afterLate = status();
  const third = await binding.advance({runKey: "run-3", entryKey: "entry", now});
  process.stdout.write(JSON.stringify({
    first, second, late, third, updatesBeforeSettlement, updates, remoteCalls, afterLate,
  }));
})().catch(error => { process.stderr.write(error.stack + "\n"); process.exit(1); });
'''


POST_UPDATE_READBACK_RUNNER = r'''
"use strict";
const fs = require("node:fs");
const childProcess = require("node:child_process");
const bindingFactory = eval(fs.readFileSync(process.argv[1], "utf8"));
const claudeFactory = eval(fs.readFileSync(process.argv[2], "utf8"));
const engine = process.argv[3];
const skill = process.argv[4];
const entry = process.argv[5];
const now = process.argv[6];
const triggerId = process.argv[7];
const scenario = JSON.parse(process.argv[8]);
const slots = new Map([["entry", entry]]);
const remoteCalls = [];
const updates = [];
let getCount = 0;
const copy = value => JSON.parse(JSON.stringify(value));
const nativeResponse = payload => ({kind: "completed", status: 200,
  json: JSON.stringify(payload)});

const engineTransport = async argv => {
  const result = childProcess.spawnSync(argv[0], argv.slice(1), {
    cwd: skill, encoding: "utf8", env: {...process.env, PYTHONDONTWRITEBYTECODE: "1"},
  });
  return {kind: "completed", exit_code: result.status,
    stdout: result.stdout || "", stderr: result.stderr || ""};
};

const remoteTrigger = async input => {
  remoteCalls.push(copy(input));
  if (input.action === "update") {
    updates.push(copy(input));
    return nativeResponse({id: triggerId, enabled: true});
  }
  getCount += 1;
  if (getCount === 1 || getCount === 3) {
    return nativeResponse({id: triggerId, enabled: false,
      run_once_at: "2026-10-07T15:00:00Z", cron_expression: null});
  }
  if (getCount === 2) {
    if (scenario.readback && scenario.readback.throw_remote) {
      throw new Error("controlled readback loss with account-secret");
    }
    return scenario.readback;
  }
  return nativeResponse({id: triggerId, enabled: true,
    next_run_at: input.body && input.body.run_once_at || "2026-10-07T17:00:00Z"});
};

const controls = claudeFactory.createClaudeRoutineControls({remoteTrigger, triggerId});
const adapters = bindingFactory.createNativeAdapters({
  taskRead: async () => ({
    kind: "completed",
    actual_result: {observed_at: now},
    summary: {task_status: "idle", episode_context: "controlled matching episode",
      episode_matches: true},
  }),
  runArgv: async ({argv}) => {
    const requestsPath = argv[argv.indexOf("--requests") + 1];
    const outputPath = argv[argv.indexOf("--output") + 1];
    const reportPath = argv[argv.indexOf("--report") + 1];
    const requests = JSON.parse(fs.readFileSync(requestsPath, "utf8")).observation_requests;
    fs.writeFileSync(outputPath, JSON.stringify({observations: requests.map(item => ({
      gate_key: item.gate_key, status: "ok", observed_at: now,
      account: "controlled-account", route: "controlled-route",
      buckets: [{name: "weekly", remaining_percent: 0}],
    })), task_states: []}) + "\n");
    fs.writeFileSync(reportPath, JSON.stringify({adapter: "praxis-aeon-bell-codex-status",
      gates: requests.map(item => ({gate_key: item.gate_key, kind: item.kind,
        outcome: "observed", reason: "typed-observation"}))}) + "\n");
    return {kind: "completed", actual_result: {exit_code: 0}};
  },
  emit: async () => ({kind: "completed", actual_result: {emitted: true}}),
  heartbeatSet: controls.heartbeatSet,
});
const binding = bindingFactory.createStructuredMonitorBinding({
  state: {get: key => slots.get(key), put: (key, value) => slots.set(key, copy(value))},
  engineTransport,
  nativeAdapters: adapters,
});

async function advance(runKey) {
  let classification;
  for (let step = 0; step < 64; step += 1) {
    const result = await binding.advance({runKey, entryKey: "entry", now, classification});
    classification = undefined;
    if (result.status === "needs_classification") {
      classification = {decision_id: result.view.decision_id, choice: "idle"};
      continue;
    }
    if (["complete", "unresolved", "unsupported", "stopped", "correction_required"].includes(result.status)) {
      return result;
    }
  }
  throw new Error("cycle exceeded 64 binding advances");
}

function status() {
  const result = childProcess.spawnSync("python3", [engine, "monitor", "status",
    "--entry-ref", entry, "--now", now], {
    cwd: skill, encoding: "utf8", env: {...process.env, PYTHONDONTWRITEBYTECODE: "1"},
  });
  if (result.status !== 0) throw new Error(result.stderr || result.stdout);
  return JSON.parse(result.stdout);
}

function continueLate(continuation, resultJson) {
  const result = childProcess.spawnSync("python3", [engine, "monitor", "continue",
    "--continuation", continuation, "--result-json", JSON.stringify(resultJson),
    "--now", now], {
    cwd: skill, encoding: "utf8", env: {...process.env, PYTHONDONTWRITEBYTECODE: "1"},
  });
  if (result.status !== 0) throw new Error(result.stderr || result.stdout);
  return JSON.parse(result.stdout);
}

(async () => {
  const first = await advance("run-1");
  const continuation = slots.get("run-1").continuation;
  const second = await advance("run-2");
  const beforeLate = status();
  let late = null;
  let afterLate = null;
  let third = null;
  if (Object.prototype.hasOwnProperty.call(scenario, "late_result")) {
    late = continueLate(continuation, scenario.late_result);
    afterLate = status();
    if (scenario.run_third === true) third = await advance("run-3");
  }
  process.stdout.write(JSON.stringify({
    first, second, continuation, updates, remoteCalls, beforeLate, late, afterLate,
    third, monitorStatus: status(),
  }));
})().catch(error => { process.stderr.write(error.stack + "\n"); process.exit(1); });
'''


def native_response(payload: object, *, status: int = 200) -> dict:
    return {
        "kind": "completed",
        "status": status,
        "json": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        "summary": "ignored native prose",
    }


class ClaudeRoutineAdapterCycleTests(unittest.TestCase):
    maxDiff = None

    def command(self, *arguments: object) -> dict:
        result = subprocess.run(
            ["python3", "-B", str(ENGINE), *map(str, arguments)],
            cwd=SKILL,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def run_cycle(
        self,
        responses: list[dict],
        *,
        trigger_id: object = ROUTINE_ID,
        action_override: dict | None = None,
        now: str = NOW,
    ) -> tuple[dict, dict]:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            store = directory / "store"
            binding_path = directory / "controlled-binding.json"
            binding_path.write_text("{}\n")
            bound = self.command(
                "monitor", "bind", "--store", store, "--initialize-registry",
                "--binding", binding_path, "--heartbeat", ROUTINE_ID,
            )
            registration = self.command(
                "register", "--store", store, "--owner", "controlled-owner",
                "--host", "controlled-host", "--task-id", "controlled-task",
                "--episode", "claude-episode-1", "--gate-json", json.dumps(GATE),
                "--continuation", "Continue the controlled request.",
                "--poll-interval-minutes", "60", "--now", now,
            )
            result = subprocess.run(
                [
                    "node", "-e", RUNNER, str(BINDING), str(ADAPTER), str(ENGINE),
                    str(SKILL), bound["entry_ref"], now, json.dumps(registration),
                    json.dumps({
                        "responses": responses,
                        "trigger_id": trigger_id,
                        "action_override": action_override,
                    }),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout), self.command("inspect", "--store", store, "--now", now)

    def run_post_update_readback(
        self,
        readback: dict,
        *,
        late_result: dict | None = None,
        run_third: bool = False,
    ) -> dict:
        with tempfile.TemporaryDirectory() as directory_name:
            store = Path(directory_name) / "store"
            bound = self.command(
                "monitor", "bind", "--store", store, "--initialize-registry",
                "--heartbeat", ROUTINE_ID,
            )
            self.command(
                "register", "--store", store, "--owner", "controlled-owner",
                "--host", "controlled-host", "--task-id", "controlled-task",
                "--episode", "claude-episode-1", "--gate-json", json.dumps(GATE),
                "--continuation", "Continue the controlled request.",
                "--poll-interval-minutes", "60", "--now", NOW,
            )
            scenario = {"readback": readback}
            if late_result is not None:
                scenario["late_result"] = late_result
                scenario["run_third"] = run_third
            result = subprocess.run(
                [
                    "node", "-e", POST_UPDATE_READBACK_RUNNER, str(BINDING),
                    str(ADAPTER), str(ENGINE), str(SKILL), bound["entry_ref"],
                    NOW, ROUTINE_ID, json.dumps(scenario),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_successful_update_with_unstarted_readback_holds_fresh_entry(self) -> None:
        observed = self.run_post_update_readback({"kind": "not_started"})

        self.assertEqual(observed["first"]["status"], "unresolved")
        self.assertEqual(observed["second"]["status"], "complete")
        self.assertEqual(observed["updates"], [{
            "action": "update",
            "trigger_id": ROUTINE_ID,
            "body": {"run_once_at": "2026-10-07T22:00:00Z", "enabled": True},
        }])
        self.assertEqual(observed["monitorStatus"]["interrupted_effects"], {
            "count": 1,
            "reserved_send_attempts": 0,
            "heartbeat_holds": 1,
        })

    def test_each_other_nonauthoritative_readback_holds_fresh_entry(self) -> None:
        cases = [
            ("transport-unknown", {"kind": "unknown"}),
            ("exception", {"throw_remote": True}),
            ("bad-status", native_response({}, status=503)),
            ("malformed-data", {
                "kind": "completed", "status": 200, "json": "{not-json",
            }),
            ("wrong-id", native_response({
                "id": "different-routine", "enabled": True,
                "next_run_at": NATIVE_TARGET,
            })),
            ("disabled", native_response({
                "id": ROUTINE_ID, "enabled": False, "next_run_at": NATIVE_TARGET,
            })),
            ("missing-next-run", native_response({
                "id": ROUTINE_ID, "enabled": True,
            })),
            ("invalid-next-run", native_response({
                "id": ROUTINE_ID, "enabled": True,
                "next_run_at": "2026-02-30T17:00:00Z",
            })),
        ]
        for name, readback in cases:
            with self.subTest(name=name):
                observed = self.run_post_update_readback(readback)

                self.assertEqual(observed["first"]["status"], "unresolved")
                self.assertEqual(observed["second"]["status"], "complete")
                self.assertEqual(len(observed["updates"]), 1)
                self.assertEqual(
                    observed["monitorStatus"]["interrupted_effects"],
                    {"count": 1, "reserved_send_attempts": 0, "heartbeat_holds": 1},
                )
                self.assertNotIn("account-secret", json.dumps(observed, sort_keys=True))

    def test_ambiguous_exact_late_failure_retains_heartbeat_hold(self) -> None:
        observed = self.run_post_update_readback(
            {"kind": "not_started"},
            late_result={
                "disposition": "failed",
                "reason": "native-readback-remains-uncertain",
            },
            run_third=True,
        )

        self.assertEqual(observed["late"], {
            "status": "stopped",
            "reason": "superseded-invocation",
            "late_result": "unresolved",
        })
        self.assertEqual(
            observed["afterLate"]["interrupted_effects"],
            {"count": 1, "reserved_send_attempts": 0, "heartbeat_holds": 1},
        )
        self.assertEqual(observed["third"]["status"], "complete")
        self.assertEqual(len(observed["updates"]), 1)

    def test_definitive_exact_late_result_releases_hold_and_allows_scheduling(self) -> None:
        effective = "2026-10-07T14:30:00.875-04:00"
        observed = self.run_post_update_readback(
            {"kind": "not_started"},
            late_result={"applied": True, "next_run_at": effective},
            run_third=True,
        )

        self.assertEqual(observed["late"], {
            "status": "stopped",
            "reason": "superseded-invocation",
            "late_result": "recorded",
        })
        self.assertEqual(observed["afterLate"]["heartbeat_effective"], {
            "next_run_at": "2026-10-07T18:30:00.875+00:00",
            "recorded_at": NOW,
            "source": "late-result",
        })
        self.assertEqual(
            observed["afterLate"]["interrupted_effects"],
            {"count": 0, "reserved_send_attempts": 0, "heartbeat_holds": 0},
        )
        self.assertEqual(observed["third"]["status"], "complete")
        self.assertEqual(len(observed["updates"]), 2)

    def test_microsecond_engine_clock_rounds_heartbeat_request_up_to_millisecond(self) -> None:
        now = "2026-10-07T16:00:00.123001+00:00"
        rounded_target = "2026-10-07T17:00:00.124+00:00"
        native_target = "2026-10-07T17:00:00.124Z"
        observed, inspected = self.run_cycle([
            native_response({
                "id": ROUTINE_ID,
                "enabled": False,
                "run_once_at": "2026-10-07T15:00:00Z",
                "cron_expression": None,
            }),
            native_response({"id": ROUTINE_ID, "enabled": True}),
            native_response({
                "id": ROUTINE_ID,
                "enabled": True,
                "next_run_at": native_target,
            }),
        ], now=now)

        self.assertEqual(observed["result"]["status"], "complete")
        self.assertEqual(observed["remoteCalls"], [
            {"action": "get", "trigger_id": ROUTINE_ID},
            {
                "action": "update",
                "trigger_id": ROUTINE_ID,
                "body": {"run_once_at": native_target, "enabled": True},
            },
            {"action": "get", "trigger_id": ROUTINE_ID},
        ])
        heartbeat = observed["engineReplies"][-1]["outcome"]["heartbeat"]
        self.assertEqual(heartbeat["target_at"], rounded_target)
        self.assertEqual(heartbeat["result"], "applied")
        self.assertEqual(observed["monitorStatus"]["heartbeat_effective"], {
            "next_run_at": rounded_target,
            "recorded_at": now,
            "source": "action-result",
        })
        self.assertEqual(inspected["schedule"]["next_check_at"], "2026-10-07T17:00:00.123001+00:00")

    def test_aligned_and_boundary_engine_clocks_complete_native_cycle(self) -> None:
        cases = [
            (
                "integral",
                "2026-10-07T16:00:00+00:00",
                "2026-10-07T17:00:00+00:00",
                "2026-10-07T17:00:00Z",
            ),
            (
                "millisecond-aligned",
                "2026-10-07T16:00:00.123+00:00",
                "2026-10-07T17:00:00.123+00:00",
                "2026-10-07T17:00:00.123Z",
            ),
            (
                "second-carry",
                "2026-10-07T16:59:59.999001+00:00",
                "2026-10-07T18:00:00+00:00",
                "2026-10-07T18:00:00Z",
            ),
            (
                "day-carry",
                "2026-10-07T23:59:59.999001+00:00",
                "2026-10-08T01:00:00+00:00",
                "2026-10-08T01:00:00Z",
            ),
        ]
        for name, now, intended, native_target in cases:
            with self.subTest(name=name):
                observed, _ = self.run_cycle([
                    native_response({
                        "id": ROUTINE_ID,
                        "enabled": False,
                        "run_once_at": "2026-10-07T15:00:00Z",
                        "cron_expression": None,
                    }),
                    native_response({"id": ROUTINE_ID, "enabled": True}),
                    native_response({
                        "id": ROUTINE_ID,
                        "enabled": True,
                        "next_run_at": native_target,
                    }),
                ], now=now)

                self.assertEqual(observed["result"]["status"], "complete")
                self.assertEqual(observed["remoteCalls"], [
                    {"action": "get", "trigger_id": ROUTINE_ID},
                    {
                        "action": "update",
                        "trigger_id": ROUTINE_ID,
                        "body": {"run_once_at": native_target, "enabled": True},
                    },
                    {"action": "get", "trigger_id": ROUTINE_ID},
                ])
                heartbeat = observed["engineReplies"][-1]["outcome"]["heartbeat"]
                self.assertEqual(heartbeat["target_at"], intended)
                self.assertEqual(heartbeat["result"], "applied")
                self.assertEqual(observed["monitorStatus"]["heartbeat_effective"], {
                    "next_run_at": intended,
                    "recorded_at": now,
                    "source": "action-result",
                })

    def test_rearms_existing_one_off_and_uses_effective_readback(self) -> None:
        effective = "2026-10-07T13:00:00.125-04:00"
        preflight = {
            "id": ROUTINE_ID,
            "enabled": False,
            "run_once_at": "2026-10-07T15:00:00Z",
            "next_run_at": None,
            "cron_expression": None,
            "session_request": {"account": "must-not-copy"},
            "job_config": {"environment_id": "must-not-copy"},
            "mcp_connections": [{"name": "must-not-copy"}],
        }
        update_reply = {
            "id": ROUTINE_ID,
            "enabled": True,
            "run_once_at": NATIVE_TARGET,
            "account": "must-not-retain",
        }
        readback = {
            "id": ROUTINE_ID,
            "enabled": True,
            "run_once_at": NATIVE_TARGET,
            "next_run_at": effective,
            "job_config": {"model": "must-not-retain"},
        }

        observed, inspected = self.run_cycle([
            native_response(preflight),
            native_response(update_reply),
            native_response(readback),
        ])

        self.assertEqual(observed["result"]["status"], "complete")
        self.assertEqual(observed["responses_remaining"], 0)
        self.assertEqual(observed["remoteCalls"], [
            {"action": "get", "trigger_id": ROUTINE_ID},
            {
                "action": "update",
                "trigger_id": ROUTINE_ID,
                "body": {"run_once_at": NATIVE_TARGET, "enabled": True},
            },
            {"action": "get", "trigger_id": ROUTINE_ID},
        ])
        self.assertEqual(observed["heartbeatSnapshots"], [{
            "kind": "completed",
            "actual_result": {"applied": True, "next_run_at": effective},
        }])
        serialized = json.dumps(observed, sort_keys=True)
        for forbidden in ("must-not-copy", "must-not-retain", "session_request", "job_config", "mcp_connections"):
            self.assertNotIn(forbidden, serialized)
        final = observed["engineReplies"][-1]
        self.assertEqual(final["status"], "complete")
        self.assertEqual(final["outcome"]["heartbeat"]["target_at"], TARGET)
        self.assertEqual(final["outcome"]["heartbeat"]["result"], "applied")
        self.assertEqual(observed["monitorStatus"]["heartbeat_effective"], {
            "next_run_at": "2026-10-07T17:00:00.125+00:00",
            "recorded_at": NOW,
            "source": "action-result",
        })
        self.assertEqual(inspected["schedule"]["next_check_at"], TARGET)

    def test_unsettled_heartbeat_holds_fresh_invocations_until_late_result(self) -> None:
        late_effective = "2026-10-07T14:30:00.875-04:00"
        for first_mode in ("delayed", "throw"):
            with self.subTest(first_mode=first_mode), tempfile.TemporaryDirectory() as directory_name:
                store = Path(directory_name) / "store"
                bound = self.command(
                    "monitor", "bind", "--store", store, "--initialize-registry",
                    "--heartbeat", ROUTINE_ID,
                )
                result = subprocess.run(
                    [
                        "node", "-e", CROSS_INVOCATION_RUNNER, str(BINDING),
                        str(ADAPTER), str(ENGINE), str(SKILL), bound["entry_ref"],
                        NOW, ROUTINE_ID, late_effective, first_mode,
                    ],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )

            self.assertEqual(result.returncode, 0, result.stderr)
            observed = json.loads(result.stdout)
            if first_mode == "throw":
                self.assertEqual(observed["first"]["status"], "unresolved")
            self.assertEqual(observed["second"]["status"], "complete")
            self.assertEqual(observed["updatesBeforeSettlement"], 1)
            self.assertEqual(observed["late"]["status"], "stopped")
            self.assertEqual(observed["afterLate"]["heartbeat_effective"], {
                "next_run_at": "2026-10-07T18:30:00.875+00:00",
                "recorded_at": NOW,
                "source": "late-result",
            })
            self.assertEqual(observed["third"]["status"], "complete")
            self.assertEqual(len(observed["updates"]), 2)

    def test_omitted_recurrence_discriminator_never_mutates(self) -> None:
        observed, _ = self.run_cycle([native_response({
            "id": ROUTINE_ID,
            "enabled": False,
            "run_once_at": "2026-10-07T15:00:00Z",
        })])

        self.assertEqual(observed["result"]["status"], "complete")
        self.assertEqual(observed["remoteCalls"], [
            {"action": "get", "trigger_id": ROUTINE_ID},
        ])
        self.assertEqual(observed["heartbeatSnapshots"], [{
            "kind": "completed",
            "actual_result": {
                "disposition": "not_performed",
                "reason": "native-routine-unsupported",
            },
        }])
        self.assertEqual(
            observed["engineReplies"][-1]["outcome"]["heartbeat"]["result"],
            "not_performed",
        )

    def test_recurring_or_malformed_configuration_never_mutates(self) -> None:
        recurring_values = ["0 * * * *", 17]
        for cron_expression in recurring_values:
            with self.subTest(cron_expression=cron_expression):
                observed, _ = self.run_cycle([native_response({
                    "id": ROUTINE_ID,
                    "enabled": True,
                    "run_once_at": "2026-10-07T15:00:00Z",
                    "cron_expression": cron_expression,
                })])

                self.assertEqual(observed["result"]["status"], "complete")
                self.assertEqual(observed["remoteCalls"], [
                    {"action": "get", "trigger_id": ROUTINE_ID},
                ])
                self.assertEqual(observed["heartbeatSnapshots"], [{
                    "kind": "completed",
                    "actual_result": {
                        "disposition": "not_performed",
                        "reason": "native-routine-unsupported",
                    },
                }])
                self.assertEqual(
                    observed["engineReplies"][-1]["outcome"]["heartbeat"]["result"],
                    "not_performed",
                )

    def test_invalid_target_or_mismatched_heartbeat_never_calls_native_control(self) -> None:
        cases = [
            ("unknown-offset", ROUTINE_ID, {"target_at": "2026-10-07T17:00:00-00:00"},
             "invalid-heartbeat-target"),
            ("wrong-heartbeat", ROUTINE_ID, {"heartbeat": "different-routine"},
             "heartbeat-id-mismatch"),
        ]
        for name, trigger_id, override, reason in cases:
            with self.subTest(name=name):
                observed, _ = self.run_cycle(
                    [], trigger_id=trigger_id, action_override=override,
                )

                self.assertEqual(observed["result"]["status"], "complete")
                self.assertEqual(observed["remoteCalls"], [])
                self.assertEqual(observed["heartbeatSnapshots"], [{
                    "kind": "completed",
                    "actual_result": {"disposition": "not_performed", "reason": reason},
                }])
                self.assertEqual(
                    observed["engineReplies"][-1]["outcome"]["heartbeat"]["result"],
                    "not_performed",
                )

    def test_utc_year_crossings_are_rejected_while_in_range_offsets_remain_supported(self) -> None:
        crossing_targets = [
            "0001-01-01T00:00:00+14:00",
            "9999-12-31T23:59:59-14:00",
        ]
        for target_at in crossing_targets:
            with self.subTest(seam="target", target_at=target_at):
                observed, _ = self.run_cycle([], action_override={"target_at": target_at})

                self.assertEqual(observed["result"]["status"], "complete")
                self.assertEqual(observed["remoteCalls"], [])
                self.assertEqual(observed["heartbeatSnapshots"], [{
                    "kind": "completed",
                    "actual_result": {
                        "disposition": "not_performed",
                        "reason": "invalid-heartbeat-target",
                    },
                }])

        underflow = "0001-01-01T00:00:00+14:00"
        preflight_underflow, _ = self.run_cycle([native_response({
            "id": ROUTINE_ID,
            "enabled": False,
            "run_once_at": underflow,
            "cron_expression": None,
        })])
        self.assertEqual(preflight_underflow["result"]["status"], "complete")
        self.assertEqual(preflight_underflow["remoteCalls"], [
            {"action": "get", "trigger_id": ROUTINE_ID},
        ])
        self.assertEqual(preflight_underflow["heartbeatSnapshots"], [{
            "kind": "completed",
            "actual_result": {
                "disposition": "not_performed",
                "reason": "native-routine-unsupported",
            },
        }])
        self.assertEqual(
            preflight_underflow["engineReplies"][-1]["outcome"]["heartbeat"]["result"],
            "not_performed",
        )

        preflight = native_response({
            "id": ROUTINE_ID,
            "enabled": False,
            "run_once_at": "2026-10-07T15:00:00Z",
            "cron_expression": None,
        })
        update = native_response({"id": ROUTINE_ID, "enabled": True})
        readback_underflow, _ = self.run_cycle([
            preflight,
            update,
            native_response({
                "id": ROUTINE_ID,
                "enabled": True,
                "next_run_at": underflow,
            }),
        ])
        self.assertEqual(readback_underflow["result"]["status"], "unresolved")
        self.assertEqual(len(readback_underflow["remoteCalls"]), 3)
        self.assertEqual(readback_underflow["heartbeatSnapshots"], [])

        controls = [
            ("0001-01-01T14:00:00+14:00", "0001-01-01T00:00:00Z"),
            ("9999-12-31T09:59:59-14:00", "9999-12-31T23:59:59Z"),
        ]
        for target_at, normalized in controls:
            with self.subTest(seam="in-range-control", target_at=target_at):
                observed, _ = self.run_cycle(
                    [
                        native_response({
                            "id": ROUTINE_ID,
                            "enabled": False,
                            "run_once_at": target_at,
                            "cron_expression": None,
                        }),
                        update,
                        native_response({
                            "id": ROUTINE_ID,
                            "enabled": True,
                            "next_run_at": target_at,
                        }),
                    ],
                    action_override={"target_at": target_at},
                )

                self.assertEqual(observed["result"]["status"], "complete")
                self.assertEqual(observed["remoteCalls"][1]["body"], {
                    "run_once_at": normalized,
                    "enabled": True,
                })
                self.assertEqual(len(observed["remoteCalls"]), 3)
                self.assertEqual(
                    observed["engineReplies"][-1]["outcome"]["heartbeat"]["result"],
                    "applied-off-target",
                )

    def test_off_target_readback_is_reported_as_observed(self) -> None:
        effective = "2026-10-07T17:05:30-04:00"
        observed, inspected = self.run_cycle([
            native_response({
                "id": ROUTINE_ID,
                "enabled": True,
                "run_once_at": "2026-10-07T15:00:00Z",
                "cron_expression": "",
            }),
            native_response({"id": ROUTINE_ID, "enabled": True}),
            native_response({
                "id": ROUTINE_ID,
                "enabled": True,
                "next_run_at": effective,
            }),
        ])

        self.assertEqual(observed["result"]["status"], "complete")
        self.assertEqual(observed["remoteCalls"][1]["body"], {
            "run_once_at": NATIVE_TARGET,
            "enabled": True,
        })
        self.assertEqual(observed["heartbeatSnapshots"], [{
            "kind": "completed",
            "actual_result": {"applied": True, "next_run_at": effective},
        }])
        heartbeat = observed["engineReplies"][-1]["outcome"]["heartbeat"]
        self.assertEqual(heartbeat["target_at"], TARGET)
        self.assertEqual(heartbeat["result"], "applied-off-target")
        self.assertEqual(inspected["schedule"]["next_check_at"], TARGET)

    def test_invalid_preflight_states_complete_without_mutation(self) -> None:
        cases = [
            ("missing-id", native_response({
                "enabled": False, "run_once_at": "2026-10-07T15:00:00Z",
                "cron_expression": None,
            })),
            ("wrong-id", native_response({
                "id": "different-routine", "enabled": False,
                "run_once_at": "2026-10-07T15:00:00Z",
                "cron_expression": None,
            })),
            ("missing-run-once", native_response({
                "id": ROUTINE_ID, "enabled": False, "cron_expression": None,
            })),
            ("normalized-date", native_response({
                "id": ROUTINE_ID, "enabled": False,
                "run_once_at": "2026-02-30T15:00:00Z",
                "cron_expression": None,
            })),
            ("malformed-json", {
                "kind": "completed", "status": 200, "json": "{not-json",
            }),
            ("http-error", native_response({}, status=503)),
            ("missing-status", {"kind": "completed", "json": "{}"}),
        ]
        for name, response in cases:
            with self.subTest(name=name):
                observed, _ = self.run_cycle([response])

                self.assertEqual(observed["result"]["status"], "complete")
                self.assertEqual(observed["remoteCalls"], [
                    {"action": "get", "trigger_id": ROUTINE_ID},
                ])
                self.assertEqual(
                    observed["engineReplies"][-1]["outcome"]["heartbeat"]["result"],
                    "not_performed",
                )
                self.assertEqual(
                    observed["monitorStatus"]["interrupted_effects"],
                    {"count": 0, "reserved_send_attempts": 0, "heartbeat_holds": 0},
                )
                retained = json.dumps(observed["heartbeatSnapshots"], sort_keys=True)
                self.assertNotIn("not-json", retained)
                self.assertNotIn("different-routine", retained)

    def test_definitive_no_write_update_rejection_completes_without_hold(self) -> None:
        preflight = native_response({
            "id": ROUTINE_ID,
            "enabled": False,
            "run_once_at": "2026-10-07T15:00:00Z",
            "cron_expression": None,
        })
        update_error, _ = self.run_cycle([preflight, native_response({}, status=409)])
        self.assertEqual(update_error["result"]["status"], "complete")
        self.assertEqual(len(update_error["remoteCalls"]), 2)
        self.assertEqual(
            update_error["engineReplies"][-1]["outcome"]["heartbeat"]["result"],
            "failed",
        )
        self.assertEqual(
            update_error["monitorStatus"]["interrupted_effects"],
            {"count": 0, "reserved_send_attempts": 0, "heartbeat_holds": 0},
        )

    def test_transport_uncertainty_is_never_retried_or_upgraded(self) -> None:
        preflight = native_response({
            "id": ROUTINE_ID,
            "enabled": False,
            "run_once_at": "2026-10-07T15:00:00Z",
            "cron_expression": "",
        })
        update = native_response({"id": ROUTINE_ID, "enabled": True})
        cases = [
            ("preflight-not-started", [{"kind": "not_started"}], "complete", 1, "not_performed"),
            ("preflight-unknown", [{"kind": "unknown"}], "unresolved", 1, None),
            ("preflight-lost", [{"throw_remote": True}], "unresolved", 1, None),
            ("update-not-started", [preflight, {"kind": "not_started"}],
             "complete", 2, "not_performed"),
            ("update-unknown", [preflight, {"kind": "unknown"}], "unresolved", 2, None),
            ("update-lost", [preflight, {"throw_remote": True}], "unresolved", 2, None),
            ("update-malformed-json", [
                preflight, {"kind": "completed", "status": 200, "json": "{not-json"},
            ], "unresolved", 2, None),
            ("update-missing-json", [
                preflight, {"kind": "completed", "status": 200},
            ], "unresolved", 2, None),
            ("update-missing-status", [
                preflight, {"kind": "completed", "json": "{}"},
            ], "unresolved", 2, None),
            ("readback-not-started", [preflight, update, {"kind": "not_started"}],
             "unresolved", 3, None),
            ("readback-unknown", [preflight, update, {"kind": "unknown"}],
             "unresolved", 3, None),
            ("readback-lost", [preflight, update, {"throw_remote": True}],
             "unresolved", 3, None),
        ]
        for name, responses, status, calls, engine_result in cases:
            with self.subTest(name=name):
                observed, _ = self.run_cycle(responses)

                self.assertEqual(observed["result"]["status"], status)
                self.assertEqual(len(observed["remoteCalls"]), calls)
                self.assertEqual(observed["responses_remaining"], 0)
                if engine_result is not None:
                    self.assertEqual(
                        observed["engineReplies"][-1]["outcome"]["heartbeat"]["result"],
                        engine_result,
                    )
                else:
                    self.assertNotIn("account-secret", json.dumps(observed, sort_keys=True))
                if name in {"preflight-not-started", "update-not-started"}:
                    self.assertEqual(
                        observed["monitorStatus"]["interrupted_effects"],
                        {"count": 0, "reserved_send_attempts": 0, "heartbeat_holds": 0},
                    )

    def test_not_started_outcomes_retain_only_the_transport_kind(self) -> None:
        sentinel = "transport-envelope-must-not-persist"
        not_started = {
            "kind": "not_started",
            "summary": sentinel,
            "arbitrary": {"nested": [sentinel]},
        }
        preflight = native_response({
            "id": ROUTINE_ID,
            "enabled": False,
            "run_once_at": "2026-10-07T15:00:00Z",
            "cron_expression": None,
        })
        cases = [
            ("preflight", [not_started], 1),
            ("update", [preflight, not_started], 2),
        ]
        for seam, responses, calls in cases:
            with self.subTest(seam=seam):
                observed, inspected = self.run_cycle(responses)

                self.assertEqual(observed["result"]["status"], "complete")
                self.assertEqual(len(observed["remoteCalls"]), calls)
                self.assertEqual(observed["responses_remaining"], 0)
                self.assertEqual(observed["heartbeatSnapshots"], [{"kind": "not_started"}])
                self.assertEqual(
                    observed["engineReplies"][-1]["outcome"]["heartbeat"]["result"],
                    "not_performed",
                )
                retained_state = json.dumps(
                    {"cycle": observed, "engine": inspected}, sort_keys=True,
                )
                self.assertNotIn(sentinel, retained_state)
                self.assertNotIn("arbitrary", retained_state)

    def test_non_serializable_not_started_extra_does_not_disrupt_classification(self) -> None:
        observed, inspected = self.run_cycle([{
            "kind": "not_started",
            "non_serializable_extra": True,
        }])

        self.assertEqual(observed["result"]["status"], "complete")
        self.assertEqual(observed["remoteCalls"], [
            {"action": "get", "trigger_id": ROUTINE_ID},
        ])
        self.assertEqual(observed["responses_remaining"], 0)
        self.assertEqual(observed["heartbeatSnapshots"], [{"kind": "not_started"}])
        self.assertEqual(
            observed["engineReplies"][-1]["outcome"]["heartbeat"]["result"],
            "not_performed",
        )
        self.assertNotIn("arbitrary", json.dumps(
            {"cycle": observed, "engine": inspected}, sort_keys=True,
        ))


if __name__ == "__main__":
    unittest.main()
