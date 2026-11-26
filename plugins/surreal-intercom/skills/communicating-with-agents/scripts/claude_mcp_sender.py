#!/usr/bin/env python3
"""Submit one peer envelope through an owned stdio `claude mcp serve` child.

A request addresses its recipient either by name, resolved in this attempt's
own `ListAgents` listing, or by a recipient-prepared `uds:` route that the
caller supplies. This source profile uses MCP 2024-11-05 negotiation; the
listing profile is limited to the observed Claude Desktop layout.
Submission never establishes receiver receipt. A name or route is a caller
nomination, not authentication or permission. operation_seconds bounds
protocol I/O and the wait after closing the child's input; the signal steps
that follow, and reaping, may exceed it. No descendant closure is asserted.
"""
import argparse
from collections import Counter
import json
import math
import os
import re
import selectors
import sqlite3
import subprocess
import time

from native_codex_mailbox import Mailbox, MailboxError, text
from peer_message import serialize_peer_message


class InspectionError(ValueError):
    pass


class PathRefusal(Exception):
    """A definite refusal before any SendMessage call, with its reason.

    `candidates` lists matching rows from this attempt's listing.
    """

    def __init__(self, reason, detail, candidates=None):
        super().__init__(reason)
        self.reason = reason
        self.detail = detail
        self.candidates = candidates


# Close the child's input, then wait this long (within the deadline) for exit.
INPUT_CLOSE_GRACE_SECONDS = 3
# After SIGTERM, wait this long before SIGKILL; this wait may pass the deadline.
TERMINATE_GRACE_SECONDS = 2
ROUTE_PREFIX = "uds:"
REF_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
SURROGATE_PATTERN = re.compile(r"[\ud800-\udfff]")
RECONCILIATION_FIELDS = frozenset({"after_attempt", "decision_ref"})


def utf16_units(value):
    return sum(2 if ord(character) > 0xFFFF else 1 for character in value)


def validate(request):
    base = {
        "message_id", "attempt_id", "actor", "recipient", "command",
        "evidence_ref", "limits",
    }
    if not isinstance(request, dict):
        raise InspectionError("invalid_request")
    keys = set(request)
    # A later attempt names the latest attempt and the caller's decision: both or neither.
    reconciliation = keys & RECONCILIATION_FIELDS
    if reconciliation:
        if reconciliation != RECONCILIATION_FIELDS or any(
            not isinstance(request[key], str) or not request[key].strip()
            for key in RECONCILIATION_FIELDS
        ):
            raise InspectionError("invalid_reconciliation")
        keys -= reconciliation
    if keys not in (base | {"target"}, base | {"name"}, base | {"name", "selection"}):
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
    if "target" in request:
        target = request["target"]
        if not isinstance(target, str) or not target.startswith(ROUTE_PREFIX) or not target[4:]:
            raise InspectionError("invalid_nomination")
    else:
        name = request["name"]
        if name == "main":
            raise InspectionError("self_destination")
        if (
            not supported_listing_label(name) or unreadable_listing_label(name)
            or SURROGATE_PATTERN.search(name)
            # A name is never sent as a route: the sender does not look for one itself.
            or name.startswith(ROUTE_PREFIX)
        ):
            raise InspectionError("invalid_name")
        if "selection" in request:
            selection = request["selection"]
            if (
                not isinstance(selection, dict) or selection.keys() != {"ref"}
                or not isinstance(selection["ref"], str)
                or REF_PATTERN.fullmatch(selection["ref"]) is None
            ):
                raise InspectionError("invalid_selection")
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


def sendmessage_call(message, actor, target, identity=3):
    """Build the one SendMessage call frame for a planned message."""
    return {
        "jsonrpc": "2.0", "id": identity, "method": "tools/call",
        "params": {
            "name": "SendMessage",
            "arguments": {
                "to": target,
                "message": serialize_peer_message(message, actor),
            },
        },
    }


def name_destination(name, ref=None):
    """The SendMessage `to` for a name: bare, or `name [ref]` for a selected row."""
    return name if ref is None else f"{name} [{ref}]"


def request_destination(request):
    """The address checked before listing, including a reference when selected."""
    if "target" in request:
        return request["target"]
    selection = request.get("selection")
    return name_destination(request["name"], None if selection is None else selection["ref"])


def frame_fits(value):
    try:
        encoded_frame(value)
    except InspectionError:
        return False
    return True


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


