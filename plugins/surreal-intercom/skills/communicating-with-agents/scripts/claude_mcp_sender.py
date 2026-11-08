#!/usr/bin/env python3
"""Submit one peer envelope through an explicitly nominated stdio MCP child.

This source profile uses synthetic MCP 2024-11-05 negotiation; live peer
negotiation remains unqualified. Submission never establishes receiver receipt.
The target is a caller nomination, not authentication or permission.
operation_seconds bounds protocol I/O and graceful shutdown. Reaping after
killing the owned child may exceed it; no descendant closure is asserted.
"""
import argparse
import json
import math
import os
import selectors
import sqlite3
import subprocess
import time

from native_codex_mailbox import Mailbox, MailboxError, text
from peer_message import serialize_peer_message


class InspectionError(ValueError):
    pass


def validate(request):
    required = {
        "message_id", "attempt_id", "actor", "recipient", "target",
        "command", "evidence_ref", "limits",
    }
    if not isinstance(request, dict) or request.keys() != required:
        raise InspectionError("invalid_request")
    for key in ("message_id", "attempt_id", "evidence_ref"):
        text(request[key], key)
    if len(json.dumps(request["attempt_id"], ensure_ascii=True)) > 256:
        raise InspectionError("attempt_id_limit")
    for key in ("actor", "recipient"):
        identity = request[key]
        if not isinstance(identity, dict) or identity.keys() != {"thread_id", "host_id"}:
            raise InspectionError("invalid_identity")
        for field in ("thread_id", "host_id"):
            text(identity[field], field)
    target = request["target"]
    if not isinstance(target, str) or not target.startswith("uds:") or not target[4:]:
        raise InspectionError("invalid_nomination")
    command = request["command"]
    if (
        not isinstance(command, list) or not command
        or any(not isinstance(item, str) or "\0" in item for item in command)
        or not os.path.isabs(command[0])
    ):
        raise InspectionError("invalid_command")
    limits = request["limits"]
    if not isinstance(limits, dict) or limits.keys() != {
        "operation_seconds", "stdout_bytes", "stderr_bytes",
    }:
        raise InspectionError("invalid_limits")
    seconds = limits["operation_seconds"]
    if (
        type(seconds) not in (int, float) or not 0 < seconds <= 60
        or not math.isfinite(seconds)
    ):
        raise InspectionError("invalid_limits")
    for key in ("stdout_bytes", "stderr_bytes"):
        if type(limits[key]) is not int or not 1 <= limits[key] <= 1048576:
            raise InspectionError("invalid_limits")


def encoded_frame(value):
    data = json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode() + b"\n"
    # A source-profile ceiling for atomic Linux pipe writes, not a native peer limit.
    if len(data) > 4096:
        raise InspectionError("control_frame_limit")
    return data


# Recognized literal profile only: never evaluate arbitrary schema patterns.
DESTINATION_CONSTRAINTS = [
    {"pattern": r"^[^\n\r]*$"},
    {"pattern": r"^[\s\S]{0,300}$"},
]


def supports_sendmessage(tool):
    schema = tool["inputSchema"]
    properties = schema.get("properties")
    required = schema.get("required")
    if (
        not schema.keys() <= {
            "type", "properties", "required", "additionalProperties", "title", "description", "$schema",
        }
        or schema.get("$schema", "https://json-schema.org/draft/2020-12/schema")
        != "https://json-schema.org/draft/2020-12/schema"
        or schema.get("type") != "object"
        or not isinstance(properties, dict)
        or not {"to", "message"} <= properties.keys()
        or any(not isinstance(value, dict) for value in properties.values())
        or not isinstance(required, list) or len(required) != 2
        or any(not isinstance(item, str) for item in required)
        or set(required) != {"to", "message"}
        or schema.get("additionalProperties") is not False
        or any(
            name in schema and not isinstance(schema[name], str)
            for name in ("title", "description")
        )
    ):
        return False
    return all(
        properties[name].keys() <= (
            {"type", "title", "description", "default", "allOf"}
            if name == "to" else {"type", "title", "description", "default"}
        )
        and ("allOf" not in properties[name] or properties[name]["allOf"] == DESTINATION_CONSTRAINTS)
        and properties[name].get("type") == "string"
        and all(
            annotation not in properties[name]
            or isinstance(properties[name][annotation], str)
            for annotation in ("title", "description")
        )
        for name in ("to", "message")
    )


def destination_violation(tool, target):
    if "allOf" not in tool["inputSchema"]["properties"]["to"]:
        return None
    if "\r" in target or "\n" in target:
        return "Destination contains CR/LF."
    # Conservative source limit: astral characters consume two UTF-16 code units.
    if sum(2 if ord(character) > 0xFFFF else 1 for character in target) > 300:
        return "Destination exceeds the supported 300 UTF-16 code units."
    return None


