#!/usr/bin/env python3
"""Public conformance tests for the Aeon Bell structured harness binding."""

from __future__ import annotations

import json
import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BINDING = ROOT / "plugins/praxis/skills/aeon-bell/scripts/monitor_binding.js"
NODE = "node"


def run_javascript(program: str, *arguments: str) -> dict:
    result = subprocess.run(
        [NODE, "-e", program, str(BINDING), *arguments],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr or result.stdout)
    return json.loads(result.stdout)


HARNESS = r'''
const fs = require("fs");
const factory = eval(fs.readFileSync(process.argv[1], "utf8"));
const scenario = JSON.parse(process.argv[2]);
const slots = new Map([["entry", scenario.entry], ...(scenario.initial_run ? [["run", scenario.initial_run]] : [])]);
const engineCalls = [];
const nativeCalls = [];
const engineOutcomes = [...scenario.engine_outcomes];
const nativeOutcomes = Object.fromEntries(Object.entries(scenario.native_outcomes || {}).map(([key, value]) => [key, [...value]]));
const adapters = {};
for (const kind of ["task_read", "observe", "send", "emit", "heartbeat_set"]) {
  if ((scenario.absent_kinds || []).includes(kind)) continue;
  adapters[kind] = {invoke: async input => {
    nativeCalls.push(JSON.parse(JSON.stringify({kind, input})));
    return nativeOutcomes[kind].shift();
  }};
}
const binding = factory.createStructuredMonitorBinding({
  state: {get: key => slots.get(key), put: (key, value) => slots.set(key, value)},
  engineTransport: async argv => {engineCalls.push(argv); return engineOutcomes.shift();},
  nativeAdapters: adapters,
  displayPolicy: scenario.corrupt_display ? view => JSON.parse(JSON.stringify(view).replaceAll("a", "?").replaceAll("1", "l")) : undefined,
});
(async () => {
  const results = [];
  const counts = [];
  for (const call of scenario.calls) {
    results.push(await binding.advance({runKey: "run", entryKey: "entry", now: scenario.now, classification: call}));
    counts.push({engine: engineCalls.length, native: nativeCalls.length});
  }
  process.stdout.write(JSON.stringify({results, counts, engineCalls, nativeCalls, run: slots.get("run")}));
})().catch(error => { console.error(error.stack); process.exit(1); });
'''


def completed(reply: dict) -> dict:
    return {"kind": "completed", "exit_code": 0, "stdout": json.dumps(reply)}


def action_reply(kind: str, continuation: str, arguments: dict, *, generation: int = 7) -> dict:
    purposes = {
        "task_read": "task-state", "observe": "query", "send": "wake",
        "emit": "notice", "heartbeat_set": "schedule",
    }
    return {
        "status": "action_required", "registry_id": "registry", "invocation_id": "invocation",
        "generation": generation, "continuation": continuation,
        "action": {"kind": kind, "purpose": purposes[kind], "arguments": arguments,
                   "require": {}, "result_shape": {}, "failure_form": {}},
    }


def complete_reply() -> dict:
    return {"status": "complete", "invocation_id": "invocation", "outcome": {}, "printed_anything": False}


