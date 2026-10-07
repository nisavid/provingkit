#!/usr/bin/env python3
"""Bounded cycle tests for the Cursor Cloud Agent continuation controls."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "plugins/praxis/skills/aeon-bell"
BINDING = SKILL / "scripts/monitor_binding.js"
CURSOR_ADAPTER = SKILL / "scripts/cursor_cloud_agent_adapter.js"
ENGINE = SKILL / "scripts/aeon_bell.py"
NOW = "2026-10-07T16:00:00+00:00"
HOST = "cursor-cloud-agent"
TARGET = "bc-00000000-0000-0000-0000-000000000041"
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
const cursorFactory = eval(fs.readFileSync(process.argv[2], "utf8"));
const engine = process.argv[3];
const skill = process.argv[4];
const entry = process.argv[5];
const now = process.argv[6];
const registration = JSON.parse(process.argv[7]);
const scenario = JSON.parse(process.argv[8]);
const slots = new Map([["entry", entry]]);
const engineReplies = [];
const requestCalls = [];
const sendActions = [];
const durableNativeResults = [];
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

const request = async input => {
  requestCalls.push(copy(input));
  const response = responses.shift();
  if (response && response.throw_request) throw new Error("controlled lost response");
  return response;
};

const cursorControls = cursorFactory.createCursorCloudAgentControls({request});
const nativeAdapters = bindingFactory.createNativeAdapters({
  taskRead: scenario.native_task_read ? cursorControls.taskRead : async () => ({
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
      buckets: [{name: registration.gate.bucket, remaining_percent: 40}],
    })), task_states: []}) + "\n");
    fs.writeFileSync(reportPath, JSON.stringify({
      adapter: "praxis-aeon-bell-codex-status",
      gates: requests.map(item => ({gate_key: item.gate_key, kind: item.kind,
        outcome: "observed", reason: "typed-observation"})),
    }) + "\n");
    return {kind: "completed", actual_result: {exit_code: 0}};
  },
  send: async input => {
    sendActions.push(copy(input));
    return cursorControls.send(input);
  },
  emit: async () => ({kind: "completed", actual_result: {emitted: true}}),
  heartbeatSet: async ({action}) => ({kind: "completed", actual_result: {
    applied: true, next_run_at: action.arguments.target_at,
  }}),
});

const binding = bindingFactory.createStructuredMonitorBinding({
  state: {get: key => slots.get(key), put: (key, value) => slots.set(key, copy(value))},
  engineTransport,
  nativeAdapters,
});

(async () => {
  let classification;
  const results = [];
  for (let step = 0; step < 64; step += 1) {
    const result = await binding.advance({runKey: "run", entryKey: "entry", now, classification});
    results.push(result);
    const storedRun = slots.get("run");
    if (storedRun && storedRun.native_actual_result !== null) {
      durableNativeResults.push({
        action_kind: storedRun.action && storedRun.action.kind,
        native_actual_result: copy(storedRun.native_actual_result),
      });
    }
    classification = undefined;
    if (result.status === "needs_classification") {
      classification = {
        decision_id: result.view.decision_id,
        choice: result.view.action_kind === "task_read"
          ? (scenario.task_choice || "idle") : scenario.send_choice,
      };
      continue;
    }
    if (result.status === "complete") {
      process.stdout.write(JSON.stringify({
        result, results, engineReplies, requestCalls, sendActions,
        durableNativeResults,
        requests_remaining: responses.length,
      }));
      return;
    }
    if (["unresolved", "unsupported", "stopped", "correction_required"].includes(result.status)) {
      throw new Error("cycle stopped at " + result.status + ": " + JSON.stringify(result.view));
    }
  }
  throw new Error("cycle exceeded 64 binding advances");
})().catch(error => { process.stderr.write(error.stack + "\n"); process.exit(1); });
'''


DIRECT_RUNNER = r'''
"use strict";
const fs = require("node:fs");
const cursorFactory = eval(fs.readFileSync(process.argv[1], "utf8"));
const scenario = JSON.parse(process.argv[2]);
const calls = [];
const responses = [...scenario.responses];
const copy = value => JSON.parse(JSON.stringify(value));
const request = async input => {
  calls.push(copy(input));
  return responses.shift();
};
const controls = cursorFactory.createCursorCloudAgentControls({request});

(async () => {
  const result = await controls[scenario.control](scenario.input);
  process.stdout.write(JSON.stringify({result, calls, responses_remaining: responses.length}));
})().catch(error => { process.stderr.write(error.stack + "\n"); process.exit(1); });
'''


class CursorAdapterCycleTests(unittest.TestCase):
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

    def run_cycle(self, scenario: dict, *, host: str = HOST, target: str = TARGET) -> tuple[dict, dict]:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            store = directory / "store"
            binding_path = directory / "controlled-binding.json"
            binding_path.write_text("{}\n")
            bound = self.command(
                "monitor", "bind", "--store", store, "--initialize-registry",
                "--binding", binding_path, "--heartbeat", "controlled-heartbeat",
            )
            continuation = "Continue the literal request.\nUnicode: 雪. Shell text stays literal: $(no-op); ' \"."
            registration = self.command(
                "register", "--store", store, "--owner", "controlled-owner",
                "--host", host, "--task-id", target, "--episode", "cursor-episode-1",
                "--gate-json", json.dumps(GATE), "--continuation", continuation,
                "--now", NOW,
            )
            result = subprocess.run(
                [
                    "node", "-e", RUNNER, str(BINDING), str(CURSOR_ADAPTER), str(ENGINE),
                    str(SKILL), bound["entry_ref"], NOW, json.dumps(registration),
                    json.dumps(scenario),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            observed = json.loads(result.stdout)
            inspected = self.command("inspect", "--store", store, "--now", NOW)
            return observed, inspected

    def run_direct(self, scenario: dict) -> dict:
        result = subprocess.run(
            ["node", "-e", DIRECT_RUNNER, str(CURSOR_ADAPTER), json.dumps(scenario)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_malformed_requested_ids_never_start_a_request_directly_or_in_a_cycle(self) -> None:
        malformed = [
            ".",
            "..",
            "agent/run",
            "agent\\run",
            "agent%2frun",
            "agent%2Frun",
            "agent%5crun",
            "agent%5Crun",
            "%2e",
            "%2E%2e",
            ".%2e",
            "e\u0301",
            "\uff21gent",
        ]
        for target in malformed:
            with self.subTest(target=target, seam="direct-send"):
                direct = self.run_direct({
                    "control": "send",
                    "input": {"host": HOST, "task_id": target, "message": "continue"},
                    "responses": [],
                })
                self.assertEqual(direct["result"], {"kind": "not_started"})
                self.assertEqual(direct["calls"], [])

            with self.subTest(target=target, seam="direct-read"):
                direct = self.run_direct({
                    "control": "taskRead",
                    "input": {"host": HOST, "task_id": target, "episode": "episode-1"},
                    "responses": [],
                })
                self.assertEqual(direct["result"], {"kind": "not_started"})
                self.assertEqual(direct["calls"], [])

            with self.subTest(target=target, seam="complete-cycle"):
                observed, inspected = self.run_cycle(
                    {"responses": [], "send_choice": "not_sent"}, target=target,
                )
                self.assertEqual(observed["requestCalls"], [])
                final = observed["engineReplies"][-1]
                self.assertEqual(final["outcome"]["wakes"][0]["result"], "not_sent")
                record = next(
                    item for item in inspected["registrations"]
                    if item["task_id"] == target
                )
                self.assertEqual(record["status"], "waiting")

    def test_invalid_returned_native_ids_never_become_authoritative(self) -> None:
        invalid_ids = ["..", "run/child", "run%2fchild", "e\u0301"]
        for native_run in invalid_ids:
            with self.subTest(native_run=native_run, seam="latest-run"):
                direct = self.run_direct({
                    "control": "taskRead",
                    "input": {"host": HOST, "task_id": TARGET, "episode": "episode-1"},
                    "responses": [{
                        "kind": "completed",
                        "status": 200,
                        "body": json.dumps({
                            "id": TARGET,
                            "status": "IDLE",
                            "latestRunId": native_run,
                        }),
                    }],
                })
                self.assertEqual(len(direct["calls"]), 1)
                self.assertEqual(direct["result"]["kind"], "completed")
                self.assertEqual(direct["result"]["actual_result"]["disposition"], "failed")

            with self.subTest(native_run=native_run, seam="direct-send"):
                direct = self.run_direct({
                    "control": "send",
                    "input": {"host": HOST, "task_id": TARGET, "message": "continue"},
                    "responses": [{
                        "kind": "completed",
                        "status": 200,
                        "body": json.dumps({"run": {
                            "id": native_run,
                            "agentId": TARGET,
                            "status": "CREATING",
                        }}),
                    }],
                })
                self.assertEqual(len(direct["calls"]), 1)
                self.assertEqual(direct["result"]["summary"]["transport_status"], "unknown")
                self.assertNotIn("native_run_id", direct["result"]["actual_result"]["evidence"])

            with self.subTest(native_run=native_run, seam="complete-cycle"):
                observed, inspected = self.run_cycle({
                    "responses": [{
                        "kind": "completed",
                        "status": 200,
                        "body": json.dumps({"run": {
                            "id": native_run,
                            "agentId": TARGET,
                            "status": "CREATING",
                        }}),
                    }],
                    "send_choice": "unknown",
                })
                summaries = [
                    item["view"]["native_result_summary"] for item in observed["results"]
                    if item["status"] == "needs_classification"
                    and item["view"]["action_kind"] == "send"
                ]
                self.assertEqual(len(summaries), 1)
                self.assertEqual(summaries[0]["transport_status"], "unknown")
                final = observed["engineReplies"][-1]
                self.assertEqual(final["outcome"]["wakes"][0]["result"], "unknown")
                record = next(
                    item for item in inspected["registrations"]
                    if item["task_id"] == TARGET
                )
                self.assertEqual(record["status"], "unresolved")

    def test_precomposed_opaque_safe_ids_remain_supported(self) -> None:
        opaque = "opaque.id:part+~%25-\u00e9"
        direct = self.run_direct({
            "control": "send",
            "input": {"host": HOST, "task_id": opaque, "message": "continue"},
            "responses": [{
                "kind": "completed",
                "status": 200,
                "body": json.dumps({"run": {
                    "id": opaque,
                    "agentId": opaque,
                    "status": "CREATING",
                }}),
            }],
        })

        self.assertEqual(direct["result"]["summary"]["transport_status"], "accepted")
        self.assertEqual(direct["result"]["actual_result"]["evidence"]["native_run_id"], opaque)
        self.assertEqual(len(direct["calls"]), 1)
        self.assertEqual(
            direct["calls"][0]["url"],
            "https://api.cursor.com/v1/agents/opaque.id%3Apart%2B~%2525-%C3%A9/runs",
        )

    def test_complete_cycle_records_documented_cursor_acceptance_once(self) -> None:
        native_run = "run-00000000-0000-0000-0000-000000000042"
        observed, inspected = self.run_cycle({
            "responses": [{
                "kind": "completed",
                "status": 200,
                "body": json.dumps({"run": {
                    "id": native_run,
                    "agentId": TARGET,
                    "status": "CREATING",
                }}),
            }],
            "send_choice": "accepted",
        })

        self.assertEqual(observed["result"]["status"], "complete")
        self.assertEqual(observed["requests_remaining"], 0)
        self.assertEqual(len(observed["sendActions"]), 1)
        send_action = observed["sendActions"][0]
        self.assertEqual(send_action["host"], HOST)
        self.assertEqual(send_action["task_id"], TARGET)
        summaries = [
            item["view"]["native_result_summary"] for item in observed["results"]
            if item["status"] == "needs_classification" and item["view"]["action_kind"] == "send"
        ]
        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0]["transport_status"], "accepted")
        send_results = [
            item["native_actual_result"]
            for item in observed["durableNativeResults"]
            if item["action_kind"] == "send"
        ]
        self.assertEqual(send_results, [{
            "kind": "completed",
            "actual_result": {"evidence": {
                "http_status": 200,
                "native_run_id": native_run,
            }},
            "summary": {
                "transport_status": "accepted",
                "evidence_summary": "Cursor returned a CREATING run bound to the requested Cloud Agent",
            },
        }])
        self.assertNotIn("body", send_results[0]["actual_result"])
        self.assertEqual(observed["requestCalls"], [{
            "method": "POST",
            "url": f"https://api.cursor.com/v1/agents/{TARGET}/runs",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {"prompt": {"text": send_action["message"]}},
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        }])
        final = observed["engineReplies"][-1]
        self.assertEqual(final["status"], "complete")
        self.assertEqual(final["outcome"]["wakes"][0]["result"], "accepted")
        record = next(item for item in inspected["registrations"] if item["task_id"] == TARGET)
        self.assertEqual(record["status"], "completed")
        self.assertEqual(record["attempt_count"], 1)
        self.assertEqual(inspected["unresolved_attempts"], [])

    def test_complete_cycles_distinguish_nonadmission_unknowns_and_wrong_host(self) -> None:
        accepted_shape = {"run": {
            "id": "run-00000000-0000-0000-0000-000000000043",
            "agentId": TARGET,
            "status": "CREATING",
        }}
        cases = [
            ("busy", HOST, [{
                "kind": "completed", "status": 409,
                "error_code": "agent_busy", "body": "",
            }], "not_sent", "not_sent", "waiting", "not_sent"),
            ("lost", HOST, [{"throw_request": True}],
             "unknown", "unknown", "unresolved", "unknown"),
            ("malformed", HOST, [{
                "kind": "completed", "status": 200, "body": "{not-json",
            }], "unknown", "unknown", "unresolved", "unknown"),
            ("nonauthoritative", HOST, [{
                "kind": "completed", "status": 503,
                "body": json.dumps(accepted_shape),
            }], "unknown", "unknown", "unresolved", "unknown"),
            ("mismatched", HOST, [{
                "kind": "completed", "status": 200,
                "body": json.dumps({"run": {
                    "id": "run-00000000-0000-0000-0000-000000000044",
                    "agentId": "bc-00000000-0000-0000-0000-000000000099",
                    "status": "CREATING",
                }}),
            }], "unknown", "unknown", "unresolved", "unknown"),
            ("wrong-host", "cursor-local-ide", [],
             "not_sent", None, "waiting", "not_sent"),
        ]

        for name, host, responses, choice, transport, status, wake in cases:
            with self.subTest(name=name):
                observed, inspected = self.run_cycle(
                    {"responses": responses, "send_choice": choice}, host=host,
                )
                self.assertEqual(len(observed["sendActions"]), 1)
                expected_request_count = 0 if name == "wrong-host" else 1
                self.assertEqual(len(observed["requestCalls"]), expected_request_count)
                self.assertEqual(observed["requests_remaining"], 0)
                summaries = [
                    result["view"]["native_result_summary"]
                    for result in observed["results"]
                    if result["status"] == "needs_classification"
                    and result["view"]["action_kind"] == "send"
                ]
                if transport is None:
                    self.assertEqual(summaries, [])
                else:
                    self.assertEqual(len(summaries), 1)
                    self.assertEqual(summaries[0]["transport_status"], transport)
                final = observed["engineReplies"][-1]
                self.assertEqual(final["outcome"]["wakes"][0]["result"], wake)
                record = next(
                    item for item in inspected["registrations"]
                    if item["task_id"] == TARGET
                )
                self.assertEqual(record["status"], status)
                self.assertEqual(record["attempt_count"], 1)
                if status == "unresolved":
                    self.assertEqual(len(inspected["unresolved_attempts"]), 1)
                else:
                    self.assertEqual(inspected["unresolved_attempts"], [])

    def test_native_task_read_keeps_aeon_episode_relation_unresolved(self) -> None:
        latest_run = "run-00000000-0000-0000-0000-000000000045"
        private_reply = "PRIVATE-CONTROLLED-FINAL-REPLY"
        observed, inspected = self.run_cycle({
            "native_task_read": True,
            "task_choice": "unknown",
            "responses": [
                {
                    "kind": "completed",
                    "status": 200,
                    "observed_at": NOW,
                    "body": json.dumps({
                        "id": TARGET,
                        "status": "IDLE",
                        "latestRunId": latest_run,
                    }),
                },
                {
                    "kind": "completed",
                    "status": 200,
                    "observed_at": NOW,
                    "body": json.dumps({
                        "id": latest_run,
                        "agentId": TARGET,
                        "status": "FINISHED",
                        "result": private_reply,
                    }),
                },
            ],
        })

        self.assertEqual(observed["requestCalls"], [
            {
                "method": "GET",
                "url": f"https://api.cursor.com/v1/agents/{TARGET}",
            },
            {
                "method": "GET",
                "url": f"https://api.cursor.com/v1/agents/{TARGET}/runs/{latest_run}",
            },
        ])
        self.assertEqual(observed["requests_remaining"], 0)
        self.assertEqual(observed["sendActions"], [])
        summaries = [
            result["view"]["native_result_summary"]
            for result in observed["results"]
            if result["status"] == "needs_classification"
            and result["view"]["action_kind"] == "task_read"
        ]
        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0]["task_status"], "idle")
        self.assertFalse(summaries[0]["episode_matches"])
        self.assertIn("no Aeon wait-episode relation", summaries[0]["episode_context"])
        self.assertNotIn(private_reply, json.dumps(observed))
        self.assertEqual(observed["engineReplies"][-1]["outcome"]["wakes"], [])
        record = next(item for item in inspected["registrations"] if item["task_id"] == TARGET)
        self.assertEqual(record["status"], "waiting")
        self.assertEqual(record["attempt_count"], 0)


if __name__ == "__main__":
    unittest.main()