def supports_listagents(tool):
    """Recognize the catalog entry before calling ListAgents without arguments."""
    schema = tool["inputSchema"]
    properties = schema.get("properties")
    return (
        schema.keys() <= {"type", "properties", "required", "additionalProperties",
                          "title", "description", "$schema"}
        and schema.get("$schema", "https://json-schema.org/draft/2020-12/schema")
        == "https://json-schema.org/draft/2020-12/schema"
        and schema.get("type") == "object"
        and isinstance(properties, dict)
        and isinstance(properties.get("cursor"), dict)
        and properties["cursor"].get("type") == "string"
        and schema.get("required", []) == []
        and schema.get("additionalProperties") is False
    )


def destination_violation(target):
    if "\r" in target or "\n" in target:
        return "Destination contains CR/LF."
    # Conservative source limit: astral characters consume two UTF-16 code units.
    if utf16_units(target) > 300:
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


# Observed Claude Desktop ListAgents layout. The 2.1.331 duration formatter's
# mostSignificantOnly mode emits a single integer in s, m, h or d.
LISTING_FIELD_SEPARATOR = "  ·  "
LISTING_COUNT = r"[1-9][0-9]{0,8}"
LISTING_AGE = rf"(?:0s|{LISTING_COUNT}[smhd])"
LISTING_TITLE = re.compile(r"[^\x00-\x1f\x7f-\x9f\u2028\u2029]{1,300}")
LISTING_LABEL = rf"(?P<name>{LISTING_TITLE.pattern}) \[(?P<ref>[0-9a-f]{{6}})\]"
LISTING_CALLER = re.compile(
    rf"This session is {LISTING_LABEL} — the name other sessions use to message it "
    r"\(it is not listed below; a message to it would be a message to yourself\)\."
)
LISTING_SECTION = re.compile(rf"Peer sessions \((?P<total>{LISTING_COUNT})\):")
LISTING_FIELDS = re.escape(LISTING_FIELD_SEPARATOR)
LISTING_ROW = re.compile(
    rf"  {LISTING_LABEL}{LISTING_FIELDS}interactive{LISTING_FIELDS}(?:idle|busy)"
    rf"{LISTING_FIELDS}Claude Desktop session{LISTING_FIELDS}started {LISTING_AGE} ago"
)
LISTING_REMOTE_OFF = (
    "[Cloud sessions and other computers are not listed because Remote Control is off "
    "in this session. The user can turn it on with the Remote Control switch in the app; "
    "then list again.]"
)

# A free-form label must not absorb any of the listing's control text. Match
# fragments that identify the controls even where their counts or refs vary.
LISTING_CONTROL_TEXT = re.compile(
    r"This session is |This session:|This process's main session is |it is not listed below"
    r"|the name other sessions use to message it|would be a message to yourself"
    r"|address the main conversation"
    r"|(?:Peer sessions|Cloud and Remote Control sessions|Chats|Subagents|Teammates) \([^)]*\):"
    r"|Cloud sessions and other computers are not listed|Remote Control is off"
    r"|Remote Control switch|then list again|No reachable agents"
    r"|No other session appears in this listing|The brackets after each name below"
    r"|Your user allowed this session to message the chats below"
    r"|People or other Claude sessions wrote the titles in this block|</?other-sessions\b"
    r"|Session names and \[ref\]s listed here|nothing more to list"
    r"|one session hidden|(?:sessions?|agents?) (?:hidden|not shown)"
    r"|more(?: sessions)? not shown|missing from this listing|agents may be missing from this page"
    r"|call again with cursor|for the next page|SendMessage still finds"
    r"|other sessions could not be read|the session list on this machine could not be read"
    r"|account session list incomplete|the Remote Control session list for your account"
    r"|cloud session list could not be fetched|Cross-session messaging is switched off"
    r"|None of the agents below can be messaged"
    r"|session list too long|not chosen by a human|withheld on this connection"
    r"|not messageable by name|message it by this exact name"
)


def supported_listing_label(name):
    return (
        isinstance(name, str)
        and LISTING_TITLE.fullmatch(name) is not None
        and name == name.strip()
        and not name.startswith("<")
        and utf16_units(name) <= 300
        and LISTING_FIELD_SEPARATOR not in name
        and LISTING_CONTROL_TEXT.search(name) is None
    )


def check_listing_label(name):
    if not supported_listing_label(name):
        raise PathRefusal("unrecognized_listing", "A listing label is outside the profile; "
                          "no SendMessage was sent.")


def unreadable_listing_label(name):
    return name.startswith("(") or "[" in name or "]" in name