class StructuredBindingTests(unittest.TestCase):
    def test_documented_loader_hashes_and_returns_the_same_helper_bytes(self) -> None:
        loader = (
            "import hashlib,json,pathlib,sys; "
            "b=pathlib.Path(sys.argv[1]).read_bytes(); "
            "print(json.dumps({'sha256':hashlib.sha256(b).hexdigest(),"
            "'source':b.decode('utf-8')}))"
        )
        with tempfile.TemporaryDirectory() as directory:
            helper = Path(directory) / "installed monitor binding.js"
            source = BINDING.read_bytes()
            helper.write_bytes(source)
            result = subprocess.run(
                ["python3", "-c", loader, str(helper)],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        loaded = json.loads(result.stdout)
        self.assertEqual(loaded["sha256"], hashlib.sha256(source).hexdigest())
        self.assertEqual(loaded["source"].encode("utf-8"), source)

    def test_configured_entry_is_passed_to_engine_without_display_round_trip(self) -> None:
        program = r'''
const fs = require("fs");
const source = fs.readFileSync(process.argv[1], "utf8");
const factory = eval(source);
const slots = new Map([["entry", "ab1." + "opaque-".repeat(180)]]);
const calls = [];
const binding = factory.createStructuredMonitorBinding({
  state: {get: key => slots.get(key), put: (key, value) => slots.set(key, value)},
  engineTransport: async argv => {
    calls.push(argv);
    return {kind: "completed", exit_code: 0, stdout: JSON.stringify({
      status: "complete", invocation_id: "invocation", outcome: {}, printed_anything: false
    })};
  },
  nativeAdapters: {},
  displayPolicy: view => JSON.parse(JSON.stringify(view).replaceAll("a", "?")),
});
(async () => {
  const result = await binding.advance({runKey: "run", entryKey: "entry", now: "2026-09-19T00:00:00+00:00"});
  process.stdout.write(JSON.stringify({result, calls, entry: slots.get("entry")}));
})().catch(error => { console.error(error.stack); process.exit(1); });
'''
        observed = run_javascript(program)
        self.assertEqual(observed["result"]["status"], "complete")
        self.assertEqual(observed["calls"], [[
            "python3", "scripts/aeon_bell.py", "monitor", "enter", "--entry-ref",
            observed["entry"], "--now", "2026-09-19T00:00:00+00:00",
        ]])

    def test_due_open_application_preserves_all_action_values_and_classification(self) -> None:
        entry = "ab1." + "entry-opaque-" * 120
        continuations = [
            "ab1c." + "near-neighbor-O0l1-" * 90 + suffix
            for suffix in ("A", "B", "C", "D", "E")
        ]
        argv = ["printf", "%s", "space quote ' newline\n雪", "", "$(never-run)", "; also-literal"]
        message = "Send this exact line.\nQuotes: ' \"; snow: 雪; literal: $(never-run)"
        heartbeat = {
            "heartbeat": "opaque-heartbeat", "target_at": "2026-09-19T01:00:00+00:00",
            "delay_minutes": 60, "rule": "schedule-as-printed", "write_number": 2,
            "fingerprint": "f" * 64, "basis": {"answered_due_gate_keys": ["g" * 64]},
        }
        replies = [
            action_reply("task_read", continuations[0], {"host": "local", "task_id": "task-1", "episode": 4}),
            action_reply("observe", continuations[1], {"argv": argv, "cwd": None}),
            action_reply("send", continuations[2], {"host": "local", "task_id": "task-1", "message": message}),
            action_reply("emit", continuations[3], {"channel": "notice", "text": "literal notice 雪"}),
            action_reply("heartbeat_set", continuations[4], heartbeat),
            complete_reply(),
        ]
        scenario = {
            "entry": entry, "now": "2026-09-19T00:00:00+00:00", "corrupt_display": True,
            "engine_outcomes": [completed(reply) for reply in replies],
            "native_outcomes": {
                "task_read": [{"kind": "completed", "actual_result": {"provider": "idle-ish", "observed_at": "2026-09-19T00:00:00+00:00"}, "summary": {"task_status": "idle-ish", "episode_context": "episode 4 is still waiting"}}],
                "observe": [{"kind": "completed", "actual_result": {"exit_code": 0}}],
                "send": [{"kind": "completed", "actual_result": {"request": "accepted-ish", "evidence": {"native_id": "n-1"}}, "summary": {"transport_status": "accepted-ish", "evidence_summary": "native request n-1"}}],
                "emit": [{"kind": "completed", "actual_result": {"printed": True}}],
                "heartbeat_set": [{"kind": "completed", "actual_result": {"applied": True, "next_run_at": heartbeat["target_at"], "previous_next_run_at": None}}],
            },
            "calls": [None, {"decision_id": "wrong", "choice": "idle"},
                      {"decision_id": "decision-binding-7-1", "choice": "idle"},
                      {"decision_id": "decision-binding-7-3", "choice": "accepted"}],
        }
        observed = run_javascript(HARNESS, json.dumps(scenario))

        self.assertEqual([result["status"] for result in observed["results"]],
                         ["needs_classification", "needs_classification", "needs_classification", "complete"])
        self.assertEqual(observed["counts"][0], observed["counts"][1])
        self.assertEqual(len(observed["nativeCalls"]), 5)
        self.assertEqual(observed["nativeCalls"][1]["input"]["action"]["arguments"]["argv"], argv)
        self.assertEqual(observed["nativeCalls"][2]["input"]["action"]["arguments"]["message"], message)
        self.assertEqual(observed["nativeCalls"][4]["input"]["engine"],
                         {"registry_id": "registry", "invocation_id": "invocation", "generation": 7})
        self.assertEqual(observed["engineCalls"][0][5], entry)
        continue_calls = observed["engineCalls"][1:]
        self.assertEqual([call[5] for call in continue_calls], continuations)
        self.assertEqual(json.loads(continue_calls[0][7]),
                         {"status": "idle", "observed_at": "2026-09-19T00:00:00+00:00"})
        self.assertEqual(json.loads(continue_calls[2][7]),
                         {"outcome": "accepted", "evidence": {"native_id": "n-1"}})

    def test_task_read_view_contains_only_explicit_bounded_semantic_summary(self) -> None:
        summary = {"task_status": "idle-ish", "episode_context": "episode 4 is still waiting"}
        scenario = {
            "entry": "ab1.entry", "now": "2026-09-19T00:00:00+00:00",
            "engine_outcomes": [completed(action_reply("task_read", "ab1c.one", {"host": "local", "task_id": "target", "episode": 4}))],
            "native_outcomes": {"task_read": [{
                "kind": "completed", "actual_result": {"raw_provider_payload": "RAW-FORBIDDEN", "observed_at": "2026-09-19T00:00:00+00:00"},
                "summary": summary,
            }]},
            "calls": [None],
        }
        observed = run_javascript(HARNESS, json.dumps(scenario))
        view = observed["results"][0]["view"]
        self.assertEqual(view["native_result_summary"], summary)
        self.assertNotIn("RAW-FORBIDDEN", json.dumps(view))

    def test_stale_decision_id_cannot_classify_later_same_kind_action(self) -> None:
        scenario = {
            "entry": "ab1.entry", "now": "2026-09-19T00:00:00+00:00",
            "engine_outcomes": [
                completed(action_reply("task_read", "ab1c.one", {"host": "local", "task_id": "one", "episode": 1})),
                completed(action_reply("task_read", "ab1c.two", {"host": "local", "task_id": "two", "episode": 2})),
                completed(complete_reply()),
            ],
            "native_outcomes": {"task_read": [
                {"kind": "completed", "actual_result": {"observed_at": "2026-09-19T00:00:00+00:00"}, "summary": {"episode_context": "one"}},
                {"kind": "completed", "actual_result": {"observed_at": "2026-09-19T00:00:00+00:00"}, "summary": {"episode_context": "two"}},
            ]},
            "calls": [None, {"decision_id": "decision-binding-7-1", "choice": "idle"},
                      {"decision_id": "decision-binding-7-1", "choice": "idle"}],
        }
        observed = run_javascript(HARNESS, json.dumps(scenario))
        self.assertEqual(observed["results"][2]["status"], "needs_classification")
        self.assertEqual(len(observed["engineCalls"]), 2)

    def test_cached_open_application_reuses_submission_after_two_not_started_outcomes(self) -> None:
        continuation = "ab1c." + "opaque-neighbor-" * 200
        message = "exact message with 'quotes', newlines\n雪, and $(literal)"
        scenario = {
            "entry": "ab1.entry", "now": "2026-09-19T00:00:00+00:00",
            "engine_outcomes": [
                completed(action_reply("send", continuation, {"host": "local", "task_id": "target", "message": message})),
                {"kind": "not_started"}, {"kind": "not_started"}, completed(complete_reply()),
            ],
            "native_outcomes": {"send": [{"kind": "completed", "actual_result": {"evidence": {"accepted": True}}, "summary": {"transport_status": "accepted", "evidence_summary": "accepted true"}}]},
            "calls": [None, {"decision_id": "decision-binding-7-1", "choice": "accepted"}],
        }
        observed = run_javascript(HARNESS, json.dumps(scenario))
        self.assertEqual(observed["results"][-1]["status"], "complete")
        self.assertEqual(len(observed["nativeCalls"]), 1)
        self.assertEqual(len(observed["engineCalls"]), 4)
        retries = observed["engineCalls"][1:]
        self.assertEqual([call[5] for call in retries], [continuation] * 3)
        self.assertEqual([call[7] for call in retries], [retries[0][7]] * 3)
        self.assertEqual([call[3] for call in observed["engineCalls"]].count("enter"), 1)

    def test_exhausted_immediate_retries_resume_only_the_same_continue(self) -> None:
        continuation = "ab1c.same-continuation"
        scenario = {
            "entry": "ab1.entry", "now": None,
            "engine_outcomes": [
                completed(action_reply("emit", continuation, {"text": "notice"})),
                {"kind": "not_started"}, {"kind": "not_started"}, {"kind": "not_started"},
                completed(complete_reply()),
            ],
            "native_outcomes": {"emit": [{"kind": "completed", "actual_result": {"printed": True}}]},
            "calls": [None, None],
        }
        observed = run_javascript(HARNESS, json.dumps(scenario))
        self.assertEqual([item["status"] for item in observed["results"]], ["stopped", "complete"])
        self.assertEqual(len(observed["nativeCalls"]), 1)
        self.assertEqual([call[3] for call in observed["engineCalls"]].count("enter"), 1)
        continues = observed["engineCalls"][1:]
        self.assertEqual([call[5] for call in continues], [continuation] * 4)
        self.assertEqual([call[7] for call in continues], [continues[0][7]] * 4)

    def test_unknown_submission_freezes_the_original_action_and_never_replays(self) -> None:
        scenario = {
            "entry": "ab1.entry", "now": "2026-09-19T00:00:00+00:00",
            "engine_outcomes": [
                completed(action_reply("send", "ab1c.continuation", {"host": "local", "task_id": "target", "message": "exact"})),
                {"kind": "unknown"},
            ],
            "native_outcomes": {"send": [{"kind": "completed", "actual_result": {"evidence": {"request": "sent"}}, "summary": {"transport_status": "possibly accepted", "evidence_summary": "request sent"}}]},
            "calls": [None, {"decision_id": "decision-binding-7-1", "choice": "accepted"}, None],
        }
        observed = run_javascript(HARNESS, json.dumps(scenario))
        self.assertEqual([item["status"] for item in observed["results"]],
                         ["needs_classification", "unresolved", "unresolved"])
        self.assertEqual(len(observed["nativeCalls"]), 1)
        self.assertEqual(len(observed["engineCalls"]), 2)
        self.assertEqual(observed["run"]["continuation"], "ab1c.continuation")
        self.assertEqual(observed["run"]["native_actual_result"]["actual_result"]["evidence"], {"request": "sent"})

    def test_native_started_crash_windows_never_replay_any_effect_kind(self) -> None:
        for kind in ("task_read", "observe", "send", "emit", "heartbeat_set"):
            with self.subTest(kind=kind):
                initial = {
                    "phase": "native_started", "entry_ref": "ab1.entry", "logical_now": None,
                    "engine_request": {}, "engine_reply": action_reply(kind, "ab1c.cont", {}),
                    "registry_id": "registry", "invocation_id": "invocation", "generation": 1,
                    "continuation": "ab1c.cont", "action": action_reply(kind, "ab1c.cont", {})["action"],
                    "action_binding_id": "binding", "native_phase": "started", "native_actual_result": None,
                    "native_result_summary": None, "decision_id": None, "mapped_engine_result": None,
                    "result_json": None, "submission_attempts": 0, "terminal_reason": None,
                }
                scenario = {"entry": "ab1.entry", "initial_run": initial, "now": None,
                            "engine_outcomes": [], "native_outcomes": {}, "calls": [None, None]}
                observed = run_javascript(HARNESS, json.dumps(scenario))
                self.assertEqual([item["status"] for item in observed["results"]], ["unresolved", "unresolved"])
                self.assertEqual(observed["engineCalls"], [])
                self.assertEqual(observed["nativeCalls"], [])

    def test_views_are_redacted_and_cannot_be_used_as_run_state(self) -> None:
        forbidden = ["ENTRY-SENTINEL", "CONTINUATION-SENTINEL", "MESSAGE-SENTINEL", "ACTION-SENTINEL"]
        scenario = {
            "entry": forbidden[0], "now": None,
            "engine_outcomes": [completed(action_reply("send", forbidden[1], {"host": "local", "task_id": forbidden[3], "message": forbidden[2]}))],
            "native_outcomes": {"send": [{"kind": "completed", "actual_result": {"raw": "RAW-SENTINEL"}}]},
            "calls": [None],
        }
        observed = run_javascript(HARNESS, json.dumps(scenario))
        rendered = json.dumps(observed["results"])
        for sentinel in [*forbidden, "RAW-SENTINEL"]:
            self.assertNotIn(sentinel, rendered)
        view = observed["results"][0]["view"]
        scenario["initial_run"] = view
        scenario["engine_outcomes"] = []
        scenario["native_outcomes"] = {}
        replay = run_javascript(HARNESS, json.dumps(scenario))
        self.assertEqual(replay["results"][0]["status"], "unsupported")

    def test_exec_transport_quotes_literal_argv_and_polls_the_exact_session(self) -> None:
        program = r'''
const fs = require("fs");
const factory = eval(fs.readFileSync(process.argv[1], "utf8"));
const execCalls = [], polls = [];
const transport = factory.createExecCommandEngineTransport({
  execCommand: async input => { execCalls.push(input); return {session_id: 73, output: '{"sta'}; },
  writeStdin: async input => {
    polls.push(input);
    return polls.length === 1
      ? {session_id: 73, output: 'tus":"comp'}
      : {exit_code: 0, output: 'lete"}'};
  },
  workdir: "repo",
});
(async () => {
  const result = await transport(["python3", "a b", "x'y", "$(literal)", "雪"]);
  process.stdout.write(JSON.stringify({result, execCalls, polls}));
})().catch(error => { console.error(error.stack); process.exit(1); });
'''
        observed = run_javascript(program)
        self.assertEqual(observed["execCalls"], [{
            "cmd": "'python3' 'a b' 'x'\\''y' '$(literal)' '雪'", "workdir": "repo",
        }])
        self.assertEqual(observed["polls"], [{"session_id": 73, "chars": ""}, {"session_id": 73, "chars": ""}])
        self.assertEqual(observed["result"]["kind"], "completed")
        self.assertEqual(json.loads(observed["result"]["stdout"]), {"status": "complete"})

    def test_completed_heartbeat_control_failure_reaches_engine_failure_form(self) -> None:
        failure = {"disposition": "unavailable", "reason": "native schedule control is unavailable"}
        scenario = {
            "entry": "ab1.entry", "now": "2026-09-19T00:00:00+00:00",
            "engine_outcomes": [
                completed(action_reply("heartbeat_set", "ab1c.heartbeat", {"heartbeat": "h", "target_at": "t", "write_number": 1, "fingerprint": "f"})),
                completed(complete_reply()),
            ],
            "native_outcomes": {"heartbeat_set": [{"kind": "completed", "actual_result": failure,
                                                     "summary": {"control_status": "unavailable"}}]},
            "calls": [None],
        }
        observed = run_javascript(HARNESS, json.dumps(scenario))
        self.assertEqual(observed["results"][0]["status"], "complete")
        self.assertEqual(json.loads(observed["engineCalls"][1][7]), failure)

    def test_absent_heartbeat_adapter_and_unknown_effect_remain_distinct(self) -> None:
        reply = completed(action_reply(
            "heartbeat_set", "ab1c.heartbeat",
            {"heartbeat": "h", "target_at": "t", "write_number": 1, "fingerprint": "f"},
        ))
        absent = {
            "entry": "ab1.entry", "now": None, "engine_outcomes": [reply],
            "native_outcomes": {}, "absent_kinds": ["heartbeat_set"], "calls": [None],
        }
        unknown = {
            "entry": "ab1.entry", "now": None, "engine_outcomes": [reply],
            "native_outcomes": {"heartbeat_set": [{"kind": "unknown"}]}, "calls": [None],
        }
        absent_result = run_javascript(HARNESS, json.dumps(absent))
        unknown_result = run_javascript(HARNESS, json.dumps(unknown))
        self.assertEqual(absent_result["results"][0]["status"], "unsupported")
        self.assertEqual(absent_result["nativeCalls"], [])
        self.assertEqual(unknown_result["results"][0]["status"], "unresolved")
        self.assertEqual(len(unknown_result["nativeCalls"]), 1)

    def test_native_adapter_factory_forwards_complete_heartbeat_action(self) -> None:
        program = r'''
const fs = require("fs");
const factory = eval(fs.readFileSync(process.argv[1], "utf8"));
const calls = [];
const adapters = factory.createNativeAdapters({heartbeatSet: async input => {calls.push(input); return {kind: "completed"};}});
(async () => {
  await adapters.heartbeat_set.invoke({engine: {registry_id: "r", invocation_id: "i", generation: 9}, action: {kind: "heartbeat_set", purpose: "schedule", arguments: {heartbeat: "h", target_at: "t", write_number: 2, fingerprint: "f", rule: "fresh-owner-work", basis: {x: 1}}}});
  process.stdout.write(JSON.stringify(calls));
})().catch(error => { console.error(error.stack); process.exit(1); });
'''
        observed = run_javascript(program)
        self.assertEqual(observed[0]["action"]["purpose"], "schedule")
        self.assertEqual(observed[0]["action"]["arguments"]["basis"], {"x": 1})

    def test_unconditional_heartbeat_control_can_still_rollback_newer_target(self) -> None:
        program = r'''
const fs = require("fs");
const factory = eval(fs.readFileSync(process.argv[1], "utf8"));
let target = null;
const adapters = factory.createNativeAdapters({heartbeatSet: async ({engine, action}) => {
  target = action.arguments.target_at;
  return {kind: "completed", actual_result: {applied: true, next_run_at: target, generation: engine.generation}};
}});
(async () => {
  const newer = {engine: {registry_id: "r", invocation_id: "new", generation: 2}, action: {kind: "heartbeat_set", purpose: "schedule", arguments: {heartbeat: "h", target_at: "B", write_number: 1, fingerprint: "new"}}};
  const older = {engine: {registry_id: "r", invocation_id: "old", generation: 1}, action: {kind: "heartbeat_set", purpose: "schedule", arguments: {heartbeat: "h", target_at: "A", write_number: 1, fingerprint: "old"}}};
  await adapters.heartbeat_set.invoke(newer);
  await adapters.heartbeat_set.invoke(older);
  process.stdout.write(JSON.stringify({target}));
})().catch(error => { console.error(error.stack); process.exit(1); });
'''
        observed = run_javascript(program)
        self.assertEqual(observed["target"], "A")


if __name__ == "__main__":
    unittest.main()
