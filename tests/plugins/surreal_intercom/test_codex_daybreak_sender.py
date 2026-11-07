"""Public Daybreak operation contract with caller-owned native controls."""

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

    def command(self,scratch,root):
        counter=0

        def launch(phase,operation_id=None,value=None):
            nonlocal counter
            argv=[sys.executable,"-B",str(SENDER),"--root",str(root),phase]
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

    def completed_bootstrap_submission(self,pending_first=False,failure=None,continuation=False,task_observation=False,accepted_tail=None):
        with tempfile.TemporaryDirectory(prefix="db-task-") as directory:
            scratch=Path(directory).resolve()
            root=scratch/"operations"
            root.mkdir(mode=0o700)
            endpoint=scratch/"peer.sock"
            store=scratch/"mailbox.sqlite3"
            command=self.command(scratch,root)

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

                        def receive():
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
                        reply(settings,{"settings":{"daybreakEnabled":failure!="false-readback"}},
                              "invented-owner-client",
                              tail=prefix_tail if failure=="readback-prefix" else b"")
                        if failure in {"false-readback","outgoing-frame","readback-prefix"}:
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
                    if failure in {"outgoing-frame","readback-prefix"}:
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
                                  True if failure in {"lost-task-response","outgoing-frame","readback-prefix"} else None)
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
                    self.assertEqual(set(accepted["refs"]),set(refs)|set(references))
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
                            "outgoing-frame":("task-submit","outgoing-frame-limit"),
                            "false-readback":("daybreak-readback","saved-selection-unconfirmed"),
                        }[failure]
                        self.assertEqual(first,dict(zip(("stage","reason"),expected_failure)))
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
                    # The caller acquires each invented native result after the
                    # command emits its existing bounded read call.
                    original_files=dict(retained)
                    original_wire=list(wire)
                    wait_request={"task_wait":{"observation_seconds":1,"after_ref":None}}

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

                    waiting=command("reconcile",op,wait_request)
                    self.assertEqual(waiting["status"],"turn_accepted",waiting)
                    self.assertEqual(waiting["task_observation"],"pending")
                    self.assertEqual(waiting["task_completion"],"unknown")
                    preserves_submission(waiting)
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