def parse_listing(listing, name, selection):
    """Yield supported peers in order, with None for a provably unrelated unreadable label."""
    lines = listing.split("\n")
    if (len(lines) < 6 or lines[1] != "" or lines[-2] != ""
            or lines[-1] != LISTING_REMOTE_OFF):
        raise PathRefusal("listing_incomplete", "The listing lacks its complete observed layout; "
                          "no SendMessage was sent.")
    caller = LISTING_CALLER.fullmatch(lines[0])
    section = LISTING_SECTION.fullmatch(lines[2])
    if caller is None or section is None:
        raise PathRefusal("unrecognized_listing", "A listing heading is outside the profile; "
                          "no SendMessage was sent.")
    peer_lines = lines[3:-2]

    caller_name = caller["name"]
    check_listing_label(caller_name)
    if unreadable_listing_label(caller_name):
        raise PathRefusal("unrecognized_listing", "The caller label is outside the profile; "
                          "no SendMessage was sent.")
    if name == caller_name or (selection is not None and selection["ref"] == caller["ref"]):
        raise PathRefusal("self_destination", "The name or selection can address the caller; "
                          "no SendMessage was sent.")

    seen_lines = set()
    for line in peer_lines:
        if line in seen_lines:
            raise PathRefusal("listing_incomplete", "The listing repeats a peer row; "
                              "no SendMessage was sent.")
        seen_lines.add(line)
        row = LISTING_ROW.fullmatch(line)
        if row is None:
            raise PathRefusal("unrecognized_listing", "A listing row is outside the profile; "
                              "no SendMessage was sent.")
        row_name = row["name"]
        check_listing_label(row_name)
        if row["ref"] == caller["ref"]:
            raise PathRefusal("listing_incomplete", "A peer row repeats the caller's reference; "
                              "no SendMessage was sent.")
        if unreadable_listing_label(row_name):
            first_field, _, _ = line[2:].partition(LISTING_FIELD_SEPARATOR)
            if first_field == name or first_field.startswith(name + " ["):
                raise PathRefusal(
                    "unrecognized_listing", "An unreadable peer label could carry the "
                    "requested name; no SendMessage was sent.")
            yield None
        else:
            yield {"section": "Peer sessions", "name": row_name, "ref": row["ref"],
                   "kind": "interactive", "local": True}
    if int(section["total"]) != len(peer_lines):
        raise PathRefusal("listing_incomplete", "The declared peer total differs from the row count; "
                          "no SendMessage was sent.")


def candidate_view(row):
    return {key: row[key] for key in ("name", "ref", "kind", "local")}


def select_row(rows, name, selection):
    """Bind a local listing row and use its reference only to disambiguate."""
    named = [row for row in rows if row["name"] == name]
    candidates = [candidate_view(row) for row in named]
    if selection is not None:
        chosen = [row for row in named if row["ref"] == selection["ref"]]
        if not chosen:
            raise PathRefusal(
                "selection_not_in_listing",
                "The selected reference is not shown for this name in this attempt's "
                "listing; no SendMessage was sent.", candidates)
        if len(chosen) > 1:
            raise PathRefusal(
                "ambiguous_selection",
                f"{len(chosen)} rows in this attempt's listing show this name and the "
                "selected reference; no SendMessage was sent.", candidates)
        row = chosen[0]
    elif not named:
        raise PathRefusal(
            "no_matching_local_row",
            "No row in this attempt's listing has this name; no SendMessage was sent.")
    elif len(named) > 1:
        raise PathRefusal(
            "ambiguous_name",
            f"{len(named)} rows in this attempt's listing have this name and no "
            "selection was supplied; no SendMessage was sent.", candidates)
    else:
        row = named[0]
    return row, name_destination(row["name"], row["ref"] if len(named) > 1 else None)


