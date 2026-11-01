"""Consumer tests for the draft native-tree boundary; no native calls execute."""

import copy
import contextlib
import hashlib
import importlib.util
import json
import multiprocessing
import sqlite3
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest


MODULE = (Path(__file__).resolve().parents[2] / "plugins" / "rolecasting" / "skills"
          / "delegating-cross-agent-work" / "scripts" / "native_tree.py")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def load():
    spec = importlib.util.spec_from_file_location("native_tree_candidate", MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_record():
    return {
        "schema": "native-tree-run-v1",
        "run_id": "synthetic-run",
        "controller_ref": "fixture-controller",
        "profile_id": "chatgpt-codex-native-tree-v1",
        "profile_sha256": digest("synthetic-profile"),
        "capability_ref": "synthetic-current-schema",
        "capability_sha256": digest("synthetic-current-schema"),
        "product_version": {"state": "unavailable", "reason": "not exposed by this fixture"},
    }


def binding(role="worker", generation=1, target="/root/worker"):
    return {
        "schema": "native-tree-binding-v1", "run_id": "synthetic-run",
        "controller_ref": "fixture-controller", "role": role, "generation": generation,
        "relation": "root" if role == "concierge" else "child",
        "native_target": target, "observation_ref": "synthetic-native-observation",
        "source_kind": "harness-context" if role == "concierge" else "native-inventory",
        "selection_ref": "synthetic-selection",
    }


def plan(payload, command_id="command-1", assignment_id="assignment-1"):
    result = {"schema": "native-tree-plan-v1", "run_id": "synthetic-run",
              "command_id": command_id, "plan_sha256": digest("frozen bounded owner plan"),
              "request_sha256": digest(payload), "authority_ref": "synthetic bounded grant",
              "verification_contract_ref": "synthetic verification contract",
              "stop_ref": "synthetic stop conditions"}
    if assignment_id is not None:
        result.update(assignment_id=assignment_id,
                      owner={"role": "concierge", "generation": 1},
                      reply_to={"role": "concierge", "generation": 1})
    return result


def concurrent_claim(path, run, actor, barrier, queue, command_id="command-1"):
    try:
        with load().NativeTree(path, run=run, actor=actor) as tree:
            barrier.wait(timeout=10)
            queue.put(tree.claim(command_id))
    except Exception as error:
        queue.put({"error": repr(error)})


class NativeTreeConsumerTests(unittest.TestCase):
    def setUp(self):
        self.module = load()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "state.sqlite3"
        self.run = run_record()
        self.actor = {"role": "concierge", "generation": 1}
        self.tree = self.module.NativeTree(self.path, run=self.run, actor=self.actor, create=True)
        self.addCleanup(self.tree.close)
        self.tree.bind_role(binding("concierge", target="/root"))

    def test_cloud_binding_preserves_target_without_inventing_optional_ids(self):
        supplied = binding()
        expected = copy.deepcopy(supplied)
        result = self.tree.bind_role(supplied)
        supplied["native_target"] = "changed-after-binding"
        self.assertTrue(result["created"])
        self.assertEqual(result["binding"], expected)
        for name in ("agent_id", "session_id", "task_id"):
            self.assertNotIn(name, result["binding"])
        again = self.tree.bind_role(expected)
        self.assertFalse(again["created"])

    def prepare_work(self, command_id="command-1", assignment_id="assignment-1"):
        self.tree.bind_role(binding())
        payload = {"message": "Run assignment-1; reply to Concierge.\r\nCafe\u0301"}
        frozen_plan = plan(payload, command_id, assignment_id)
        result = self.tree.prepare(frozen_plan, "activate-or-steer", "worker", 1, payload, "assign")
        return result, frozen_plan, payload

    def test_claim_returns_exact_call_once_and_freezes_mutable_input(self):
        prepared, frozen_plan, payload = self.prepare_work()
        self.assertTrue(prepared["created"])
        self.assertFalse(self.tree.prepare(frozen_plan, "activate-or-steer", "worker", 1, payload, "assign")["created"])
        payload["message"] = "changed after preparation"
        frozen_plan["authority_ref"] = "changed after preparation"
        first = self.tree.claim("command-1")
        self.assertTrue(first["claimed"])
        self.assertEqual(first["native_call"], {"tool": "collaboration.followup_task", "arguments": {
            "target": "/root/worker", "message": "Run assignment-1; reply to Concierge.\r\nCafe\u0301"}})
        duplicate = self.tree.claim("command-1")
        self.assertFalse(duplicate["claimed"])
        self.assertNotIn("native_call", duplicate)
        with self.module.NativeTree(self.path, run=self.run, actor=self.actor) as reopened:
            recovered = reopened.claim("command-1")
            self.assertFalse(recovered["claimed"])
            self.assertNotIn("native_call", recovered)

    def test_changed_command_bytes_are_rejected(self):
        _, frozen_plan, payload = self.prepare_work()
        payload["message"] = "different work"
        frozen_plan["request_sha256"] = digest(payload)
        with self.assertRaises(self.module.NativeTreeError):
            self.tree.prepare(frozen_plan, "activate-or-steer", "worker", 1, payload, "assign")

    def test_claim_rechecks_recipient_generation(self):
        self.prepare_work()
        self.tree.bind_role(binding(generation=2, target="/root/replacement"))
        with self.assertRaises(self.module.NativeTreeError):
            self.tree.claim("command-1")

    def test_two_processes_emit_only_one_native_call(self):
        self.prepare_work()
        context = multiprocessing.get_context("spawn")
        barrier, queue = context.Barrier(2), context.Queue()
        workers = [context.Process(target=concurrent_claim,
                   args=(self.path, self.run, self.actor, barrier, queue)) for _ in range(2)]
        try:
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join(15)
                self.assertEqual(worker.exitcode, 0)
            results = [queue.get(timeout=2) for _ in workers]
            self.assertEqual(sum(item.get("claimed", False) for item in results), 1, results)
            self.assertEqual(sum("native_call" in item for item in results), 1, results)
            self.assertFalse(any("error" in item for item in results), results)
        finally:
            for worker in workers:
                if worker.is_alive():
                    worker.terminate()
                    worker.join(5)
            queue.close()

    def test_an_unresolved_assignment_keeps_the_child_reserved(self):
        self.prepare_work()
        self.assertTrue(self.tree.claim("command-1")["claimed"])
        payload = {"message": "unrelated assignment"}
        self.tree.prepare(plan(payload, "command-2", "assignment-2"),
                          "activate-or-steer", "worker", 1, payload, "assign")
        second = self.tree.claim("command-2")
        self.assertFalse(second["claimed"])
        self.assertNotIn("native_call", second)

    def test_root_activation_and_inherited_model_override_are_refused(self):
        payload = {"message": "work"}
        with self.assertRaises(self.module.NativeTreeError):
            self.tree.prepare(plan(payload), "activate-or-steer", "concierge", 1, payload, "assign")
        payload = {"task_name": "fresh", "message": "work", "fork_turns": "all",
                   "model": "gpt-6.1-sol", "reasoning_effort": "high"}
        with self.assertRaises(self.module.NativeTreeError):
            self.tree.prepare(plan(payload), "spawn", "fresh", 1, payload, "inherit")

    def command(self, command_id="command-1"):
        snapshot = self.tree.inspect("synthetic-run", command_id)
        return next(item for item in snapshot["commands"] if item["command_id"] == command_id)

    def observe(self, raw, source="native-tool-result", command_id="command-1", observation_id="observation-1", collected_by=None):
        envelope = {
            "observation_id": observation_id, "raw": raw,
            "evidence_ref": "synthetic-evidence-" + observation_id,
        }
        if collected_by is not None:
            envelope["collected_by"] = collected_by
        return self.tree.observe(command_id, envelope, source)

    def claim_inventory(self, command_id="inspect-1"):
        self.tree.prepare(plan({}, command_id, None), "inspect", None, None, {}, "inventory")
        self.tree.claim(command_id)

    def test_unknown_observation_is_retained_once_without_invented_facts(self):
        self.prepare_work()
        self.tree.claim("command-1")
        self.assertTrue(self.observe({"future_envelope": 7})["created"])
        self.assertFalse(self.observe({"future_envelope": 7})["created"])
        record = self.command()["observations"][0]
        self.assertEqual(record["raw"], {"future_envelope": 7})
        self.assertEqual(record["facts"], {})
        self.assertEqual(record["source_kind"], "native-tool-result")
        with self.assertRaises(self.module.NativeTreeError):
            self.observe({"future_envelope": 8})

    def test_worker_prose_does_not_establish_native_completion_or_model(self):
        self.prepare_work()
        self.tree.claim("command-1")
        self.observe({"agent_name": "/root/worker", "agent_status": {"completed": "DONE"},
                      "model": "asserted-by-worker"}, "worker-report")
        self.assertEqual(self.command()["observations"][0]["facts"], {})

    def test_previous_running_and_timeout_are_not_post_state_or_nondelivery(self):
        self.tree.bind_role(binding())
        self.tree.prepare(plan({}, "interrupt", None), "interrupt", "worker", 1, {}, "request")
        self.tree.claim("interrupt")
        self.observe({"previous_status": "running"}, command_id="interrupt")
        self.assertEqual(self.command("interrupt")["observations"][0]["facts"], {"previous_status": "running"})
        payload = {"timeout_ms": 10000}
        self.tree.prepare(plan(payload, "wait", None), "wait", None, None, payload, "bounded")
        self.tree.claim("wait")
        self.observe({"message": "Wait timed out.", "timed_out": True}, command_id="wait", observation_id="timeout")
        self.assertEqual(self.command("wait")["observations"][0]["facts"], {"wait_timed_out": True})

    def test_unknown_attempt_cannot_be_resent_as_continuation(self):
        self.prepare_work()
        self.tree.claim("command-1")
        payload = {"message": "resume assignment-1"}
        self.tree.prepare(plan(payload, "continue-1"), "activate-or-steer", "worker", 1, payload, "continue")
        with self.assertRaises(self.module.NativeTreeError):
            self.tree.claim("continue-1")

    def test_observed_interruption_allows_same_assignment_continuation(self):
        self.prepare_work()
        self.tree.claim("command-1")
        self.claim_inventory()
        self.observe({"agents": [{"agent_name": "/root/worker", "agent_status": "interrupted"}]},
                     "native-inventory", collected_by="inspect-1")
        payload = {"message": "recover assignment-1 from checkpoint"}
        self.tree.prepare(plan(payload, "continue-1"), "activate-or-steer", "worker", 1, payload, "continue")
        self.assertTrue(self.tree.claim("continue-1")["claimed"])

    def test_other_targets_inventory_does_not_resolve_this_attempt(self):
        self.prepare_work()
        self.tree.claim("command-1")
        self.observe({"agents": [{"agent_name": "/root/other", "agent_status": "interrupted"}]},
                     "native-inventory")
        self.assertEqual(self.command()["observations"][0]["facts"], {})

    def test_old_inventory_cannot_authorize_continuation(self):
        self.claim_inventory("old-inspect")
        self.prepare_work()
        self.tree.claim("command-1")
        self.observe({"agents": [{"agent_name": "/root/worker", "agent_status": "interrupted"}]},
                     "native-inventory", collected_by="old-inspect")
        payload = {"message": "resume assignment-1"}
        self.tree.prepare(plan(payload, "continue-1"), "activate-or-steer", "worker", 1, payload, "continue")
        with self.assertRaises(self.module.NativeTreeError):
            self.tree.claim("continue-1")

    def test_observation_replay_cannot_change_source(self):
        self.prepare_work()
        self.tree.claim("command-1")
        self.observe({"future_envelope": 7})
        with self.assertRaises(self.module.NativeTreeError):
            self.observe({"future_envelope": 7}, "worker-report")

    def reported_result(self):
        _, frozen_plan, _ = self.prepare_work()
        self.tree.claim("command-1")
        result = {"answer": 42}
        result_digest = digest(result)
        report = {"assignment_id": "assignment-1", "generation": 1,
                  "input_digest": frozen_plan["request_sha256"],
                  "result": result, "result_digest": result_digest}
        self.observe(report, "worker-report", observation_id="report")
        return result_digest, frozen_plan["request_sha256"]

    def verify_result(self, result_digest, input_digest, usable=True, observation_id="verify"):
        ref = "synthetic-evidence-" + observation_id
        raw = {"assignment_id": "assignment-1", "generation": 1,
               "input_digest": input_digest, "result_digest": result_digest,
               "usable": usable, "evidence_ref": ref}
        self.observe(raw, "owner-verification", observation_id=observation_id)
        return ref

    def test_owner_acceptance_requires_bound_result_and_verification(self):
        result_digest, input_digest = self.reported_result()
        with self.assertRaises(self.module.NativeTreeError):
            self.tree.accept("assignment-1", 1, result_digest, "missing-verification")
        ref = self.verify_result(result_digest, input_digest)
        self.assertTrue(self.tree.accept("assignment-1", 1, result_digest, ref)["accepted"])
        self.assertFalse(self.tree.accept("assignment-1", 1, result_digest, ref)["accepted"])
        with self.assertRaises(self.module.NativeTreeError):
            self.tree.accept("assignment-1", 1, result_digest, "another-verification")

    def test_acceptance_does_not_release_an_unobserved_native_target(self):
        result_digest, input_digest = self.reported_result()
        ref = self.verify_result(result_digest, input_digest)
        self.tree.accept("assignment-1", 1, result_digest, ref)
        payload = {"message": "new unrelated assignment"}
        self.tree.prepare(plan(payload, "command-2", "assignment-2"),
                          "activate-or-steer", "worker", 1, payload, "assign")
        self.assertFalse(self.tree.claim("command-2")["claimed"])
        self.claim_inventory("post-acceptance-inventory")
        self.observe({"agents": [{"agent_name": "/root/worker", "agent_status": {"completed": "done"}}]},
                     "native-inventory", observation_id="post-acceptance-completed",
                     collected_by="post-acceptance-inventory")
        self.assertTrue(self.tree.claim("command-2")["claimed"])

    def test_failed_or_non_boolean_verification_cannot_be_accepted(self):
        result_digest, input_digest = self.reported_result()
        for index, usable in enumerate((False, 1, "true")):
            with self.subTest(usable=usable):
                ref = self.verify_result(result_digest, input_digest, usable, "verify-" + str(index))
                with self.assertRaises(self.module.NativeTreeError):
                    self.tree.accept("assignment-1", 1, result_digest, ref)

    def test_wrong_owner_or_recipient_generation_cannot_accept(self):
        result_digest, input_digest = self.reported_result()
        ref = self.verify_result(result_digest, input_digest)
        with self.module.NativeTree(self.path, run=self.run, actor={"role": "worker", "generation": 1}) as worker:
            with self.assertRaises(self.module.NativeTreeError):
                worker.accept("assignment-1", 1, result_digest, ref)
        with self.assertRaises(self.module.NativeTreeError):
            self.tree.accept("assignment-1", 2, result_digest, ref)
        self.tree.bind_role(binding(generation=2, target="/root/replacement"))
        with self.assertRaises(self.module.NativeTreeError):
            self.tree.accept("assignment-1", 1, result_digest, ref)

    def test_retry_authorization_is_consumed_by_one_successor_only(self):
        _, original_plan, payload = self.prepare_work()
        self.tree.claim("command-1")
        evidence = {"reconciliation_id": "reconcile-1", "decision_ref": "synthetic owner decision",
                    "basis": "nondelivery-established", "evidence_ref": "synthetic nondelivery evidence"}
        receipt = self.tree.reconcile("command-1", "authorize-new-attempt", evidence)
        self.assertEqual(receipt["reconciliation_id"], "reconcile-1")
        for command_id in ("retry-1", "retry-2"):
            retry_plan = dict(original_plan, command_id=command_id,
                              predecessor_reconciliation_ref="reconcile-1")
            self.tree.prepare(retry_plan, "activate-or-steer", "worker", 1, payload, "assign")
        context = multiprocessing.get_context("spawn")
        barrier, queue = context.Barrier(2), context.Queue()
        workers = [context.Process(target=concurrent_claim,
                   args=(self.path, self.run, self.actor, barrier, queue, command_id))
                   for command_id in ("retry-1", "retry-2")]
        try:
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join(15)
                self.assertEqual(worker.exitcode, 0)
            results = [queue.get(timeout=2) for _ in workers]
            self.assertEqual(sum(item.get("claimed", False) for item in results), 1, results)
            self.assertFalse(any("error" in item for item in results), results)
        finally:
            for worker in workers:
                if worker.is_alive():
                    worker.terminate()
                    worker.join(5)
            queue.close()

    def test_wait_timeout_does_not_authorize_retry(self):
        self.prepare_work()
        self.tree.claim("command-1")
        with self.assertRaises(self.module.NativeTreeError):
            self.tree.reconcile("command-1", "authorize-new-attempt", {
                "reconciliation_id": "reconcile-1", "decision_ref": "synthetic decision",
                "basis": "wait-timeout", "evidence_ref": "synthetic timeout"})

    def claimed_spawn(self):
        payload = {"task_name": "fresh", "message": "bounded synthetic assignment",
                   "fork_turns": "none", "model": "gpt-6.1-sol", "reasoning_effort": "high"}
        frozen_plan = dict(plan(payload, "spawn-1"), selection_ref="synthetic-selection")
        self.tree.prepare(frozen_plan, "spawn", "fresh", 1, payload, "fresh")
        self.tree.claim("spawn-1")
        return frozen_plan, payload

    def test_spawn_binding_requires_its_recorded_launch_observation(self):
        self.claimed_spawn()
        new_binding = dict(binding("fresh", target="/root/fresh"), source_kind="native-tool-result",
                           observation_ref="missing-launch-observation")
        with self.assertRaises(self.module.NativeTreeError):
            self.tree.bind_role(new_binding)

    def test_spawn_binding_uses_current_task_name_envelope(self):
        self.claimed_spawn()
        self.observe({"task_name": "/root/fresh"}, command_id="spawn-1", observation_id="launch")
        new_binding = dict(binding("fresh", target="/root/fresh"), source_kind="native-tool-result",
                           observation_ref="synthetic-evidence-launch")
        result = self.tree.bind_role(new_binding)
        self.assertTrue(result["created"])
        self.assertEqual(result["binding"]["native_target"], "/root/fresh")
        self.assertNotIn("session_id", result["binding"])

    def cli(self, request, *, store=None, create=False, raw=False):
        context_path = Path(self.temp.name) / "context.json"
        context_path.write_text(json.dumps({"run": self.run, "actor": self.actor}))
        command = [sys.executable, "-I", "-S", "-B", str(MODULE),
                   "--store", str(store or self.path), "--context", str(context_path)]
        if create:
            command.append("--create")
        return subprocess.run(command, input=request if raw else json.dumps(request),
                              capture_output=True, text=True, timeout=10)

    def test_cli_prepare_claim_emits_one_exact_instruction(self):
        self.tree.bind_role(binding())
        payload = {"message": "bounded CLI work"}
        request = {"operation": "prepare-claim", "plan": plan(payload),
                   "action": "activate-or-steer", "role": "worker", "generation": 1,
                   "payload": payload, "mode": "assign"}
        first = self.cli(request)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertTrue(first.stdout.strip(), "CLI must return the claimed native instruction")
        claimed = json.loads(first.stdout)
        self.assertTrue(claimed["claimed"])
        self.assertEqual(claimed["native_call"], {"tool": "collaboration.followup_task",
                         "arguments": {"target": "/root/worker", "message": "bounded CLI work"}})
        second = self.cli(request)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertFalse(json.loads(second.stdout)["claimed"])
        self.assertNotIn("native_call", json.loads(second.stdout))

    def test_cli_rejects_duplicate_json_keys_before_creating_a_store(self):
        unused = Path(self.temp.name) / "must-not-be-created.sqlite3"
        reply = self.cli('{"operation":"inspect","operation":"claim"}',
                         store=unused, create=True, raw=True)
        self.assertNotEqual(reply.returncode, 0)
        self.assertFalse(unused.exists())
        self.assertEqual(reply.stdout, "")

    def assignment_view(self):
        return next(item for item in self.tree.inspect("synthetic-run")["assignments"]
                    if item["assignment_id"] == "assignment-1")

    def bound_spawn(self):
        frozen_plan, payload = self.claimed_spawn()
        self.observe({"task_name": "/root/fresh"}, command_id="spawn-1", observation_id="launch")
        self.tree.bind_role(dict(binding("fresh", target="/root/fresh"), source_kind="native-tool-result",
                                observation_ref="synthetic-evidence-launch"))
        return frozen_plan, payload

    def assert_native_outcome(self, command_id, state, *, missing=False, tree=None):
        snapshot = (tree or self.tree).inspect("synthetic-run", command_id)
        command = snapshot["commands"][0]
        self.assertEqual({"command_id": command_id, "kind": "native-outcome"}
                         in snapshot["missing_evidence"], missing)
        self.assertEqual(command["native_outcome"]["state"], state)
        # A derived outcome must never rewrite the committed claim history.
        self.assertEqual(command["state"], "unknown")
        return command["native_outcome"]

    def test_native_outcome_recovers_spawn_receipt_and_final_without_acceptance(self):
        frozen_plan, _ = self.claimed_spawn()
        self.assertIn({"command_id": "spawn-1", "kind": "native-outcome"},
                      self.tree.inspect("synthetic-run", "spawn-1")["missing_evidence"])
        self.observe({"task_name": "/root/fresh"}, command_id="spawn-1", observation_id="launch")
        receipt = self.assert_native_outcome("spawn-1", "creation-observed")
        self.assertEqual(receipt["native_target"], "/root/fresh")
        self.assertEqual(receipt["evidence_refs"], ["synthetic-evidence-launch"])
        self.tree.bind_role(dict(binding("fresh", target="/root/fresh"), source_kind="native-tool-result",
                                observation_ref="synthetic-evidence-launch"))
        payload = "An attributable result."
        self.observe("Message Type: FINAL_ANSWER\nTask name: /root\nSender: /root/fresh\nPayload:\n" + payload,
                     "harness-final-event", command_id="spawn-1", observation_id="final")
        result = self.assert_native_outcome("spawn-1", "output-observed")
        self.assertEqual(result["result_digest"], digest(payload))
        self.assertIn("synthetic-evidence-final", result["evidence_refs"])
        self.assertFalse(self.assignment_view()["evidence"]["accepted"])
        self.assertTrue(self.assignment_view()["native_busy"])
        with self.module.NativeTree(self.path, run=self.run, actor=self.actor) as reopened:
            self.assertEqual(self.assert_native_outcome("spawn-1", "output-observed", tree=reopened), result)
        self.tree.reconcile("spawn-1", "use-observed-result", {
            "reconciliation_id": "use-final", "decision_ref": "owner decision",
            "evidence_ref": "synthetic-evidence-final"})
        verification = {"assignment_id": "assignment-1", "generation": 1,
                        "input_digest": frozen_plan["request_sha256"], "result_digest": digest(payload),
                        "usable": True, "evidence_ref": "synthetic-evidence-verify-final"}
        self.observe(verification, "owner-verification", command_id="spawn-1", observation_id="verify-final")
        self.tree.accept("assignment-1", 1, digest(payload), verification["evidence_ref"])
        self.assertTrue(self.assignment_view()["evidence"]["usable"])
        self.assertTrue(self.assignment_view()["native_busy"])
        self.claim_inventory("inventory-final")
        self.claim_inventory("unrelated-inventory")
        self.observe({"agents": [{"agent_name": "/root/fresh", "agent_status": {"completed": payload}}]},
                     "native-inventory", command_id="spawn-1", observation_id="completed-final",
                     collected_by="inventory-final")
        self.assert_native_outcome("spawn-1", "output-observed")
        inventory = self.assert_native_outcome("inventory-final", "inventory-observed")
        self.assertEqual(inventory["evidence_refs"], ["synthetic-evidence-completed-final"])
        self.assert_native_outcome("unrelated-inventory", "unknown", missing=True)
        self.assertFalse(self.assignment_view()["native_busy"])
        self.assertFalse(self.tree.claim("spawn-1")["claimed"])

    def test_native_outcome_keeps_worker_acceptance_and_disposition_separate(self):
        result_digest, input_digest = self.reported_result()
        self.tree.reconcile("command-1", "use-observed-result", {
            "reconciliation_id": "use-worker", "decision_ref": "owner decision",
            "evidence_ref": "synthetic-evidence-report"})
        ref = self.verify_result(result_digest, input_digest)
        self.tree.accept("assignment-1", 1, result_digest, ref)
        self.assert_native_outcome("command-1", "unknown", missing=True)
        self.assertTrue(self.assignment_view()["evidence"]["usable"])
        self.assertFalse(self.assignment_view()["evidence"]["native_completion"]["observed"])
        self.assertTrue(self.assignment_view()["native_busy"])

    def test_native_outcome_limits_interrupt_and_timeout_to_the_observed_response(self):
        self.prepare_work()
        self.tree.claim("command-1")
        self.tree.prepare(plan({}, "interrupt", None), "interrupt", "worker", 1, {}, "request")
        self.tree.claim("interrupt")
        self.observe({"previous_status": "running"}, command_id="interrupt", observation_id="interrupted")
        outcome = self.assert_native_outcome("interrupt", "interrupt-response-observed")
        self.assertEqual(outcome["previous_status"], "running")
        self.assertEqual(outcome["operation_effect"], "unknown")
        self.tree.prepare(plan({}, "wait", None), "wait", None, None, {}, "bounded")
        self.tree.claim("wait")
        self.observe({"timed_out": True}, command_id="wait", observation_id="timeout")
        outcome = self.assert_native_outcome("wait", "wait-timeout-observed")
        self.assertEqual(outcome["operation_effect"], "unknown")
        self.assert_native_outcome("command-1", "unknown", missing=True)
        payload = {"message": "continue without established interruption"}
        self.tree.prepare(plan(payload, "continuation"), "activate-or-steer", "worker", 1, payload, "continue")
        with self.assertRaises(self.module.NativeTreeError):
            self.tree.claim("continuation")
        with self.assertRaises(self.module.NativeTreeError):
            self.tree.reconcile("command-1", "authorize-new-attempt", {
                "reconciliation_id": "retry-timeout", "decision_ref": "owner decision",
                "basis": "wait-timeout", "evidence_ref": "synthetic-evidence-timeout"})

    def test_native_outcome_inventory_is_collector_evidence_not_subject_completion(self):
        self.claim_inventory("old-inventory")
        self.prepare_work()
        self.tree.claim("command-1")
        self.observe({"agents": [{"agent_name": "/root/worker", "agent_status": {"completed": "done"}}]},
                     "native-inventory", collected_by="old-inventory")
        self.assert_native_outcome("old-inventory", "inventory-observed")
        self.assert_native_outcome("command-1", "unknown", missing=True)
        self.assertTrue(self.assignment_view()["native_busy"])
        self.claim_inventory("empty-inventory")
        self.observe({"agents": []}, "native-inventory", observation_id="empty", collected_by="empty-inventory")
        self.assert_native_outcome("empty-inventory", "inventory-observed")
        self.claim_inventory("unmapped-inventory")
        for index, raw in enumerate(({"unknown": []}, {"agents": [{"agent_name": "/root/worker", "agent_status": "future"}]},
                                     {"agents": [{"agent_name": "/root/worker", "agent_status": "running"},
                                                 {"agent_name": "/root/worker", "agent_status": "interrupted"}]})):
            self.observe(raw, "native-inventory", observation_id="unmapped-" + str(index),
                         collected_by="unmapped-inventory")
        self.assert_native_outcome("unmapped-inventory", "unknown", missing=True)
        self.assert_native_outcome("command-1", "unknown", missing=True)

    def test_native_outcome_does_not_attribute_copied_foreign_or_ambiguous_finals(self):
        self.bound_spawn()
        envelope = "Message Type: FINAL_ANSWER\nTask name: /root\nSender: /root/fresh\nPayload:\nDONE"
        for index, (raw, source) in enumerate(((envelope, "worker-report"),
                (envelope.replace("Task name: /root\n", "Task name: /root/other\n"), "harness-final-event"),
                (envelope.replace("Sender: /root/fresh\n", "Sender: /root/foreign\n"), "harness-final-event"),
                ({"future_envelope": "DONE"}, "native-tool-result"))):
            self.observe(raw, source, command_id="spawn-1", observation_id="unsupported-" + str(index))
        self.assert_native_outcome("spawn-1", "creation-observed")
        payload = {"message": "another input"}
        self.tree.prepare(plan(payload, "notice", None), "notify", "fresh", 1, payload, "information")
        self.tree.claim("notice")
        self.observe(envelope, "harness-final-event", command_id="spawn-1", observation_id="ambiguous")
        self.observe({"acknowledged": True}, command_id="notice", observation_id="acknowledgement")
        self.assert_native_outcome("spawn-1", "creation-observed")
        self.assert_native_outcome("notice", "unknown", missing=True)
        self.assertFalse(self.assignment_view()["evidence"]["native_completion"]["observed"])
        self.observe({"task_name": "/root/conflicting"}, command_id="spawn-1", observation_id="conflicting-target")
        self.assert_native_outcome("spawn-1", "conflicting", missing=True)

    def test_native_outcome_keeps_older_attempt_unknown_after_retry_receipt(self):
        frozen_plan, payload = self.claimed_spawn()
        self.tree.reconcile("spawn-1", "keep-unknown", {
            "reconciliation_id": "keep-old", "decision_ref": "owner decision", "evidence_ref": "lost response"})
        self.tree.reconcile("spawn-1", "authorize-new-attempt", {
            "reconciliation_id": "retry-old", "decision_ref": "owner decision",
            "basis": "duplicate-risk-accepted", "evidence_ref": "bounded retry decision"})
        retry = dict(frozen_plan, command_id="spawn-retry", predecessor_reconciliation_ref="retry-old")
        self.tree.prepare(retry, "spawn", "fresh", 1, payload, "fresh")
        self.tree.claim("spawn-retry")
        self.observe({"task_name": "/root/retry"}, command_id="spawn-retry", observation_id="retry-launch")
        self.assert_native_outcome("spawn-retry", "creation-observed")
        self.assert_native_outcome("spawn-1", "unknown", missing=True)
        self.tree.reconcile("spawn-retry", "abandon", {
            "reconciliation_id": "abandon-retry", "decision_ref": "owner decision", "evidence_ref": "uncertain work"})
        self.assert_native_outcome("spawn-1", "unknown", missing=True)
        self.assertTrue(self.assignment_view()["native_busy"])
        replay = self.tree.claim("spawn-retry")
        self.assertFalse(replay["claimed"])
        self.assertNotIn("native_call", replay)

    def test_business_input_digest_is_distinct_from_transport_request_digest(self):
        self.tree.bind_role(binding())
        input_digest = digest({"business_input": "fixed source data"})
        payload = {"message": "Echo this input digest in the result: " + input_digest}
        request = dict(plan(payload), input_sha256=input_digest)
        self.assertNotEqual(request["request_sha256"], input_digest)
        self.tree.prepare(request, "activate-or-steer", "worker", 1, payload, "assign")
        self.tree.claim("command-1")
        result = {"answer": 42}
        result_digest = digest(result)
        self.observe({"assignment_id": "assignment-1", "generation": 1,
                      "input_digest": input_digest, "result": result,
                      "result_digest": result_digest}, "worker-report", observation_id="report")
        ref = self.verify_result(result_digest, input_digest)
        self.assertTrue(self.tree.accept("assignment-1", 1, result_digest, ref)["accepted"])

    def test_profile_ceiling_is_not_achieved_evidence(self):
        self.claimed_spawn()
        evidence = self.assignment_view()["evidence"]
        self.assertFalse(evidence["usable"])
        self.assertEqual(evidence["dimensions"]["target"]["maximum"], "controller-observed")
        for name in ("target", "topology", "model", "authority", "execution_result"):
            self.assertIsNone(evidence["dimensions"][name]["achieved"])
        self.assertEqual(evidence["dimensions"]["model"]["maximum"], "self-reported")

    def test_exact_fresh_child_final_maps_output_without_accepting_it(self):
        self.bound_spawn()
        payload = "A result\r\nwith Cafe\u0301, DONE, and model claims.\n"
        envelope = "Message Type: FINAL_ANSWER\nTask name: /root\nSender: /root/fresh\nPayload:\n" + payload
        self.observe(envelope, "harness-final-event", command_id="spawn-1", observation_id="final")
        evidence = self.assignment_view()["evidence"]
        self.assertEqual(evidence["dimensions"]["target"]["achieved"], "controller-observed")
        self.assertEqual(evidence["dimensions"]["topology"]["achieved"], "controller-observed")
        self.assertEqual(evidence["dimensions"]["execution_result"]["achieved"], "controller-observed")
        self.assertEqual(evidence["result_digest"], digest(payload))
        self.assertIsNone(evidence["dimensions"]["model"]["achieved"])
        self.assertIsNone(evidence["dimensions"]["authority"]["achieved"])
        self.assertFalse(evidence["usable"])

    def test_copied_or_wrong_receiver_final_does_not_gain_host_assurance(self):
        self.bound_spawn()
        payload = "DONE"
        envelope = "Message Type: FINAL_ANSWER\nTask name: /root\nSender: /root/fresh\nPayload:\n" + payload
        self.observe(envelope, "worker-report", command_id="spawn-1", observation_id="copied")
        self.observe(envelope.replace("Task name: /root\n", "Task name: /root/other\n"),
                     "harness-final-event", command_id="spawn-1", observation_id="wrong-receiver")
        self.assertIsNone(self.assignment_view()["evidence"]["dimensions"]["execution_result"]["achieved"])

    def test_additional_input_prevents_ambiguous_final_attribution(self):
        self.bound_spawn()
        payload = {"message": "additional input for the same child"}
        self.tree.prepare(plan(payload, "notification", None), "notify", "fresh", 1, payload, "information")
        self.tree.claim("notification")
        self.observe("Message Type: FINAL_ANSWER\nTask name: /root\nSender: /root/fresh\nPayload:\nDONE",
                     "harness-final-event", command_id="spawn-1", observation_id="late-final")
        self.assertIsNone(self.assignment_view()["evidence"]["dimensions"]["execution_result"]["achieved"])

    def test_unavailable_or_excessive_assurance_is_rejected_before_claim(self):
        self.tree.bind_role(binding())
        payload = {"message": "bounded work"}
        for dimension, minimum in (("model", "self-reported"), ("execution_result", "product-attested")):
            with self.subTest(dimension=dimension):
                request = dict(plan(payload), assurance_minima={dimension: minimum})
                with self.assertRaises(self.module.NativeTreeError):
                    self.tree.prepare(request, "activate-or-steer", "worker", 1, payload, "assign")

    def test_bound_spawn_replay_is_lookup_in_api_and_cli(self):
        frozen_plan, payload = self.bound_spawn()
        self.assertFalse(self.tree.prepare(frozen_plan, "spawn", "fresh", 1, payload, "fresh")["created"])
        replay = self.cli({"operation": "prepare-claim", "plan": frozen_plan,
                           "action": "spawn", "role": "fresh", "generation": 1,
                           "payload": payload, "mode": "fresh"})
        self.assertEqual(replay.returncode, 0, replay.stderr)
        self.assertFalse(json.loads(replay.stdout)["claimed"])
        self.assertNotIn("native_call", json.loads(replay.stdout))

    def test_current_owner_can_preserve_and_abandon_a_lost_spawn(self):
        self.claimed_spawn()
        evidence = {"reconciliation_id": "keep", "decision_ref": "owner decision",
                    "evidence_ref": "lost response retained"}
        self.assertTrue(self.tree.reconcile("spawn-1", "keep-unknown", evidence)["created"])
        evidence["reconciliation_id"] = "abandon"
        self.assertTrue(self.tree.reconcile("spawn-1", "abandon", evidence)["created"])
        assignment = self.assignment_view()
        self.assertEqual(assignment["state"], "abandoned")
        self.assertTrue(assignment["native_busy"])
        self.assertIsNone(assignment["native_target"])

    def test_lost_spawn_can_consume_one_explicit_unchanged_retry(self):
        frozen_plan, payload = self.claimed_spawn()
        self.tree.reconcile("spawn-1", "authorize-new-attempt", {
            "reconciliation_id": "retry-spawn", "decision_ref": "owner decision",
            "basis": "nondelivery-established", "evidence_ref": "synthetic proof"})
        request = dict(frozen_plan, command_id="spawn-retry", predecessor_reconciliation_ref="retry-spawn")
        self.tree.prepare(request, "spawn", "fresh", 1, payload, "fresh")
        self.assertTrue(self.tree.claim("spawn-retry")["claimed"])
        self.assertFalse(self.tree.claim("spawn-retry")["claimed"])

    def test_lost_spawn_reconciliation_works_through_cli(self):
        self.claimed_spawn()
        reply = self.cli({"operation": "reconcile", "command_id": "spawn-1",
                          "disposition": "keep-unknown", "evidence": {
                              "reconciliation_id": "cli-keep", "decision_ref": "owner decision",
                              "evidence_ref": "missing launch result"}})
        self.assertEqual(reply.returncode, 0, reply.stderr)
        self.assertTrue(json.loads(reply.stdout)["created"])

    def test_changed_message_continuation_can_retry_its_own_exact_payload(self):
        _, original_plan, _ = self.prepare_work()
        self.tree.claim("command-1")
        self.claim_inventory()
        self.observe({"agents": [{"agent_name": "/root/worker", "agent_status": "interrupted"}]},
                     "native-inventory", collected_by="inspect-1")
        payload = {"message": "resume from a different checkpoint instruction"}
        continuation = dict(plan(payload, "continuation"), input_sha256=original_plan["request_sha256"])
        self.tree.prepare(continuation, "activate-or-steer", "worker", 1, payload, "continue")
        self.tree.claim("continuation")
        self.tree.reconcile("continuation", "authorize-new-attempt", {
            "reconciliation_id": "retry-continuation", "decision_ref": "owner decision",
            "basis": "nondelivery-established", "evidence_ref": "synthetic proof"})
        retry = dict(continuation, command_id="continuation-retry", predecessor_reconciliation_ref="retry-continuation")
        self.tree.prepare(retry, "activate-or-steer", "worker", 1, payload, "continue")
        self.assertTrue(self.tree.claim("continuation-retry")["claimed"])

    def test_local_retirement_preserves_identity_and_blocks_pending_dispatch(self):
        self.prepare_work()
        self.assertTrue(self.tree.retire_role("worker", 1, "retirement decision")["retired"])
        self.assertFalse(self.tree.retire_role("worker", 1, "retirement decision")["retired"])
        with self.assertRaises(self.module.NativeTreeError):
            self.tree.claim("command-1")
        entry = next(item for item in self.tree.inspect("synthetic-run")["bindings"] if item["role"] == "worker")
        self.assertTrue(entry["retired"])
        self.assertEqual(entry["native_target"], "/root/worker")

    def test_retirement_does_not_clear_ongoing_actual_target_hazard(self):
        self.prepare_work()
        self.tree.claim("command-1")
        self.tree.retire_role("worker", 1, "retirement decision")
        self.tree.bind_role(binding(generation=2))
        payload = {"message": "different assignment"}
        self.tree.prepare(plan(payload, "work-2", "assignment-2"), "activate-or-steer", "worker", 2, payload, "assign")
        self.assertFalse(self.tree.claim("work-2")["claimed"])
        self.tree.bind_role(binding(generation=3, target="/root/new-worker"))
        self.tree.prepare(plan(payload, "work-3", "assignment-3"), "activate-or-steer", "worker", 3, payload, "assign")
        self.assertTrue(self.tree.claim("work-3")["claimed"])

    def late_abandoned_spawn(self):
        self.claimed_spawn()
        self.tree.reconcile("spawn-1", "abandon", {
            "reconciliation_id": "abandoned-before-receipt", "decision_ref": "owner decision",
            "evidence_ref": "lost receipt retained"})
        self.observe({"task_name": "/root/fresh"}, command_id="spawn-1", observation_id="late-launch")
        self.tree.bind_role(dict(binding("fresh", target="/root/fresh"),
                                source_kind="native-tool-result",
                                observation_ref="synthetic-evidence-late-launch"))
        self.tree.retire_role("fresh", 1, "retire late child")

    def test_late_launch_keeps_abandoned_target_reserved_until_fresh_completion(self):
        self.late_abandoned_spawn()
        self.assertEqual(self.assignment_view()["native_target"], "/root/fresh")
        self.assertTrue(self.assignment_view()["native_busy"])
        self.tree.bind_role(binding("fresh", 2, "/root/fresh"))
        payload = {"message": "replacement work"}
        self.tree.prepare(plan(payload, "new-work", "assignment-2"),
                          "activate-or-steer", "fresh", 2, payload, "assign")
        self.assertFalse(self.tree.claim("new-work")["claimed"])
        self.claim_inventory("after-abandonment")
        self.observe({"agents": [{"agent_name": "/root/fresh", "agent_status": {"completed": "done"}}]},
                     "native-inventory", command_id="spawn-1", observation_id="late-completed",
                     collected_by="after-abandonment")
        self.assertTrue(self.tree.claim("new-work")["claimed"])

    def test_late_abandoned_target_cannot_be_used_through_a_role_alias(self):
        self.late_abandoned_spawn()
        payload = {"message": "alias work"}
        try:
            self.tree.bind_role(binding("alias", 1, "/root/fresh"))
        except self.module.NativeTreeError:
            pass
        else:
            self.tree.prepare(plan(payload, "alias-work", "alias-assignment"),
                              "activate-or-steer", "alias", 1, payload, "assign")
            self.assertFalse(self.tree.claim("alias-work")["claimed"])
        self.tree.bind_role(binding("fresh", 2, "/root/different"))
        self.tree.prepare(plan(payload, "different-work", "different-assignment"),
                          "activate-or-steer", "fresh", 2, payload, "assign")
        self.assertTrue(self.tree.claim("different-work")["claimed"])

    def test_late_identity_reserves_activity_even_after_role_generation_advanced(self):
        self.claimed_spawn()
        self.tree.reconcile("spawn-1", "abandon", {
            "reconciliation_id": "close-old", "decision_ref": "owner decision",
            "evidence_ref": "old unknown attempt"})
        self.tree.bind_role(binding("fresh", 2, "/root/current"))
        self.observe({"task_name": "/root/late-original"}, command_id="spawn-1", observation_id="late-original")
        self.tree.bind_role(binding("old-target", 1, "/root/late-original"))
        payload = {"message": "unrelated work"}
        self.tree.prepare(plan(payload, "old-target-work", "different-assignment"),
                          "activate-or-steer", "old-target", 1, payload, "assign")
        self.assertFalse(self.tree.claim("old-target-work")["claimed"])
        self.tree.prepare(plan(payload, "current-target-work", "current-assignment"),
                          "activate-or-steer", "fresh", 2, payload, "assign")
        self.assertTrue(self.tree.claim("current-target-work")["claimed"])

    def test_each_observed_retry_target_stays_reserved_and_releases_separately(self):
        original_plan, payload = self.claimed_spawn()
        self.tree.reconcile("spawn-1", "authorize-new-attempt", {
            "reconciliation_id": "allow-duplicate", "decision_ref": "explicit owner decision",
            "evidence_ref": "bounded retry decision", "basis": "duplicate-risk-accepted"})
        retry = dict(original_plan, command_id="spawn-retry", predecessor_reconciliation_ref="allow-duplicate")
        self.tree.prepare(retry, "spawn", "fresh", 1, payload, "fresh")
        self.tree.claim("spawn-retry")
        self.observe({"task_name": "/root/retry-child"}, command_id="spawn-retry", observation_id="retry-launch")
        self.tree.bind_role(dict(binding("fresh", 1, "/root/retry-child"),
                                source_kind="native-tool-result", observation_ref="synthetic-evidence-retry-launch"))
        self.observe({"task_name": "/root/original-child"}, command_id="spawn-1", observation_id="original-launch")
        self.tree.reconcile("spawn-retry", "abandon", {
            "reconciliation_id": "close-retries", "decision_ref": "owner decision",
            "evidence_ref": "both attempts retained"})
        self.tree.retire_role("fresh", 1, "retire both from logical service")
        for role, target in (("old", "/root/original-child"), ("new", "/root/retry-child")):
            self.tree.bind_role(binding(role, 1, target))
            packet = {"message": "unrelated " + role}
            self.tree.prepare(plan(packet, role + "-work", role + "-assignment"),
                              "activate-or-steer", role, 1, packet, "assign")
            self.assertFalse(self.tree.claim(role + "-work")["claimed"])
        self.claim_inventory("check-old")
        self.observe({"agents": [{"agent_name": "/root/original-child", "agent_status": {"completed": "done"}}]},
                     "native-inventory", command_id="spawn-1", observation_id="old-completed", collected_by="check-old")
        self.assertTrue(self.tree.claim("old-work")["claimed"])
        self.assertFalse(self.tree.claim("new-work")["claimed"])
        self.claim_inventory("check-new")
        self.observe({"agents": [{"agent_name": "/root/retry-child", "agent_status": {"completed": "done"}}]},
                     "native-inventory", command_id="spawn-retry", observation_id="new-completed", collected_by="check-new")
        self.assertTrue(self.tree.claim("new-work")["claimed"])

    def test_inspection_recovers_retry_decision_and_consumption_after_reopen(self):
        _, original_plan, payload = self.prepare_work()
        self.tree.claim("command-1")
        self.tree.reconcile("command-1", "authorize-new-attempt", {
            "reconciliation_id": "recoverable-decision", "decision_ref": "owner decision",
            "evidence_ref": "nondelivery evidence", "basis": "nondelivery-established"})
        with self.module.NativeTree(self.path, run=self.run, actor=self.actor) as opened:
            decision = next(item for item in opened.inspect("synthetic-run")["reconciliations"]
                            if item["reconciliation_id"] == "recoverable-decision")
            self.assertIsNone(decision["consumed_by"])
            self.assertEqual(decision["evidence"]["decision_ref"], "owner decision")
        retry = dict(original_plan, command_id="recovered-retry", predecessor_reconciliation_ref="recoverable-decision")
        self.tree.prepare(retry, "activate-or-steer", "worker", 1, payload, "assign")
        self.tree.claim("recovered-retry")
        result = self.cli({"operation": "inspect", "run_id": "synthetic-run"})
        self.assertEqual(result.returncode, 0, result.stderr)
        decision = next(item for item in json.loads(result.stdout)["reconciliations"]
                        if item["reconciliation_id"] == "recoverable-decision")
        self.assertEqual(decision["consumed_by"], "recovered-retry")

    def test_inspection_never_advertises_a_known_blocked_claim(self):
        self.prepare_work()
        actions = self.tree.inspect("synthetic-run", "command-1")["next_actions"]
        self.assertTrue(any(item.get("operation") == "claim" for item in actions))
        self.tree.retire_role("worker", 1, "withdrawn")
        actions = self.tree.inspect("synthetic-run", "command-1")["next_actions"]
        self.assertFalse(any(item.get("operation") == "claim" for item in actions))

    def test_notification_cannot_reference_a_nonexistent_assignment(self):
        self.tree.bind_role(binding())
        payload = {"message": "Information with no established assignment."}
        with self.assertRaises(self.module.NativeTreeError):
            self.tree.prepare(plan(payload, "notice", "future-assignment"),
                              "notify", "worker", 1, payload, "information")
        snapshot = self.tree.inspect("synthetic-run")
        self.assertEqual(snapshot["assignments"], [])
        self.assertEqual(snapshot["activities"], [])
        self.assertFalse(any(item["command_id"] == "notice" for item in snapshot["commands"]))

    def test_cli_refuses_orphan_correlation_without_emitting_a_call(self):
        self.tree.bind_role(binding())
        payload = {"message": "Informational CLI message."}
        reply = self.cli({"operation": "prepare-claim", "plan": plan(payload, "notice", "future-assignment"),
                          "action": "notify", "role": "worker", "generation": 1,
                          "payload": payload, "mode": "information"})
        self.assertNotEqual(reply.returncode, 0)
        self.assertEqual(reply.stdout, "")
        snapshot = self.cli({"operation": "inspect", "run_id": "synthetic-run"})
        self.assertEqual(snapshot.returncode, 0, snapshot.stderr)
        self.assertEqual(json.loads(snapshot.stdout)["assignments"], [])

    def test_notifications_preserve_existing_or_absent_assignment_correlation(self):
        self.prepare_work()
        self.tree.claim("command-1")
        for command_id, assignment_id in (("correlated-notice", "assignment-1"), ("uncorrelated-notice", None)):
            payload = {"message": "Keep exact notification text.\r\nCafe\u0301"}
            self.tree.prepare(plan(payload, command_id, assignment_id),
                              "notify", "worker", 1, payload, "information")
            claimed = self.tree.claim(command_id)
            self.assertEqual(claimed["native_call"], {"tool": "collaboration.send_message",
                             "arguments": {"target": "/root/worker", "message": payload["message"]}})
            self.assertFalse(self.tree.claim(command_id)["claimed"])
        self.assertEqual(len(self.tree.inspect("synthetic-run")["assignments"]), 1)

    def test_nonwork_correlation_cannot_change_established_ownership(self):
        self.prepare_work()
        self.tree.claim("command-1")
        payload = {"message": "Notification about existing work."}
        request = plan(payload, "wrong-owner", "assignment-1")
        request["owner"] = {"role": "worker", "generation": 1}
        with self.assertRaises(self.module.NativeTreeError):
            self.tree.prepare(request, "notify", "worker", 1, payload, "information")

    def test_legacy_emitted_orphan_remains_inspectable_after_reopen(self):
        self.tree.bind_role(binding())
        payload = {"message": "Previously emitted correlation.\r\nCafe\u0301"}
        self.tree.prepare(plan(payload, "legacy-notice", None),
                          "notify", "worker", 1, payload, "information")
        self.tree.claim("legacy-notice")
        self.tree.prepare(plan({}, "unrelated-wait", None), "wait", None, None, {}, "bounded")
        # Compatibility fixture: this is the exact command record accepted and
        # emitted by the earlier public API. Seed its persisted plan, without
        # using a repair path or inventing an assignment lifecycle row.
        with contextlib.closing(sqlite3.connect(self.path)) as database, database:
            record = json.loads(database.execute("SELECT content FROM commands WHERE command_id=?",
                                                ("legacy-notice",)).fetchone()[0])
            record["plan"] = plan(payload, "legacy-notice", "legacy-future-assignment")
            encoded = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
            database.execute("UPDATE commands SET content=?, command_sha256=? WHERE command_id=?",
                             (encoded, digest(record), "legacy-notice"))
        with self.module.NativeTree(self.path, run=self.run, actor=self.actor) as reopened:
            for selected in (None, "legacy-notice", "worker"):
                snapshot = reopened.inspect("synthetic-run", selected)
                notice = next(item for item in snapshot["commands"] if item["command_id"] == "legacy-notice")
                self.assertEqual(notice["plan"]["assignment_id"], "legacy-future-assignment")
                self.assertEqual(notice["payload"], payload)
                self.assertEqual(snapshot["assignments"], [])
                self.assertEqual(snapshot["activities"], [])
                self.assertFalse(any(item["command_id"] == "legacy-notice" and item["operation"] in ("claim", "reconcile")
                                     for item in snapshot["next_actions"]))
            self.assertFalse(reopened.claim("legacy-notice")["claimed"])
        result = self.cli({"operation": "inspect", "run_id": "synthetic-run"})
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = json.loads(result.stdout)["commands"]
        self.assertTrue(any(item["command_id"] == "unrelated-wait" for item in commands))


if __name__ == "__main__":
    unittest.main()