def supported_tool_result(result):
    # This slice supports only MCP text content; other content stays unknown.
    return (
        result.keys() <= {"content", "isError", "_meta"}
        and isinstance(result.get("content"), list)
        and ("isError" not in result or type(result["isError"]) is bool)
        and ("_meta" not in result or isinstance(result["_meta"], dict))
        and all(
            isinstance(item, dict) and item.keys() == {"type", "text"}
            and item["type"] == "text" and isinstance(item["text"], str)
            for item in result["content"]
        )
    )


class StdioMcpChild:
    """One owned child; byte counts cover only this invocation's pipe reads."""

    def __init__(self, limits, deadline):
        self.deadline = deadline
        self.limits = limits
        self.counts = {"stdout": 0, "stderr": 0}
        self.buffer = bytearray()
        self.selector = selectors.DefaultSelector()
        self.process = None

    def start(self, command):
        if time.monotonic() >= self.deadline:
            raise InspectionError("deadline")
        self.process = subprocess.Popen(
            command, shell=False, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0,
        )
        for name in ("stdout", "stderr"):
            stream = getattr(self.process, name)
            os.set_blocking(stream.fileno(), False)
            self.selector.register(stream, selectors.EVENT_READ, name)
        os.set_blocking(self.process.stdin.fileno(), False)

    def send(self, value):
        if time.monotonic() >= self.deadline:
            raise InspectionError("deadline")
        data = encoded_frame(value)
        try:
            count = os.write(self.process.stdin.fileno(), data)
        except (OSError, ValueError) as error:
            raise InspectionError("control_write_failed") from error
        if count != len(data):
            raise InspectionError("control_write_failed")

    def pump(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise InspectionError("deadline")
        events = self.selector.select(remaining)
        if not events:
            raise InspectionError("deadline")
        for key, _ in events:
            name = key.data
            available = self.limits[name + "_bytes"] - self.counts[name]
            try:
                data = os.read(key.fileobj.fileno(), min(4096, available + 1))
            except BlockingIOError:
                continue
            self.counts[name] += len(data)
            if self.counts[name] > self.limits[name + "_bytes"]:
                raise InspectionError(name + "_limit")
            if not data:
                self.selector.unregister(key.fileobj)
            elif name == "stdout":
                self.buffer.extend(data)

    def reply(self, identity):
        while True:
            if b"\n" in self.buffer:
                line, _, rest = self.buffer.partition(b"\n")
                self.buffer = bytearray(rest)
                try:
                    value = json.loads(line)
                except (ValueError, UnicodeError) as error:
                    raise InspectionError("invalid_jsonrpc") from error
                if (
                    not isinstance(value, dict) or value.get("jsonrpc") != "2.0"
                    or type(value.get("id")) is not int or value["id"] != identity
                    or "error" in value or not isinstance(value.get("result"), dict)
                ):
                    raise InspectionError("invalid_jsonrpc")
                return value["result"]
            if not any(key.data == "stdout" for key in self.selector.get_map().values()):
                raise InspectionError("stdout_eof")
            self.pump()

    def close(self):
        process = self.process
        if process is None:
            self.selector.close()
            return {"started": False, "reaped": False, "exit_code": None}
        closure_error = None
        try:
            process.stdin.close()
            while self.selector.get_map():
                self.pump()
            remaining = max(0, self.deadline - time.monotonic())
            process.wait(timeout=remaining)
        except (InspectionError, OSError, ValueError, subprocess.TimeoutExpired) as error:
            closure_error = str(error) if isinstance(error, InspectionError) else "closure_failed"
            if process.poll() is None:
                process.kill()
            # Reap only the process created by this invocation, never a group.
            process.wait()
        finally:
            for stream in (process.stdout, process.stderr):
                stream.close()
            self.selector.close()
        closure = {"started": True, "reaped": True, "exit_code": process.returncode}
        if closure_error is not None:
            closure["closure_error"] = closure_error
        return closure


def initialize_mcp(child):
    child.send({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "provingkit-catalog-inspector", "version": "1"},
        },
    })
    initialized = child.reply(1)
    if (
        initialized.get("protocolVersion") != "2024-11-05"
        or not isinstance(initialized.get("capabilities"), dict)
        or not isinstance(initialized["capabilities"].get("tools"), dict)
    ):
        raise InspectionError("incompatible_initialize")
    child.send({"jsonrpc": "2.0", "method": "notifications/initialized"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", required=True)
    parser.add_argument("--request", required=True, help="explicit trusted local UTF-8 JSON request file path")
    arguments = parser.parse_args()
    result = {
        "stage": "request", "reason": "invalid_request", "claimed": False,
        "peer_input": "not_attempted",
        "owned_child": {"started": False, "reaped": False, "exit_code": None},
    }
    mailbox = None
    child = None
    try:
        with open(arguments.request, "rb", buffering=0) as request_file:
            request_bytes = request_file.read(32769)
        if len(request_bytes) > 32768:
            raise InspectionError("request_limit")
        request = json.loads(request_bytes.decode("utf-8"))
        validate(request)
        deadline = time.monotonic() + request["limits"]["operation_seconds"]
        result["stage"] = "claim"
        mailbox = Mailbox(arguments.store)
        planned = mailbox.get(request["message_id"])
        if planned["recipient"] != request["recipient"]:
            raise InspectionError("recipient_mismatch")
        claim = mailbox.claim(request["message_id"], request["attempt_id"], request["actor"])
        result["claimed"] = claim["claimed"] is True
        result["attempt_id"] = request["attempt_id"]
        if not result["claimed"]:
            result["reason"] = "claim_not_acquired"
        else:
            # Commit bound uncertainty before launching any external process.
            mailbox.observe(
                request["message_id"], request["attempt_id"], "unknown",
                request["evidence_ref"], json.dumps(request, ensure_ascii=True, sort_keys=True),
            )
            result["stage"] = "startup"
            child = StdioMcpChild(request["limits"], deadline)
            child.start(request["command"])
            result["stage"] = "initialize"
            initialize_mcp(child)
            result["stage"] = "catalog"
            child.send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
            catalog = child.reply(2)
            tools = catalog.get("tools")
            if not isinstance(tools, list) or any(
                not isinstance(tool, dict) or not isinstance(tool.get("name"), str)
                or not isinstance(tool.get("inputSchema"), dict) for tool in tools
            ):
                raise InspectionError("invalid_catalog")
            if catalog.get("nextCursor") is not None:
                raise InspectionError("incomplete_catalog")
            nominated = [tool for tool in tools if tool["name"] == "SendMessage"]
            if nominated and (len(nominated) != 1 or not supports_sendmessage(nominated[0])):
                mailbox.observe(
                    request["message_id"], request["attempt_id"], "refused",
                    request["evidence_ref"],
                    "SendMessage schema is outside the supported to/message string profile; no tools/call was sent.",
                )
                result["reason"] = "unsupported_sendmessage_schema"
            elif nominated and (violation := destination_violation(nominated[0], request["target"])):
                mailbox.observe(
                    request["message_id"], request["attempt_id"], "refused",
                    request["evidence_ref"], violation + " No tools/call was sent.",
                )
                result["reason"] = "destination_constraint_violation"
            elif nominated:
                message = {
                    key: value for key, value in planned.items()
                    if key not in {"attempts", "state"}
                }
                call = {
                    "jsonrpc": "2.0", "id": 3, "method": "tools/call",
                    "params": {
                        "name": "SendMessage",
                        "arguments": {
                            "to": request["target"],
                            "message": serialize_peer_message(message, request["actor"]),
                        },
                    },
                }
                # Refuse oversized frames before persisting possible submission.
                encoded_frame(call)
                result["stage"] = "call"
                mailbox.observe(
                    request["message_id"], request["attempt_id"], "unknown",
                    request["evidence_ref"], json.dumps({
                        "phase": "possible_submission", "target": request["target"],
                    }, ensure_ascii=True, sort_keys=True),
                )
                # Once writing may begin, every uncertainty remains non-replayable.
                result["peer_input"] = "possible_submission"
                child.send(call)
                tool_result = child.reply(3)
                supported = supported_tool_result(tool_result)
                submitted = supported and not tool_result.get("isError", False)
                mailbox.observe(
                    request["message_id"], request["attempt_id"],
                    "submitted" if submitted else "unknown",
                    request["evidence_ref"], json.dumps({
                        "target": request["target"], "tool_result": tool_result,
                    }, ensure_ascii=True, sort_keys=True),
                )
                if submitted:
                    result["peer_input"] = "submitted"
                    result["reason"] = "submitted"
                else:
                    result["reason"] = "tool_error" if supported else "unsupported_tool_result"
            else:
                mailbox.observe(
                    request["message_id"], request["attempt_id"], "refused",
                    request["evidence_ref"],
                    "Complete tools/list catalog has no SendMessage; no tools/call was sent.",
                )
                result["reason"] = "missing_sendmessage"
    except InspectionError as error:
        result["reason"] = str(error)
    except (ValueError, RecursionError, OSError, sqlite3.Error, MailboxError):
        result["reason"] = "local_or_protocol_failure"
    finally:
        if child is not None:
            result["owned_child"] = child.close()
        if mailbox is not None:
            mailbox.close()
    # Fixed vocabulary and a bounded request keep this single result bounded.
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
