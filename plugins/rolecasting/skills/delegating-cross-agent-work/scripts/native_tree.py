"""Local bookkeeping for the ordinary same-controller native-tree profile.

This module does not execute native tools. It returns inert call instructions
after committed local claims. Supplied controller references and evidence
claims are not external authentication.
"""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import sys


class NativeTreeError(ValueError):
    """A native-tree request cannot preserve its declared contract."""


_MAPPING_REVISION = "chatgpt-codex-native-tree-observations-v3"
_OBSERVATION_SOURCES = {"native-tool-result", "native-inventory", "harness-final-event",
                        "worker-report", "owner-verification"}
_NATIVE_STATUSES = {"running", "interrupted"}
_MAXIMUM_ASSURANCE = {
    "target": "controller-observed", "topology": "controller-observed",
    "model": "self-reported", "authority": "self-reported",
    "execution_result": "controller-observed",
}
_ASSURANCE_RANK = {"self-reported": 0, "controller-observed": 1, "product-attested": 2}


def _minima(value):
    _shape(value, set(), set(_MAXIMUM_ASSURANCE))
    for dimension, level in value.items():
        if type(level) is not str or level not in _ASSURANCE_RANK:
            raise NativeTreeError("unknown assurance level")
        if _ASSURANCE_RANK[level] > _ASSURANCE_RANK[_MAXIMUM_ASSURANCE[dimension]]:
            raise NativeTreeError("assurance minimum exceeds profile maximum")
        if dimension in ("model", "authority"):
            raise NativeTreeError("required assurance is unavailable in current mappings")


def _input_digest(assignment):
    return assignment.get("input_sha256", assignment["request_sha256"])


def _native_status(value):
    if type(value) is str and value in _NATIVE_STATUSES:
        return value
    if type(value) is dict and set(value) == {"completed"}:
        return "completed"
    return None


def _json_value(value):
    if value is None or type(value) in (bool, int, str):
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is list:
        for item in value:
            _json_value(item)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for item in value.values():
            _json_value(item)
        return
    raise NativeTreeError("record must contain only JSON values and string object keys")


def _canonical(value):
    try:
        _json_value(value)
        result = json.dumps(value, sort_keys=True, separators=(",", ":"),
                            ensure_ascii=False, allow_nan=False)
        result.encode("utf-8")
        return result
    except (TypeError, ValueError, RecursionError, UnicodeError) as error:
        raise NativeTreeError("record must be canonical JSON") from error


def _shape(value, required, optional=()):
    if not isinstance(value, dict) or not required <= value.keys():
        raise NativeTreeError("record has missing required fields")
    if value.keys() - required - set(optional):
        raise NativeTreeError("record has unsupported fields")


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise NativeTreeError(f"{label} must be a nonempty string")


def _generation(value):
    if type(value) is not int or value < 1:
        raise NativeTreeError("generation must be a positive integer")


def _sha(value, label):
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise NativeTreeError(f"{label} must be a SHA-256 digest")


def _digest(value):
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _role_ref(value):
    _shape(value, {"role", "generation"})
    _text(value["role"], "role")
    _generation(value["generation"])


def _native_call(action, mode, payload, recipient):
    """Render only current native arguments; selection policy stays external."""
    if action == "spawn":
        _shape(payload, {"task_name", "message", "fork_turns"},
               {"model", "reasoning_effort"})
        if not isinstance(payload["task_name"], str) or re.fullmatch(r"[a-z0-9_]+", payload["task_name"]) is None:
            raise NativeTreeError("task_name requires lowercase letters, digits or underscores")
        if mode == "fresh":
            if payload["fork_turns"] != "none" or not {"model", "reasoning_effort"} <= payload.keys():
                raise NativeTreeError("fresh spawn requires explicit model, effort and fork_turns=none")
            _text(payload["model"], "model")
            _text(payload["reasoning_effort"], "reasoning_effort")
        elif mode == "inherit":
            if payload["fork_turns"] != "all" or {"model", "reasoning_effort"} & payload.keys():
                raise NativeTreeError("inherited spawn cannot override model or effort")
        else:
            raise NativeTreeError("unsupported spawn mode")
        _text(payload["message"], "message")
        return {"tool": "collaboration.spawn_agent", "arguments": payload}
    if action in ("notify", "activate-or-steer"):
        _shape(payload, {"message"})
        _text(payload["message"], "message")
        modes = {"information", "reply"} if action == "notify" else {"assign", "continue", "steer"}
        if mode not in modes:
            raise NativeTreeError("unsupported message mode")
        if action == "activate-or-steer" and recipient["relation"] == "root":
            raise NativeTreeError("native root activation is unsupported")
        if recipient["native_target"] is None:
            raise NativeTreeError("recipient has no observed native target")
        tool = "send_message" if action == "notify" else "followup_task"
        return {"tool": "collaboration." + tool,
                "arguments": {"target": recipient["native_target"], "message": payload["message"]}}
    if action == "interrupt":
        _shape(payload, set())
        if mode != "request" or recipient["relation"] == "root":
            raise NativeTreeError("unsupported native interruption")
        if recipient["native_target"] is None:
            raise NativeTreeError("recipient has no observed native target")
        return {"tool": "collaboration.interrupt_agent", "arguments": {"target": recipient["native_target"]}}
    if action == "inspect":
        _shape(payload, set(), {"path_prefix"})
        if mode != "inventory":
            raise NativeTreeError("unsupported inventory mode")
        if "path_prefix" in payload:
            _text(payload["path_prefix"], "path_prefix")
        return {"tool": "collaboration.list_agents", "arguments": payload}
    if action == "wait":
        _shape(payload, set(), {"timeout_ms"})
        if mode != "bounded":
            raise NativeTreeError("unsupported wait mode")
        if "timeout_ms" in payload and (type(payload["timeout_ms"]) is not int or not 10000 <= payload["timeout_ms"] <= 3600000):
            raise NativeTreeError("timeout_ms is outside the supported native range")
        return {"tool": "collaboration.wait_agent", "arguments": payload}
    raise NativeTreeError("unsupported native action")


def _run_record(run):
    _shape(run, {"schema", "run_id", "controller_ref", "profile_id",
                 "profile_sha256", "capability_ref", "capability_sha256",
                 "product_version"})
    if run["schema"] != "native-tree-run-v1":
        raise NativeTreeError("unsupported run schema")
    if run["profile_id"] != "chatgpt-codex-native-tree-v1":
        raise NativeTreeError("unsupported native-tree profile")
    for key in ("run_id", "controller_ref", "capability_ref"):
        _text(run[key], key)
    for key in ("profile_sha256", "capability_sha256"):
        _sha(run[key], key)
    version = run["product_version"]
    if not isinstance(version, dict):
        raise NativeTreeError("product_version must explicitly describe evidence")
    if version.get("state") == "unavailable":
        _shape(version, {"state", "reason"})
        _text(version["reason"], "product version unavailable reason")
    elif version.get("state") == "observed":
        _shape(version, {"state", "value", "evidence_ref"})
        _text(version["value"], "product version")
        _text(version["evidence_ref"], "product version evidence")
    else:
        raise NativeTreeError("product version evidence state is unsupported")
    return _canonical(run)


