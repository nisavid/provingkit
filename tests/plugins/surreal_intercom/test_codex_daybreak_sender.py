"""Public Daybreak operation contract with caller-owned native controls."""

import hashlib
import json
from pathlib import Path
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import unittest

SENDER = (Path(__file__).resolve().parents[3] / "plugins/surreal-intercom/skills/communicating-with-agents/scripts/codex_daybreak_sender.py")
NATIVE_FIXTURE = r"""
import json,sys
from pathlib import Path
request=json.load(sys.stdin)
call=request["call"]
path=Path(request["log"])
calls=json.loads(path.read_text()) if path.exists() else []
a=call["arguments"]
if call["tool"]=="mcp__codex_app__create_thread":
    assert a["model"]=="gpt-6-sol"
    assert a["target"]=={"type":"projectless"}
    assert "thinking" not in a and "title" not in a
    assert isinstance(a["prompt"],str) and a["prompt"].strip()
    result={"threadId":"fixture-child-01","hostId":"local"}
elif call["tool"]=="mcp__codex_app__read_thread":
    assert a=={"threadId":"fixture-child-01","hostId":"local","turnLimit":1,"includeOutputs":False,"maxOutputCharsPerItem":2048}
    result={"threadId":"fixture-child-01","bootstrap":"pending"}
else:
    raise AssertionError("unexpected external native control")
calls.append(call)
path.write_text(json.dumps(calls))
print(json.dumps({"content":[{"type":"text","text":json.dumps(result)}]}))
"""


