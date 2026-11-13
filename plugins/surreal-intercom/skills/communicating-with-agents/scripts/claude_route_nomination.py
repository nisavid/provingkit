#!/usr/bin/env python3
"""Publish a receiver-owned Claude route or prepare its existing sender request."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import posixpath
import re
import shutil
import stat
import sys

from claude_mcp_sender import validate as validate_sender_request
from codex_capture import CaptureWriter
from native_codex_mailbox import Mailbox


class RouteRefusal(ValueError):
    """A missing or changed Claude route input."""


def _nonempty(value, reason):
    if not isinstance(value, str) or not value or "\0" in value:
        raise RouteRefusal(reason)
    return value


def _identity(value, reason="invalid-identity"):
    if (
        not isinstance(value, dict)
        or value.keys() != {"thread_id", "host_id"}
        or any(not isinstance(item, str) or not item.strip() for item in value.values())
    ):
        raise RouteRefusal(reason)
    return value


def _read_json(path, maximum, reason):
    with Path(path).open("rb") as source:
        data = source.read(maximum + 1)
    if len(data) > maximum:
        raise RouteRefusal(reason)
    return json.loads(data.decode("utf-8"))


def _private_directory(path, effective_uid):
    path = Path(path)
    try:
        observed = path.lstat()
    except OSError as error:
        raise RouteRefusal("invalid-private-directory") from error
    if (
        not path.is_absolute()
        or stat.S_ISLNK(observed.st_mode)
        or not stat.S_ISDIR(observed.st_mode)
        or stat.S_IMODE(observed.st_mode) != 0o700
        or observed.st_uid != effective_uid
        or any(parent.is_symlink() for parent in path.parents)
    ):
        raise RouteRefusal("invalid-private-directory")


def _publication(value, effective_uid):
    if (
        not isinstance(value, dict)
        or value.keys() != {"path", "ownerUid", "capture"}
        or type(value["ownerUid"]) is not int
        or value["ownerUid"] != effective_uid
        or not isinstance(value["capture"], dict)
    ):
        raise RouteRefusal("invalid-publication-custody")
    output = Path(value["path"])
    root = Path(value["capture"].get("run_root", ""))
    if not output.is_absolute() or root != output.parent:
        raise RouteRefusal("invalid-publication-custody")
    _private_directory(root, effective_uid)
    return output, value["capture"]


def _socket_target(value):
    value = _nonempty(value, "messaging-socket-field-unavailable")
    if (
        not value.startswith("/")
        or value.startswith("//")
        or value == "/"
        or posixpath.normpath(value) != value
        or any(character in value for character in "\r\n")
    ):
        raise RouteRefusal("unsupported-messaging-socket")
    target = "uds:" + value
    if len(target.encode("utf-16-le")) // 2 > 300:
        raise RouteRefusal("unsupported-messaging-socket")
    return target


def _launcher(environment, launcher_lookup):
    path_value = environment.get("PATH")
    if not isinstance(path_value, str) or not path_value:
        raise RouteRefusal("launcher-control-unavailable")
    try:
        launcher = launcher_lookup("claude", path_value)
    except (OSError, ValueError, TypeError) as error:
        raise RouteRefusal("launcher-control-unavailable") from error
    if (
        not isinstance(launcher, str)
        or not Path(launcher).is_absolute()
        or Path(launcher).name != "claude"
        or any(character in launcher for character in "\0\r\n")
    ):
        raise RouteRefusal("claude-launcher-unavailable")
    # Preserve the resolver's selected path and invoked name. In particular,
    # never resolve a multi-call or credential wrapper to another executable.
    return launcher


def _nomination_record(request, effective_uid, environment, launcher_lookup):
    required = {"schema", "recipient", "producer", "publication"}
    if (
        not isinstance(request, dict)
        or request.keys() != required
        or request["schema"] != "claude-route-nomination-request-v1"
    ):
        raise RouteRefusal("invalid-nomination-request")
    recipient = _identity(request["recipient"])
    producer = _identity(request["producer"])
    if producer != recipient:
        raise RouteRefusal("producer-recipient-mismatch")
    host_session = environment.get("CLAUDE_CODE_HOST_SESSION_ID")
    if not isinstance(host_session, str) or not host_session:
        raise RouteRefusal("host-session-field-unavailable")
    if host_session != recipient["thread_id"]:
        raise RouteRefusal("recipient-host-session-mismatch")
    target = _socket_target(environment.get("CLAUDE_CODE_MESSAGING_SOCKET"))
    launcher = _launcher(environment, launcher_lookup)
    output, capture = _publication(request["publication"], effective_uid)
    record = {
        "schema": "claude-route-nomination-v1",
        "status": "nominated",
        "recipient": recipient,
        "producer": producer,
        "launch": {
            "invokedName": "claude",
            "command": [launcher, "mcp", "serve"],
        },
        "route": {"target": target},
        "privacy": {
            "boundary": "unix-account-private",
            "sameUidIsolation": False,
            "pathIsAuthority": False,
        },
        "retention": {"replace": False, "bindingMustRemainCurrent": True},
    }
    encoded = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    if len(encoded) > 4096:
        raise RouteRefusal("nomination-record-byte-limit")
    return output, capture, record, encoded


def _stat_identity(value):
    return (
        value.st_dev,
        value.st_ino,
        value.st_uid,
        value.st_mode,
        value.st_nlink,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _read_private_nomination(reference, effective_uid):
    if (
        not isinstance(reference, dict)
        or reference.keys() != {"path", "bytes", "sha256"}
        or type(reference["bytes"]) is not int
        or not 1 <= reference["bytes"] <= 4096
        or not isinstance(reference["sha256"], str)
        or re.fullmatch(r"[0-9a-f]{64}", reference["sha256"]) is None
    ):
        raise RouteRefusal("invalid-nomination-pin")
    path = Path(reference["path"])
    if not path.is_absolute():
        raise RouteRefusal("invalid-nomination-pin")
    _private_directory(path.parent, effective_uid)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb", buffering=0) as source:
        before = os.fstat(source.fileno())
        try:
            named_before = path.lstat()
        except OSError as error:
            raise RouteRefusal("changed-private-nomination") from error
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != effective_uid
            or stat.S_IMODE(before.st_mode) != 0o600
            or before.st_nlink != 1
            or before.st_size != reference["bytes"]
            or _stat_identity(before) != _stat_identity(named_before)
        ):
            raise RouteRefusal("unqualified-private-nomination")
        raw = source.read(reference["bytes"] + 1)
        after = os.fstat(source.fileno())
    try:
        named_after = path.lstat()
    except OSError as error:
        raise RouteRefusal("changed-private-nomination") from error
    if (
        len(raw) != reference["bytes"]
        or _stat_identity(before) != _stat_identity(after)
        or _stat_identity(before) != _stat_identity(named_after)
        or hashlib.sha256(raw).hexdigest() != reference["sha256"]
    ):
        raise RouteRefusal("changed-private-nomination")
    return json.loads(raw.decode("utf-8"))


def _validated_nomination(record):
    required = {
        "schema", "status", "recipient", "producer", "launch", "route",
        "privacy", "retention",
    }
    if (
        not isinstance(record, dict)
        or record.keys() != required
        or record["schema"] != "claude-route-nomination-v1"
        or record["status"] != "nominated"
    ):
        raise RouteRefusal("malformed-private-nomination")
    recipient = _identity(record["recipient"], "malformed-private-nomination")
    producer = _identity(record["producer"], "malformed-private-nomination")
    launch = record["launch"]
    route = record["route"]
    try:
        supported_target = (
            _socket_target(route.get("target", "")[4:])
            if isinstance(route, dict) and isinstance(route.get("target"), str)
            and route["target"].startswith("uds:")
            else None
        )
    except RouteRefusal:
        supported_target = None
    if (
        producer != recipient
        or not isinstance(launch, dict)
        or launch.keys() != {"invokedName", "command"}
        or launch["invokedName"] != "claude"
        or not isinstance(launch["command"], list)
        or len(launch["command"]) != 3
        or launch["command"][1:] != ["mcp", "serve"]
        or not isinstance(launch["command"][0], str)
        or not Path(launch["command"][0]).is_absolute()
        or Path(launch["command"][0]).name != launch["invokedName"]
        or not isinstance(route, dict)
        or route.keys() != {"target"}
        or supported_target != route.get("target")
        or record["privacy"] != {
            "boundary": "unix-account-private",
            "sameUidIsolation": False,
            "pathIsAuthority": False,
        }
        or record["retention"] != {"replace": False, "bindingMustRemainCurrent": True}
    ):
        raise RouteRefusal("malformed-private-nomination")
    return recipient, launch["command"], route["target"]


def _mailbox_path(value, effective_uid):
    path = Path(value)
    if not path.is_absolute():
        raise RouteRefusal("invalid-mailbox-custody")
    _private_directory(path.parent, effective_uid)
    if path.exists() or path.is_symlink():
        observed = path.lstat()
        if (
            stat.S_ISLNK(observed.st_mode)
            or not stat.S_ISREG(observed.st_mode)
            or observed.st_uid != effective_uid
            or stat.S_IMODE(observed.st_mode) != 0o600
            or observed.st_nlink != 1
        ):
            raise RouteRefusal("invalid-mailbox-custody")
    return path


def _prepared_request(request, effective_uid):
    required = {
        "schema", "nomination", "message", "attempt_id", "actor", "limits",
        "mailbox", "publication",
    }
    if (
        not isinstance(request, dict)
        or request.keys() != required
        or request["schema"] != "claude-sender-request-preparation-v1"
    ):
        raise RouteRefusal("invalid-preparation-request")
    record = _read_private_nomination(request["nomination"], effective_uid)
    recipient, command, target = _validated_nomination(record)
    message = request["message"]
    if not isinstance(message, dict) or message.get("recipient") != recipient:
        raise RouteRefusal("recipient-nomination-mismatch")
    actor = _identity(request["actor"])
    attempt_id = _nonempty(request["attempt_id"], "invalid-attempt")
    output, capture = _publication(request["publication"], effective_uid)
    if output.exists() or output.is_symlink():
        raise RouteRefusal("sender-request-already-exists")
    mailbox_path = _mailbox_path(request["mailbox"], effective_uid)
    sender_request = {
        "message_id": message.get("message_id"),
        "attempt_id": attempt_id,
        "actor": actor,
        "recipient": recipient,
        "target": target,
        "command": command,
        "evidence_ref": "sha256:" + request["nomination"]["sha256"],
        "limits": request["limits"],
    }
    validate_sender_request(sender_request)
    encoded = json.dumps(sender_request, sort_keys=True, separators=(",", ":")).encode()
    if len(encoded) > 32768:
        raise RouteRefusal("sender-request-byte-limit")
    return output, capture, mailbox_path, message, sender_request, encoded


def _default_lookup(invoked_name, path):
    return shutil.which(invoked_name, path=path)


def main(argv=None, *, effective_uid=None, environment=None, launcher_lookup=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    for operation in ("nominate", "prepare"):
        command = commands.add_parser(operation)
        command.add_argument("--request", required=True)
    arguments = parser.parse_args(argv)
    uid = os.geteuid() if effective_uid is None else effective_uid
    result = {
        "published" if arguments.operation == "nominate" else "prepared": False,
        "reason": "invalid-request",
        "closure": "no-provider-started",
    }
    try:
        request = _read_json(arguments.request, 32768, "request-byte-limit")
        if arguments.operation == "nominate":
            output, capture, record, expected = _nomination_record(
                request,
                uid,
                os.environ if environment is None else environment,
                _default_lookup if launcher_lookup is None else launcher_lookup,
            )
            digest = CaptureWriter(capture).write_json(output, record)
            actual = output.read_bytes()
            observed = output.lstat()
            if (
                actual != expected
                or stat.S_IMODE(observed.st_mode) != 0o600
                or observed.st_uid != uid
                or observed.st_nlink != 1
            ):
                raise RouteRefusal("published-nomination-verification-failed")
            result = {
                "published": True,
                "reason": "published",
                "path": str(output),
                "bytes": len(actual),
                "sha256": digest,
                "closure": "no-provider-started",
            }
        else:
            output, capture, mailbox_path, message, sender_request, expected = _prepared_request(
                request, uid,
            )
            mailbox = Mailbox(mailbox_path, initialize=not mailbox_path.exists())
            try:
                mailbox.plan(message)
            finally:
                mailbox.close()
            digest = CaptureWriter(capture).write_json(output, sender_request)
            actual = output.read_bytes()
            observed = output.lstat()
            if (
                actual != expected
                or stat.S_IMODE(observed.st_mode) != 0o600
                or observed.st_uid != uid
                or observed.st_nlink != 1
            ):
                raise RouteRefusal("published-request-verification-failed")
            result = {
                "prepared": True,
                "reason": "prepared",
                "path": str(output),
                "bytes": len(actual),
                "sha256": digest,
                "mailbox": str(mailbox_path),
                "sender": "not-invoked",
                "uncertainty": "preserve-original-attempt",
                "closure": "no-provider-started",
            }
    except FileExistsError:
        result["reason"] = "private-output-already-exists"
    except (
        RouteRefusal, OSError, UnicodeError, ValueError, KeyError, TypeError,
        RecursionError,
    ) as error:
        result["reason"] = str(error)
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