_SCHEMA = (
    "CREATE TABLE run (singleton INTEGER PRIMARY KEY CHECK(singleton=1), content TEXT NOT NULL)",
    "CREATE TABLE bindings (role TEXT NOT NULL, generation INTEGER NOT NULL, content TEXT NOT NULL, PRIMARY KEY(role,generation))",
    "CREATE TABLE retirements (role TEXT NOT NULL, generation INTEGER NOT NULL, content TEXT NOT NULL, PRIMARY KEY(role,generation), FOREIGN KEY(role,generation) REFERENCES bindings(role,generation))",
    "CREATE TABLE commands (command_id TEXT PRIMARY KEY NOT NULL, content TEXT NOT NULL, command_sha256 TEXT NOT NULL, role TEXT, generation INTEGER, action TEXT NOT NULL, claimed INTEGER NOT NULL DEFAULT 0 CHECK(claimed IN (0,1)), claim_actor TEXT, outcome TEXT NOT NULL DEFAULT 'prepared', claim_sequence INTEGER UNIQUE)",
    "CREATE TABLE assignments (assignment_id TEXT PRIMARY KEY NOT NULL, content TEXT NOT NULL, role TEXT NOT NULL, generation INTEGER NOT NULL, native_target TEXT, state TEXT NOT NULL, native_busy INTEGER NOT NULL DEFAULT 1 CHECK(native_busy IN (0,1)), closure_sequence INTEGER, acceptance TEXT)",
    "CREATE TABLE observations (sequence INTEGER PRIMARY KEY, observation_id TEXT UNIQUE NOT NULL, command_id TEXT NOT NULL REFERENCES commands(command_id), content TEXT NOT NULL, facts TEXT NOT NULL)",
    "CREATE TABLE reconciliations (reconciliation_id TEXT PRIMARY KEY NOT NULL, command_id TEXT NOT NULL REFERENCES commands(command_id), disposition TEXT NOT NULL, content TEXT NOT NULL, consumed_by TEXT UNIQUE REFERENCES commands(command_id))",
    "CREATE UNIQUE INDEX one_retry_authorization ON reconciliations(command_id) WHERE disposition='authorize-new-attempt'",
)