class PendingBootstrapCommandTests(unittest.TestCase):
    def negative_outcome_intent(self, scratch, root):
        return {
            "operation_id": "negative-operation", "message_id": "negative-message",
            "attempt_id": "negative-attempt", "correlation_id": "negative-exchange",
            "sender": {"thread_id": "origin", "host_id": "local"},
            "actor": {"thread_id": "caller", "host_id": "local"},
            "owner": {"thread_id": "owner", "host_id": "local"},
            "authority_ref": "synthetic://negative-grant", "holds": [],
            "payload": "Do not submit the task after uncertain native evidence.",
            "endpoint": str(scratch / "unused.sock"), "mailbox": str(scratch / "mailbox.sqlite3"),
            "capture": {"run_root": str(root), "allowance_bytes": 8388608,
                        "terminal_provision_bytes": 524288, "later_forecast_bytes": 0},
            "observation_seconds": 0.1,
        }

    def test_prepare_refuses_unusable_intent_before_creation_and_allows_corrected_retry(self):
        missing=object()
        variants={
            "sender":(missing,None,"caller",{},
                      {"thread_id":"origin"},{"thread_id":"origin","host_id":" "},
                      {"thread_id":0,"host_id":"local"},
                      {"thread_id":"origin","host_id":"local","extra":True}),
            "correlation_id":(missing,None,""," ",0,{}),
            "mailbox":(missing,None,""," ",0,{}),
            "capture":(missing,None,False,[],{}, {"unexpected":True}),
            "capture.run_root":(".",None),
            "capture.allowance_bytes":(True,524288),
            "capture.terminal_provision_bytes":(True,0),
            "capture.later_forecast_bytes":(True,-1),
            "observation_seconds":(missing,None,True,"0.1",{},[],0,-1,10.1),
        }
        for field,values in variants.items():
            for bad in values:
                with self.subTest(field=field,value="omitted" if bad is missing else bad), tempfile.TemporaryDirectory(prefix="db-intent-") as directory:
                    scratch=Path(directory).resolve()
                    root=scratch/"operations"
                    root.mkdir(mode=0o700)
                    command=self.command(scratch,root)
                    valid=self.negative_outcome_intent(scratch,root)
                    valid["sender"]={"thread_id":"origin","host_id":"local"}
                    invalid=dict(valid)
                    key,_,setting=field.partition(".")
                    if setting:
                        invalid[key]={**valid[key],setting:bad}
                    elif bad is missing:
                        del invalid[key]
                    else:
                        invalid[key]=bad
                    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as listener:
                        listener.bind(valid["endpoint"])
                        listener.listen(1)
                        listener.setblocking(False)
                        refused=command("prepare",value=invalid)
                        self.assertEqual(refused["status"],"refused",refused)
                        self.assertIsNone(refused["native_call"])
                        self.assertEqual(refused["ipc"],"not_attempted")
                        self.assertEqual(list(root.iterdir()),[])
                        self.assertFalse(Path(valid["mailbox"]).exists())
                        with self.assertRaises(BlockingIOError):
                            connection,_=listener.accept()
                            connection.close()
                        prepared=command("prepare",value=valid)
                        self.assertEqual(prepared["status"],"prepared",prepared)
                        self.assertEqual(prepared["refs"]["operation_id"],valid["operation_id"])
                        self.assertEqual(prepared["native_call"]["tool"],"mcp__codex_app__create_thread")
                        self.assertEqual(json.loads(Path(prepared["refs"]["operation_ref"]).read_bytes()),valid)
                        self.assertFalse(Path(valid["mailbox"]).exists())
                        with self.assertRaises(BlockingIOError):
                            connection,_=listener.accept()
                            connection.close()

    def test_creation_failure_and_uncertainty_retain_original_result_and_references(self):
        variants = [("failed", {}), ("unknown", {"client_thread_id": "invented-pending"}),
                    ("unknown", {"child": {"thread_id": "invented-child", "host_id": "local"}})]
        for state, identity in variants:
            with self.subTest(state=state, identity=identity), tempfile.TemporaryDirectory(prefix="db-create-error-") as directory:
                scratch = Path(directory).resolve()
                root = scratch / "operations"
                root.mkdir(mode=0o700)
                command = self.command(scratch, root)
                request = self.negative_outcome_intent(scratch, root)
                prepared = command("prepare", value=request)
                receipt = {"call": prepared["native_call"],
                           "result": {"isError": True, "content": [{"type": "text", "text": "invented native failure"}]},
                           "creation": {"state": state, "evidence_ref": "synthetic://creation-error"}, **identity}
                retained = command("bind", request["operation_id"], receipt)
                self.assertEqual(retained["status"], "creation_" + state)
                self.assertIsNone(retained["native_call"])
                self.assertEqual(retained["ipc"], "not_attempted")
                self.assertEqual(retained["child"], identity.get("child"))
                if "client_thread_id" in identity:
                    self.assertEqual(retained["client_thread_id"], "invented-pending")
                for key in ("operation_id", "message_id", "attempt_id", "operation_ref"):
                    self.assertEqual(retained["refs"][key], prepared["refs"][key])
                self.assertEqual(json.loads(Path(retained["refs"]["creation_ref"]).read_bytes()), receipt)
                before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
                repeated = command("bind", request["operation_id"], receipt)
                shown = command("show", request["operation_id"])
                for observed in (repeated, shown, command("prepare", value=request)):
                    self.assertEqual(observed["status"], retained["status"])
                    self.assertEqual(observed["refs"], retained["refs"])
                    self.assertIsNone(observed["native_call"])
                conflict = command("bind", request["operation_id"], {
                    **receipt, "creation": {"state": state, "evidence_ref": "synthetic://different-error"},
                })
                self.assertEqual(conflict["status"], "refused")
                self.assertEqual({p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}, before)
                self.assertFalse((scratch / "mailbox.sqlite3").exists())

    def test_native_receipts_refuse_unsupported_requirements_before_retention_or_effects(self):
        for phase in ("bind", "creation-reconcile", "submit", "bootstrap-reconcile"):
            for field in ("account", "model", "effort", "cyberAccessProgram"):
                with self.subTest(phase=phase, field=field), tempfile.TemporaryDirectory(prefix="db-schema-") as directory:
                    scratch = Path(directory).resolve()
                    root = scratch / "operations"
                    root.mkdir(mode=0o700)
                    command = self.command(scratch, root)
                    request = self.negative_outcome_intent(scratch, root)
                    prepared = command("prepare", value=request)
                    child = {"thread_id": "invented-child", "host_id": "local"}
                    creation = {"call": prepared["native_call"], "result": {"invented": "creation"}, "child": child}
                    invocation = phase
                    if phase == "bind":
                        receipt = creation
                    elif phase == "creation-reconcile":
                        pending = {"call": prepared["native_call"], "result": {"invented": "queued"},
                                   "client_thread_id": "invented-pending"}
                        command("bind", request["operation_id"], pending)
                        receipt = {**creation, "client_thread_id": "invented-pending",
                                   "evidence_ref": "synthetic://creation-resolution"}
                        invocation = "reconcile"
                    else:
                        bound = command("bind", request["operation_id"], creation)
                        receipt = {"call": bound["native_call"], "result": {"invented": "completed"},
                                   "bootstrap": {"state": "completed", "evidence_ref": "synthetic://completion"}}
                        if phase == "bootstrap-reconcile":
                            command("submit", request["operation_id"], {
                                **receipt, "bootstrap": {"state": "pending", "evidence_ref": "synthetic://pending"},
                            })
                            invocation = "reconcile"
                    before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
                    refused = command(invocation, request["operation_id"], {**receipt, field: "unsupported"})
                    self.assertEqual(refused["status"], "refused")
                    self.assertIsNone(refused["native_call"])
                    self.assertEqual(refused["ipc"], "not_attempted")
                    self.assertEqual({p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}, before)
                    self.assertFalse((scratch / "mailbox.sqlite3").exists())

    def test_pending_creation_retains_unknown_result_before_same_handle_resolution(self):
        with tempfile.TemporaryDirectory(prefix="db-pending-error-") as directory:
            scratch = Path(directory).resolve()
            root = scratch / "operations"
            root.mkdir(mode=0o700)
            command = self.command(scratch, root)
            request = self.negative_outcome_intent(scratch, root)
            prepared = command("prepare", value=request)
            pending = {"call": prepared["native_call"], "result": {"invented": "queued"},
                       "client_thread_id": "invented-pending"}
            original = command("bind", request["operation_id"], pending)
            receipt = {"call": prepared["native_call"], "client_thread_id": "invented-pending",
                       "result": {"isError": True, "error": "invented uncertain resolution"},
                       "creation": {"state": "unknown", "evidence_ref": "synthetic://pending-error"}}
            retained = command("reconcile", request["operation_id"], receipt)
            self.assertEqual(retained["status"], "creation_unknown")
            self.assertEqual(retained["client_thread_id"], "invented-pending")
            self.assertIsNone(retained["native_call"])
            self.assertEqual(retained["refs"]["creation_ref"], original["refs"]["creation_ref"])
            observation = Path(retained["refs"]["creation_outcome_ref"])
            self.assertEqual(json.loads(observation.read_bytes()), receipt)
            before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            self.assertEqual(command("reconcile", request["operation_id"], receipt)["status"], "creation_unknown")
            self.assertEqual(command("show", request["operation_id"])["refs"], retained["refs"])
            conflict = command("reconcile", request["operation_id"], {
                **receipt, "creation": {"state": "unknown", "evidence_ref": "synthetic://different-error"},
            })
            self.assertEqual(conflict["status"], "refused")
            self.assertEqual({p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}, before)
            child = {"thread_id": "invented-child", "host_id": "local"}
            resolved = command("reconcile", request["operation_id"], {
                "call": prepared["native_call"], "client_thread_id": "invented-pending",
                "result": {"invented": "resolved"}, "child": child,
                "evidence_ref": "synthetic://later-resolution",
            })
            self.assertEqual(resolved["status"], "bootstrap_unobserved")
            self.assertEqual(resolved["child"], child)
            self.assertEqual(resolved["refs"]["creation_outcome_ref"], str(observation))
            self.assertEqual(resolved["native_call"]["arguments"]["threadId"], "invented-child")
            self.assertEqual(json.loads(observation.read_bytes()), receipt)
            self.assertFalse((scratch / "mailbox.sqlite3").exists())

    def test_bootstrap_read_error_retains_unknown_without_task_or_failure_claim(self):
        for pending_first in (False, True):
            with self.subTest(pending_first=pending_first), tempfile.TemporaryDirectory(prefix="db-bootstrap-error-") as directory:
                scratch = Path(directory).resolve()
                root = scratch / "operations"
                root.mkdir(mode=0o700)
                command = self.command(scratch, root)
                request = self.negative_outcome_intent(scratch, root)
                prepared = command("prepare", value=request)
                child = {"thread_id": "invented-child", "host_id": "local"}
                bound = command("bind", request["operation_id"], {
                    "call": prepared["native_call"], "result": {"invented": "creation"}, "child": child,
                })
                invocation = "submit"
                if pending_first:
                    command("submit", request["operation_id"], {
                        "call": bound["native_call"], "result": {"invented": "pending"},
                        "bootstrap": {"state": "pending", "evidence_ref": "synthetic://bootstrap-pending"},
                    })
                    invocation = "reconcile"
                receipt = {"call": bound["native_call"], "result": {"isError": True, "error": "invented read failure"},
                           "bootstrap": {"state": "unknown", "evidence_ref": "synthetic://read-error"}}
                before_error = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
                for false_state in ("failed", "completed"):
                    refused = command(invocation, request["operation_id"], {
                        **receipt, "bootstrap": {"state": false_state, "evidence_ref": "synthetic://read-error"},
                    })
                    self.assertEqual(refused["status"], "refused")
                    self.assertEqual({p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}, before_error)
                retained = command(invocation, request["operation_id"], receipt)
                self.assertEqual(retained["status"], "bootstrap_unknown")
                self.assertEqual(retained["child"], child)
                self.assertIsNone(retained["native_call"])
                self.assertEqual(retained["ipc"], "not_attempted")
                for key in ("operation_id", "message_id", "attempt_id", "operation_ref"):
                    self.assertEqual(retained["refs"][key], prepared["refs"][key])
                outcome = (Path(retained["refs"]["bootstrap_outcome_ref"]) if pending_first
                           else Path(retained["refs"]["operation_ref"]).with_name("bootstrap.json"))
                self.assertEqual(json.loads(outcome.read_bytes()), receipt)
                before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
                self.assertEqual(command(invocation, request["operation_id"], receipt)["status"], "bootstrap_unknown")
                self.assertEqual(command("show", request["operation_id"])["refs"], retained["refs"])
                conflict = command(invocation, request["operation_id"], {
                    **receipt, "bootstrap": {"state": "unknown", "evidence_ref": "synthetic://different-read-error"},
                })
                self.assertEqual(conflict["status"], "refused")
                self.assertEqual({p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}, before)
                self.assertFalse((scratch / "mailbox.sqlite3").exists())

    def command(self,scratch,root,standing_args=(),*,launcher=SENDER):
        counter=0

        def launch(phase,operation_id=None,value=None,*,extra_standing_args=()):
            nonlocal counter
            argv=[sys.executable,"-B",str(launcher),"--root",str(root),
                  *standing_args,*extra_standing_args,phase]
            if operation_id is not None:
                argv.append(operation_id)
            if value is not None:
                counter+=1
                source=scratch/f"input-{counter}.json"
                source.write_text(json.dumps(value))
                argv.extend(["--input",str(source)])
            result=subprocess.run(argv,capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stdout+"\n"+result.stderr)
            return json.loads(result.stdout)

        return launch

    def test_direct_binding_refuses_remote_child_without_consuming_creation(self):
        with tempfile.TemporaryDirectory(prefix="db-remote-") as directory:
            scratch=Path(directory).resolve()
            root=scratch/"operations"
            root.mkdir(mode=0o700)
            command=self.command(scratch,root)
            request={
                "operation_id":"remote-bind-operation", "message_id":"remote-bind-message",
                "attempt_id":"remote-bind-attempt", "correlation_id":"remote-bind-exchange",
                "sender":{"thread_id":"origin","host_id":"local"},
                "actor":{"thread_id":"caller","host_id":"local"},
                "owner":{"thread_id":"owner","host_id":"local"},
                "authority_ref":"synthetic://binding-grant", "holds":[],
                "payload":"Original task stays withheld during binding.",
                "endpoint":str(scratch/"unused.sock"), "mailbox":str(scratch/"mailbox.sqlite3"),
                "capture":{"run_root":str(root),"allowance_bytes":8388608,
                           "terminal_provision_bytes":524288,"later_forecast_bytes":0},
                "observation_seconds":0.5,
            }
            prepared=command("prepare",value=request)
            self.assertEqual(prepared["status"],"prepared")
            before={p.relative_to(root):p.read_bytes() for p in root.rglob("*") if p.is_file()}
            receipt={"call":prepared["native_call"],"result":{"invented":"creation"},
                     "child":{"thread_id":"invented-child","host_id":"remote-host"}}
            refused=command("bind",request["operation_id"],receipt)
            self.assertEqual(refused["status"],"refused")
            self.assertEqual(refused["reason"],"unsupported-remote-child")
            self.assertIsNone(refused["native_call"])
            self.assertEqual(refused["ipc"],"not_attempted")
            self.assertEqual({p.relative_to(root):p.read_bytes() for p in root.rglob("*")
                              if p.is_file()},before)
            self.assertFalse((scratch/"mailbox.sqlite3").exists())
            local=command("bind",request["operation_id"],{
                **receipt,"child":{"thread_id":"invented-child","host_id":"local"},
            })
            self.assertEqual(local["status"],"bootstrap_unobserved")
            self.assertEqual(local["child"],{"thread_id":"invented-child","host_id":"local"})
            self.assertEqual(local["native_call"]["arguments"]["hostId"],"local")

    def test_pending_bootstrap_retains_one_child_original_refs_and_no_ipc(self):
        with tempfile.TemporaryDirectory(prefix="db-pending-") as directory:
            scratch=Path(directory).resolve()
            root=scratch/"operations"
            root.mkdir(mode=0o700)
            endpoint=scratch/"peer.sock"
            log=scratch/"native.json"
            command=self.command(scratch,root)

            def native(call):
                result=subprocess.run([sys.executable,"-B","-c",NATIVE_FIXTURE],input=json.dumps({"call":call,"log":str(log)}),capture_output=True,text=True,timeout=10)
                self.assertEqual(result.returncode,0,result.stderr)
                raw=json.loads(result.stdout)
                # Only the invented external fixture has this decoding contract.
                return raw,json.loads(raw["content"][0]["text"])

            request={
                **self.negative_outcome_intent(scratch,root),
                "operation_id":"operation-task-only-01",
                "message_id":"message-task-only-01",
                "attempt_id":"attempt-task-only-01",
                "actor":{"thread_id":"caller-task-only","host_id":"local"},
                "owner":{"thread_id":"owner-task-only","host_id":"local"},
                "authority_ref":"grant-task-only",
                "holds":["hold-task-only"],
                "payload":"TASK_ONLY_PAYLOAD; complete original task context TASK_ONLY_CONTEXT",
                "endpoint":str(endpoint),
            }
            op=request["operation_id"]
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as peer:
                peer.bind(str(endpoint))
                peer.listen(8)
                peer.setblocking(False)
                prepared=command("prepare",value=request)
                self.assertEqual(prepared["status"],"prepared")
                refs=prepared["refs"]
                for key in ("operation_id","message_id","attempt_id"):
                    self.assertEqual(refs[key],request[key])
                intent=Path(refs["operation_ref"])
                original=intent.read_bytes()
                self.assertIn(request["payload"].encode(),original)
                self.assertIsNone(prepared["child"])
                create=prepared["native_call"]
                encoded=json.dumps(create["arguments"])
                for marker in (op,request["message_id"],request["attempt_id"],request["actor"]["thread_id"],request["owner"]["thread_id"],request["authority_ref"],request["holds"][0],request["payload"],str(endpoint),"TASK_ONLY_CONTEXT"):
                    self.assertNotIn(marker,encoded)
                raw,created=native(create)
                child={"thread_id":created["threadId"],"host_id":created["hostId"]}
                receipt={"call":create,"result":raw,"child":child}
                bound=command("bind",op,receipt)
                self.assertEqual(bound["status"],"bootstrap_unobserved")
                self.assertEqual(bound["refs"],refs)
                self.assertEqual(bound["child"],child)
                read=bound["native_call"]
                pending_raw,_=native(read)
                observation={"call":read,"result":pending_raw,"bootstrap":{"state":"pending","evidence_ref":"synthetic/bootstrap-pending-01"}}
                results=[command("submit",op,observation),command("bind",op,receipt),command("submit",op),command("reconcile",op),command("prepare",value=request)]
                for result in results:
                    self.assertEqual(result["status"],"bootstrap_pending")
                    self.assertEqual(result["refs"],refs)
                    self.assertEqual(result["child"],child)
                    self.assertEqual(result["ipc"],"not_attempted")
                    self.assertIsNone(result["native_call"])
                self.assertEqual(intent.read_bytes(),original)
                self.assertEqual([x["tool"] for x in json.loads(log.read_text())],["mcp__codex_app__create_thread","mcp__codex_app__read_thread"])
                with self.assertRaises(BlockingIOError):
                    connection,_=peer.accept()
                    connection.close()


    def test_client_setup_reference_stays_pending_without_becoming_a_recipient(self):
        with tempfile.TemporaryDirectory(prefix="db-creation-pending-") as directory:
            scratch=Path(directory).resolve()
            root=scratch/"operations"
            root.mkdir(mode=0o700)
            command=self.command(scratch,root)

            request={
                **self.negative_outcome_intent(scratch,root),
                "operation_id":"pending-creation-operation",
                "message_id":"pending-creation-message",
                "attempt_id":"pending-creation-attempt",
                "actor":{"thread_id":"caller","host_id":"local"},
                "owner":{"thread_id":"owner","host_id":"local"},
                "authority_ref":"existing-source-grant",
                "holds":["existing-scope-hold"],
                "payload":"Keep this task out of native creation.",
                "endpoint":str(scratch/"must-not-connect.sock"),
            }
            prepared=command("prepare",value=request)
            self.assertEqual(prepared["status"],"prepared")
            refs=prepared["refs"]
            intent=Path(refs["operation_ref"])
            original=intent.read_bytes()
            receipt={
                "call":prepared["native_call"],
                "result":{"content":[{"type":"text","text":"invented native setup result"}]},
                "client_thread_id":"fixture-setup-reference-not-a-thread-id",
            }
            bound=command("bind",request["operation_id"],receipt)
            self.assertEqual(bound["status"],"creation_pending")
            for key,original_ref in refs.items():
                self.assertEqual(bound["refs"][key],original_ref)
            self.assertEqual(bound["client_thread_id"],receipt["client_thread_id"])
            pending_ref=Path(bound["refs"]["creation_ref"])
            original_receipt=pending_ref.read_bytes()
            self.assertEqual(json.loads(original_receipt),receipt)
            for result in [bound,command("bind",request["operation_id"],receipt),
                           command("prepare",value=request),command("submit",request["operation_id"]),
                           command("reconcile",request["operation_id"]),command("show",request["operation_id"])]:
                self.assertEqual(result["status"],"creation_pending")
                self.assertIsNone(result["child"])
                self.assertEqual(result["refs"],bound["refs"])
                self.assertEqual(result["client_thread_id"],receipt["client_thread_id"])
                self.assertIsNone(result["native_call"])
                self.assertEqual(result["ipc"],"not_attempted")
            self.assertEqual(intent.read_bytes(),original)
            self.assertEqual(pending_ref.read_bytes(),original_receipt)


    def test_pending_creation_resolves_original_child_and_recovers_without_effects(self):
        with tempfile.TemporaryDirectory(prefix="db-creation-resolution-") as directory:
            scratch=Path(directory).resolve()
            root=scratch/"operations"
            root.mkdir(mode=0o700)
            endpoint=scratch/"peer.sock"
            command=self.command(scratch,root)
            request={
                **self.negative_outcome_intent(scratch,root),
                "operation_id":"creation-resolution-operation",
                "message_id":"creation-resolution-message",
                "attempt_id":"creation-resolution-attempt",
                "actor":{"thread_id":"caller","host_id":"local"},
                "owner":{"thread_id":"owner","host_id":"local"},
                "authority_ref":"synthetic://existing-creation-authority",
                "holds":["synthetic://existing-creation-hold"],
                "payload":"Retain the original task until its actual child is known.",
                "endpoint":str(endpoint),
            }
            op=request["operation_id"]
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as peer:
                peer.bind(str(endpoint))
                peer.listen(8)
                peer.setblocking(False)
                prepared=command("prepare",value=request)
                self.assertEqual(prepared["status"],"prepared")
                create=prepared["native_call"]
                pending={
                    "call":create,
                    "result":{"content":[{"type":"text","text":"Invented pending creation result."}]},
                    "client_thread_id":"invented-original-creation-handle",
                }
                bound=command("bind",op,pending)
                self.assertEqual(bound["status"],"creation_pending")
                self.assertIsNone(bound["child"])
                original_refs=dict(bound["refs"])
                intent=Path(original_refs["operation_ref"])
                creation=Path(original_refs["creation_ref"])
                original_intent=intent.read_bytes()
                original_creation=creation.read_bytes()
                child={"thread_id":"invented-resolved-local-child","host_id":"local"}
                resolution={
                    "call":create,
                    "result":{"content":[{"type":"text","text":"Invented caller-observed original creation completion."}]},
                    "client_thread_id":pending["client_thread_id"],
                    "child":child,
                    "evidence_ref":"synthetic://original-creation-completed",
                }

                def retained_bytes():
                    return {str(path.relative_to(root)):path.read_bytes()
                            for path in root.rglob("*") if path.is_file()}

                def refuses_without_writes(value):
                    before=retained_bytes()
                    refused=command("reconcile",op,value)
                    self.assertEqual(refused["status"],"refused",refused)
                    self.assertIsInstance(refused["reason"],str)
                    self.assertTrue(refused["reason"].strip())
                    self.assertIsNone(refused["native_call"])
                    self.assertEqual(refused["ipc"],"not_attempted")
                    self.assertEqual(retained_bytes(),before)
                    with self.assertRaises(BlockingIOError):
                        connection,_=peer.accept()
                        connection.close()

                for conflict in (
                    {"client_thread_id":"invented-unrelated-creation-handle"},
                    {"call":{**create,"arguments":{**create["arguments"],"prompt":"Different creation."}}},
                    {"child":{**child,"host_id":"remote"}},
                    {"evidence_ref":""},
                ):
                    with self.subTest(conflict=conflict):
                        refuses_without_writes({**resolution,**conflict})

                resolved=command("reconcile",op,resolution)
                self.assertEqual(resolved["status"],"bootstrap_unobserved",resolved)
                self.assertEqual(resolved["child"],child)
                self.assertEqual(resolved["ipc"],"not_attempted")
                for key,value in original_refs.items():
                    self.assertEqual(resolved["refs"][key],value)
                resolution_ref=Path(resolved["refs"]["creation_resolution_ref"])
                self.assertNotEqual(resolution_ref,creation)
                self.assertNotEqual(resolution_ref,intent)
                self.assertEqual(json.loads(resolution_ref.read_bytes()),resolution)
                self.assertEqual(resolved["native_call"],{
                    "tool":"mcp__codex_app__read_thread",
                    "arguments":{"threadId":child["thread_id"],"hostId":"local",
                                 "turnLimit":1,"includeOutputs":False,"maxOutputCharsPerItem":2048},
                })
                self.assertEqual(intent.read_bytes(),original_intent)
                self.assertEqual(creation.read_bytes(),original_creation)
                retained=retained_bytes()
                for repeated in (
                    command("reconcile",op,resolution),command("reconcile",op),
                    command("show",op),command("submit",op),
                    command("prepare",value=request),command("bind",op,pending),
                ):
                    self.assertEqual(repeated["status"],"bootstrap_unobserved",repeated)
                    self.assertEqual(repeated["child"],child)
                    self.assertEqual(repeated["refs"],resolved["refs"])
                    self.assertIsNone(repeated["native_call"])
                    self.assertEqual(repeated["ipc"],"not_attempted")
                self.assertEqual(retained_bytes(),retained)
                refuses_without_writes({
                    **resolution,"child":{**child,"thread_id":"invented-contradictory-child"},
                })
                self.assertEqual(intent.read_bytes(),original_intent)
                self.assertEqual(creation.read_bytes(),original_creation)
                with self.assertRaises(BlockingIOError):
                    connection,_=peer.accept()
                    connection.close()


    def test_oversized_task_frame_refuses_before_wire_write_without_replay(self):
        self.completed_bootstrap_submission(failure="outgoing-frame")

    def test_completed_bootstrap_sets_daybreak_and_accepts_one_original_task(self):
        self.completed_bootstrap_submission()

    def test_pending_bootstrap_resumes_same_child_without_duplicate_creation(self):
        self.completed_bootstrap_submission(pending_first=True)

    def test_false_saved_selection_stops_before_the_original_task(self):
        self.completed_bootstrap_submission(failure="false-readback")

    def test_lost_task_response_retains_unknown_without_replay(self):
        self.completed_bootstrap_submission(failure="lost-task-response")

    def test_capture_failure_preserves_first_diagnostic_when_evidence_cannot_save(self):
        self.completed_bootstrap_submission(failure="capture-unavailable")

    def test_new_explicit_task_continues_on_original_child_without_replay(self):
        self.completed_bootstrap_submission(continuation=True)

    def test_caller_task_observation_resumes_pending_without_resubmission(self):
        self.completed_bootstrap_submission(task_observation=True)

    def test_accepted_turn_survives_invalid_receive_tail_and_remains_observable(self):
        for tail in ("malformed-json","oversized-header"):
            with self.subTest(tail=tail):
                self.completed_bootstrap_submission(task_observation=True,accepted_tail=tail)

    def test_setup_and_readback_receive_prefixes_stop_before_the_next_rpc(self):
        for stage in ("setup-prefix","readback-prefix"):
            for tail in ("malformed-json","oversized-header"):
                with self.subTest(stage=stage,tail=tail):
                    self.completed_bootstrap_submission(failure=stage,accepted_tail=tail)

    def test_retained_inspection_preserves_claim_when_terminal_records_are_damaged(self):
        for task_observation in (False,True):
            for damaged in ((),("failure.json",),("submission.json",),
                            ("failure.json","submission.json")):
                with self.subTest(damaged=damaged,task_wait=task_observation):
                    self.completed_bootstrap_submission(
                        damaged_results=damaged,task_observation=task_observation)

    def test_standing_gate_retains_independent_hold_without_replay(self):
        self.completed_bootstrap_submission(failure="independent-hold", standing=True)

    def test_standing_gate_preserves_oversized_frame_refusal(self):
        self.completed_bootstrap_submission(failure="outgoing-frame", standing=True)

    def test_standing_gate_applies_to_same_child_continuation(self):
        self.completed_bootstrap_submission(continuation=True, standing=True)

    def test_standing_gate_observes_hold_after_daybreak_setup(self):
        self.completed_bootstrap_submission(failure="standing-hold", standing=True)

    def test_standing_task_write_error_retains_original_attempt(self):
        self.completed_bootstrap_submission(failure="task-write-error", standing=True)

    def test_standing_gate_preserves_the_original_daybreak_task(self):
        self.completed_bootstrap_submission(standing=True, pending_first=True)

    def test_standing_decision_survives_missing_task_response(self):
        self.completed_bootstrap_submission(failure="lost-task-response", standing=True)

    def test_write_evidence_overrules_a_false_capture_refusal(self):
        for failure in ("lost-task-response", "task-write-error"):
            with self.subTest(failure=failure):
                self.completed_bootstrap_submission(
                    failure=failure, standing=True, false_capture_refusal=True,
                )

    def test_standing_decision_capture_failure_withholds_task(self):
        self.completed_bootstrap_submission(failure="decision-capture", standing=True)

    def test_interrupted_standing_attempt_keeps_original_decision_discoverable(self):
        self.completed_bootstrap_submission(standing=True, damaged_results=("submission.json",))

    def test_wrong_shaped_standing_result_keeps_the_claim_and_decision(self):
        for terminal in (b"null", b'{"refs":null}'):
            with self.subTest(terminal=terminal):
                self.completed_bootstrap_submission(
                    standing=True, damaged_results=("submission.json",),
                    damaged_bytes=terminal, damage_reason="invalid-result",
                )

    def test_missing_standing_result_keeps_known_waits_without_promoting_outcome(self):
        self.completed_bootstrap_submission(
            standing=True, damaged_results=("submission.json",),
            damaged_bytes=None, task_observation=True,
        )

    def test_inconsistent_standing_result_cannot_override_original_evidence(self):
        for changes in (
            {"native_call": {"tool": "untrusted-capture", "arguments": {}}},
            {"turn_id": "another-turn"},
            {"status": "submission_unknown"},
            {"status": "submission_unknown", "turn_id": None},
            {"status": "submission_unknown", "turn_id": None, "task_write": "not_attempted"},
        ):
            with self.subTest(changes=changes):
                self.completed_bootstrap_submission(
                    standing=True, task_observation=not {"native_call", "task_write"} & changes.keys(),
                    damaged_results=("submission.json",), damaged_bytes=changes,
                    damage_reason="invalid-result",
                )

    def test_deeply_nested_terminal_capture_keeps_original_evidence(self):
        self.completed_bootstrap_submission(
            standing=True, task_observation=True,
            damaged_results=("submission.json",), damaged_bytes=b"[" * 50000 + b"]" * 50000,
        )

    def test_standing_gate_rejects_ineligible_reader_results(self):
        for result in ("failed", "unavailable", "replaced", "malformed", "nested",
                       "incomplete", "wrong-grant", "invalid-runtime", "legacy", "ineligible"):
            with self.subTest(result=result):
                self.completed_bootstrap_submission(failure="standing-" + result, standing=True)

    def test_mismatched_standing_attempt_supplies_no_retained_evidence(self):
        self.completed_bootstrap_submission(standing=True, mismatched_attempt=True)

    def test_unknown_terminal_summary_requires_bound_write_evidence(self):
        self.completed_bootstrap_submission(
            standing=True, failure="lost-task-response", mismatched_attempt=True,
        )

    def completed_bootstrap_submission(
        self, pending_first=False, failure=None, continuation=False,
        task_observation=False, accepted_tail=None, damaged_results=None, standing=False,
        damaged_bytes=b'{"partial":', damage_reason="invalid-json", false_capture_refusal=False,
        mismatched_attempt=False,
    ):
        with tempfile.TemporaryDirectory(prefix="db-task-") as directory:
            scratch=Path(directory).resolve()
            root=scratch/"operations"
            root.mkdir(mode=0o700)
            endpoint=scratch/"peer.sock"
            store=scratch/"mailbox.sqlite3"
            standing_args=()
            refused_by_standing = failure is not None and failure.startswith("standing-")
            if standing:
                decision=scratch/"standing-result"
                allow = {
                    "schema":"routine-standing-decision/v1", "status":"ALLOW",
                    "reason":"fixture", "grant_id":"fixture-grant", "runtime_id":"a"*32,
                }
                decision.write_text(json.dumps(allow))
                reader=scratch/"reader.py"
                reader.write_text(
                    "from pathlib import Path\n"
                    "result=Path(__file__).with_name('standing-result').read_text()\n"
                    "if result == 'exit nonzero': raise SystemExit(2)\n"
                    "print(result)\n"
                )

                def withhold_at_task():
                    if failure in {"standing-unavailable", "standing-replaced"}:
                        if failure == "standing-replaced":
                            other = scratch / "unqualified-reader.py"
                            other.write_bytes(reader.read_bytes())
                        reader.unlink()
                        if failure == "standing-replaced":
                            reader.symlink_to(other)
                        return
                    outputs = {
                        "standing-hold": json.dumps(dict(allow, status="HOLD")),
                        "standing-failed": "exit nonzero",
                        "standing-malformed": "{",
                        "standing-nested": "["*1500 + "]"*1500,
                        "standing-ineligible": json.dumps(dict(allow, status="INELIGIBLE")),
                        "standing-incomplete": json.dumps({"status":"ALLOW"}),
                        "standing-wrong-grant": json.dumps(dict(allow, grant_id="other-grant")),
                        "standing-invalid-runtime": json.dumps(dict(allow, runtime_id="unknown")),
                        "standing-legacy": json.dumps(dict(allow, schema="routine-standing-decision/v0")),
                    }
                    decision.write_text(outputs[failure])
                authority=scratch/"authority"
                state=scratch/"state"
                authority.mkdir(mode=0o700)
                state.mkdir(mode=0o700)
                binding=scratch/"standing-binding.json"
                binding.write_text(json.dumps({
                    "reader":str(reader),"authority_dir":str(authority),
                    "state_dir":str(state),"grant_id":"fixture-grant",
                }))
                binding.chmod(0o600)
                standing_args=("--standing-binding",str(binding),"--standing-eligible")
            launcher=SENDER
            if failure == "decision-capture":
                launcher = scratch / "occupied-decision-fixture.py"
                launcher.write_text(
                    "import sys\n"
                    f"sys.path.insert(0, {str(SENDER.parent)!r})\n"
                    "from codex_capture import CaptureWriter\n"
                    "from codex_daybreak_sender import main\n"
                    "original_write = CaptureWriter.write_json\n"
                    "def occupy_decision(self, path, value):\n"
                    "    original_write(self, path, value)\n"
                    "    return original_write(self, path, value)\n"
                    "CaptureWriter.write_json = occupy_decision\n"
                    "raise SystemExit(main())\n"
                )
            if failure=="task-write-error":
                launcher=scratch/"write-error-fixture.py"
                launcher.write_text(
                    "import json, sys\n"
                    f"sys.path.insert(0, {str(SENDER.parent)!r})\n"
                    "from codex_ipc_transport import UnixStream\n"
                    "from codex_daybreak_sender import main\n"
                    "original_write = UnixStream.write\n"
                    "def fail_task_write(self, data, timeout):\n"
                    "    if json.loads(data[4:]).get('method') == 'thread-follower-start-turn':\n"
                    "        raise OSError('synthetic-task-write-error')\n"
                    "    return original_write(self, data, timeout)\n"
                    "UnixStream.write = fail_task_write\n"
                    "raise SystemExit(main())\n"
                )
            command=self.command(scratch,root,standing_args,launcher=launcher)

            def mailbox(*arguments):
                result=subprocess.run(
                    [sys.executable,"-B",str(SENDER.with_name("native_codex_mailbox.py")),
                     "--store",str(store),*arguments],
                    capture_output=True,text=True,timeout=10,
                )
                self.assertEqual(result.returncode,0,result.stderr)
                return json.loads(result.stdout)

            self.assertEqual(mailbox("init"),{"initialized":True})
            request={
                "operation_id":"daybreak-task-operation",
                "message_id":"daybreak-task-message",
                "attempt_id":"daybreak-task-attempt",
                "correlation_id":"original-task-correlation",
                "sender":{"thread_id":"original-sender","host_id":"origin-host"},
                "actor":{"thread_id":"current-caller","host_id":"local"},
                "owner":{"thread_id":"task-owner","host_id":"owner-host"},
                "authority_ref":"synthetic://existing-task-authority",
                "holds":["synthetic://existing-task-hold"],
                "payload":"TASK_ONLY_CONTEXT: Keep caf\u00e9 and \u96ea.\nFull original task, second line: \U0001f44b",
                "endpoint":str(endpoint),
                "mailbox":str(store),
                "capture":{"run_root":str(root),"allowance_bytes":8388608,
                           "terminal_provision_bytes":524288,"later_forecast_bytes":0},
                "observation_seconds":0.5,
            }
            if standing:
                request["resource_admission"]="standing-v1"
            if failure=="outgoing-frame":
                request["payload"]="X"*65536
            op=request["operation_id"]
            child={"thread_id":"invented-daybreak-child","host_id":"local"}
            message={
                key:request[key] for key in
                ("message_id","correlation_id","sender","owner","authority_ref","holds","payload")
            }
            message["recipient"]=child
            expected_text="Peer message (no new operator authority).\n"+json.dumps({
                "schema":"provingkit-peer-message-v1",**message,"actor":request["actor"],
            },ensure_ascii=True,sort_keys=True,separators=(",",":"))
            prepared=command("prepare",value=request)
            self.assertEqual(prepared["status"],"prepared")
            self.assertIsNone(prepared["child"])
            refs=prepared["refs"]
            for key in ("operation_id","message_id","attempt_id"):
                self.assertEqual(refs[key],request[key])
            original_intent=Path(refs["operation_ref"]).read_bytes()
            self.assertEqual(json.loads(original_intent),request)
            create=prepared["native_call"]
            self.assertEqual(create["tool"],"mcp__codex_app__create_thread")
            self.assertEqual(set(create["arguments"]),{"model","target","prompt"})
            self.assertEqual(create["arguments"]["model"],"gpt-6-sol")
            self.assertEqual(create["arguments"]["target"],{"type":"projectless"})
            self.assertTrue(create["arguments"]["prompt"].strip())
            creation_text=json.dumps(create)
            for marker in (
                request["operation_id"],request["message_id"],request["attempt_id"],
                request["correlation_id"],request["sender"]["thread_id"],
                request["actor"]["thread_id"],request["owner"]["thread_id"],
                request["authority_ref"],request["holds"][0],
                request["payload"],"TASK_ONLY_CONTEXT",str(endpoint),str(store),
            ):
                self.assertNotIn(marker,creation_text)
            self.assertEqual(mailbox("pending"),[])
            created={
                "call":create,
                "result":{"content":[{"type":"text","text":"Invented caller creation result."}]},
                "child":child,
            }
            bound=command("bind",op,created)
            self.assertEqual(bound["status"],"bootstrap_unobserved")
            self.assertEqual(bound["child"],child)
            self.assertEqual(bound["refs"],refs)
            self.assertEqual(mailbox("pending"),[])
            read=bound["native_call"]
            self.assertEqual(read,{
                "tool":"mcp__codex_app__read_thread",
                "arguments":{"threadId":child["thread_id"],"hostId":"local",
                             "turnLimit":1,"includeOutputs":False,"maxOutputCharsPerItem":2048},
            })
            observation={
                "call":read,
                "result":{"content":[{"type":"text","text":"Invented terminal bootstrap result."}]},
                "bootstrap":{"state":"completed","evidence_ref":"synthetic://bootstrap-completed"},
            }
            wire,errors,prewrite=[],[],[]
            discovery_reply=[]
            prefix_tail={None:b"", "malformed-json":struct.pack("<I",1)+b"{",
                         "oversized-header":struct.pack("<I",65537)}[accepted_tail]
            capture_obstacles=[]
            closed=threading.Event()
            connected=threading.Event()

            def serve(listener):
                try:
                    try:
                        connection,_=listener.accept()
                    except TimeoutError:
                        return  # Refusal before connection leaves this fixture unconnected.
                    connected.set()
                    with connection:
                        connection.settimeout(3)

                        def receive(*,request=True):
                            def exact(count):
                                data=b""
                                while len(data)<count:
                                    part=connection.recv(count-len(data))
                                    if not part:
                                        raise AssertionError("unexpected fixture EOF")
                                    data+=part
                                return data
                            length=struct.unpack("<I",exact(4))[0]
                            self.assertGreater(length,0)
                            self.assertLessEqual(length,65536)
                            value=json.loads(exact(length))
                            if request:
                                wire.append(value)
                            return value

                        def reply(frame,result,owner=None,tail=b""):
                            value={
                                "type":"response","requestId":frame["requestId"],
                                "method":frame["method"],"resultType":"success","result":result,
                            }
                            if owner is not None:
                                value["handledByClientId"]=owner
                            data=json.dumps(value).encode()
                            connection.sendall(struct.pack("<I",len(data))+data+tail)

                        initialize=receive()
                        self.assertEqual(initialize,{
                            "type":"request","requestId":initialize["requestId"],
                            "version":0,"method":"initialize","params":{"clientType":"cli"},
                        })
                        reply(initialize,{"clientId":"invented-source-client"})
                        discovery=receive()
                        self.assertEqual(discovery,{
                            "type":"request","requestId":discovery["requestId"],
                            "sourceClientId":"invented-source-client","version":1,
                            "method":"thread-owner-discovery",
                            "params":{"hostId":"local","conversationId":child["thread_id"]},
                        })
                        if failure=="capture-unavailable":
                            # operation_ref exposes the owned operation directory.
                            # These four names are the maintained sender's setup and
                            # evidence capture destinations. Its create-only writer
                            # cannot use a directory as a file, even under UID 0.
                            # Occupy only those destinations after discovery, once the
                            # command has read and claimed the original operation.
                            # This exercises filesystem IO through the public command.
                            for name in ("setup.json","failure.json","transport.json","submission.json"):
                                path=Path(refs["operation_ref"]).parent/name
                                path.mkdir()
                                capture_obstacles.append(path)
                        reply(discovery,{},"invented-owner-client")
                        if failure=="capture-unavailable":
                            self.assertEqual(connection.recv(1),b"")
                            closed.set()
                            return

                        def targeted(frame,method,version,params):
                            self.assertEqual(frame,{
                                "type":"request","requestId":frame["requestId"],
                                "sourceClientId":"invented-source-client",
                                "targetClientId":"invented-owner-client",
                                "version":version,"method":method,"params":params,
                            })

                        def captured(frame,reference):
                            shown=command("show",op)
                            for key,value in refs.items():
                                self.assertEqual(shown["refs"][key],value)
                            self.assertEqual(shown["child"],child)
                            path=Path(shown["refs"][reference])
                            retained=path.read_bytes()
                            record=json.loads(retained)
                            self.assertEqual(record["envelope"],frame)
                            self.assertEqual(record["correlation"],frame["requestId"])
                            self.assertEqual(record["actor"],request["actor"])
                            self.assertEqual(record["declaredOrigin"],request["sender"])
                            self.assertEqual(record["authorityRefs"],[request["authority_ref"]])
                            self.assertEqual(record["holdRefs"],request["holds"])
                            for key,value in refs.items():
                                self.assertEqual(record["refs"][key],value)
                            prewrite.append((reference,str(path),retained))
                            return shown

                        setup=receive()
                        targeted(setup,"thread-follower-update-daybreak",1,{
                            "conversationId":child["thread_id"],"daybreakEnabled":True,
                        })
                        captured(setup,"setup_ref")
                        reply(setup,{"ok":True},"invented-owner-client",
                              tail=prefix_tail if failure=="setup-prefix" else b"")
                        if failure=="setup-prefix":
                            self.assertEqual(connection.recv(1),b"")
                            closed.set()
                            return
                        settings=receive()
                        targeted(settings,"thread-follower-read-model-settings",1,{
                            "conversationId":child["thread_id"],
                        })
                        if standing:
                            discovery_event = json.dumps({
                                "type":"client-discovery-request",
                                "requestId":"invented-follower-discovery",
                            }).encode()
                            connection.sendall(struct.pack("<I",len(discovery_event)) + discovery_event)
                            answer = receive(request=False)
                            self.assertEqual(answer,{
                                "type":"client-discovery-response",
                                "requestId":"invented-follower-discovery",
                                "response":{"canHandle":False},
                            })
                            discovery_reply[:] = [answer]
                        if refused_by_standing:
                            withhold_at_task()
                        reply(settings,{"settings":{"daybreakEnabled":failure!="false-readback"}},
                              "invented-owner-client",
                              tail=prefix_tail if failure=="readback-prefix" else b"")
                        if refused_by_standing or failure in {
                            "false-readback","outgoing-frame","readback-prefix","task-write-error",
                            "decision-capture",
                        }:
                            self.assertEqual(connection.recv(1),b"")
                            closed.set()
                            return
                        start=receive()
                        targeted(start,"thread-follower-start-turn",2,{
                            "conversationId":child["thread_id"],
                            "turnStart":{"request":{
                                "threadId":child["thread_id"],
                                "clientUserMessageId":request["attempt_id"],
                                "input":[{"type":"text","text":expected_text,"text_elements":[]}],
                                "model":"gpt-6-sol","effort":"medium",
                                "cyberAccessProgram":"daybreakBlue",
                                "collaborationMode":{"mode":"default","settings":{
                                    "model":"gpt-6-sol","reasoning_effort":"medium",
                                    "developer_instructions":None,
                                }},
                            },"context":{}},
                        })
                        shown=captured(start,"attempt_ref")
                        self.assertEqual(shown["refs"]["setup_ref"],prewrite[0][1])
                        if standing:
                            evidence = Path(shown["refs"]["operation_ref"]).parent / "standing-decision.json"
                            self.assertEqual(evidence.stat().st_mode & 0o777, 0o600)
                            self.assertEqual(json.loads(evidence.read_bytes()), {
                                "attempt_id": request["attempt_id"],
                                "correlation_id": request["correlation_id"],
                                "request_id": start["requestId"],
                                "decision": allow,
                            })
                        pending=mailbox("show",request["message_id"])
                        self.assertEqual(len(pending["attempts"]),1)
                        self.assertEqual(pending["attempts"][0]["attempt_id"],request["attempt_id"])
                        self.assertEqual(pending["attempts"][0]["actor"],request["actor"])
                        correlations=[frame["requestId"] for frame in wire]
                        self.assertTrue(all(isinstance(value,str) and value for value in correlations))
                        self.assertEqual(len(set(correlations)),len(correlations))
                        if failure=="lost-task-response":
                            # Withhold the response and half-close its direction. The
                            # receive below still observes the sender's actual close.
                            connection.shutdown(socket.SHUT_WR)
                        else:
                            reply(start,{"result":{"turn":{"id":"invented-accepted-turn"}}},
                                  "invented-owner-client",tail=prefix_tail)
                        self.assertEqual(connection.recv(1),b"")
                        closed.set()
                except BaseException as error:
                    errors.append(error)

            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as listener:
                listener.bind(str(endpoint))
                listener.listen(8)
                listener.settimeout(0.5)
                pending_ref=None
                original_pending=None
                if pending_first:
                    pending={
                        "call":read,
                        "result":{"content":[{"type":"text","text":"Invented pending bootstrap result."}]},
                        "bootstrap":{"state":"pending","evidence_ref":"synthetic://bootstrap-pending"},
                    }
                    pending_result=command("submit",op,pending)
                    self.assertEqual(pending_result["status"],"bootstrap_pending")
                    pending_ref=Path(refs["operation_ref"]).parent/"bootstrap.json"
                    original_pending=pending_ref.read_bytes()
                    self.assertEqual(json.loads(original_pending),pending)
                    pending_files={path:path.read_bytes() for path in root.rglob("*")
                                   if path.is_file()}
                    for result in (
                        pending_result,command("bind",op,created),command("submit",op),
                        command("reconcile",op),command("show",op),
                        command("prepare",value=request),
                    ):
                        self.assertEqual(result["status"],"bootstrap_pending")
                        self.assertEqual(result["refs"],refs)
                        self.assertEqual(result["child"],child)
                        self.assertEqual(result["ipc"],"not_attempted")
                        self.assertIsNone(result["native_call"])
                    self.assertEqual(mailbox("pending"),[])
                    self.assertEqual({path:path.read_bytes() for path in root.rglob("*")
                                      if path.is_file()},pending_files)
                    listener.setblocking(False)
                    with self.assertRaises(BlockingIOError):
                        connection,_=listener.accept()
                        connection.close()
                    listener.settimeout(0.5)
                if failure=="independent-hold":
                    listener.setblocking(False)
                    refused=command("submit",op,observation,
                                    extra_standing_args=("--standing-independent-hold",))
                    self.assertEqual(refused["task_write"],"not_attempted",refused)
                    self.assertEqual(refused["ipc"],"not_attempted")
                    self.assertEqual(refused["reason"],"standing-independent-ineligible")
                    self.assertEqual(refused["owned_connection"],{"started":False,"closed":False})
                    self.assertEqual(mailbox("pending"),[])
                    for repeated in (command("submit",op,observation),command("show",op)):
                        for key in ("task_write","ipc","reason","refs","owned_connection"):
                            self.assertEqual(repeated[key],refused[key],repeated)
                    with self.assertRaises(BlockingIOError):
                        connection,_=listener.accept()
                        connection.close()
                    return
                server=threading.Thread(target=serve,args=(listener,),daemon=True)
                server.start()
                try:
                    accepted=command("reconcile" if pending_first else "submit",op,observation)
                finally:
                    server.join(timeout=5)
                self.assertFalse(server.is_alive(),"owned fixture server did not terminate")
                if failure is not None:
                    self.assertEqual(errors,[],accepted)
                    self.assertTrue(connected.is_set(),accepted)
                    self.assertTrue(closed.is_set(),accepted)
                    methods=["initialize","thread-owner-discovery"]
                    references=[]
                    if failure!="capture-unavailable":
                        methods.append("thread-follower-update-daybreak")
                        if failure!="setup-prefix":
                            methods.append("thread-follower-read-model-settings")
                        references.append("setup_ref")
                    if failure=="lost-task-response":
                        methods.append("thread-follower-start-turn")
                        references.append("attempt_ref")
                    if refused_by_standing or failure in {
                        "outgoing-frame","readback-prefix","task-write-error",
                        "decision-capture",
                    }:
                        references.append("attempt_ref")
                        path=Path(accepted["refs"]["attempt_ref"])
                        retained=path.read_bytes()
                        pending_task=json.loads(retained)["envelope"]
                        self.assertEqual(pending_task["method"],"thread-follower-start-turn")
                        self.assertEqual(pending_task["params"]["turnStart"]["request"]["input"],
                                         [{"type":"text","text":expected_text,"text_elements":[]}])
                        if failure=="outgoing-frame":
                            self.assertGreater(len(json.dumps(pending_task,separators=(",",":")).encode()),65536)
                        prewrite.append(("attempt_ref",str(path),retained))
                        self.assertIs(accepted["saved_selection"],True)
                    self.assertEqual([frame["method"] for frame in wire],methods,accepted)
                    self.assertEqual(accepted["status"],"submission_unknown",accepted)
                    self.assertIsNone(accepted.get("turn_id"),accepted)
                    self.assertIs(accepted["saved_selection"],
                                  True if refused_by_standing or failure in {
                                      "lost-task-response","outgoing-frame","readback-prefix","task-write-error",
                                      "decision-capture",
                                  } else None)
                    self.assertEqual(accepted["receipt"],"unknown")
                    self.assertEqual(accepted["task_completion"],"unknown")
                    self.assertEqual(accepted["effective_program"],"unknown")
                    self.assertEqual(accepted["owned_connection"],{"started":True,"closed":True})
                    self.assertIsNone(accepted["native_call"])
                    self.assertEqual(accepted["ipc"],"attempted")
                    for key,value in refs.items():
                        self.assertEqual(accepted["refs"][key],value)
                    self.assertEqual(accepted["child"],child)
                    self.assertEqual([item[0] for item in prewrite],references)
                    expected_refs = set(refs) | set(references)
                    if standing and failure in {"lost-task-response", "task-write-error"}:
                        expected_refs.add("standing_decision_ref")
                        evidence = Path(accepted["refs"]["standing_decision_ref"])
                        self.assertEqual(evidence.name, "standing-decision.json")
                        self.assertEqual(json.loads(evidence.read_bytes())["decision"], allow)
                    self.assertEqual(set(accepted["refs"]), expected_refs)
                    for reference,path,retained in prewrite:
                        self.assertEqual(accepted["refs"][reference],path)
                        self.assertEqual(Path(path).read_bytes(),retained)
                    self.assertEqual(Path(refs["operation_ref"]).read_bytes(),original_intent)
                    first=accepted["failures"][0]
                    self.assertEqual(accepted["reason"],first["reason"])
                    if failure=="capture-unavailable":
                        self.assertEqual([item["stage"] for item in accepted["failures"]],[
                            "daybreak-setup-capture","failure-capture",
                            "transport-capture","submission-capture",
                        ])
                        for item,path in zip(accepted["failures"],capture_obstacles):
                            self.assertIn(str(path),item["reason"])
                        for secondary in accepted["failures"][1:]:
                            self.assertNotEqual(secondary["reason"],first["reason"])
                        # Remove only the fixture's empty obstacles. Original records
                        # remain at their public refs, and offline reads can project
                        # the surviving claim without pretending diagnostics saved.
                        for path in capture_obstacles:
                            path.rmdir()
                    elif failure in {"setup-prefix","readback-prefix"}:
                        reason={"malformed-json":"frame-decode-error",
                                "oversized-header":"frame-byte-limit"}[accepted_tail]
                        stage="daybreak-setup" if failure=="setup-prefix" else "daybreak-readback"
                        self.assertEqual(first,{"stage":stage,"reason":reason})
                        operation_dir=Path(accepted["refs"]["operation_ref"]).parent
                        name="setup" if failure=="setup-prefix" else "readback"
                        response=json.loads((operation_dir/(name+"-response.json")).read_bytes())
                        self.assertEqual(response["envelope"],wire[-1])
                        self.assertEqual(len(response["records"]),1)
                        expected_response={
                            "type":"response","requestId":wire[-1]["requestId"],
                            "method":wire[-1]["method"],"resultType":"success",
                            "handledByClientId":"invented-owner-client",
                            "result":({"ok":True} if failure=="setup-prefix"
                                      else {"settings":{"daybreakEnabled":True}}),
                        }
                        self.assertEqual(response["records"][0][1],expected_response)
                        transport=json.loads((operation_dir/"transport.json").read_bytes())
                        self.assertEqual(transport["received"][-1][1],expected_response)
                        self.assertEqual(transport["incomplete"],reason)
                        self.assertIn(reason,transport["receiveStatus"])
                        self.assertEqual(transport["outbound"],wire)
                        self.assertEqual(transport["owned_connection"],{"started":True,"closed":True})
                        if failure=="readback-prefix":
                            selection=json.loads((operation_dir/"selection.json").read_bytes())
                            self.assertEqual(selection,{"saved_selection":True,"response":expected_response})
                    else:
                        self.assertEqual(len(accepted["failures"]),1)
                        expected_failure={
                            "lost-task-response":("task-submit","start-response-unavailable"),
                            "task-write-error":("task-submit","synthetic-task-write-error"),
                            "outgoing-frame":("task-submit","outgoing-frame-limit"),
                            "false-readback":("daybreak-readback","saved-selection-unconfirmed"),
                            "decision-capture":("task-submit","standing-decision-capture-failed"),
                        }
                        if refused_by_standing:
                            failure_point = ("task-submit","standing-decision-withheld")
                        else:
                            failure_point = expected_failure[failure]
                        self.assertEqual(first,dict(zip(("stage","reason"),failure_point)))
                    if standing:
                        write_raised=failure=="task-write-error"
                        expected_task_write = (
                            "attempted" if write_raised or failure == "lost-task-response"
                            else "not_attempted"
                        )
                        self.assertEqual(accepted["task_write"],expected_task_write)
                        operation_dir=Path(accepted["refs"]["operation_ref"]).parent
                        if failure == "decision-capture":
                            self.assertEqual(
                                json.loads((operation_dir / "standing-decision.json").read_bytes()),
                                {"attempt_id": request["attempt_id"],
                                 "correlation_id": request["correlation_id"],
                                 "request_id": pending_task["requestId"], "decision": allow},
                            )
                        self.assertEqual(
                            (operation_dir / "start-response.json").exists(),
                            failure == "lost-task-response",
                        )
                        transport=json.loads((operation_dir/"transport.json").read_bytes())
                        expected_outbound=[*wire[:4],*discovery_reply,*wire[4:]]
                        expected_boundary={}
                        if expected_task_write == "attempted":
                            if write_raised:
                                expected_outbound.append(pending_task)
                            expected_boundary={
                                "pendingExistedBeforeWrite":True,
                                "pendingSha256":hashlib.sha256(Path(accepted["refs"]["attempt_ref"]).read_bytes()).hexdigest(),
                            }
                        self.assertEqual(transport["outbound"],expected_outbound)
                        self.assertEqual(transport["writeBoundary"],expected_boundary)
                        decision.write_text(json.dumps(allow))
                        if reader.is_symlink():
                            restored_reader = reader.resolve(strict=True).read_bytes()
                            reader.unlink()
                            reader.write_bytes(restored_reader)
                        repeated=command("submit",op,observation)
                        self.assertEqual(repeated["task_write"],expected_task_write)
                        self.assertEqual(repeated["reason"],accepted["reason"])
                        if failure == "decision-capture":
                            self.assertNotIn("standing_decision_ref", repeated["refs"])
                    recorded=mailbox("show",request["message_id"])
                    self.assertEqual({key:value for key,value in recorded.items()
                                      if key not in {"state","attempts"}},message)
                    self.assertEqual(recorded["state"],"unknown")
                    self.assertEqual(len(recorded["attempts"]),1)
                    attempt=recorded["attempts"][0]
                    self.assertEqual(attempt["attempt_id"],request["attempt_id"])
                    self.assertEqual(attempt["actor"],request["actor"])
                    self.assertEqual(attempt["submission"],"unknown")
                    self.assertIsNone(attempt["reconciliation"])
                    self.assertEqual(attempt["observations"],[])
                    for stage in ("received","handled","completed"):
                        self.assertIs(attempt[stage],False)
                    self.assertEqual(mailbox("pending"),[recorded])
                    retained={path:path.read_bytes() for path in root.rglob("*")
                              if path.is_file()}
                    for phase in ("reconcile","show","submit","reconcile","show","submit"):
                        repeated=command(phase,op)
                        self.assertEqual(repeated["status"],"submission_unknown")
                        self.assertEqual(repeated["refs"],accepted["refs"])
                        self.assertEqual(repeated["child"],child)
                        self.assertIsNone(repeated.get("turn_id"))
                        self.assertEqual(repeated["receipt"],"unknown")
                        self.assertEqual(repeated["task_completion"],"unknown")
                        self.assertEqual(repeated["effective_program"],"unknown")
                        self.assertIsNone(repeated["native_call"])
                        if failure=="capture-unavailable":
                            self.assertNotIn("reason",repeated)
                            self.assertNotIn("failures",repeated)
                            self.assertIsNone(repeated["saved_selection"])
                            self.assertEqual(repeated["owned_connection"],
                                             {"started":None,"closed":None})
                        else:
                            self.assertEqual(repeated["reason"],accepted["reason"])
                            self.assertEqual(repeated["failures"],accepted["failures"])
                            self.assertIs(repeated["saved_selection"],accepted["saved_selection"])
                            self.assertEqual(repeated["owned_connection"],
                                             {"started":True,"closed":True})
                    self.assertEqual(mailbox("show",request["message_id"]),recorded)
                    self.assertEqual(mailbox("pending"),[recorded])
                    self.assertEqual({path:path.read_bytes() for path in root.rglob("*")
                                      if path.is_file()},retained)
                    if mismatched_attempt:
                        attempt_file = operation_dir / "attempt.json"
                        response_file = operation_dir / "start-response.json"
                        transport_file = operation_dir / "transport.json"
                        original_attempt = attempt_file.read_bytes()
                        original_response = response_file.read_bytes()
                        original_transport = transport_file.read_bytes()
                        wrong_attempt = json.loads(original_attempt)
                        wrong_envelope = wrong_attempt["envelope"]
                        wrong_envelope["params"]["turnStart"]["request"]["threadId"] = "wrong-child"
                        response = json.loads(original_response)
                        response["envelope"] = wrong_envelope
                        attempt_file.write_text(json.dumps(wrong_attempt))
                        response_file.write_text(json.dumps(response))
                        for phase in ("show", "submit"):
                            shown = command(phase, op)
                            self.assertEqual(shown["status"], "submission_unknown")
                            self.assertEqual(shown["task_write"], "unknown")
                            self.assertEqual(shown["ipc"], "attempted")
                            self.assertEqual(shown["owned_connection"], accepted["owned_connection"])
                            self.assertNotIn("standing_decision_ref", shown["refs"])
                            self.assertIsNone(shown["native_call"])
                        attempt_file.write_bytes(original_attempt)
                        response_file.unlink()
                        transport_file.unlink()
                        shown = command("show", op)
                        self.assertEqual(shown["task_write"], "unknown")
                        self.assertEqual(shown["refs"], accepted["refs"])
                        response_file.write_bytes(original_response)
                        transport_file.write_bytes(original_transport)
                        response_file.chmod(0o600)
                        transport_file.chmod(0o600)
                        shown = command("show", op)
                        self.assertEqual(shown["task_write"], "attempted")
                        self.assertEqual(shown["status"], "submission_unknown")
                        self.assertIsNone(shown["native_call"])
                    if false_capture_refusal:
                        submission = operation_dir / "submission.json"
                        terminal = json.loads(submission.read_bytes())
                        terminal.update(
                            task_write="not_attempted",
                            reason="standing-decision-capture-failed",
                            failures=[{"stage": "task-submit", "reason": "standing-decision-capture-failed"}],
                        )
                        submission.write_text(json.dumps(terminal))
                        (operation_dir / "failure.json").unlink()
                        if failure == "lost-task-response":
                            (operation_dir / "transport.json").unlink()
                        evidence = Path(accepted["refs"]["standing_decision_ref"])
                        original_evidence = evidence.read_bytes()
                        for phase in ("show", "submit"):
                            recovered = command(phase, op)
                            self.assertEqual(recovered["status"], "submission_unknown")
                            self.assertEqual(recovered["task_write"], "attempted")
                            self.assertEqual(recovered["ipc"], "attempted")
                            self.assertEqual(recovered["refs"]["standing_decision_ref"], str(evidence))
                            self.assertEqual(recovered["evidence_read_failures"], [
                                {"path": str(submission), "reason": "invalid-result"},
                            ])
                            self.assertIsNone(recovered["native_call"])
                            self.assertEqual(evidence.read_bytes(), original_evidence)
                            self.assertEqual(mailbox("show", request["message_id"]), recorded)
                    if failure in {"standing-hold", "decision-capture"}:
                        if failure == "decision-capture":
                            unrelated = dict(pending_task, requestId="another-request")
                            (operation_dir / "start-response.json").write_text(json.dumps({
                                "envelope": unrelated, "records": [],
                            }))
                            (operation_dir / "start-response.json").chmod(0o600)
                        (operation_dir / "submission.json").write_text("{")
                        for fallback in (command("show",op),command("submit",op,observation)):
                            self.assertEqual(fallback["ipc"],"attempted",fallback)
                            self.assertEqual(fallback["task_write"],"not_attempted")
                            self.assertIs(fallback["saved_selection"],True)
                            self.assertEqual(fallback["owned_connection"],{"started":True,"closed":None})
                            self.assertNotIn("standing_decision_ref", fallback["refs"])
                    listener.setblocking(False)
                    with self.assertRaises(BlockingIOError):
                        connection,_=listener.accept()
                        connection.close()
                    return
                if accepted_tail is not None:
                    self.assertEqual(accepted.get("turn_id"),"invented-accepted-turn",accepted)
                self.assertEqual(accepted["status"],"turn_accepted",{"result":accepted,"fixture_errors":[repr(e) for e in errors]})
                self.assertEqual(errors,[])
                self.assertTrue(connected.is_set())
                self.assertTrue(closed.is_set())
                self.assertEqual([frame["method"] for frame in wire],[
                    "initialize","thread-owner-discovery","thread-follower-update-daybreak",
                    "thread-follower-read-model-settings","thread-follower-start-turn",
                ])
                for key,value in refs.items():
                    self.assertEqual(accepted["refs"][key],value)
                self.assertEqual(accepted["child"],child)
                self.assertEqual(accepted["turn_id"],"invented-accepted-turn")
                if mismatched_attempt:
                    operation_dir = Path(accepted["refs"]["operation_ref"]).parent
                    attempt_path = operation_dir / "attempt.json"
                    response_path = operation_dir / "start-response.json"
                    attempt_raw = attempt_path.read_bytes()
                    response_raw = response_path.read_bytes()
                    for mismatch in ("outer target", "inner target", "correlation", "operation reference"):
                        with self.subTest(mismatch=mismatch):
                            attempt = json.loads(attempt_raw)
                            envelope = attempt["envelope"]
                            if mismatch == "outer target":
                                envelope["params"]["conversationId"] = "another-child"
                            elif mismatch == "inner target":
                                envelope["params"]["turnStart"]["request"]["threadId"] = "another-child"
                            elif mismatch == "correlation":
                                attempt["correlation"] = "another-request"
                            else:
                                attempt["refs"]["operation_ref"] = "/another/intent.json"
                            response = json.loads(response_raw)
                            response["envelope"] = envelope
                            attempt_path.write_text(json.dumps(attempt))
                            response_path.write_text(json.dumps(response))
                            for phase in ("show", "submit"):
                                retained = command(phase, op)
                                self.assertEqual(retained["status"], "submission_unknown")
                                self.assertEqual(retained["task_write"], "unknown")
                                self.assertNotIn("standing_decision_ref", retained["refs"])
                                self.assertIsNone(retained["native_call"])
                    attempt_path.write_bytes(attempt_raw)
                    response_path.write_bytes(response_raw)
                if standing:
                    self.assertEqual(accepted["task_write"],"attempted")
                    operation_dir=Path(accepted["refs"]["operation_ref"]).parent
                    self.assertEqual(
                        accepted["refs"]["standing_decision_ref"],
                        str(operation_dir / "standing-decision.json"),
                    )
                    transport=json.loads((operation_dir/"transport.json").read_bytes())
                    self.assertEqual(transport["outbound"],[*wire[:4],*discovery_reply,*wire[4:]])
                    pending_capture=Path(accepted["refs"]["attempt_ref"]).read_bytes()
                    self.assertEqual(transport["writeBoundary"],{
                        "pendingExistedBeforeWrite":True,
                        "pendingSha256":hashlib.sha256(pending_capture).hexdigest(),
                    })
                if accepted_tail is not None:
                    reason={"malformed-json":"frame-decode-error",
                            "oversized-header":"frame-byte-limit"}[accepted_tail]
                    self.assertEqual(accepted["reason"],reason)
                    self.assertIn({"stage":"task-submit","reason":reason},accepted["failures"])
                    operation_dir=Path(accepted["refs"]["operation_ref"]).parent
                    response=json.loads((operation_dir/"start-response.json").read_bytes())
                    self.assertEqual(response["envelope"],wire[-1])
                    self.assertEqual(len(response["records"]),1)
                    accepted_response={
                        "type":"response","requestId":wire[-1]["requestId"],
                        "method":"thread-follower-start-turn","resultType":"success",
                        "handledByClientId":"invented-owner-client",
                        "result":{"result":{"turn":{"id":"invented-accepted-turn"}}},
                    }
                    self.assertEqual(response["records"][0][1],accepted_response)
                    transport=json.loads((operation_dir/"transport.json").read_bytes())
                    self.assertEqual(transport["received"][-1][1],accepted_response)
                    self.assertEqual(transport["incomplete"],reason)
                    self.assertIn(reason,transport["receiveStatus"])
                    self.assertEqual(transport["outbound"],wire)
                    self.assertEqual(json.loads((operation_dir/"submission.json").read_bytes()),
                                     {key:value for key,value in accepted.items() if key!="phase"})
                self.assertIs(accepted["saved_selection"],True)
                self.assertEqual(accepted["receipt"],"unknown")
                self.assertEqual(accepted["task_completion"],"unknown")
                self.assertEqual(accepted["effective_program"],"unknown")
                self.assertEqual(accepted["owned_connection"],{"started":True,"closed":True})
                self.assertIsNone(accepted["native_call"])
                self.assertEqual([item[0] for item in prewrite],["setup_ref","attempt_ref"])
                for reference,path,retained in prewrite:
                    self.assertEqual(accepted["refs"][reference],path)
                    self.assertEqual(Path(path).read_bytes(),retained)
                self.assertEqual(Path(refs["operation_ref"]).read_bytes(),original_intent)
                if pending_first:
                    self.assertEqual(pending_ref.read_bytes(),original_pending)
                recorded=mailbox("show",request["message_id"])
                self.assertEqual({key:value for key,value in recorded.items()
                                  if key not in {"state","attempts"}},message)
                self.assertEqual(recorded["state"],"submitted")
                self.assertEqual(len(recorded["attempts"]),1)
                attempt=recorded["attempts"][0]
                self.assertEqual(attempt["attempt_id"],request["attempt_id"])
                self.assertEqual(attempt["actor"],request["actor"])
                self.assertEqual(attempt["submission"],"submitted")
                self.assertIsNone(attempt["reconciliation"])
                for stage in ("received","handled","completed"):
                    self.assertIs(attempt[stage],False)
                self.assertEqual(mailbox("pending"),[recorded])
                retained={path:path.read_bytes() for path in root.rglob("*") if path.is_file()}
                for repeated in (
                    command("submit",op),command("reconcile",op),command("show",op),
                    command("prepare",value=request),
                ):
                    self.assertEqual(repeated["status"],"turn_accepted")
                    self.assertEqual(repeated["refs"],accepted["refs"])
                    self.assertEqual(repeated["child"],child)
                    self.assertEqual(repeated["turn_id"],"invented-accepted-turn")
                    for key in ("reason","failures"):
                        self.assertEqual(repeated.get(key),accepted.get(key))
                    self.assertIsNone(repeated["native_call"])
                self.assertEqual(mailbox("show",request["message_id"]),recorded)
                self.assertEqual(mailbox("pending"),[recorded])
                self.assertEqual({path:path.read_bytes() for path in root.rglob("*")
                                  if path.is_file()},retained)
                listener.setblocking(False)
                with self.assertRaises(BlockingIOError):
                    connection,_=listener.accept()
                    connection.close()


                if task_observation:
                    wait_request={"task_wait":{"observation_seconds":1,"after_ref":None}}
                    waiting=command("reconcile",op,wait_request)
                    self.assertEqual(waiting["status"],"turn_accepted",waiting)
                    self.assertEqual(waiting["task_observation"],"pending")
                    self.assertEqual(waiting["task_completion"],"unknown")
                    task_call={
                        "tool":"mcp__codex_app__read_thread",
                        "arguments":{"threadId":"invented-daybreak-child","hostId":"local",
                                     "turnLimit":1,"includeOutputs":False,
                                     "maxOutputCharsPerItem":2048},
                    }
                    self.assertEqual(waiting["native_call"],task_call)
                    wait_ref=waiting["refs"]["task_wait_ref"]
                    self.assertTrue(Path(wait_ref).is_file())
                    self.assertEqual(json.loads(Path(wait_ref).read_bytes())["task_wait"],
                                     wait_request["task_wait"])

                if damaged_results is not None:
                    # Seeded-record reader proof after an actual disposable-peer
                    # submission; this does not simulate a write or fsync failure.
                    latest_wait_ref=None
                    if task_observation:
                        pending_observation={
                            "task_wait_ref":wait_ref,"call":task_call,
                            "result":{"content":[{"type":"text",
                                "text":"Invented caller observation: original task still running."}]},
                            "task":{"attempt_id":request["attempt_id"],
                                    "turn_id":"invented-accepted-turn","state":"pending",
                                    "evidence_ref":"synthetic://caller-task-pending"},
                        }
                        pending=command("reconcile",op,pending_observation)
                        self.assertEqual(pending["status"],"turn_accepted",pending)
                        self.assertEqual(pending["task_observation"],"pending")
                        self.assertEqual(pending["task_completion"],"unknown")
                        self.assertIsNone(pending["native_call"])
                        pending_ref=pending["refs"]["task_observation_ref"]
                        self.assertEqual(pending["refs"],{
                            **accepted["refs"],"task_wait_ref":wait_ref,
                            "task_observation_ref":pending_ref,
                        })
                        self.assertEqual(json.loads(Path(pending_ref).read_bytes()),pending_observation)
                        next_wait_request={"task_wait":{"observation_seconds":1,"after_ref":pending_ref}}
                        next_wait=command("reconcile",op,next_wait_request)
                        self.assertEqual(next_wait["status"],"turn_accepted",next_wait)
                        self.assertEqual(next_wait["task_observation"],"pending")
                        self.assertEqual(next_wait["task_completion"],"unknown")
                        self.assertEqual(next_wait["native_call"],task_call)
                        latest_wait_ref=next_wait["refs"]["task_wait_ref"]
                        self.assertNotEqual(latest_wait_ref,wait_ref)
                        self.assertEqual(next_wait["refs"],{
                            **pending["refs"],"task_wait_ref":latest_wait_ref,
                        })
                        self.assertEqual(json.loads(Path(latest_wait_ref).read_bytes())["task_wait"],
                                         next_wait_request["task_wait"])
                    operation_dir=Path(accepted["refs"]["operation_ref"]).parent
                    claim=operation_dir/"claim.json"
                    original_claim=claim.read_bytes()
                    if isinstance(damaged_bytes, dict):
                        terminal = json.loads((operation_dir / "submission.json").read_bytes())
                        damaged_bytes = json.dumps({**terminal, **damaged_bytes}).encode()
                    for name in damaged_results:
                        damaged = operation_dir / name
                        if damaged_bytes is None:
                            damaged.unlink()
                        else:
                            damaged.write_bytes(damaged_bytes)
                    seeded={path:path.read_bytes() for path in root.rglob("*") if path.is_file()}
                    original_wire=list(wire)
                    expected_diagnostics=[
                        {"path":str(operation_dir/name),"reason":damage_reason}
                        for name in damaged_results if damaged_bytes is not None
                    ]
                    final_valid="submission.json" not in damaged_results
                    expected_refs=dict(accepted["refs"])
                    if task_observation:
                        expected_refs["task_wait_ref"]=latest_wait_ref
                        expected_refs["task_observation_ref"]=pending_ref
                    for phase,value in (
                        ("show",None),("reconcile",None),("submit",None),
                        ("reconcile",wait_request if task_observation else None),
                        *([("reconcile",pending_observation),("reconcile",next_wait_request)]
                          if task_observation else []),
                        ("prepare",request),("bind",created),("submit",observation),
                        ("show",None),("reconcile",None),
                    ):
                        result=command(phase,None if phase=="prepare" else op,value)
                        self.assertEqual(result["status"],
                                         "turn_accepted" if final_valid else "submission_unknown",result)
                        self.assertEqual(result["refs"],expected_refs)
                        if task_observation:
                            self.assertEqual(result["task_observation"],"pending")
                        self.assertEqual(result["child"],child)
                        self.assertEqual(result.get("turn_id"),
                                         "invented-accepted-turn" if final_valid else None)
                        self.assertIs(result["saved_selection"],True if final_valid else None)
                        self.assertEqual(result["ipc"],"attempted" if final_valid or standing else "unknown")
                        self.assertEqual(result["owned_connection"],
                                         {"started":True,"closed":True} if final_valid
                                         else {"started":None,"closed":None})
                        for key in ("receipt","task_completion","effective_program"):
                            self.assertEqual(result[key],"unknown")
                        self.assertIsNone(result["native_call"])
                        self.assertEqual(result.get("evidence_read_failures",[]),expected_diagnostics)
                        self.assertEqual(claim.read_bytes(),original_claim)
                        self.assertEqual({path:path.read_bytes() for path in root.rglob("*")
                                          if path.is_file()},seeded)
                        for name in damaged_results:
                            if damaged_bytes is None:
                                self.assertFalse((operation_dir / name).exists())
                            else:
                                self.assertEqual((operation_dir / name).read_bytes(), damaged_bytes)
                        self.assertEqual(mailbox("show",request["message_id"]),recorded)
                        self.assertEqual(mailbox("pending"),[recorded])
                        self.assertEqual(wire,original_wire)
                        with self.assertRaises(BlockingIOError):
                            connection,_=listener.accept()
                            connection.close()
                    if standing and not final_valid:
                        evidence = Path(accepted["refs"]["standing_decision_ref"])
                        original_evidence = evidence.read_bytes()
                        mismatched = json.loads(original_evidence)
                        mismatched["request_id"] = "another-request"
                        for invalid in (b'{"incomplete":', json.dumps(mismatched).encode()):
                            evidence.write_bytes(invalid)
                            shown = command("show", op)
                            self.assertNotIn("standing_decision_ref", shown["refs"])
                            self.assertEqual(shown["task_write"], "attempted")
                            self.assertEqual(shown["status"], "submission_unknown")
                            self.assertEqual(evidence.read_bytes(), invalid)
                        evidence.write_bytes(original_evidence)
                        self.assertEqual(command("show", op)["refs"], expected_refs)
                    if task_observation and not final_valid:
                        fresh_observation={
                            **pending_observation,"task_wait_ref":latest_wait_ref,
                            "task":{**pending_observation["task"],
                                    "evidence_ref":"synthetic://caller-task-fresh-pending"},
                        }
                        refused=command("reconcile",op,fresh_observation)
                        self.assertEqual(refused["status"],"refused",refused)
                        self.assertEqual(refused["reason"],"task-turn-not-accepted")
                        self.assertIsNone(refused["native_call"])
                        self.assertEqual(refused["ipc"],"not_attempted")
                        self.assertEqual({path:path.read_bytes() for path in root.rglob("*")
                                          if path.is_file()},seeded)
                        self.assertEqual(mailbox("show",request["message_id"]),recorded)
                        self.assertEqual(mailbox("pending"),[recorded])
                        self.assertEqual(wire,original_wire)
                        with self.assertRaises(BlockingIOError):
                            connection,_=listener.accept()
                            connection.close()
                    return

                if task_observation:
                    # The caller acquires each invented native result after the
                    # command emits its existing bounded read call.
                    original_files=dict(retained)
                    original_wire=list(wire)

                    def retained_bytes():
                        return {path:path.read_bytes() for path in root.rglob("*")
                                if path.is_file()}

                    def preserves_submission(result):
                        for key in ("status","child","turn_id","saved_selection","receipt",
                                    "effective_program","owned_connection","ipc"):
                            self.assertEqual(result[key],accepted[key],result)
                        for key in ("reason","failures"):
                            self.assertEqual(result.get(key),accepted.get(key))
                        for key,value in accepted["refs"].items():
                            self.assertEqual(result["refs"][key],value)
                        for path,data in original_files.items():
                            self.assertEqual(path.read_bytes(),data)
                        self.assertEqual(mailbox("show",request["message_id"]),recorded)
                        self.assertEqual(mailbox("pending"),[recorded])
                        self.assertEqual(wire,original_wire)
                        with self.assertRaises(BlockingIOError):
                            connection,_=listener.accept()
                            connection.close()

                    preserves_submission(waiting)
                    # No native call is performed here. These are invented
                    # caller-owned raw and normalized observation fixtures.
                    pending_observation={
                        "task_wait_ref":wait_ref,
                        "call":task_call,
                        "result":{"content":[{"type":"text",
                            "text":"Invented caller observation: original task still running."}]},
                        "task":{"attempt_id":request["attempt_id"],
                                "turn_id":"invented-accepted-turn","state":"pending",
                                "evidence_ref":"synthetic://caller-task-pending"},
                    }

                    def refuses_without_writes(value):
                        before=retained_bytes()
                        refused=command("reconcile",op,value)
                        self.assertEqual(refused["status"],"refused",refused)
                        self.assertIsInstance(refused["reason"],str)
                        self.assertTrue(refused["reason"].strip())
                        self.assertIsNone(refused["native_call"])
                        self.assertEqual(refused["ipc"],"not_attempted")
                        self.assertEqual(retained_bytes(),before)
                        self.assertEqual(mailbox("show",request["message_id"]),recorded)
                        self.assertEqual(wire,original_wire)
                        with self.assertRaises(BlockingIOError):
                            connection,_=listener.accept()
                            connection.close()

                    for conflict in (
                        {"task":{**pending_observation["task"],
                                 "attempt_id":"invented-unrelated-attempt"}},
                        {"task":{**pending_observation["task"],
                                 "turn_id":"invented-unrelated-turn"}},
                        {"call":{**task_call,"arguments":{**task_call["arguments"],
                                                         "threadId":"unrelated-child"}}},
                        {"task_wait_ref":accepted["refs"]["operation_ref"]},
                    ):
                        with self.subTest(conflict=conflict):
                            refuses_without_writes({**pending_observation,**conflict})

                    pending=command("reconcile",op,pending_observation)
                    preserves_submission(pending)
                    self.assertEqual(pending["task_observation"],"pending")
                    self.assertEqual(pending["task_completion"],"unknown")
                    self.assertIsNone(pending["native_call"])
                    self.assertEqual(pending["refs"]["task_wait_ref"],wait_ref)
                    pending_ref=pending["refs"]["task_observation_ref"]
                    self.assertNotEqual(pending_ref,wait_ref)
                    self.assertEqual(json.loads(Path(pending_ref).read_bytes()),
                                     pending_observation)
                    pending_files=retained_bytes()
                    for repeated in (
                        command("reconcile",op,pending_observation),
                        command("reconcile",op,wait_request),
                        command("show",op),command("reconcile",op),
                    ):
                        preserves_submission(repeated)
                        self.assertEqual(repeated["task_observation"],"pending")
                        self.assertEqual(repeated["task_completion"],"unknown")
                        self.assertEqual(repeated["refs"],pending["refs"])
                        self.assertIsNone(repeated["native_call"])
                    self.assertEqual(retained_bytes(),pending_files)

                    error_wait_request={"task_wait":{"observation_seconds":1,
                                                      "after_ref":pending_ref}}
                    error_wait=command("reconcile",op,error_wait_request)
                    preserves_submission(error_wait)
                    self.assertEqual(error_wait["native_call"],task_call)
                    error_wait_ref=error_wait["refs"]["task_wait_ref"]
                    error_observation={
                        "task_wait_ref":error_wait_ref,"call":task_call,
                        "result":{"isError":True,"content":[{"type":"text",
                                  "text":"Invented caller read failure; task state unknown."}]},
                        "task":{"attempt_id":request["attempt_id"],
                                "turn_id":"invented-accepted-turn","state":"unknown",
                                "evidence_ref":"synthetic://caller-task-read-unknown"},
                    }
                    refuses_without_writes({
                        **error_observation,"task":{**error_observation["task"],
                                                    "state":"completed"},
                    })
                    unknown=command("reconcile",op,error_observation)
                    preserves_submission(unknown)
                    self.assertEqual(unknown["task_observation"],"unknown")
                    self.assertEqual(unknown["task_completion"],"unknown")
                    self.assertIsNone(unknown["native_call"])
                    pending_ref=unknown["refs"]["task_observation_ref"]
                    self.assertEqual(json.loads(Path(pending_ref).read_bytes()),
                                     error_observation)
                    pending_files=retained_bytes()
                    resume_request={"task_wait":{"observation_seconds":1,
                                                 "after_ref":pending_ref}}
                    refuses_without_writes({"task_wait":{"observation_seconds":1,
                                                          "after_ref":wait_ref}})
                    resumed=command("reconcile",op,resume_request)
                    preserves_submission(resumed)
                    self.assertEqual(resumed["task_observation"],"pending")
                    self.assertEqual(resumed["task_completion"],"unknown")
                    self.assertEqual(resumed["native_call"],task_call)
                    resume_ref=resumed["refs"]["task_wait_ref"]
                    self.assertNotEqual(resume_ref,wait_ref)
                    self.assertNotEqual(resume_ref,pending_ref)
                    self.assertEqual(json.loads(Path(resume_ref).read_bytes())["task_wait"],
                                     resume_request["task_wait"])
                    for path,data in pending_files.items():
                        self.assertEqual(path.read_bytes(),data)
                    completed_observation={
                        "task_wait_ref":resume_ref,
                        "call":task_call,
                        "result":{"content":[{"type":"text",
                            "text":"Invented caller observation: original task completed."}]},
                        "task":{"attempt_id":request["attempt_id"],
                                "turn_id":"invented-accepted-turn","state":"completed",
                                "evidence_ref":"synthetic://caller-task-completed"},
                    }
                    refuses_without_writes({**completed_observation,
                                            "task_wait_ref":wait_ref})
                    completed=command("reconcile",op,completed_observation)
                    preserves_submission(completed)
                    self.assertEqual(completed["task_observation"],"completed")
                    self.assertEqual(completed["task_completion"],"completed")
                    self.assertIsNone(completed["native_call"])
                    self.assertEqual(completed["refs"]["task_wait_ref"],resume_ref)
                    completed_ref=completed["refs"]["task_observation_ref"]
                    self.assertNotIn(completed_ref,(pending_ref,wait_ref,resume_ref))
                    self.assertEqual(json.loads(Path(completed_ref).read_bytes()),
                                     completed_observation)
                    for path,data in pending_files.items():
                        self.assertEqual(path.read_bytes(),data)
                    completed_files=retained_bytes()
                    # Keep the unserved listener to catch accidental reconnects.
                    for repeated in (
                        command("reconcile",op,completed_observation),
                        command("reconcile",op,resume_request),
                        command("show",op),command("reconcile",op),
                        command("submit",op),command("prepare",value=request),
                    ):
                        for key in ("status","child","turn_id","saved_selection","receipt",
                                    "effective_program","owned_connection","ipc"):
                            self.assertEqual(repeated[key],accepted[key],repeated)
                        self.assertEqual(repeated["task_observation"],"completed")
                        self.assertEqual(repeated["task_completion"],"completed")
                        self.assertEqual(repeated["refs"],completed["refs"])
                        self.assertIsNone(repeated["native_call"])
                    self.assertEqual(retained_bytes(),completed_files)
                    self.assertEqual(mailbox("show",request["message_id"]),recorded)
                    self.assertEqual(mailbox("pending"),[recorded])
                    self.assertEqual(wire,original_wire)
                    return

                if not continuation:
                    return

                # A has passed the original healthy path and offline checks above.
                # B is a new explicit task, not another observation or attempt of A.
                previous_request=dict(request)
                previous_refs=dict(accepted["refs"])
                previous_recorded=recorded
                previous_files=dict(retained)
                previous_wire=list(wire)
                request={
                    **request,
                    "previous_operation_id":previous_request["operation_id"],
                    "operation_id":"continuation-task-operation",
                    "message_id":"continuation-task-message",
                    "attempt_id":"continuation-task-attempt",
                    "correlation_id":"continuation-task-correlation",
                    "sender":{"thread_id":"continuation-sender","host_id":"origin-host"},
                    "actor":{"thread_id":"continuation-caller","host_id":"local"},
                    "owner":{"thread_id":"continuation-owner","host_id":"owner-host"},
                    "authority_ref":"synthetic://existing-continuation-authority",
                    "holds":["synthetic://continuation-hold-one",
                             "synthetic://continuation-hold-two"],
                    "payload":"NEW_TASK_B: Keep caf\u00e9 and \u96ea.\\nNew task only: \U0001f44b",
                }
                op=request["operation_id"]
                message={
                    key:request[key] for key in
                    ("message_id","correlation_id","sender","owner","authority_ref","holds","payload")
                }
                message["recipient"]=child
                expected_text="Peer message (no new operator authority).\n"+json.dumps({
                    "schema":"provingkit-peer-message-v1",**message,"actor":request["actor"],
                },ensure_ascii=True,sort_keys=True,separators=(",",":"))
                refs={key:request[key] for key in ("operation_id","message_id","attempt_id")}
                if standing:
                    legacy=dict(request)
                    del legacy["resource_admission"]
                    downgraded=command("continue",value=legacy)
                    self.assertEqual(downgraded["status"],"refused")
                    self.assertEqual(downgraded["reason"],"standing-continuation-downgrade")
                    listener.setblocking(False)
                    with self.assertRaises(BlockingIOError):
                        connection,_=listener.accept()
                        connection.close()
                wire,errors,prewrite=[],[],[]
                closed=threading.Event()
                connected=threading.Event()
                listener.settimeout(0.5)
                server=threading.Thread(target=serve,args=(listener,),daemon=True)
                server.start()
                try:
                    continued=command("continue",value=request)
                finally:
                    server.join(timeout=5)
                self.assertFalse(server.is_alive(),"owned continuation fixture did not terminate")
                self.assertEqual(continued["status"],"turn_accepted",continued)
                self.assertEqual(errors,[],continued)
                self.assertTrue(connected.is_set(),continued)
                self.assertTrue(closed.is_set(),continued)
                methods=[
                    "initialize","thread-owner-discovery","thread-follower-update-daybreak",
                    "thread-follower-read-model-settings","thread-follower-start-turn",
                ]
                self.assertEqual([frame["method"] for frame in previous_wire],methods)
                self.assertEqual([frame["method"] for frame in wire],methods)
                # Each serve invocation accepts one connection. A queued third
                # connection would fail the final nonblocking accept below.
                self.assertEqual(continued["child"],child)
                self.assertIsNone(continued["native_call"])
                self.assertEqual(continued["ipc"],"attempted")
                if standing:
                    self.assertEqual(continued["task_write"],"attempted")
                self.assertIs(continued["saved_selection"],True)
                self.assertEqual(continued["turn_id"],"invented-accepted-turn")
                self.assertEqual(continued["owned_connection"],{"started":True,"closed":True})
                for key in ("receipt","task_completion","effective_program"):
                    self.assertEqual(continued[key],"unknown")
                for key in ("operation_id","message_id","attempt_id"):
                    self.assertEqual(continued["refs"][key],request[key])
                    self.assertNotEqual(continued["refs"][key],previous_refs[key])
                for key in ("operation_ref","setup_ref","attempt_ref"):
                    self.assertNotEqual(continued["refs"][key],previous_refs[key])
                self.assertEqual([item[0] for item in prewrite],["setup_ref","attempt_ref"])
                for reference,path,retained_bytes in prewrite:
                    self.assertEqual(continued["refs"][reference],path)
                    self.assertEqual(Path(path).read_bytes(),retained_bytes)
                intent_path=Path(continued["refs"]["operation_ref"])
                continuation_path=Path(continued["refs"]["continuation_ref"])
                self.assertEqual(continuation_path.name,"continuation.json")
                self.assertNotEqual(intent_path,continuation_path)
                self.assertEqual(json.loads(intent_path.read_bytes()),request)
                continuation_record=json.loads(continuation_path.read_bytes())
                self.assertEqual(continuation_record["previous_operation_id"],
                                 previous_request["operation_id"])
                self.assertEqual(continuation_record["child"],child)
                recorded_b=mailbox("show",request["message_id"])
                self.assertEqual({key:value for key,value in recorded_b.items()
                                  if key not in {"state","attempts"}},message)
                self.assertEqual(recorded_b["state"],"submitted")
                self.assertEqual(len(recorded_b["attempts"]),1)
                attempt_b=recorded_b["attempts"][0]
                self.assertEqual(attempt_b["attempt_id"],request["attempt_id"])
                self.assertEqual(attempt_b["actor"],request["actor"])
                self.assertEqual(attempt_b["submission"],"submitted")
                self.assertIsNone(attempt_b["reconciliation"])
                for stage in ("received","handled","completed"):
                    self.assertIs(attempt_b[stage],False)
                self.assertEqual(mailbox("show",previous_request["message_id"]),previous_recorded)
                self.assertEqual({item["message_id"] for item in mailbox("pending")},
                                 {previous_request["message_id"],request["message_id"]})
                for path,data in previous_files.items():
                    self.assertEqual(path.read_bytes(),data)
                all_files={path:path.read_bytes() for path in root.rglob("*") if path.is_file()}
                listener.setblocking(False)
                for repeated in (
                    command("continue",value=request),command("show",op),
                    command("reconcile",op),command("submit",op),
                    command("show",previous_request["operation_id"]),
                    command("reconcile",previous_request["operation_id"]),
                ):
                    expected=accepted if repeated["refs"]["operation_id"]==previous_request["operation_id"] else continued
                    self.assertEqual(repeated["status"],"turn_accepted",repeated)
                    self.assertEqual(repeated["refs"],expected["refs"])
                    self.assertEqual(repeated["child"],child)
                    self.assertEqual(repeated["turn_id"],expected["turn_id"])
                    self.assertIsNone(repeated["native_call"])
                self.assertEqual({path:path.read_bytes() for path in root.rglob("*")
                                  if path.is_file()},all_files)
                self.assertEqual(mailbox("show",previous_request["message_id"]),previous_recorded)
                self.assertEqual(mailbox("show",request["message_id"]),recorded_b)
                with self.assertRaises(BlockingIOError):
                    connection,_=listener.accept()
                    connection.close()


    def test_prepare_refuses_unsupported_selection_and_account_before_creation(self):
        for field,value in (("model","unsupported-model"),("effort","ultra"),
                            ("cyberAccessProgram","other-program"),
                            ("account","invented-other-account")):
            with self.subTest(field=field), tempfile.TemporaryDirectory(prefix="db-refused-") as directory:
                scratch=Path(directory).resolve()
                root=scratch/"operations"
                root.mkdir(mode=0o700)
                command=self.command(scratch,root)
                request={
                    "operation_id":"unsupported-selection-operation",
                    "message_id":"unsupported-selection-message",
                    "attempt_id":"unsupported-selection-attempt",
                    "correlation_id":"unsupported-selection-correlation",
                    "sender":{"thread_id":"sender","host_id":"local"},
                    "actor":{"thread_id":"caller","host_id":"local"},
                    "owner":{"thread_id":"owner","host_id":"local"},
                    "authority_ref":"synthetic://existing-authority",
                    "holds":["synthetic://existing-hold"],
                    "payload":"Preserve the original task until selection is supported.",
                    "endpoint":str(scratch/"must-not-connect.sock"),
                    "mailbox":str(scratch/"mailbox.sqlite3"),
                    "capture":{"run_root":str(root),"allowance_bytes":8388608,
                               "terminal_provision_bytes":524288,"later_forecast_bytes":0},
                    "observation_seconds":0.1,
                    field:value,
                }
                result=command("prepare",value=request)
                self.assertEqual(result["status"],"refused",result)
                self.assertIsInstance(result["reason"],str)
                self.assertTrue(result["reason"].strip())
                self.assertIsNone(result["native_call"])
                self.assertEqual(result["ipc"],"not_attempted")
                self.assertIsNone(result.get("child"))
                self.assertIsNone(result.get("recipient"))


if __name__=="__main__":
    unittest.main()
