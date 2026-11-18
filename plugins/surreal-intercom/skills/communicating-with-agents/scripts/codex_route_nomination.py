#!/usr/bin/env python3
"""Collect and publish one provisional Codex route from the invoked helper."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import stat
import struct
import sys
import time

from codex_capture import CaptureWriter
from codex_ipc_core import Refusal, bounded_bytes, print_result


EXECUTABLE_KEYS = {"path", "device", "inode"}
SAMPLE_LIMITS = {
    "sharedWatchdogMilliseconds": 5000,
    "descriptorEntries": 1024,
    "unixRows": 4096,
    "unixBytes": 524288,
    "descriptorLinkBytes": 262144,
    "maxMetadataBytes": 8192,
}
MAX_CLASSIFICATIONS = 2
MAX_SAME_PATH_LISTENERS = 8
MAX_DIAG_REPLY_BYTES = 256
MAX_MOUNT_TABLE_BYTES = 65536
MAX_U32 = (1 << 32) - 1
NETLINK_SOCK_DIAG = 4
SOCK_DIAG_BY_FAMILY = 20
TCP_LISTEN = 10
UDIAG_SHOW_VFS = 2
UNIX_DIAG_VFS = 1
AGGREGATE_SAMPLE_LIMITS = {
    key: SAMPLE_LIMITS[key] * MAX_CLASSIFICATIONS
    for key in ("descriptorEntries", "unixRows", "unixBytes", "descriptorLinkBytes")
}


class ProcfsObservation:
    """Bounded production reads used by the public command."""

    @staticmethod
    def getpid():
        return os.getpid()

    @staticmethod
    def geteuid():
        return os.geteuid()

    @staticmethod
    def monotonic_milliseconds():
        return time.monotonic_ns() // 1_000_000

    @staticmethod
    def read_bytes(path, maximum):
        with Path(path).open("rb") as source:
            return source.read(maximum + 1)

    @staticmethod
    def readlink(path, maximum):
        value = os.readlink(path)
        if len(value.encode()) > maximum:
            raise OSError("link-byte-limit")
        return value

    @staticmethod
    def listdir(path, maximum_entries):
        entries = []
        with os.scandir(path) as iterator:
            for entry in iterator:
                entries.append(entry.name)
                if len(entries) > maximum_entries:
                    break
        return entries

    @staticmethod
    def executable_identity(process_link, resolved_path):
        observed = os.stat(process_link)
        return {"path": resolved_path, "device": observed.st_dev, "inode": observed.st_ino}

    @staticmethod
    def lstat(path):
        return os.lstat(path)


    def observe_backing_nodes(self, endpoint, node, inodes, deadline):
        # O_PATH opens a filesystem reference, not a connection to the listener.
        try:
            fd = os.open(endpoint, os.O_PATH | os.O_NOFOLLOW | os.O_CLOEXEC)
            try:
                held = os.fstat(fd)
                if (not stat.S_ISSOCK(held.st_mode) or stat.S_IMODE(held.st_mode) != 0o600
                        or (held.st_uid, held.st_dev, held.st_ino) !=
                        (node["uid"], node["device"], node["inode"])):
                    raise Refusal("sample-identity-changed")
                mount_id = _exact_mount_id(self, fd)
                _require_ext4_mount(self, mount_id, held.st_dev)
                with socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, NETLINK_SOCK_DIAG) as diag:
                    return {
                        inode: _query_backing_node(diag, inode, sequence, deadline, self)
                        for sequence, inode in enumerate(inodes, 1)
                    }
            finally:
                os.close(fd)
        except (AttributeError, OSError, ValueError, struct.error) as error:
            raise Refusal("listener-backing-observation-unavailable") from error


def _exact_mount_id(observer, fd):
    metadata = _bounded_read(
        observer, f"/proc/self/fdinfo/{fd}", SAMPLE_LIMITS["maxMetadataBytes"],
        "listener-mount-unavailable",
    )
    ids = [line.split()[1:] for line in metadata.splitlines() if line.startswith(b"mnt_id:")]
    if len(ids) != 1 or len(ids[0]) != 1 or not ids[0][0].isdigit():
        raise Refusal("listener-mount-unavailable")
    return ids[0][0]


def _require_ext4_mount(observer, mount_id, device):
    # UNIX_DIAG_VFS reports a 32-bit inode. Restrict this discriminant to
    # an actual ext4 mount so older entries cannot alias by truncation.
    mounts = _bounded_read(
        observer, "/proc/self/mountinfo", MAX_MOUNT_TABLE_BYTES,
        "listener-mount-unavailable",
    )
    device_number = f"{os.major(device)}:{os.minor(device)}".encode("ascii")
    matches = []
    for line in mounts.splitlines():
        left, marker, right = line.partition(b" - ")
        fields = left.split()
        if fields and fields[0] == mount_id:
            details = right.split()
            if not marker or len(fields) < 6 or len(details) < 3:
                raise Refusal("listener-mount-unavailable")
            matches.append((fields[2], details[0]))
    if matches != [(device_number, b"ext4")]:
        raise Refusal("unsupported-listener-backing-filesystem")


def _query_backing_node(diag, inode, sequence, deadline, observer):
    request = struct.pack(
        "=BBHIIIII", socket.AF_UNIX, 0, 0, 1 << TCP_LISTEN, inode,
        UDIAG_SHOW_VFS, MAX_U32, MAX_U32,
    )
    header = struct.pack("=IHHII", 16 + len(request), SOCK_DIAG_BY_FAMILY, 1, sequence, 0)

    def remaining_seconds():
        remaining = deadline - observer.monotonic_milliseconds()
        if remaining <= 0:
            raise Refusal("sample-watchdog-exceeded")
        return remaining / 1000

    diag.settimeout(remaining_seconds())
    if diag.sendto(header + request, (0, 0)) != len(header) + len(request):
        raise Refusal("listener-backing-observation-unavailable")
    diag.settimeout(remaining_seconds())
    message, ancillary, flags, sender = diag.recvmsg(MAX_DIAG_REPLY_BYTES)
    if ancillary or flags or sender != (0, 0) or len(message) < 32:
        raise Refusal("invalid-listener-backing-observation")
    size, kind, response_flags, response_sequence, _ = struct.unpack_from("=IHHII", message)
    if (size != len(message) or kind != SOCK_DIAG_BY_FAMILY
            or response_flags or response_sequence != sequence):
        raise Refusal("invalid-listener-backing-observation")
    family, kind, state, pad, observed_inode, cookie_low, cookie_high = struct.unpack_from(
        "=BBBBIII", message, 16,
    )
    if (family, kind, state, pad, observed_inode) != (
            socket.AF_UNIX, socket.SOCK_STREAM, TCP_LISTEN, 0, inode):
        raise Refusal("invalid-listener-backing-observation")
    offset = 32
    backing = None
    while offset < size:
        if size - offset < 4:
            raise Refusal("invalid-listener-backing-observation")
        length, kind = struct.unpack_from("=HH", message, offset)
        aligned = (length + 3) & ~3
        if not 4 <= length <= aligned <= size - offset:
            raise Refusal("invalid-listener-backing-observation")
        if kind == UNIX_DIAG_VFS:
            if backing is not None or length != 12:
                raise Refusal("invalid-listener-backing-observation")
            backing = struct.unpack_from("=II", message, offset + 4)
        offset += aligned
    if backing is None:
        raise Refusal("listener-backing-observation-unavailable")
    return (*backing, cookie_low, cookie_high)


def _nonempty(value, reason):
    if not isinstance(value, str) or not value:
        raise Refusal(reason)
    return value


def _executable(value):
    if (not isinstance(value, dict) or value.keys() != EXECUTABLE_KEYS
            or not Path(_nonempty(value["path"], "invalid-executable-identity")).is_absolute()
            or any(type(value[key]) is not int or value[key] < 0 for key in ("device", "inode"))):
        raise Refusal("invalid-executable-identity")
    return value


def _bounded_read(observer, path, maximum, reason):
    try:
        data = observer.read_bytes(path, maximum)
    except (OSError, KeyError) as error:
        raise Refusal(reason) from error
    if not isinstance(data, bytes) or len(data) > maximum:
        raise Refusal(reason)
    return data


def _bounded_link(observer, path, maximum, reason):
    try:
        value = observer.readlink(path, maximum)
    except (OSError, KeyError) as error:
        raise Refusal(reason) from error
    if not isinstance(value, str) or len(value.encode()) > maximum:
        raise Refusal(reason)
    return value


def _watchdog(observer, started):
    now = observer.monotonic_milliseconds()
    if type(now) is not int or now < started or now - started > SAMPLE_LIMITS["sharedWatchdogMilliseconds"]:
        raise Refusal("sample-watchdog-exceeded")
    return now


def _process_stat(data, pid):
    try:
        text_value = data.decode("utf-8")
        close = text_value.rindex(")")
        observed_pid = int(text_value[:text_value.index(" ")])
        fields = text_value[close + 2:].split()
        ppid = int(fields[1])
        start_ticks = int(fields[19])
    except (UnicodeError, ValueError, IndexError) as error:
        raise Refusal("invalid-process-metadata") from error
    if observed_pid != pid or ppid < 0 or start_ticks <= 0:
        raise Refusal("invalid-process-metadata")
    return ppid, start_ticks


def _process_ids(data):
    values = {}
    try:
        for line in data.decode("utf-8").splitlines():
            if line.startswith(("Uid:", "Gid:")):
                parts = line.split()
                values[parts[0][:-1]] = int(parts[2])
    except (UnicodeError, ValueError, IndexError) as error:
        raise Refusal("invalid-process-metadata") from error
    if values.keys() != {"Uid", "Gid"} or any(value < 0 for value in values.values()):
        raise Refusal("invalid-process-metadata")
    return values["Uid"], values["Gid"]


def _observe_process(observer, pid):
    prefix = Path("/proc") / str(pid)
    ppid, start_ticks = _process_stat(
        _bounded_read(observer, prefix / "stat", SAMPLE_LIMITS["maxMetadataBytes"],
                      "process-metadata-unavailable"),
        pid,
    )
    uid, gid = _process_ids(
        _bounded_read(observer, prefix / "status", SAMPLE_LIMITS["maxMetadataBytes"],
                      "process-metadata-unavailable")
    )
    resolved = _bounded_link(
        observer, prefix / "exe", SAMPLE_LIMITS["maxMetadataBytes"],
        "executable-identity-unavailable",
    )
    try:
        executable = observer.executable_identity(prefix / "exe", resolved)
    except (OSError, KeyError) as error:
        raise Refusal("executable-identity-unavailable") from error
    _executable(executable)
    namespace = _bounded_link(
        observer, prefix / "ns" / "net", SAMPLE_LIMITS["maxMetadataBytes"],
        "namespace-identity-unavailable",
    )
    return {
        "pid": pid, "ppid": ppid, "uid": uid, "gid": gid,
        "startTicks": start_ticks, "executable": executable,
        "networkNamespace": namespace,
    }


def _selection(value):
    if (not isinstance(value, dict)
            or value.keys() != {"launchSourceRef", "listenerSourceRef", "roles", "routeForm"}
            or value["routeForm"] != "direct-primary"
            or any(not _nonempty(value[key], "incomplete-selection-source")
                   for key in ("launchSourceRef", "listenerSourceRef"))):
        raise Refusal("unsupported-selection-policy")
    expected = (
        ("helper", "invoked-helper"),
        ("app-server", "direct-parent-app-server"),
        ("desktop-main", "direct-parent-desktop-main"),
    )
    roles = value["roles"]
    if not isinstance(roles, list) or len(roles) != len(expected):
        raise Refusal("unsupported-launch-chain")
    for item, (role, discriminator) in zip(roles, expected):
        if (not isinstance(item, dict)
                or item.keys() != {"role", "discriminator", "evidenceRef", "executable"}
                or (item["role"], item["discriminator"]) != (role, discriminator)
                or not _nonempty(item["evidenceRef"], "role-evidence-unavailable")):
            raise Refusal("unsupported-launch-chain")
        _executable(item["executable"])
    return roles


def _walk_ancestry(observer, selection, effective_uid, started):
    roles = _selection(selection)
    pid = observer.getpid()
    if type(pid) is not int or pid <= 0 or observer.geteuid() != effective_uid:
        raise Refusal("invalid-invoked-helper-identity")
    ancestry = []
    for index, role in enumerate(roles):
        _watchdog(observer, started)
        process = _observe_process(observer, pid)
        if (process["uid"] != effective_uid
                or process["executable"] != role["executable"]):
            raise Refusal("unsupported-launch-chain")
        process.update(
            role=role["role"], roleEvidence=role["evidenceRef"],
            roleDiscriminator=role["discriminator"],
        )
        ancestry.append(process)
        if index + 1 < len(roles):
            if process["ppid"] <= 0:
                raise Refusal("unsupported-launch-chain")
            pid = process["ppid"]
    if len({item["networkNamespace"] for item in ancestry}) != 1:
        raise Refusal("cross-namespace-ancestry")
    return ancestry


def _parse_unix_table(data):
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeError as error:
        raise Refusal("invalid-unix-table") from error
    if not lines or len(lines) - 1 > SAMPLE_LIMITS["unixRows"]:
        raise Refusal("incomplete-or-oversized-sample")
    rows = []
    for line in lines[1:]:
        fields = line.split(None, 7)
        if len(fields) < 7:
            raise Refusal("invalid-unix-table")
        try:
            flags = int(fields[3], 16)
            inode = int(fields[6])
        except ValueError as error:
            raise Refusal("invalid-unix-table") from error
        rows.append({
            "flags": flags, "type": fields[4], "state": fields[5], "inode": inode,
            "path": fields[7] if len(fields) == 8 else "",
        })
    return rows


def _route_node(observer, path, kind, uid, mode):
    try:
        node = observer.lstat(path)
    except (OSError, KeyError) as error:
        raise Refusal("unsafe-direct-primary-route") from error
    kind_ok = stat.S_ISDIR(node.st_mode) if kind == "directory" else stat.S_ISSOCK(node.st_mode)
    if (not kind_ok or stat.S_ISLNK(node.st_mode) or stat.S_IMODE(node.st_mode) != mode
            or node.st_uid != uid):
        raise Refusal("unsafe-direct-primary-route")
    return {
        "path": str(path), "kind": kind, "uid": node.st_uid, "mode": mode,
        "symlink": False, "device": node.st_dev, "inode": node.st_ino,
    }


def _select_same_path_listener(observer, candidates, links, ancestry, started):
    if len(candidates) > MAX_SAME_PATH_LISTENERS or len({path for _, path in candidates}) != 1:
        raise Refusal("ambiguous-or-unsupported-listener")
    endpoint = candidates[0][1]
    namespaces = tuple(
        _bounded_link(
            observer, Path("/proc") / str(process["pid"]) / "ns" / "mnt",
            SAMPLE_LIMITS["maxMetadataBytes"], "listener-mount-namespace-unavailable",
        )
        for process in ancestry
    )
    if len(set(namespaces)) != 1:
        raise Refusal("cross-mount-namespace-ancestry")
    node = _route_node(observer, endpoint, "socket", ancestry[-1]["uid"], 0o600)
    major, minor = os.major(node["device"]), os.minor(node["device"])
    inodes = tuple(sorted(row["inode"] for row, _ in candidates))
    if (not 0 < node["inode"] <= MAX_U32 or not 0 <= major < 1 << 12
            or not 0 <= minor < 1 << 20 or len(set(inodes)) != len(inodes)
            or any(not 0 < inode <= MAX_U32 for inode in inodes)):
        raise Refusal("unsupported-listener-backing-identity")
    deadline = started + SAMPLE_LIMITS["sharedWatchdogMilliseconds"]
    proof = observer.observe_backing_nodes(endpoint, node, inodes, deadline)
    _watchdog(observer, started)
    if (not isinstance(proof, dict) or proof.keys() != set(inodes)
            or any(not isinstance(identity, tuple) or len(identity) != 4
                   or any(type(value) is not int or not 0 <= value <= MAX_U32
                          for value in identity)
                   for identity in proof.values())):
        raise Refusal("invalid-listener-backing-observation")
    target = node["inode"], (major << 20) | minor
    matches = [(row, path) for row, path in candidates if proof[row["inode"]][:2] == target]
    if len(matches) != 1:
        raise Refusal("ambiguous-or-unsupported-listener")
    after = _route_node(observer, endpoint, "socket", ancestry[-1]["uid"], 0o600)
    if after != node:
        raise Refusal("sample-identity-changed")
    # Both samples must agree on the candidate identities, not just on the
    # pathname or the final match.
    descriptors = tuple((inode, tuple(sorted(links[inode])), proof[inode]) for inode in inodes)
    evidence = (namespaces, node, descriptors)
    return matches[0], evidence


def _classify_listener_set(observer, ancestry, started, budget):
    desktop = ancestry[-1]
    fd_root = Path("/proc") / str(desktop["pid"]) / "fd"
    try:
        entries = observer.listdir(fd_root, budget["descriptorEntries"])
    except (OSError, KeyError) as error:
        raise Refusal("descriptor-enumeration-unavailable") from error
    if (not isinstance(entries, list) or len(entries) > budget["descriptorEntries"]
            or any(not isinstance(item, str) or not item.isdigit() for item in entries)):
        raise Refusal("incomplete-or-oversized-sample")
    links = {}
    link_bytes = 0
    for entry in entries:
        _watchdog(observer, started)
        remaining = budget["descriptorLinkBytes"] - link_bytes
        if remaining < 0:
            raise Refusal("incomplete-or-oversized-sample")
        value = _bounded_link(
            observer, fd_root / entry, remaining, "descriptor-enumeration-unavailable",
        )
        link_bytes += len(value.encode())
        if value.startswith("socket:[") and value.endswith("]"):
            try:
                links.setdefault(int(value[8:-1]), []).append(int(entry))
            except ValueError as error:
                raise Refusal("invalid-descriptor-link") from error
    if not links:
        raise Refusal("ambiguous-or-unsupported-listener")
    _watchdog(observer, started)
    unix_data = _bounded_read(
        observer, Path("/proc") / str(desktop["pid"]) / "net" / "unix",
        budget["unixBytes"], "incomplete-or-oversized-sample",
    )
    rows = _parse_unix_table(unix_data)
    if len(rows) > budget["unixRows"]:
        raise Refusal("incomplete-or-oversized-sample")
    # Linux __SO_ACCEPTCON distinguishes listening from merely unconnected streams.
    held = [row for row in rows if row["inode"] in links and row["flags"] & (1 << 16)
            and row["type"] == "0001"
            and row["state"] == "01" and row["path"]]
    direct_primary = []
    for row in held:
        endpoint = Path(row["path"])
        if (endpoint.is_absolute() and ".." not in endpoint.parts
                and str(endpoint) == row["path"]
                and endpoint.name == "ipc.sock" and endpoint.parent.name == "ipc"):
            direct_primary.append((row, endpoint))
    if not direct_primary:
        raise Refusal("ambiguous-or-unsupported-listener")
    backing = None
    if len(direct_primary) == 1:
        listener, endpoint = direct_primary[0]
    else:
        (listener, endpoint), backing = _select_same_path_listener(
            observer, direct_primary, links, ancestry, started,
        )
    listener_descriptors = links[listener["inode"]]
    descriptor = min(listener_descriptors) if backing is not None else listener_descriptors[-1]
    return {
        "backing": backing, "selectedDescriptor": descriptor,
        "entries": entries, "linkBytes": link_bytes,
        "unixData": unix_data, "rows": rows,
        "listener": listener, "endpoint": endpoint,
    }


def _collect_sample(observer, selection, effective_uid):
    started = observer.monotonic_milliseconds()
    if type(started) is not int or started < 0:
        raise Refusal("invalid-observation-clock")
    ancestry = _walk_ancestry(observer, selection, effective_uid, started)
    desktop = ancestry[-1]
    _watchdog(observer, started)
    boot = _bounded_read(
        observer, "/proc/sys/kernel/random/boot_id", SAMPLE_LIMITS["maxMetadataBytes"],
        "boot-identity-unavailable",
    ).decode("utf-8").strip()
    _nonempty(boot, "boot-identity-unavailable")
    initial = _classify_listener_set(observer, ancestry, started, SAMPLE_LIMITS)
    listener, endpoint = initial["listener"], initial["endpoint"]
    ipc_directory = _route_node(observer, endpoint.parent, "directory", effective_uid, 0o700)
    socket_node = _route_node(observer, endpoint, "socket", effective_uid, 0o600)
    selected_descriptor = initial["selectedDescriptor"]
    _watchdog(observer, started)
    try:
        final_ancestry = _walk_ancestry(observer, selection, effective_uid, started)
    except Refusal as error:
        if str(error) == "sample-watchdog-exceeded":
            raise
        raise Refusal("sample-identity-changed") from error
    final_boot = _bounded_read(
        observer, "/proc/sys/kernel/random/boot_id", SAMPLE_LIMITS["maxMetadataBytes"],
        "boot-identity-unavailable",
    ).decode("utf-8").strip()
    final = _classify_listener_set(observer, final_ancestry, started, SAMPLE_LIMITS)
    final_directory = _route_node(observer, endpoint.parent, "directory", effective_uid, 0o700)
    final_socket = _route_node(observer, endpoint, "socket", effective_uid, 0o600)
    finished = _watchdog(observer, started)
    initial_backing = initial["backing"]
    final_backing = final["backing"]
    if (final_ancestry != ancestry or final_boot != boot
            or final["listener"] != listener or final["endpoint"] != endpoint
            or final_backing != initial_backing
            or (initial_backing is not None and initial_backing[1] != socket_node)
            or (final_backing is not None and final_backing[1] != final_socket)
            or final["selectedDescriptor"] != selected_descriptor
            or final_directory != ipc_directory or final_socket != socket_node):
        raise Refusal("sample-identity-changed")
    aggregate = {
        "descriptorEntries": len(initial["entries"]) + len(final["entries"]),
        "unixRows": len(initial["rows"]) + len(final["rows"]),
        "unixBytes": len(initial["unixData"]) + len(final["unixData"]),
        "descriptorLinkBytes": initial["linkBytes"] + final["linkBytes"],
    }
    if any(aggregate[key] > maximum
           for key, maximum in AGGREGATE_SAMPLE_LIMITS.items()):
        raise Refusal("incomplete-or-oversized-sample")
    acceptor = {
        key: desktop[key] for key in ("pid", "uid", "gid", "startTicks", "executable")
    }
    acceptor.update(bootId=boot, networkNamespace=desktop["networkNamespace"])
    evidence = {
        "startedMilliseconds": started, "finishedMilliseconds": finished,
        "descriptorEntries": max(len(initial["entries"]), len(final["entries"])),
        "unixRows": max(len(initial["rows"]), len(final["rows"])),
        "unixBytes": max(len(initial["unixData"]), len(final["unixData"])),
        "descriptorLinkBytes": max(initial["linkBytes"], final["linkBytes"]),
        "selectedDescriptor": selected_descriptor, "socketInode": listener["inode"],
        "launchSourceRef": selection["launchSourceRef"],
        "listenerSourceRef": selection["listenerSourceRef"],
    }
    return endpoint, acceptor, evidence


def _identity(value):
    if (not isinstance(value, dict) or value.keys() != {"thread_id", "host_id"}
            or any(not _nonempty(item, "invalid-peer-identity") for item in value.values())):
        raise Refusal("invalid-peer-identity")
    return value


def _validate_permission_v2(name, value, request):
    required = {
        "evidenceRef", "issuer", "actor", "act", "chat", "operationId",
        "validityRef", "revocationRef", "consumer",
    }
    acts = {
        "metadata": (request["producer"], "acquire-route-metadata", "nomination-controller"),
        "nomination": (request["producer"], "publish-route-nomination", "codex-route-nomination"),
        "routeUse": (request["submitter"], "consume-route-nomination", "owner-admission-sender"),
    }
    actor, act, consumer = acts[name]
    if (not isinstance(value, dict) or value.keys() != required
            or value["actor"] != actor or value["chat"] != request["recipient"]
            or value["operationId"] != request["operationId"]
            or (value["act"], value["consumer"]) != (act, consumer)
            or not isinstance(value["issuer"], dict)
            or value["issuer"].keys() != {"thread_id", "host_id"}
            or any(not _nonempty(item, "incomplete-permission-evidence")
                   for item in value["issuer"].values())
            or any(not _nonempty(value[key], "incomplete-permission-evidence")
                   for key in ("evidenceRef", "validityRef", "revocationRef"))):
        raise Refusal("permission-binding-mismatch")


def _expected_invocation(value, request):
    required = {
        "control", "taskRef", "attemptId", "chat", "command", "workingDirectory", "helper",
    }
    if (not isinstance(value, dict) or value.keys() != required
            or value["control"] != "native-read-thread-command-execution"
            or value["chat"] != request["recipient"]
            or value["attemptId"] != request["operationId"]
            or any(not _nonempty(value[key], "incomplete-native-invocation")
                   for key in ("taskRef", "attemptId", "workingDirectory"))
            or not Path(value["workingDirectory"]).is_absolute()
            or not isinstance(value["command"], list)
            or any(not isinstance(item, str) or not item for item in value["command"])
            or not isinstance(value["helper"], dict)
            or value["helper"].keys() != {"path", "sha256"}
            or value["helper"]["path"] not in value["command"]
            or len(value["helper"]["sha256"]) != 64
            or any(char not in "0123456789abcdef" for char in value["helper"]["sha256"])):
        raise Refusal("incomplete-native-invocation")
    return value


def _publication(value, effective_uid):
    if (not isinstance(value, dict)
            or value.keys() != {"path", "ownerUid", "capture"}
            or type(value["ownerUid"]) is not int
            or value["ownerUid"] != effective_uid):
        raise Refusal("invalid-publication-custody")
    output = Path(value["path"])
    capture = value["capture"]
    if (not output.is_absolute() or not isinstance(capture, dict)
            or Path(capture.get("run_root", "")) != output.parent):
        raise Refusal("invalid-publication-custody")
    try:
        parent = output.parent.lstat()
    except OSError as error:
        raise Refusal("invalid-publication-custody") from error
    if (stat.S_ISLNK(parent.st_mode) or not stat.S_ISDIR(parent.st_mode)
            or stat.S_IMODE(parent.st_mode) != 0o700 or parent.st_uid != effective_uid):
        raise Refusal("invalid-publication-custody")
    return output, capture


def _prepare_v2(request, effective_uid, observer):
    required = {
        "schema", "invocation", "permissions", "recipient", "producer", "submitter",
        "operationId", "acquisitionHolds", "selection", "publication",
    }
    if (not isinstance(request, dict) or request.keys() != required
            or request["schema"] != "codex-route-nomination-request-v2"):
        raise Refusal("invalid-nomination-request")
    _identity(request["recipient"])
    _identity(request["producer"])
    _identity(request["submitter"])
    if request["producer"] != request["recipient"]:
        raise Refusal("producer-recipient-mismatch")
    _nonempty(request["operationId"], "invalid-operation-identity")
    if (not isinstance(request["acquisitionHolds"], list)
            or any(not isinstance(item, str) or not item
                   for item in request["acquisitionHolds"])
            or len(set(request["acquisitionHolds"])) != len(request["acquisitionHolds"])):
        raise Refusal("invalid-holds")
    invocation = _expected_invocation(request["invocation"], request)
    permissions = request["permissions"]
    if (not isinstance(permissions, dict)
            or permissions.keys() != {"metadata", "nomination", "routeUse"}):
        raise Refusal("incomplete-permission-evidence")
    for name, value in permissions.items():
        _validate_permission_v2(name, value, request)
    _selection(request["selection"])
    output, capture = _publication(request["publication"], effective_uid)
    endpoint, acceptor, evidence = _collect_sample(observer, request["selection"], effective_uid)
    record = {
        "schema": "codex-route-nomination-v2", "status": "provisional",
        "route": {"endpoint": str(endpoint), "host": "local",
                  "target": request["recipient"]["thread_id"]},
        "recipient": request["recipient"], "producer": request["producer"],
        "submitter": request["submitter"], "operationId": request["operationId"],
        "acceptor": acceptor,
        "expectedInvocation": invocation,
        "permissions": permissions, "acquisitionHolds": request["acquisitionHolds"],
        "freshness": {"observedAtMilliseconds": evidence["finishedMilliseconds"]},
        "acquisition": evidence,
        "privacy": {"boundary": "unix-account-private", "sameUidIsolation": False,
                    "pathIsAuthority": False},
        "retirement": {"scope": "original-invocation-staging-only"},
    }
    data = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    if len(data) > 4096:
        raise Refusal("nomination-record-byte-limit")
    return output, capture, record, data


def main(argv=None, *, effective_uid=None, observer=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True)
    arguments = parser.parse_args(argv)
    result = {"published": False, "reason": "invalid-nomination-request",
              "closure": "no-connection-opened"}
    try:
        request = json.loads(bounded_bytes(Path(arguments.request), "request-byte-limit"))
        uid = os.geteuid() if effective_uid is None else effective_uid
        if (not isinstance(request, dict)
                or request.get("schema") != "codex-route-nomination-request-v2"):
            raise Refusal("invalid-nomination-request")
        output, capture, record, expected = _prepare_v2(
            request, uid, ProcfsObservation() if observer is None else observer,
        )
        writer = CaptureWriter(capture)
        digest = writer.write_json(output, record)
        actual = output.read_bytes()
        observed = output.lstat()
        if (actual != expected or stat.S_IMODE(observed.st_mode) != 0o600
                or observed.st_uid != uid):
            raise Refusal("published-nomination-verification-failed")
        result = {
            "published": True, "reason": "published", "path": str(output),
            "bytes": len(actual), "sha256": digest, "closure": "no-connection-opened",
        }
    except FileExistsError:
        result["reason"] = "nomination-already-exists"
    except (Refusal, OSError, UnicodeError, ValueError, KeyError, TypeError, RecursionError) as error:
        result["reason"] = str(error)
    return print_result(result)


if __name__ == "__main__":
    sys.exit(main())