class NativeTree:
    """A local, versioned SQLite store for supplied controller claims.

    The actor may initially be unbound only to bind itself as the first root.
    Stored identities and evidence references do not authenticate the caller.
    """

    def __init__(self, path, *, run, actor, create=False):
        self._run_content = _run_record(run)
        _shape(actor, {"role", "generation"})
        _text(actor["role"], "actor role")
        _generation(actor["generation"])
        self._actor_content = _canonical(actor)
        if type(create) is not bool:
            raise NativeTreeError("create must be a strict Boolean")
        self.path = Path(path).resolve()
        self._closed = False
        self.db = None
        if create:
            descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(descriptor)
        try:
            self.db = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, timeout=5)
            if create:
                with self.db:
                    self.db.execute("BEGIN IMMEDIATE")
                    for statement in _SCHEMA:
                        self.db.execute(statement)
                    self.db.execute("INSERT INTO run VALUES (1, ?)", (self._run_content,))
                    self.db.execute("PRAGMA user_version = 1")
            if self.db.execute("PRAGMA user_version").fetchone()[0] != 1:
                raise NativeTreeError("unsupported or uninitialized native-tree store")
            actual_schema = {row[0] for row in self.db.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'")}
            if actual_schema != set(_SCHEMA):
                raise NativeTreeError("unsupported or incomplete native-tree schema")
            stored_run = self.db.execute("SELECT content FROM run WHERE singleton=1").fetchone()
            if stored_run is None or stored_run[0] != self._run_content:
                raise NativeTreeError("stored run does not match supplied immutable run")
            self.db.execute("SELECT role, generation, content FROM bindings LIMIT 0")
            self.db.execute("SELECT command_id, claimed, outcome, claim_sequence FROM commands LIMIT 0")
            self.db.execute("SELECT assignment_id, native_target, state FROM assignments LIMIT 0")
            self.db.execute("SELECT observation_id, command_id, content, facts FROM observations LIMIT 0")
            self.db.execute("PRAGMA foreign_keys = ON")
            self.db.execute("PRAGMA synchronous = FULL")
        except BaseException:
            self.close()
            raise

    @property
    def run(self):
        return json.loads(self._run_content)

    @property
    def actor(self):
        return json.loads(self._actor_content)

    def __enter__(self):
        if self._closed:
            raise NativeTreeError("native-tree store is closed")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False

    def close(self):
        """Close the store; safe to call repeatedly."""
        if self.db is not None:
            self.db.close()
            self.db = None
        self._closed = True

    def _check_open(self):
        if self._closed:
            raise NativeTreeError("native-tree store is closed")

    def _binding(self, reference, *, allow_retired=False):
        row = self.db.execute("SELECT generation, content FROM bindings WHERE role=? ORDER BY generation DESC LIMIT 1", (reference["role"],)).fetchone()
        if row is None:
            raise NativeTreeError("role is unbound")
        if row[0] != reference["generation"]:
            raise NativeTreeError("stale binding generation")
        if not allow_retired and self.db.execute("SELECT 1 FROM retirements WHERE role=? AND generation=?", (reference["role"], reference["generation"])).fetchone():
            raise NativeTreeError("role binding is retired")
        return json.loads(row[1])

    def _command(self, command_id):
        _text(command_id, "command_id")
        row = self.db.execute("SELECT content, command_sha256, claimed, outcome FROM commands WHERE command_id=?", (command_id,)).fetchone()
        if row is None:
            raise NativeTreeError("unknown command")
        command = json.loads(row[0])
        if _digest(command) != row[1]:
            raise NativeTreeError("stored command digest mismatch")
        return command, row

    def _command_target_evidence(self, command):
        targets = {}
        if command["native_target"] is not None:
            targets[command["native_target"]] = {"evidence_refs": [], "discovered_after_sequence": 0}
        if command["action"] == "spawn":
            for content, facts_content in self.db.execute("SELECT content, facts FROM observations WHERE command_id=? ORDER BY sequence", (command["plan"]["command_id"],)):
                observation, facts = json.loads(content), json.loads(facts_content)
                target = facts.get("native_target")
                if observation["source_kind"] == "native-tool-result" and target is not None:
                    evidence = targets.setdefault(target, {"evidence_refs": [], "discovered_after_sequence": observation.get("recorded_after_claim_sequence", 0)})
                    evidence["evidence_refs"].append(observation["evidence_ref"])
        return targets

    def _command_targets(self, command):
        return set(self._command_target_evidence(command))

    def _subject_target(self, command):
        targets = self._command_targets(command)
        return next(iter(targets)) if len(targets) == 1 else None

    def _assignment_targets(self, assignment_id):
        targets = set()
        for content, in self.db.execute("SELECT content FROM commands WHERE claimed=1"):
            command = json.loads(content)
            if command["action"] in ("spawn", "activate-or-steer") and command["plan"].get("assignment_id") == assignment_id:
                targets.update(self._command_targets(command))
        return targets

    def _activity_view(self):
        """Derive each claimed attempt's hazards without consulting the directory."""
        activities = []
        for content, sequence in self.db.execute("SELECT content, claim_sequence FROM commands WHERE claimed=1 ORDER BY claim_sequence"):
            command = json.loads(content)
            if command["action"] not in ("spawn", "activate-or-steer"):
                continue
            assignment, row = self._assignment(command["plan"]["assignment_id"])
            targets = self._command_target_evidence(command)
            for target, evidence in (targets.items() if targets else [(None, {"evidence_refs": [], "discovered_after_sequence": 0})]):
                after = max(sequence, row[4] or 0, evidence["discovered_after_sequence"])
                released_by = (self._activity_release(target, after)
                               if row[1] in ("accepted", "abandoned") and target is not None else [])
                blocking = not released_by
                activities.append({"command_id": command["plan"]["command_id"],
                                   "assignment_id": assignment["assignment_id"], "recipient": command["recipient"],
                                   "native_target": target, "claim_sequence": sequence,
                                   "logical_state": row[1], "closure_sequence": row[4],
                                   "evidence_refs": evidence["evidence_refs"],
                                   "discovered_after_sequence": evidence["discovered_after_sequence"],
                                   "released_by": released_by,
                                   "blocking": blocking,
                                   "reason": None if not blocking else "unresolved-work" if row[1] == "unresolved" else "native-completion-unverified"})
        return activities

    def _launch_evidence(self, assignment):
        launches = []
        for content, in self.db.execute("SELECT content FROM commands WHERE claimed=1 AND action='spawn'"):
            command = json.loads(content)
            if command["plan"].get("assignment_id") == assignment["assignment_id"]:
                launches.append(command)
        if len(launches) != 1:
            return None
        launch = launches[0]
        reference = assignment["recipient"]
        row = self.db.execute("SELECT content FROM bindings WHERE role=? AND generation=?", (reference["role"], reference["generation"])).fetchone()
        if row is None:
            return None
        binding = json.loads(row[0])
        if binding["source_kind"] != "native-tool-result" or binding["selection_ref"] != launch["plan"]["selection_ref"]:
            return None
        for content, facts in self.db.execute("SELECT content, facts FROM observations ORDER BY sequence"):
            observation, mapped = json.loads(content), json.loads(facts)
            if (observation["command_id"] == launch["plan"]["command_id"]
                    and observation["source_kind"] == "native-tool-result"
                    and observation["collected_by"] == observation["command_id"]
                    and observation["evidence_ref"] == binding["observation_ref"]
                    and mapped.get("native_target") == binding["native_target"]):
                return launch, binding, observation
        return None

    def _final_facts(self, command, raw):
        envelope = re.match(r"\AMessage Type: FINAL_ANSWER\nTask name: ([^\r\n]+)\nSender: ([^\r\n]+)\nPayload:\n", raw)
        if envelope is None:
            return {}
        receiver, sender = envelope.groups()
        payload = raw[envelope.end():]
        facts = {"harness_final": {"receiver": receiver, "sender": sender,
                                   "payload": payload, "payload_digest": _digest(payload)}}
        assignment_id = command["plan"].get("assignment_id")
        if assignment_id is None:
            return facts
        try:
            assignment, _ = self._assignment(assignment_id)
        except NativeTreeError:
            return facts
        launch_evidence = self._launch_evidence(assignment)
        if launch_evidence is None:
            return facts
        launch, binding, receipt = launch_evidence
        if (command["plan"]["command_id"] != launch["plan"]["command_id"]
                or launch["mode"] != "fresh" or launch["payload"]["fork_turns"] != "none"
                or launch["actor"] != self.actor or binding["native_target"] != sender
                or self._command_targets(launch) != {sender}):
            return facts
        try:
            actor = self._binding(self.actor)
        except NativeTreeError:
            return facts
        if actor["relation"] != "root" or actor["native_target"] != receiver:
            return facts
        # This sufficient attribution rule assumes cooperative coverage of all
        # native inputs; known additional inputs make the event ambiguous.
        for content, in self.db.execute("SELECT content FROM commands WHERE claimed=1"):
            other = json.loads(content)
            if (other["plan"]["command_id"] != launch["plan"]["command_id"]
                    and other["action"] not in ("inspect", "wait")
                    and sender in self._command_targets(other)):
                return facts
        for content, in self.db.execute("SELECT content FROM bindings"):
            other = json.loads(content)
            if other["native_target"] == sender and (other["role"], other["generation"]) != (binding["role"], binding["generation"]):
                return facts
        if self.db.execute("SELECT 1 FROM assignments WHERE native_target=? AND assignment_id!=?", (sender, assignment_id)).fetchone():
            return facts
        result = {"assignment_id": assignment_id, "generation": assignment["recipient"]["generation"],
                  "input_digest": _input_digest(assignment), "result_digest": _digest(payload)}
        facts["native_result"] = {**result, "run_id": self.run["run_id"],
                                  "creation_command": launch["plan"]["command_id"],
                                  "native_target": sender, "receiver": receiver, "payload": payload,
                                  "launch_evidence_ref": receipt["evidence_ref"],
                                  "binding_evidence_ref": binding["observation_ref"]}
        if assignment["owner"] == self.actor and assignment["reply_to"] == self.actor:
            facts["worker_result"] = result
        return facts

    def _assignment_evidence(self, assignment, row, selected_digest=None):
        dimensions = {name: {"maximum": maximum, "achieved": None, "value": None,
                             "evidence_refs": [], "missing_reason": "no supported evidence"}
                      for name, maximum in _MAXIMUM_ASSURANCE.items()}
        for name in ("model", "authority"):
            dimensions[name]["missing_reason"] = "not observed by current mappings"
        def support(name, achieved, value, references):
            dimensions[name].update(achieved=achieved, value=value,
                                    evidence_refs=sorted(set(references)), missing_reason=None)
        launch = self._launch_evidence(assignment)
        if launch is not None:
            command, binding, receipt = launch
            support("target", "controller-observed", binding["native_target"], [receipt["evidence_ref"]])
            support("topology", "controller-observed",
                    {"relationship": "child", "ownership": "leader-owned", "transport": "native-tool"},
                    [receipt["evidence_ref"]])
        results, native, verifications, status = {}, {}, [], []
        targets = self._assignment_targets(assignment["assignment_id"])
        expected = {"assignment_id": assignment["assignment_id"],
                    "generation": assignment["recipient"]["generation"], "input_digest": _input_digest(assignment)}
        for content, facts_content in self.db.execute("SELECT content, facts FROM observations ORDER BY sequence"):
            observation, facts = json.loads(content), json.loads(facts_content)
            for target, native_status in self._mapped_statuses(observation, facts):
                if target in targets:
                    status.append({"native_target": target, "value": native_status, "evidence_ref": observation["evidence_ref"],
                                   "collected_by": observation["collected_by"]})
                    if launch is None and len(targets) == 1:
                        support("target", "controller-observed", target, [item["evidence_ref"] for item in status])
            for key, candidates in (("worker_result", results), ("native_result", native)):
                result = facts.get(key)
                if result is not None and all(result.get(name) == value for name, value in expected.items()):
                    candidates.setdefault(result["result_digest"], []).append(observation["evidence_ref"])
            verification = facts.get("owner_verification")
            if verification is not None and all(verification.get(name) == value for name, value in expected.items()):
                verifications.append((observation, verification))
        acceptance = None if row[5] is None else json.loads(row[5])
        candidates = set(results) | set(native)
        selected = selected_digest or (None if acceptance is None else acceptance["result_digest"])
        if selected is None and len(candidates) == 1:
            selected = next(iter(candidates))
        if selected in candidates:
            if len(native) > 1:
                dimensions["execution_result"]["missing_reason"] = "conflicting native final candidates"
            elif selected in native:
                support("execution_result", "controller-observed", selected, native[selected])
            elif selected in results:
                support("execution_result", "self-reported", selected, results[selected])
        elif candidates:
            dimensions["execution_result"]["missing_reason"] = "multiple result candidates require owner selection"
        verification_ref = None if acceptance is None else acceptance["verification_ref"]
        verified = any(observation["evidence_ref"] == verification_ref and verification["result_digest"] == selected
                       and verification["usable"] is True and observation["recorded_by"] == assignment["owner"]
                       for observation, verification in verifications)
        unmet = [name for name, level in assignment.get("assurance_minima", {}).items()
                 if dimensions[name]["achieved"] is None
                 or _ASSURANCE_RANK[dimensions[name]["achieved"]] < _ASSURANCE_RANK[level]]
        usable = acceptance is not None and selected in results and verified and not unmet
        return {"dimensions": dimensions, "input_digest": _input_digest(assignment), "result_digest": selected,
                "result_candidates": sorted(candidates), "verification_ref": verification_ref,
                "verification_usable": verified, "accepted": acceptance is not None, "usable": usable,
                "missing_minima": unmet, "unusable_reason": None if usable else "matching acceptance, verification and required evidence are needed",
                "target_status_observations": status,
                "native_completion": {"observed": selected in native,
                                      "evidence_refs": native.get(selected, [])}}

    def _observation_facts(self, command, source, raw):
        if source == "harness-final-event" and type(raw) is str:
            return self._final_facts(command, raw)
        if not isinstance(raw, dict):
            return {}
        if source == "native-tool-result":
            if command["action"] == "spawn" and set(raw) == {"task_name"}:
                target = raw["task_name"]
                if type(target) is str and target.startswith("/") and all(part not in ("", ".", "..") for part in target[1:].split("/")):
                    return {"native_target": target}
            status = _native_status(raw.get("previous_status"))
            if command["action"] == "interrupt" and status is not None:
                return {"previous_status": status}
            if command["action"] == "wait" and raw.get("timed_out") is True:
                return {"wait_timed_out": True}
        if source == "native-inventory" and isinstance(raw.get("agents"), list):
            mapped = []
            for target in sorted(self._command_targets(command)):
                statuses = [_native_status(item.get("agent_status")) for item in raw["agents"]
                            if isinstance(item, dict) and item.get("agent_name") == target]
                if statuses and all(status is not None for status in statuses) and len(set(statuses)) == 1:
                    mapped.append({"native_target": target, "status": statuses[0]})
            if mapped:
                return {"target_statuses": mapped}
        if source in ("worker-report", "owner-verification"):
            required = {"assignment_id", "generation", "input_digest", "result_digest"}
            required |= {"result"} if source == "worker-report" else {"usable", "evidence_ref"}
            if set(raw) != required or type(raw.get("generation")) is not int or type(raw.get("assignment_id")) is not str:
                return {}
            row = self.db.execute("SELECT content FROM assignments WHERE assignment_id=?", (raw["assignment_id"],)).fetchone()
            if row is None:
                return {}
            assignment = json.loads(row[0])
            if (command["plan"].get("assignment_id") != raw["assignment_id"]
                    or assignment["recipient"]["generation"] != raw["generation"]
                    or _input_digest(assignment) != raw["input_digest"]):
                return {}
            try:
                _sha(raw["result_digest"], "result_digest")
            except NativeTreeError:
                return {}
            if source == "worker-report":
                if _digest(raw["result"]) != raw["result_digest"]:
                    return {}
                return {"worker_result": {key: raw[key] for key in ("assignment_id", "generation", "input_digest", "result_digest")}}
            if self.actor != assignment["owner"]:
                raise NativeTreeError("owner verification requires the immutable assignment owner")
            self._binding(self.actor)
            if type(raw["usable"]) is bool:
                return {"owner_verification": raw}
        return {}

    def _mapped_statuses(self, observation, facts):
        if "target_statuses" in facts:
            return [(item["native_target"], item["status"]) for item in facts["target_statuses"]]
        if "native_status" in facts:
            command, _ = self._command(observation["command_id"])
            target = self._subject_target(command)
            return [] if target is None else [(target, facts["native_status"])]
        return []

    def _activity_release(self, target, after_sequence):
        """A proven historical completion stays valid after unrelated new work."""
        collections = {}
        for content, facts_content in self.db.execute("SELECT content, facts FROM observations ORDER BY sequence"):
            observation, facts = json.loads(content), json.loads(facts_content)
            if observation["source_kind"] != "native-inventory" or observation["collected_by"] is None:
                continue
            statuses = [status for observed_target, status in self._mapped_statuses(observation, facts) if observed_target == target]
            if not statuses:
                continue
            row = self.db.execute("SELECT claim_sequence FROM commands WHERE command_id=? AND claimed=1", (observation["collected_by"],)).fetchone()
            if row is not None and row[0] > after_sequence:
                collection = collections.setdefault(row[0], {"statuses": set(), "references": []})
                collection["statuses"].update(statuses)
                collection["references"].append(observation["evidence_ref"])
        for sequence in sorted(collections):
            if collections[sequence]["statuses"] == {"completed"}:
                return collections[sequence]["references"]
        return []

    def _target_status(self, target, after_sequence=0):
        """Return only a status collected after all relevant effects/closure."""
        last_effect = after_sequence
        for content, sequence in self.db.execute("SELECT content, claim_sequence FROM commands WHERE claimed=1"):
            prior = json.loads(content)
            if prior["action"] in ("spawn", "activate-or-steer", "interrupt", "notify") and target in self._command_targets(prior):
                last_effect = max(last_effect, sequence)
        latest = None
        for content, facts in self.db.execute("SELECT content, facts FROM observations ORDER BY sequence"):
            observation, mapped = json.loads(content), json.loads(facts)
            if observation["source_kind"] != "native-inventory":
                continue
            statuses = [status for observed_target, status in self._mapped_statuses(observation, mapped) if observed_target == target]
            if not statuses or observation["collected_by"] is None:
                continue
            collector = self.db.execute("SELECT claim_sequence FROM commands WHERE command_id=? AND claimed=1", (observation["collected_by"],)).fetchone()
            if collector is not None and collector[0] > last_effect:
                if latest is None or collector[0] > latest[0]:
                    latest = (collector[0], statuses[0])
                elif collector[0] == latest[0] and statuses[0] != latest[1]:
                    latest = (collector[0], "conflicting")
        return None if latest is None else latest[1]

    def _continuation_observed(self, command):
        permitted = {"running"} if command["mode"] == "steer" else {"interrupted", "completed"}
        return self._target_status(command["native_target"]) in permitted

    def _assignment(self, assignment_id):
        _text(assignment_id, "assignment_id")
        row = self.db.execute("SELECT content, state, native_target, native_busy, closure_sequence, acceptance FROM assignments WHERE assignment_id=?", (assignment_id,)).fetchone()
        if row is None:
            raise NativeTreeError("unknown assignment")
        assignment = json.loads(row[0])
        assignment.setdefault("input_sha256", assignment["request_sha256"])
        assignment.setdefault("assurance_minima", {})
        return assignment, row

    def _owner(self, assignment, *, require_recipient=True, allow_retired_owner=False):
        if self.actor != assignment["owner"]:
            raise NativeTreeError("operation requires immutable assignment owner")
        self._binding(self.actor, allow_retired=allow_retired_owner)
        if require_recipient:
            self._binding(assignment["recipient"])

    def _nonwork_correlation(self, action, plan):
        if action in ("spawn", "activate-or-steer") or "assignment_id" not in plan:
            return
        assignment, _ = self._assignment(plan["assignment_id"])
        if any(plan[key] != assignment[key] for key in ("owner", "reply_to")):
            raise NativeTreeError("non-work correlation differs from established assignment ownership")
        if "input_sha256" in plan and plan["input_sha256"] != _input_digest(assignment):
            raise NativeTreeError("non-work correlation differs from established assignment input")

    def _retry(self, command):
        reference = command["plan"].get("predecessor_reconciliation_ref")
        if reference is None:
            return None
        row = self.db.execute("SELECT content, consumed_by FROM reconciliations WHERE reconciliation_id=? AND disposition='authorize-new-attempt'", (reference,)).fetchone()
        if row is None:
            raise NativeTreeError("missing retry authorization")
        reconciliation = json.loads(row[0])
        prior, _ = self._command(reconciliation["command_id"])
        def intent(value):
            value = json.loads(_canonical(value))
            value["plan"].pop("command_id")
            value["plan"].pop("predecessor_reconciliation_ref", None)
            return value
        if intent(prior) != intent(command):
            raise NativeTreeError("retry authorization does not match immutable command intent")
        return reconciliation, row[1]

    def bind_role(self, binding):
        """Bind supplied controller evidence without claiming authentication.

        A binding requires controller_ref and source_kind. Initial root binding
        must match the actor and use harness-context. Child binding requires an
        observed canonical target and native-tool-result or native-inventory.
        Optional native IDs remain omitted when the controller omits them.
        """
        self._check_open()
        required = {"schema", "run_id", "controller_ref", "role", "generation",
                    "relation", "native_target", "observation_ref", "source_kind",
                    "selection_ref"}
        optional = {"native_parent_target", "agent_id", "session_id", "task_id", "logical_owner"}
        _shape(binding, required, optional)
        run, actor = self.run, self.actor
        if binding["schema"] != "native-tree-binding-v1":
            raise NativeTreeError("unsupported binding schema")
        if binding["run_id"] != run["run_id"] or binding["controller_ref"] != run["controller_ref"]:
            raise NativeTreeError("binding does not match current run and controller")
        for key in ("role", "observation_ref", "selection_ref"):
            _text(binding[key], key)
        _generation(binding["generation"])
        relation = binding["relation"]
        if relation not in ("root", "child"):
            raise NativeTreeError("unsupported native relation")
        allowed = {"harness-context"} if relation == "root" else {"native-tool-result", "native-inventory"}
        if binding["source_kind"] not in allowed:
            raise NativeTreeError("binding requires supplied controller evidence")
        target = binding["native_target"]
        if target is None:
            if relation != "root":
                raise NativeTreeError("child requires a canonical native target")
        elif (not isinstance(target, str) or not target.startswith("/")
              or any(part in ("", ".", "..") for part in target[1:].split("/"))):
            raise NativeTreeError("native target must be a canonical absolute target")
        for key in optional & binding.keys():
            if binding[key] is not None:
                _text(binding[key], key)
        content = _canonical(binding)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            current = self.db.execute("SELECT generation, content FROM bindings WHERE role=? ORDER BY generation DESC LIMIT 1", (binding["role"],)).fetchone()
            if current is not None and binding["generation"] < current[0]:
                raise NativeTreeError("stale binding generation")
            actor_row = self.db.execute("SELECT generation FROM bindings WHERE role=? ORDER BY generation DESC LIMIT 1", (actor["role"],)).fetchone()
            if actor_row is None:
                bootstrap = (relation == "root" and binding["role"] == actor["role"]
                             and binding["generation"] == actor["generation"]
                             and self.db.execute("SELECT 1 FROM bindings LIMIT 1").fetchone() is None)
                if not bootstrap:
                    raise NativeTreeError("unbound actor may only bootstrap itself as root")
            elif actor_row[0] != actor["generation"]:
                raise NativeTreeError("actor binding generation is stale")
            pending_spawn = self.db.execute("SELECT command_id FROM commands WHERE action='spawn' AND role=? AND generation=?", (binding["role"], binding["generation"])).fetchall()
            if pending_spawn:
                if binding["source_kind"] != "native-tool-result":
                    raise NativeTreeError("spawn binding requires its recorded native launch result")
                matching = []
                for observed_content, mapped_content in self.db.execute("SELECT content, facts FROM observations"):
                    observed, mapped = json.loads(observed_content), json.loads(mapped_content)
                    if observed["evidence_ref"] != binding["observation_ref"]:
                        continue
                    launch, launch_row = self._command(observed["command_id"])
                    if (launch["action"] == "spawn" and launch_row[2]
                            and launch["recipient"] == {"role": binding["role"], "generation": binding["generation"]}
                            and launch["plan"]["selection_ref"] == binding["selection_ref"]
                            and observed["source_kind"] == "native-tool-result"
                            and observed["collected_by"] == observed["command_id"]
                            and mapped.get("native_target") == target):
                        matching.append(observed)
                if len(matching) != 1:
                    raise NativeTreeError("binding does not match one recorded claimed spawn result")
                if any(key in binding for key in ("agent_id", "session_id", "task_id")):
                    raise NativeTreeError("current spawn result exposes no separate native IDs")
            if current is not None and binding["generation"] == current[0]:
                if current[1] != content:
                    raise NativeTreeError("binding generation already has different immutable content")
                return {"created": False, "binding": json.loads(content)}
            active = self.db.execute("SELECT b.role, b.content FROM bindings b WHERE b.generation=(SELECT MAX(latest.generation) FROM bindings latest WHERE latest.role=b.role) AND NOT EXISTS (SELECT 1 FROM retirements r WHERE r.role=b.role AND r.generation=b.generation)").fetchall()
            for other_role, other_content in active:
                other = json.loads(other_content)
                if other_role != binding["role"]:
                    if relation == "root" and other["relation"] == "root":
                        raise NativeTreeError("run already has a root binding")
                    if target is not None and other["native_target"] == target:
                        raise NativeTreeError("native target already has an active role binding")
                elif other["relation"] != relation:
                    raise NativeTreeError("role native relation cannot change")
            self.db.execute("INSERT INTO bindings VALUES (?, ?, ?)", (binding["role"], binding["generation"], content))
        return {"created": True, "binding": json.loads(content)}

    def retire_role(self, role, generation, evidence_ref):
        """Withdraw a directory binding without stopping or releasing its work."""
        self._check_open()
        reference = {"role": role, "generation": generation}
        _role_ref(reference)
        _text(evidence_ref, "evidence_ref")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            existing = self.db.execute("SELECT content FROM retirements WHERE role=? AND generation=?", (role, generation)).fetchone()
            if existing is not None:
                if json.loads(existing[0])["evidence_ref"] != evidence_ref:
                    raise NativeTreeError("retirement already binds different evidence")
                return {"retired": False, "role": role, "generation": generation}
            self._binding(reference, allow_retired=True)
            self._binding(self.actor, allow_retired=True)
            record = {"run_id": self.run["run_id"], "role": role, "generation": generation,
                      "evidence_ref": evidence_ref, "recorded_by": self.actor}
            self.db.execute("INSERT INTO retirements VALUES (?, ?, ?)", (role, generation, _canonical(record)))
        return {"retired": True, "role": role, "generation": generation}

    def prepare(self, plan, action, role, generation, payload, mode):
        """Freeze one immutable command without performing a native action."""
        self._check_open()
        _shape(plan, {"schema", "run_id", "command_id", "plan_sha256", "request_sha256",
                      "authority_ref", "verification_contract_ref", "stop_ref"},
               {"assignment_id", "owner", "reply_to", "selection_ref", "predecessor_reconciliation_ref", "input_sha256", "assurance_minima"})
        if plan["schema"] != "native-tree-plan-v1" or plan["run_id"] != self.run["run_id"]:
            raise NativeTreeError("plan schema or run does not match")
        for key in ("command_id", "authority_ref", "verification_contract_ref", "stop_ref"):
            _text(plan[key], key)
        for key in ("plan_sha256", "request_sha256"):
            _sha(plan[key], key)
        if "input_sha256" in plan:
            _sha(plan["input_sha256"], "input_sha256")
        if "assurance_minima" in plan:
            _minima(plan["assurance_minima"])
        if plan["request_sha256"] != _digest(payload):
            raise NativeTreeError("request digest does not match payload")
        for key in ("selection_ref", "predecessor_reconciliation_ref"):
            if key in plan:
                _text(plan[key], key)
        work = action in ("spawn", "activate-or-steer")
        if work or {"assignment_id", "owner", "reply_to"} & plan.keys():
            if not {"assignment_id", "owner", "reply_to"} <= plan.keys():
                raise NativeTreeError("assigned work requires assignment, owner and reply recipient")
            _text(plan["assignment_id"], "assignment_id")
            _role_ref(plan["owner"])
            _role_ref(plan["reply_to"])
        if action == "spawn" and "selection_ref" not in plan:
            raise NativeTreeError("spawn requires a selection reference")
        if action in ("inspect", "wait"):
            if role is not None or generation is not None:
                raise NativeTreeError("inventory and wait are not addressed role operations")
            recipient_ref = None
        else:
            recipient_ref = {"role": role, "generation": generation}
            _role_ref(recipient_ref)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            existing = self.db.execute("SELECT content, command_sha256, outcome FROM commands WHERE command_id=?", (plan["command_id"],)).fetchone()
            if existing is not None:
                frozen = json.loads(existing[0])
                if _digest(frozen) != existing[1]:
                    raise NativeTreeError("stored command digest mismatch")
                requested = {"run": self.run, "actor": self.actor, "plan": plan, "action": action,
                             "recipient": recipient_ref, "payload": payload, "mode": mode}
                if _canonical({key: frozen[key] for key in requested}) != _canonical(requested):
                    raise NativeTreeError("command identity already binds different immutable content")
                return {"created": False, "command_id": plan["command_id"], "command_sha256": existing[1], "state": existing[2]}
            self._binding(self.actor)
            self._nonwork_correlation(action, plan)
            if "assignment_id" in plan:
                existing_assignment = self.db.execute("SELECT content FROM assignments WHERE assignment_id=?", (plan["assignment_id"],)).fetchone()
                if existing_assignment is not None:
                    frozen_assignment = json.loads(existing_assignment[0])
                    if "input_sha256" in plan and plan["input_sha256"] != _input_digest(frozen_assignment):
                        raise NativeTreeError("assignment business input identity cannot change")
                    if "assurance_minima" in plan and plan["assurance_minima"] != frozen_assignment.get("assurance_minima", {}):
                        raise NativeTreeError("assignment assurance minima cannot change")
            for key in ("owner", "reply_to"):
                if key in plan:
                    self._binding(plan[key])
            recipient = None
            if action == "spawn":
                current = self.db.execute("SELECT MAX(generation) FROM bindings WHERE role=?", (role,)).fetchone()[0]
                if current is not None and generation <= current:
                    raise NativeTreeError("spawn requires a new unbound role generation")
            elif recipient_ref is not None:
                recipient = self._binding(recipient_ref)
            call = _native_call(action, mode, payload, recipient)
            command = {"schema": "native-tree-command-v1", "run": self.run,
                       "actor": self.actor, "plan": plan, "action": action,
                       "recipient": recipient_ref, "native_target": None if recipient is None else recipient["native_target"],
                       "payload": payload, "mode": mode, "native_call": call}
            self._retry(command)
            content, command_digest = _canonical(command), _digest(command)
            if action == "spawn" and "predecessor_reconciliation_ref" not in plan and self.db.execute("SELECT 1 FROM commands WHERE action='spawn' AND role=? AND generation=?", (role, generation)).fetchone():
                raise NativeTreeError("spawn generation already has an immutable command")
            self.db.execute("INSERT INTO commands (command_id, content, command_sha256, role, generation, action) VALUES (?, ?, ?, ?, ?, ?)",
                            (plan["command_id"], content, command_digest, role, generation, action))
        return {"created": True, "command_id": plan["command_id"], "command_sha256": command_digest, "state": "prepared"}

    def _claim_decision(self, command, row, activities=None):
        """Read-only eligibility shared by claim and recovery inspection."""
        try:
            if command["actor"] != self.actor:
                raise NativeTreeError("command belongs to a different actor")
            self._binding(self.actor)
            if row[2]:
                return {"kind": "blocked", "reason": "already-claimed"}
            if command["run"] != self.run:
                raise NativeTreeError("command does not match current run and capabilities")
            action, plan, reference = command["action"], command["plan"], command["recipient"]
            self._nonwork_correlation(action, plan)
            if action == "spawn":
                current = self.db.execute("SELECT MAX(generation) FROM bindings WHERE role=?", (reference["role"],)).fetchone()[0]
                if current is not None and reference["generation"] <= current:
                    raise NativeTreeError("spawn generation is no longer unbound")
            elif reference is not None:
                recipient = self._binding(reference)
                if recipient["native_target"] != command["native_target"]:
                    raise NativeTreeError("command recipient target changed")
            for key in ("owner", "reply_to"):
                if key in plan:
                    self._binding(plan[key])
            retry = self._retry(command)
            if retry is not None and retry[1] is not None:
                return {"kind": "blocked", "reason": "retry-authorization-consumed"}
            new_assignment = None
            if action in ("spawn", "activate-or-steer"):
                assignment_id = plan["assignment_id"]
                existing = self.db.execute("SELECT content, state FROM assignments WHERE assignment_id=?", (assignment_id,)).fetchone()
                assignment = {"assignment_id": assignment_id, "run_id": plan["run_id"],
                              "recipient": reference, "native_target": command["native_target"],
                              "owner": plan["owner"], "reply_to": plan["reply_to"],
                              "plan_sha256": plan["plan_sha256"], "request_sha256": plan["request_sha256"],
                              "input_sha256": plan.get("input_sha256", plan["request_sha256"]),
                              "assurance_minima": plan.get("assurance_minima", {}),
                              "authority_ref": plan["authority_ref"], "verification_contract_ref": plan["verification_contract_ref"], "stop_ref": plan["stop_ref"]}
                if existing is not None:
                    prior = json.loads(existing[0])
                    prior.setdefault("input_sha256", prior["request_sha256"])
                    prior.setdefault("assurance_minima", {})
                    assignment["input_sha256"] = plan.get("input_sha256", _input_digest(prior))
                    assignment["assurance_minima"] = plan.get("assurance_minima", prior.get("assurance_minima", {}))
                    stable = set(assignment) - {"request_sha256", "native_target"}
                    address_matches = command["native_target"] is None or command["native_target"] in self._assignment_targets(assignment_id)
                    if existing[1] != "unresolved" or not address_matches or any(prior[key] != assignment[key] for key in stable):
                        raise NativeTreeError("assignment identity already binds different work or mode")
                    if retry is not None:
                        latest = None
                        for prior_content, in self.db.execute("SELECT content FROM commands WHERE claimed=1 ORDER BY claim_sequence"):
                            prior_command = json.loads(prior_content)
                            if prior_command["action"] in ("spawn", "activate-or-steer") and prior_command["plan"].get("assignment_id") == assignment_id:
                                latest = prior_command["plan"]["command_id"]
                        if latest != retry[0]["command_id"]:
                            raise NativeTreeError("retry does not reference latest unchanged assignment attempt")
                        if retry[0]["evidence"]["basis"] == "nondelivery-established":
                            for facts_content, in self.db.execute("SELECT facts FROM observations"):
                                report = json.loads(facts_content).get("worker_result")
                                if report is not None and report["assignment_id"] == assignment_id:
                                    raise NativeTreeError("late result conflicts with nondelivery retry")
                    elif command["mode"] not in ("continue", "steer"):
                        raise NativeTreeError("new attempt requires explicit retry authorization")
                    elif not self._continuation_observed(command):
                        raise NativeTreeError("continuation requires causally current native-state evidence or reconciliation")
                else:
                    if retry is not None:
                        raise NativeTreeError("retry requires its original assignment")
                    if command["mode"] in ("continue", "steer"):
                        raise NativeTreeError("continuation requires an existing unresolved assignment")
                    new_assignment = assignment
                if activities is None:
                    activities = self._activity_view()
                for activity in activities:
                    if activity["assignment_id"] == assignment_id or not activity["blocking"]:
                        continue
                    target_collision = command["native_target"] is not None and activity["native_target"] == command["native_target"]
                    unknown_incarnation = activity["native_target"] is None and activity["recipient"] == reference
                    if target_collision or unknown_incarnation:
                        return {"kind": "blocked", "reason": "child-reserved"}
            return {"kind": "ready", "reason": "new-claim", "new_assignment": new_assignment, "retry": retry}
        except NativeTreeError as error:
            return {"kind": "invalid", "reason": str(error)}

    def claim(self, command_id):
        """Commit uncertainty before returning an exact native call once."""
        self._check_open()
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            command, row = self._command(command_id)
            decision = self._claim_decision(command, row)
            if decision["kind"] == "invalid":
                raise NativeTreeError(decision["reason"])
            if decision["kind"] == "blocked":
                return {"claimed": False, "command_id": command_id, "state": row[3], "reason": decision["reason"]}
            assignment = decision["new_assignment"]
            if assignment is not None:
                reference = assignment["recipient"]
                self.db.execute("INSERT INTO assignments (assignment_id,content,role,generation,native_target,state) VALUES (?, ?, ?, ?, ?, 'unresolved')",
                                (assignment["assignment_id"], _canonical(assignment), reference["role"], reference["generation"], assignment["native_target"]))
            sequence = self.db.execute("SELECT COALESCE(MAX(claim_sequence),0)+1 FROM commands").fetchone()[0]
            self.db.execute("UPDATE commands SET claimed=1, claim_actor=?, outcome='unknown', claim_sequence=? WHERE command_id=?",
                            (self._actor_content, sequence, command_id))
            if decision["retry"] is not None:
                self.db.execute("UPDATE reconciliations SET consumed_by=? WHERE reconciliation_id=? AND consumed_by IS NULL",
                                (command_id, decision["retry"][0]["reconciliation_id"]))
        return {"claimed": True, "command_id": command_id, "state": "unknown", "reason": "new-claim", "native_call": command["native_call"]}

    def observe(self, command_id, raw_observation, source_kind):
        """Retain source-tagged observations and map only supported facts."""
        self._check_open()
        if type(source_kind) is not str or source_kind not in _OBSERVATION_SOURCES:
            raise NativeTreeError("unsupported observation source")
        _shape(raw_observation, {"observation_id", "raw", "evidence_ref"}, {"collected_by"})
        for key in ("observation_id", "evidence_ref"):
            _text(raw_observation[key], key)
        raw_snapshot = json.loads(_canonical(raw_observation["raw"]))
        collected_by = raw_observation.get("collected_by")
        if collected_by is not None:
            _text(collected_by, "collected_by")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            command, row = self._command(command_id)
            if not row[2]:
                raise NativeTreeError("observation requires a claimed subject command")
            collector_id = collected_by
            if source_kind == "native-tool-result":
                if collector_id is not None and collector_id != command_id:
                    raise NativeTreeError("native tool result must belong to its collecting command")
                collector_id = command_id
            if collector_id is not None:
                collector, collector_row = self._command(collector_id)
                if not collector_row[2]:
                    raise NativeTreeError("observation collector must be claimed")
                if collector["actor"] != self.actor:
                    raise NativeTreeError("observation collector belongs to another actor")
                if source_kind == "native-inventory" and collector["action"] != "inspect":
                    raise NativeTreeError("native inventory requires an inspect collection command")
            existing = self.db.execute("SELECT content FROM observations WHERE observation_id=?", (raw_observation["observation_id"],)).fetchone()
            recorded_after = (json.loads(existing[0]).get("recorded_after_claim_sequence", 0) if existing is not None
                              else self.db.execute("SELECT COALESCE(MAX(claim_sequence),0) FROM commands").fetchone()[0])
            observation = {"observation_id": raw_observation["observation_id"],
                           "command_id": command_id, "run_id": self.run["run_id"],
                           "controller_ref": self.run["controller_ref"],
                           "source_kind": source_kind, "evidence_ref": raw_observation["evidence_ref"],
                           "recorded_by": self.actor,
                           "raw": raw_snapshot, "raw_sha256": _digest(raw_snapshot),
                           "collected_by": collector_id, "mapping_revision": _MAPPING_REVISION,
                           "recorded_after_claim_sequence": recorded_after}
            content = _canonical(observation)
            if existing is not None:
                if existing[0] != content:
                    raise NativeTreeError("observation identity already binds different content or provenance")
                return {"created": False, "observation_id": observation["observation_id"], "command_id": command_id, "state": row[3]}
            facts = self._observation_facts(command, source_kind, raw_snapshot)
            if "owner_verification" in facts and raw_snapshot["evidence_ref"] != observation["evidence_ref"]:
                facts = {}
            self.db.execute("INSERT INTO observations (observation_id, command_id, content, facts) VALUES (?, ?, ?, ?)",
                            (observation["observation_id"], command_id, content, _canonical(facts)))
        return {"created": True, "observation_id": observation["observation_id"], "command_id": command_id, "state": row[3]}

    def inspect(self, run_id, role_or_command=None):
        """Read local state without querying the native controller."""
        self._check_open()
        if run_id != self.run["run_id"]:
            raise NativeTreeError("inspection run does not match")
        if role_or_command is not None:
            _text(role_or_command, "role_or_command")
        with self.db:
            self.db.execute("BEGIN")
            activities = self._activity_view()
            bindings = [json.loads(row[0]) for row in self.db.execute("SELECT content FROM bindings ORDER BY role,generation")]
            for binding in bindings:
                retirement = self.db.execute("SELECT content FROM retirements WHERE role=? AND generation=?", (binding["role"], binding["generation"])).fetchone()
                binding["retired"] = retirement is not None
                if retirement is not None:
                    binding["retirement"] = json.loads(retirement[0])
            commands, next_actions, blocked_actions = [], [], []
            for command_id, content, command_digest, claimed, outcome in self.db.execute("SELECT command_id, content, command_sha256, claimed, outcome FROM commands ORDER BY rowid"):
                command = json.loads(content)
                reference = command["recipient"]
                if role_or_command is not None and command_id != role_or_command and (reference is None or reference["role"] != role_or_command):
                    continue
                _, stored_row = self._command(command_id)
                decision = self._claim_decision(command, stored_row, activities)
                command["claim_eligibility"] = {"eligible": decision["kind"] == "ready", "reason": decision["reason"]}
                if decision["kind"] == "ready":
                    next_actions.append({"command_id": command_id, "operation": "claim"})
                elif not claimed:
                    blocked_actions.append({"command_id": command_id, "operation": "claim", "reason": decision["reason"]})
                if claimed:
                    next_actions.append({"command_id": command_id, "operation": "observe"})
                    if "assignment_id" in command["plan"]:
                        try:
                            pending, pending_row = self._assignment(command["plan"]["assignment_id"])
                            self._owner(pending, require_recipient=False, allow_retired_owner=True)
                        except NativeTreeError:
                            pass
                        else:
                            if pending_row[1] == "unresolved":
                                next_actions.append({"command_id": command_id, "operation": "reconcile"})
                if "assignment_id" in command["plan"]:
                    established = self.db.execute("SELECT 1 FROM assignments WHERE assignment_id=?", (command["plan"]["assignment_id"],)).fetchone() is not None
                    command["assignment_correlation"] = {"assignment_id": command["plan"]["assignment_id"], "established": established}
                command.pop("native_call")
                command.update(command_id=command_id, command_sha256=command_digest,
                               claimed=bool(claimed), state=outcome, observations=[])
                for observed_content, facts in self.db.execute("SELECT content, facts FROM observations WHERE command_id=? ORDER BY sequence", (command_id,)):
                    observation = json.loads(observed_content)
                    observation["facts"] = json.loads(facts)
                    command["observations"].append(observation)
                commands.append(command)
            assignments = []
            for content, target, state, busy, acceptance in self.db.execute("SELECT content, native_target, state, native_busy, acceptance FROM assignments ORDER BY rowid"):
                assignment = json.loads(content)
                related = [item for item in activities if item["assignment_id"] == assignment["assignment_id"]]
                targets = sorted({item["native_target"] for item in related if item["native_target"] is not None})
                assignment.setdefault("input_sha256", assignment["request_sha256"])
                assignment.update(native_target=targets[0] if len(targets) == 1 else None,
                                  native_targets=targets, state=state, native_busy=any(item["blocking"] for item in related),
                                  acceptance=None if acceptance is None else json.loads(acceptance))
                frozen_assignment, assignment_row = self._assignment(assignment["assignment_id"])
                assignment["evidence"] = self._assignment_evidence(frozen_assignment, assignment_row)
                assignments.append(assignment)
            command_ids = {item["command_id"] for item in commands}
            assignment_ids = {item["plan"]["assignment_id"] for item in commands if "assignment_id" in item["plan"]}
            predecessor_refs = {item["plan"]["predecessor_reconciliation_ref"] for item in commands if "predecessor_reconciliation_ref" in item["plan"]}
            reconciliations = []
            for content, consumed_by in self.db.execute("SELECT content, consumed_by FROM reconciliations ORDER BY rowid"):
                reconciliation = json.loads(content)
                if (role_or_command is None or reconciliation["command_id"] in command_ids
                        or reconciliation["assignment_id"] in assignment_ids
                        or reconciliation["reconciliation_id"] in predecessor_refs):
                    reconciliation["consumed_by"] = consumed_by
                    reconciliations.append(reconciliation)
        return {"run_id": run_id, "bindings": bindings, "commands": commands,
                "assignments": assignments, "activities": activities, "reconciliations": reconciliations,
                "missing_evidence": [{"command_id": item["command_id"], "kind": "native-outcome"}
                                     for item in commands if item["claimed"] and item["state"] == "unknown"],
                "next_actions": next_actions, "blocked_actions": blocked_actions}

    def accept(self, assignment_id, generation, result_digest, verification_ref):
        """Record the current immutable owner's verified result acceptance."""
        self._check_open()
        _generation(generation)
        _sha(result_digest, "result_digest")
        _text(verification_ref, "verification_ref")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            assignment, row = self._assignment(assignment_id)
            self._owner(assignment)
            if generation != assignment["recipient"]["generation"]:
                raise NativeTreeError("acceptance recipient generation does not match")
            acceptance = {"run_id": self.run["run_id"], "assignment_id": assignment_id,
                          "generation": generation, "owner": self.actor,
                          "input_digest": _input_digest(assignment),
                          "result_digest": result_digest, "verification_ref": verification_ref}
            content = _canonical(acceptance)
            if row[5] is not None:
                if row[5] != content:
                    raise NativeTreeError("acceptance already binds a different result or verification")
                return {"accepted": False, "assignment_id": assignment_id, "result_digest": result_digest}
            if row[1] != "unresolved":
                raise NativeTreeError("assignment is already closed")
            expected = {key: acceptance[key] for key in ("assignment_id", "generation", "input_digest", "result_digest")}
            results, verifications = [], []
            for observation_content, facts_content in self.db.execute("SELECT content, facts FROM observations ORDER BY sequence"):
                observation, facts = json.loads(observation_content), json.loads(facts_content)
                if facts.get("worker_result") == expected:
                    results.append(observation)
                if observation["evidence_ref"] == verification_ref:
                    verified = facts.get("owner_verification")
                    if (verified is not None and observation["source_kind"] == "owner-verification"
                            and observation["recorded_by"] == self.actor
                            and verified == {**expected, "usable": True, "evidence_ref": verification_ref}):
                        verifications.append(observation)
                    else:
                        raise NativeTreeError("verification reference is conflicting or unusable")
            if not results or not verifications:
                raise NativeTreeError("acceptance requires correlated result and owner verification")
            evidence = self._assignment_evidence(assignment, row, selected_digest=result_digest)
            if evidence["missing_minima"]:
                raise NativeTreeError("acceptance does not meet frozen assurance minima")
            sequence = self.db.execute("SELECT COALESCE(MAX(claim_sequence),0) FROM commands").fetchone()[0]
            self.db.execute("UPDATE assignments SET state='accepted', acceptance=?, closure_sequence=? WHERE assignment_id=?",
                            (content, sequence, assignment_id))
        return {"accepted": True, "assignment_id": assignment_id, "result_digest": result_digest}

    def reconcile(self, command_id, disposition, evidence):
        """Preserve an uncertain claim and its explicit owner disposition."""
        self._check_open()
        if disposition not in {"keep-unknown", "use-observed-result", "abandon", "authorize-new-attempt"}:
            raise NativeTreeError("unsupported reconciliation disposition")
        _shape(evidence, {"reconciliation_id", "decision_ref", "evidence_ref"}, {"basis"})
        for key in evidence:
            _text(evidence[key], key)
        if disposition == "authorize-new-attempt" and evidence.get("basis") not in {"nondelivery-established", "duplicate-risk-accepted"}:
            raise NativeTreeError("retry requires an explicit supported evidence basis")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            command, row = self._command(command_id)
            if not row[2] or "assignment_id" not in command["plan"]:
                raise NativeTreeError("reconciliation requires a claimed assignment command")
            assignment, assignment_row = self._assignment(command["plan"]["assignment_id"])
            self._owner(assignment, require_recipient=False, allow_retired_owner=True)
            reconciliation = {"reconciliation_id": evidence["reconciliation_id"],
                              "command_id": command_id, "command_sha256": row[1],
                              "run_id": self.run["run_id"], "controller_ref": self.run["controller_ref"],
                              "assignment_id": assignment["assignment_id"], "owner": self.actor,
                              "disposition": disposition, "evidence": evidence}
            content = _canonical(reconciliation)
            existing = self.db.execute("SELECT content FROM reconciliations WHERE reconciliation_id=?", (evidence["reconciliation_id"],)).fetchone()
            if existing is not None:
                if existing[0] != content:
                    raise NativeTreeError("reconciliation identity already binds different content")
                return {"created": False, "reconciliation_id": evidence["reconciliation_id"], "command_id": command_id, "disposition": disposition}
            if assignment_row[1] != "unresolved":
                raise NativeTreeError("cannot reconcile a closed assignment")
            if disposition == "authorize-new-attempt":
                if self.db.execute("SELECT 1 FROM reconciliations WHERE command_id=? AND disposition='authorize-new-attempt'", (command_id,)).fetchone():
                    raise NativeTreeError("predecessor already has a retry authorization")
                latest = None
                progress = False
                for prior_content, in self.db.execute("SELECT content FROM commands WHERE claimed=1 ORDER BY claim_sequence"):
                    prior = json.loads(prior_content)
                    if prior["action"] in ("spawn", "activate-or-steer") and prior["plan"].get("assignment_id") == assignment["assignment_id"]:
                        latest = prior["plan"]["command_id"]
                for facts_content, in self.db.execute("SELECT facts FROM observations"):
                    report = json.loads(facts_content).get("worker_result")
                    progress |= report is not None and report["assignment_id"] == assignment["assignment_id"]
                if latest != command_id or (progress and evidence["basis"] == "nondelivery-established"):
                    raise NativeTreeError("retry conflicts with the latest attempt or recorded progress")
            if disposition == "use-observed-result":
                if not any(json.loads(facts).get("worker_result", {}).get("assignment_id") == assignment["assignment_id"] for facts, in self.db.execute("SELECT facts FROM observations")):
                    raise NativeTreeError("no correlated result to reconcile")
            self.db.execute("INSERT INTO reconciliations (reconciliation_id,command_id,disposition,content) VALUES (?, ?, ?, ?)",
                            (evidence["reconciliation_id"], command_id, disposition, content))
            if disposition == "abandon":
                sequence = self.db.execute("SELECT COALESCE(MAX(claim_sequence),0) FROM commands").fetchone()[0]
                self.db.execute("UPDATE assignments SET state='abandoned', closure_sequence=? WHERE assignment_id=?", (sequence, assignment["assignment_id"]))
        return {"created": True, "reconciliation_id": evidence["reconciliation_id"], "command_id": command_id, "disposition": disposition}


__all__ = ["NativeTree", "NativeTreeError"]


def _read_json(raw):
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise NativeTreeError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid_constant(value):
        raise NativeTreeError(f"nonfinite JSON constant: {value}")

    value = json.loads(raw, object_pairs_hook=unique_object, parse_constant=invalid_constant)
    _canonical(value)
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description="Plan and record native-tree operations without executing native tools.")
    parser.add_argument("--store", required=True, type=Path)
    parser.add_argument("--context", required=True, type=Path, help="UTF-8 JSON containing run and actor")
    parser.add_argument("--create", action="store_true", help="exclusively create a store while binding its initial root")
    arguments = parser.parse_args(argv)
    try:
        # Decode every input and reject duplicate/unknown operation keys before
        # opening even a newly requested store.
        context = _read_json(arguments.context.read_bytes().decode("utf-8"))
        request = _read_json(sys.stdin.buffer.read().decode("utf-8"))
        _shape(context, {"run", "actor"})
        if not isinstance(request, dict):
            raise NativeTreeError("operation request must be a JSON object")
        operation = request.get("operation")
        if type(operation) is not str:
            raise NativeTreeError("operation must be a string")
        fields = {
            "bind-role": ({"binding"}, set()),
            "retire-role": ({"role", "generation", "evidence_ref"}, set()),
            "prepare": ({"plan", "action", "role", "generation", "payload", "mode"}, set()),
            "prepare-claim": ({"plan", "action", "role", "generation", "payload", "mode"}, set()),
            "claim": ({"command_id"}, set()),
            "observe": ({"command_id", "raw_observation", "source_kind"}, set()),
            "observe-inspect": ({"command_id", "raw_observation", "source_kind"}, {"role_or_command"}),
            "inspect": ({"run_id"}, {"role_or_command"}),
            "accept": ({"assignment_id", "generation", "result_digest", "verification_ref"}, set()),
            "reconcile": ({"command_id", "disposition", "evidence"}, set()),
        }
        if operation not in fields:
            raise NativeTreeError("unsupported operation")
        required, optional = fields[operation]
        _shape(request, required | {"operation"}, optional)
        if arguments.create and operation != "bind-role":
            raise NativeTreeError("--create requires an initial bind-role operation")
        with NativeTree(arguments.store, run=context["run"], actor=context["actor"], create=arguments.create) as tree:
            if operation == "bind-role":
                result = tree.bind_role(request["binding"])
            elif operation == "retire-role":
                result = tree.retire_role(request["role"], request["generation"], request["evidence_ref"])
            elif operation in ("prepare", "prepare-claim"):
                prepared = tree.prepare(*(request[key] for key in ("plan", "action", "role", "generation", "payload", "mode")))
                result = prepared if operation == "prepare" else tree.claim(prepared["command_id"])
                if operation == "prepare-claim":
                    result["command_sha256"] = prepared["command_sha256"]
            elif operation == "claim":
                result = tree.claim(request["command_id"])
            elif operation in ("observe", "observe-inspect"):
                observed = tree.observe(request["command_id"], request["raw_observation"], request["source_kind"])
                result = observed if operation == "observe" else {
                    "observation": observed,
                    "snapshot": tree.inspect(tree.run["run_id"], request.get("role_or_command", request["command_id"])),
                }
            elif operation == "inspect":
                result = tree.inspect(request["run_id"], request.get("role_or_command"))
            elif operation == "accept":
                result = tree.accept(*(request[key] for key in ("assignment_id", "generation", "result_digest", "verification_ref")))
            else:
                result = tree.reconcile(request["command_id"], request["disposition"], request["evidence"])
        output = _canonical(result)
    except (ValueError, TypeError, OSError, sqlite3.Error, UnicodeError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=True), file=sys.stderr)
        return 2
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
