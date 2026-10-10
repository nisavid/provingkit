"""Prepare and run one cooperative fake amendment observation; no native route.

The fixture and its command are operator inputs. Hash binding is ordinary
reproducibility, not containment or enforcement against a hostile fixture.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import sys
import time
import types


HERE = Path(__file__).resolve().parent
TRANSPORT = HERE.parent / "jev-axi-commit-observation-2026-10-02/transport.py"
TRANSPORT_SHA256 = "0b6dada830dd6dbdff4cb2c4ccd444c6680044ddb00a08041c39c40514a49d8f"
SEED_PRODUCER_SHA256 = "3072c63a15a86d5c4094a57cbe0954543b4f1cc28707210a130dba0d799ce6c4"
TOOLS = {"commandExecution", "fileChange", "mcpToolCall", "dynamicToolCall",
         "collabAgentToolCall", "webSearch", "imageView", "sleep", "imageGeneration"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode()


def put(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)


def checked(path, expected):
    raw = path.read_bytes()
    require(sha(raw) == expected, "identity differs: " + str(path))
    return raw


def relative(root, name):
    require(isinstance(name, str) and name and "\\" not in name,
            "invalid declared path")
    path = PurePosixPath(name)
    require(not path.is_absolute() and all(p not in ("", ".", "..")
            for p in name.split("/")), "invalid declared path")
    target = root.joinpath(*path.parts)
    require(target.resolve() == target.absolute(), "symlink in declared path")
    return target


def fake_profile(raw):
    profile = json.loads(raw)
    fields = {"kind", "command", "python_sha256", "fixture_sha256"}
    native_shaped = profile.get("kind") == "cooperative-native-app-server-fake/v1"
    require((set(profile) == fields and profile["kind"] == "cooperative-python-fake/v1")
            or (native_shaped and set(profile) == fields | {"app_server_profile"}),
            "only an explicitly selected cooperative Python fake is supported; native is unqualified")
    if native_shaped:
        expected = profile["app_server_profile"]
        require(isinstance(expected, dict)
                and set(expected) in ({"schema", "version"},
                                      {"schema", "version", "model", "effort"},
                                      {"schema", "version", "model", "effort", "observe_turn"})
                and expected["schema"] == "compatibility-native-protocol-profile/v1"
                and isinstance(expected["version"], str) and expected["version"],
                "invalid synthetic native metadata profile")
        if "model" in expected:
            require(all(isinstance(expected[key], str) and expected[key]
                        for key in ("model", "effort")),
                    "invalid synthetic model or effort")
        if "observe_turn" in expected:
            require(type(expected["observe_turn"]) is bool,
                    "synthetic observe_turn must be a Boolean")
    command = profile["command"]
    require(isinstance(command, list) and len(command) == 5
            and command[:4] == [sys.executable, "-I", "-S", "-u"],
            "unsupported fake command")
    fixture = Path(command[4])
    require(fixture.is_absolute() and fixture.resolve() == fixture
            and fixture.suffix == ".py", "absolute regular Python fixture required")
    checked(Path(sys.executable), profile["python_sha256"])
    return profile, fixture, checked(fixture, profile["fixture_sha256"])


def prepare(args):
    packet = args.seed_package.resolve()
    receipt_raw = checked(packet / "receipt.json", args.seed_receipt_sha256)
    receipt = json.loads(receipt_raw)
    require(receipt["version"] == 1 and receipt["status"] == "ready"
            and receipt["producer_sha256"] == SEED_PRODUCER_SHA256,
            "unsupported seed preparation")
    spec_raw = checked(packet / "spec.json", receipt["spec_sha256"])
    profile_raw = checked(args.profile, args.profile_sha256)
    profile, fixture, fixture_raw = fake_profile(profile_raw)
    checked(TRANSPORT, TRANSPORT_SHA256)
    checked(HERE / "prepare_seed.py", SEED_PRODUCER_SHA256)
    entries = receipt["seed"]["files"]
    names = [entry["path"] for entry in entries]
    require(names == sorted(set(names)) and names, "invalid seed file list")
    identities = [{key: entry[key] for key in ("path", "sha256", "executable")}
                  for entry in entries]
    require(sha(encoded(identities)) == receipt["seed"]["identity"], "seed identity differs")
    selected = args.implementation
    require(selected and len(set(selected)) == len(selected) and set(selected) <= set(names),
            "implementation paths must name unique declared seed files")
    seed = []
    for entry in entries:
        path = relative(packet / "seed", entry["path"])
        raw = checked(path, entry["sha256"])
        require(bool(path.stat().st_mode & 0o111) == entry["executable"],
                "seed executable mode differs")
        seed.append((entry, path, raw))
    require(len(receipt["requests"]) == 2, "exactly two ordered requests required")
    requests = [(relative(packet, entry["output"]), entry)
                for entry in receipt["requests"]]
    request_bytes = [checked(path, entry["sha256"]) for path, entry in requests]
    for raw in request_bytes:
        raw.decode("utf-8")
    output = args.output.absolute()
    require(output.resolve() == output, "output must not traverse symlinks")
    inputs = [packet, args.profile.resolve(), fixture, HERE, TRANSPORT]
    require(all(output != path and output not in path.parents and path not in output.parents
                for path in inputs), "output overlaps an input")
    sources = {str(path): sha(path.read_bytes()) for path in
               [Path(__file__).resolve(), HERE / "prepare_seed.py", TRANSPORT,
                Path(sys.executable), args.profile.resolve(), fixture,
                packet / "receipt.json", packet / "spec.json",
                *(path for _, path, _ in seed), *(path for path, _ in requests)]}
    output.mkdir(exist_ok=False)
    put(output / "seed-receipt.json", receipt_raw)
    put(output / "seed-spec.json", spec_raw)
    put(output / "profile.json", profile_raw)
    put(output / "fixture.py", fixture_raw)
    for entry, _, raw in seed:
        path = relative(output / "project", entry["path"])
        put(path, raw)
        path.chmod(entry["mode"])
    for index, raw in enumerate(request_bytes):
        put(output / f"request-{index}.bin", raw)
    manifest = {"schema": "compatibility-fake-observation/v1",
        "root": str(output), "source_sha256": sources,
        "seed_receipt_sha256": sha(receipt_raw), "seed_spec_sha256": sha(spec_raw),
        "seed_identity": receipt["seed"]["identity"],
        "profile_sha256": sha(profile_raw), "fixture_sha256": sha(fixture_raw),
        "request_sha256": [sha(raw) for raw in request_bytes],
        "initial_files": {entry["path"]: entry["sha256"] for entry in entries},
        "implementation_paths": sorted(selected), "deadline_seconds": 10,
        "command": [sys.executable, "-I", "-S", "-u", str(output / "fixture.py")],
        "native_execution_authorized": False, "profile_qualification": "cooperative-fake-only"}
    raw = encoded(manifest) + b"\n"
    put(output / "manifest.json", raw)
    return {"manifest": str(output / "manifest.json"), "sha256": sha(raw)}


def run(args):
    raw = checked(args.manifest, args.expected_sha256)
    manifest = json.loads(raw)
    root = args.manifest.resolve().parent
    require(manifest["schema"] == "compatibility-fake-observation/v1"
            and manifest["root"] == str(root)
            and manifest["native_execution_authorized"] is False
            and manifest["profile_qualification"] == "cooperative-fake-only",
            "native execution is not qualified")
    attempt = root / "attempt"
    attempt.mkdir(exist_ok=False)
    state = {"status": "incomplete", "thread_id": None, "turn_id": None,
             "amendment_rpc_accepted": False, "semantic_success": "not-assessed",
             "trigger_observation_sequence": None}
    try:
        for name, expected in manifest["source_sha256"].items():
            checked(Path(name), expected)
        profile_raw = checked(root / "profile.json", manifest["profile_sha256"])
        profile, _, _ = fake_profile(profile_raw)
        checked(root / "fixture.py", profile["fixture_sha256"])
        require(manifest["fixture_sha256"] == profile["fixture_sha256"]
                and manifest["command"] == [sys.executable, "-I", "-S", "-u",
                                           str(root / "fixture.py")],
                "prepared command differs")
        receipt = json.loads(checked(root / "seed-receipt.json", manifest["seed_receipt_sha256"]))
        checked(root / "seed-spec.json", manifest["seed_spec_sha256"])
        project = root / "project"
        for name, expected in manifest["initial_files"].items():
            checked(relative(project, name), expected)
        for entry in receipt["seed"]["files"]:
            path = relative(project, entry["path"])
            mode = stat.S_IMODE(path.stat().st_mode)
            require(mode == entry["mode"] and bool(mode & 0o111) == entry["executable"],
                    f"seed file mode differs: {path} (expected {entry['mode']:04o}, got {mode:04o})")
        requests = [checked(root / f"request-{index}.bin", expected).decode("utf-8")
                    for index, expected in enumerate(manifest["request_sha256"])]
        require(len(requests) == 2, "exactly two requests required")
        transport = types.ModuleType("bound_compatibility_transport")
        transport_raw = checked(TRANSPORT, TRANSPORT_SHA256)
        exec(compile(transport_raw, str(TRANSPORT), "exec"), transport.__dict__)
        with (attempt / "receipts.jsonl").open("xb") as journal:
            sequence, received_offset, sent_offset = 0, 0, 0
            pending = {}

            def record(kind, **fields):
                nonlocal sequence
                row = {"sequence": sequence, "observed_at": datetime.now(timezone.utc).isoformat(),
                       "kind": kind, **fields}
                journal.write(encoded(row) + b"\n")
                journal.flush()
                sequence += 1
                return row["sequence"]

            def wire(filename, offset):
                with (attempt / filename).open("rb") as stream:
                    stream.seek(offset)
                    line = stream.readline()
                require(line.endswith(b"\n"), "incomplete retained protocol line")
                return {"file": filename, "offset": offset, "bytes": len(line), "sha256": sha(line)}

            def send(raw_send, message):
                nonlocal sent_offset
                if "id" in message:
                    require(message["id"] not in pending, "duplicate outbound RPC")
                    pending[message["id"]] = message["method"]
                raw_send(message)
                reference = wire("collector-sent.jsonl", sent_offset)
                sent_offset += reference["bytes"]
                record("sent", message=message, wire=reference)

            def begin(raw_send):
                send(raw_send, {"id": 1, "method": "initialize", "params": {
                    "clientInfo": {"name": "compatibility-fake-observation", "version": "1"},
                    "capabilities": {"experimentalApi": True}}})

            def receive(message, raw_send):
                nonlocal received_offset
                reference = wire("collector-stdout.log", received_offset)
                received_offset += reference["bytes"]
                event_sequence = record("received", message=message, wire=reference)
                method, ident = message.get("method"), message.get("id")
                require(not (method is not None and ident is not None),
                        "server input request is unsupported and remains unanswered")
                if ident is not None:
                    require(ident in pending and "result" in message and "error" not in message,
                            "unexpected or rejected RPC response")
                    request = pending.pop(ident)
                    if request == "initialize":
                        if profile["kind"] == "cooperative-native-app-server-fake/v1":
                            expected = profile["app_server_profile"]["version"]
                            observed = message["result"].get("userAgent")
                            require(observed == expected,
                                    f"server version differs: expected {expected}, observed {observed}")
                            if "model" not in profile["app_server_profile"]:
                                raise ValueError("native-shaped fake metadata sequence is incomplete")
                            send(raw_send, {"method": "initialized"})
                            send(raw_send, {"id": 2, "method": "model/list", "params": {
                                "cursor": None, "includeHidden": True}})
                            return False
                        send(raw_send, {"method": "initialized"})
                        send(raw_send, {"id": 2, "method": "thread/start",
                                        "params": {"cwd": str(project)}})
                    elif request == "model/list":
                        catalog = message["result"]
                        require(catalog.get("nextCursor") is None
                                and isinstance(catalog.get("data"), list),
                                "complete synthetic model catalog required; paging is unqualified")
                        expected = profile["app_server_profile"]
                        matches = [model for model in catalog["data"]
                                   if model.get("model") == expected["model"]]
                        require(len(matches) == 1,
                                f"model unavailable or ambiguous: expected {expected['model']}")
                        efforts = [item["reasoningEffort"]
                                   for item in matches[0]["supportedReasoningEfforts"]]
                        require(expected["effort"] in efforts,
                                f"effort unavailable for {expected['model']}: "
                                f"expected {expected['effort']}, observed {efforts}")
                        send(raw_send, {"id": 10, "method": "config/read", "params": {
                            "cwd": str(project), "includeLayers": False}})
                    elif request == "config/read":
                        config = message["result"]
                        require(isinstance(config.get("config"), dict)
                                and isinstance(config.get("origins"), dict),
                                "synthetic effective config and origins required")
                        send(raw_send, {"id": 11, "method": "configRequirements/read"})
                    elif request == "configRequirements/read":
                        result = message["result"]
                        require(isinstance(result, dict)
                                and (result.get("requirements") is None
                                     or isinstance(result["requirements"], dict)),
                                "invalid synthetic requirements observation")
                        send(raw_send, {"id": 12, "method": "skills/list", "params": {
                            "cwds": [str(project)], "forceReload": False}})
                    elif request == "skills/list":
                        require(isinstance(message["result"].get("data"), list),
                                "synthetic skills inventory required")
                        send(raw_send, {"id": 13, "method": "mcpServerStatus/list", "params": {
                            "cursor": None, "detail": "full"}})
                    elif request == "mcpServerStatus/list":
                        inventory = message["result"]
                        require(isinstance(inventory.get("data"), list)
                                and inventory.get("nextCursor") is None,
                                "complete synthetic MCP inventory required; paging is unqualified")
                        send(raw_send, {"id": 14, "method": "thread/start", "params": {
                            "cwd": str(project), "model": profile["app_server_profile"]["model"],
                            "allowProviderModelFallback": False}})
                    elif request == "thread/start":
                        state["thread_id"] = message["result"]["thread"]["id"]
                        if profile["kind"] == "cooperative-native-app-server-fake/v1":
                            result = message["result"]
                            expected = profile["app_server_profile"]
                            require(result["model"] == expected["model"],
                                    f"thread model differs: expected {expected['model']}, "
                                    f"observed {result['model']}")
                            state["profile_observation_sequence"] = record(
                                "fake-profile-observed", response_sequence=event_sequence,
                                requested_model=expected["model"],
                                requested_turn_effort=expected["effort"],
                                effective_profile={key: value for key, value in result.items()
                                                   if key != "thread"})
                            if not expected.get("observe_turn", False):
                                state["status"] = "fake-profile-observed"
                                return True
                        params = {
                            "threadId": state["thread_id"], "input": [
                                {"type": "text", "text": requests[0], "text_elements": []}]}
                        if profile["kind"] == "cooperative-native-app-server-fake/v1":
                            params.update(model=expected["model"], effort=expected["effort"])
                        send(raw_send, {"id": 3, "method": "turn/start", "params": params})
                    elif request == "turn/start":
                        state["turn_id"] = message["result"]["turn"]["id"]
                    elif request == "turn/steer":
                        returned = message["result"]["turnId"]
                        require(returned == state["turn_id"], "steer returned another turn")
                        state["amendment_rpc_accepted"] = True
                        record("amendment-rpc-accepted", response_sequence=event_sequence,
                               returned_turn_id=returned, semantic_success="not-assessed")
                elif method == "item/completed":
                    data = message["params"]
                    item = data.get("item", {})
                    if (data.get("threadId") == state["thread_id"]
                            and data.get("turnId") == state["turn_id"]
                            and state["turn_id"] is not None and item.get("type") in TOOLS):
                        changed = {}
                        for name in manifest["implementation_paths"]:
                            path = relative(project, name)
                            after = sha(path.read_bytes()) if path.exists() else None
                            before = manifest["initial_files"][name]
                            if after != before:
                                changed[name] = {"before": before, "after": after}
                        observed = record("tool-completed", event_sequence=event_sequence,
                            thread_id=state["thread_id"], turn_id=state["turn_id"],
                            item=item, item_sha256=sha(encoded(item)), changed=changed)
                        if changed and state["trigger_observation_sequence"] is None:
                            state["trigger_observation_sequence"] = observed
                            record("amendment-trigger", observation_sequence=observed)
                            send(raw_send, {"id": 4, "method": "turn/steer", "params": {
                                "threadId": state["thread_id"], "expectedTurnId": state["turn_id"],
                                "input": [{"type": "text", "text": requests[1], "text_elements": []}]}})
                elif method == "turn/completed":
                    data = message["params"]
                    if data.get("threadId") == state["thread_id"]:
                        turn = data["turn"]
                        require(turn["id"] == state["turn_id"] and turn["status"] == "completed"
                                and turn.get("error") is None, "turn did not complete successfully")
                        require(state["amendment_rpc_accepted"] and not pending,
                                "turn ended without an accepted amendment")
                        record("turn-completed", event_sequence=event_sequence)
                        return True
                return False

            transport.collect(manifest["command"], project, attempt, "collector",
                              time.monotonic() + manifest["deadline_seconds"],
                              on_line=receive, begin=begin)
        if state["status"] == "incomplete":
            state["status"] = "fake-observation-completed"
        return state
    except Exception as error:
        state["error"] = type(error).__name__ + ": " + str(error)
        raise
    finally:
        put(attempt / "outcome.json", encoded(state) + b"\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    preparation = commands.add_parser("prepare")
    preparation.add_argument("--seed-package", type=Path, required=True)
    preparation.add_argument("--seed-receipt-sha256", required=True)
    preparation.add_argument("--profile", type=Path, required=True)
    preparation.add_argument("--profile-sha256", required=True)
    preparation.add_argument("--implementation", action="append", required=True)
    preparation.add_argument("--output", type=Path, required=True)
    execution = commands.add_parser("run")
    execution.add_argument("--manifest", type=Path, required=True)
    execution.add_argument("--expected-sha256", required=True)
    args = parser.parse_args()
    try:
        result = prepare(args) if args.operation == "prepare" else run(args)
    except Exception as error:
        print(type(error).__name__ + ": " + str(error), file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