def has_actionable_selection(candidates, message, actor, identity):
    ref_counts = Counter(row["ref"] for row in candidates)
    for row in candidates:
        if ref_counts[row["ref"]] != 1:
            continue
        target = name_destination(row["name"], row["ref"])
        if destination_violation(target) is None and frame_fits(
            sendmessage_call(message, actor, target, identity)
        ):
            return True
    return False


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

    def read_ready(self, timeout):
        events = self.selector.select(timeout)
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
        return bool(events)

    def pump(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise InspectionError("deadline")
        if not self.read_ready(remaining):
            raise InspectionError("deadline")

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

    def await_exit(self, until):
        """Drain the pipes until the child exits or `until` passes."""
        process = self.process
        while process.poll() is None:
            remaining = until - time.monotonic()
            if remaining <= 0:
                return
            if self.selector.get_map():
                self.read_ready(min(remaining, 0.05))
            else:
                try:
                    process.wait(timeout=remaining)
                except subprocess.TimeoutExpired:
                    return

    def close(self):
        """Close input, wait, then SIGTERM, then SIGKILL, as MCP's stdio shutdown."""
        process = self.process
        if process is None:
            self.selector.close()
            return {"started": False, "reaped": False, "exit_code": None}
        closure_error = None
        closed_by = None
        try:
            process.stdin.close()
        except (OSError, ValueError):
            closure_error = "closure_failed"
        try:
            self.await_exit(time.monotonic() + max(0, min(
                INPUT_CLOSE_GRACE_SECONDS, self.deadline - time.monotonic())))
        except (InspectionError, OSError, ValueError) as error:
            closure_error = str(error) if isinstance(error, InspectionError) else "closure_failed"
        if process.poll() is None:
            # The child outlived its closed input: stop it without waiting out the deadline.
            process.terminate()
            closed_by = "terminate"
            # Keep draining: a child that writes while it stops must not block on a full pipe.
            until = time.monotonic() + TERMINATE_GRACE_SECONDS
            try:
                self.await_exit(until)
            except (InspectionError, OSError, ValueError) as error:
                if closure_error is None:
                    closure_error = (
                        str(error) if isinstance(error, InspectionError) else "closure_failed")
                try:
                    process.wait(timeout=max(0, until - time.monotonic()))
                except subprocess.TimeoutExpired:
                    pass
        if process.poll() is None:
            process.kill()
            closed_by = "kill"
        # Reap only the process created by this invocation, never a group.
        process.wait()
        for stream in (process.stdout, process.stderr):
            stream.close()
        self.selector.close()
        # Exit ends this wait: a descendant holding a pipe does not extend it.
        closure = {"started": True, "reaped": True, "exit_code": process.returncode}
        if closed_by is not None:
            closure["closed_by"] = closed_by
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


def read_listing(child, identity, name, selection):
    child.send({
        "jsonrpc": "2.0", "id": identity, "method": "tools/call",
        "params": {"name": "ListAgents", "arguments": {}},
    })
    result = child.reply(identity)
    if not supported_tool_result(result) or len(result["content"]) != 1:
        raise PathRefusal("unsupported_listing_result",
                          "The ListAgents result is outside the text profile.")
    if result.get("isError", False):
        raise PathRefusal("listing_error", "ListAgents returned an error result.")
    return parse_listing(result["content"][0]["text"], name, selection)


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
        if isinstance(request, dict) and "name" in request and "target" not in request:
            result["path"] = "name"
        validate(request)
        path = "route" if "target" in request else "name"
        result["path"] = path
        deadline = time.monotonic() + request["limits"]["operation_seconds"]
        result["stage"] = "claim"
        mailbox = Mailbox(arguments.store)
        planned = mailbox.get(request["message_id"])
        if planned["recipient"] != request["recipient"]:
            raise InspectionError("recipient_mismatch")
        # On the name path the record names its recipient by the address it is sent to.
        if path == "name" and planned["recipient"]["thread_id"] != request["name"]:
            raise InspectionError("recipient_name_mismatch")
        # The mailbox's own rule decides whether a requested later attempt may be claimed.
        claim = mailbox.claim(
            request["message_id"], request["attempt_id"], request["actor"],
            request.get("after_attempt"), request.get("decision_ref"),
        )
        result["claimed"] = claim["claimed"] is True
        result["attempt_id"] = request["attempt_id"]
        message = {
            key: value for key, value in planned.items()
            if key not in {"attempts", "state"}
        }

        def refuse(refusal):
            # No possible submission was recorded and no SendMessage call was written:
            # the sender's own phase record is the evidence that this attempt did not deliver.
            evidence = {
                "evidence": "sender_phase_record",
                "phase": "refused_before_possible_submission",
                "path": path, "reason": refusal.reason,
            }
            if "unreadable_rows" in result:
                evidence["unreadable_rows"] = result["unreadable_rows"]
            mailbox.observe_many(
                request["message_id"], request["attempt_id"], request["evidence_ref"], (
                    ("refused", refusal.detail),
                    ("not_delivered", json.dumps(evidence, ensure_ascii=True, sort_keys=True)),
                ),
            )
            result["reason"] = refusal.reason
            if refusal.candidates is not None:
                result["candidates"] = refusal.candidates

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
            listers = [tool for tool in tools if tool["name"] == "ListAgents"]
            to = request_destination(request)
            identity = 3
            # One possible-submission record shape on both paths; a name adds its row.
            bound = {"phase": "possible_submission", "path": path, "to": to}
            try:
                # Every refusal below is definite and comes before any SendMessage call.
                if not nominated:
                    raise PathRefusal(
                        "missing_sendmessage",
                        "Complete tools/list catalog has no SendMessage; no tools/call was sent.")
                if len(nominated) != 1 or not supports_sendmessage(nominated[0]):
                    raise PathRefusal(
                        "unsupported_sendmessage_schema",
                        "SendMessage schema is outside the supported to/message string profile; "
                        "no tools/call was sent.")
                if path == "name" and (len(listers) != 1 or not supports_listagents(listers[0])):
                    raise PathRefusal(
                        "unsupported_listagents",
                        "The catalog offers no ListAgents in the supported profile; no tools/call was sent.")
                # The by-name profile budgets for a reference even in a legacy catalog.
                if path == "name" or "allOf" in nominated[0]["inputSchema"]["properties"]["to"]:
                    if violation := destination_violation(to):
                        raise PathRefusal("destination_constraint_violation",
                                          violation + " No tools/call was sent.")
                if not frame_fits(sendmessage_call(message, request["actor"], to)):
                    # Refuse oversized frames before any call or possible submission.
                    raise PathRefusal(
                        "control_frame_limit",
                        "SendMessage frame exceeds the 4,096-byte control-frame ceiling; "
                        "no tools/call was sent.")
                if path == "name":
                    result["stage"] = "listing"
                    result["unreadable_rows"] = 0
                    rows = []
                    try:
                        for row in read_listing(child, identity, request["name"],
                                                request.get("selection")):
                            if row is None:
                                result["unreadable_rows"] += 1
                            else:
                                rows.append(row)
                    except InspectionError as error:
                        # Only ListAgents was written: nothing could have been submitted.
                        raise PathRefusal(
                            "listing_failed",
                            f"ListAgents did not complete ({error}); no SendMessage was sent.",
                        ) from error
                    identity += 1
                    row, to = select_row(rows, request["name"], request.get("selection"))
                    bound["to"] = to
                    # Check the frame with the address resolved from the listing.
                    if not frame_fits(sendmessage_call(message, request["actor"], to, identity)):
                        raise PathRefusal(
                            "control_frame_limit",
                            "SendMessage frame exceeds the 4,096-byte control-frame ceiling; "
                            "no SendMessage was sent.")
                    bound["row"] = row
                    bound["unreadable_rows"] = result["unreadable_rows"]
            except PathRefusal as refusal:
                refuse(refusal)
                if refusal.candidates and has_actionable_selection(
                    refusal.candidates, message, request["actor"], identity
                ):
                    result["needs"] = "selection"
            else:
                call = sendmessage_call(message, request["actor"], to, identity)
                result["stage"] = "call"
                mailbox.observe(
                    request["message_id"], request["attempt_id"], "unknown",
                    request["evidence_ref"], json.dumps(bound, ensure_ascii=True, sort_keys=True),
                )
                # Once writing may begin, every uncertainty remains non-replayable.
                result["peer_input"] = "possible_submission"
                child.send(call)
                tool_result = child.reply(identity)
                supported = supported_tool_result(tool_result)
                submitted = supported and not tool_result.get("isError", False)
                mailbox.observe(
                    request["message_id"], request["attempt_id"],
                    "submitted" if submitted else "unknown",
                    request["evidence_ref"], json.dumps({
                        "target": to, "tool_result": tool_result,
                    }, ensure_ascii=True, sort_keys=True),
                )
                if submitted:
                    result["peer_input"] = "submitted"
                    result["reason"] = "submitted"
                else:
                    result["reason"] = "tool_error" if supported else "unsupported_tool_result"
    except InspectionError as error:
        result["reason"] = str(error)
    except (ValueError, RecursionError, OSError, sqlite3.Error, MailboxError):
        result["reason"] = "local_or_protocol_failure"
    finally:
        if child is not None:
            result["owned_child"] = child.close()
        if mailbox is not None:
            mailbox.close()
    # Fixed vocabulary, a bounded request, and candidate rows read within the stdout
    # limit keep this single result bounded.
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
