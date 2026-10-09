"""Public preparation/run CLI contract; no provider or native model."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
COLLECTOR = HERE / "collect_observation.py"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode()


class CollectorCLI(unittest.TestCase):
    def prepare_failure_fixture(self, tail, seed_mode=0o644, mark_launch=False):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name)
        seed = base / "seed"
        seed.mkdir()
        initial = b"DEFAULT = 'text'\n"
        (seed / "inventory.py").write_bytes(initial)
        (seed / "inventory.py").chmod(seed_mode)
        entries = [{"path": "inventory.py", "sha256": sha(initial),
                    "executable": bool(seed_mode & 0o111)}]
        requests = []
        for index, text in enumerate([b"Add JSON output.", b"Preserve the existing default."]):
            (base / str(index)).write_bytes(text)
            requests.append({"path": str(index), "sha256": sha(text)})
        spec = {"version": 1, "seed": {"path": "seed", "files": entries,
                "identity": sha(encoded(entries))}, "requests": requests,
                "observation_cases": [], "constructed_candidates": []}
        (base / "spec.json").write_bytes(encoded(spec))
        packet, output = base / "packet", base / "observation"
        def cli(*args):
            return subprocess.run([sys.executable, "-B", *map(str, args)],
                                  capture_output=True, timeout=15)
        prepared = cli(HERE / "prepare_seed.py", "--spec", base / "spec.json", "--output", packet)
        self.assertEqual(prepared.returncode, 0, prepared.stderr.decode())
        fixture = base / "fake.py"
        launch_marker = ("from pathlib import Path\n"
                         "Path(__file__).with_name('fake-launched').write_text('launched')\n"
                         if mark_launch else "")
        fixture.write_text(launch_marker + """import json
from pathlib import Path
import sys

def receive():
    return json.loads(sys.stdin.buffer.readline())

def emit(value):
    sys.stdout.buffer.write((json.dumps(value) + "\\n").encode())
    sys.stdout.buffer.flush()

first = receive()
emit({"id": first["id"], "result": {}})
receive()
thread = receive()
emit({"id": thread["id"], "result": {"thread": {"id": "thread-1"}}})
task = receive()
emit({"id": task["id"], "result": {"turn": {"id": "turn-1"}}})
""" + tail)
        profile = {"kind": "cooperative-python-fake/v1",
                   "command": [sys.executable, "-I", "-S", "-u", str(fixture)],
                   "python_sha256": sha(Path(sys.executable).read_bytes()),
                   "fixture_sha256": sha(fixture.read_bytes())}
        profile_path = base / "profile.json"
        profile_path.write_bytes(encoded(profile))
        prepared = cli(COLLECTOR, "prepare", "--seed-package", packet,
                       "--seed-receipt-sha256", sha((packet / "receipt.json").read_bytes()),
                       "--profile", profile_path, "--profile-sha256", sha(profile_path.read_bytes()),
                       "--implementation", "inventory.py", "--output", output)
        self.assertEqual(prepared.returncode, 0, prepared.stderr.decode())
        run = (COLLECTOR, "run", "--manifest", output / "manifest.json",
               "--expected-sha256", sha((output / "manifest.json").read_bytes()))
        return cli, run, output

    def test_seed_mode_drift_is_rejected_before_launch_and_preserves_attempt(self):
        for original, changed in ((0o755, 0o644), (0o755, 0o744), (0o644, 0o755)):
            with self.subTest(original=oct(original), changed=oct(changed)):
                cli, run, output = self.prepare_failure_fixture(
                    "raise AssertionError('must not launch')\n",
                    seed_mode=original, mark_launch=True)
                project_file = output / "project" / "inventory.py"
                initial = project_file.read_bytes()
                self.assertEqual(project_file.stat().st_mode & 0o7777, original)
                project_file.chmod(changed)
                self.assertEqual(project_file.read_bytes(), initial)
                self.assertNotEqual(cli(*run).returncode, 0)
                attempt = output / "attempt"
                outcome_raw = (attempt / "outcome.json").read_bytes()
                outcome = json.loads(outcome_raw)
                self.assertEqual(outcome["status"], "incomplete")
                self.assertIn("seed file mode differs", outcome["error"])
                self.assertIn("inventory.py", outcome["error"])
                self.assertIsNone(outcome["thread_id"])
                self.assertIsNone(outcome["turn_id"])
                self.assertFalse(outcome["amendment_rpc_accepted"])
                self.assertFalse((output / "fake-launched").exists())
                self.assertFalse((attempt / "collector-process.json").exists())
                self.assertFalse((attempt / "collector-sent.jsonl").exists())
                self.assertFalse((attempt / "collector-stdout.log").exists())
                self.assertNotEqual(cli(*run).returncode, 0)
                self.assertEqual((attempt / "outcome.json").read_bytes(), outcome_raw)
                self.assertEqual(project_file.read_bytes(), initial)
                self.assertEqual(project_file.stat().st_mode & 0o7777, changed)

    def test_completed_turn_race_preserves_attempt_without_resending_amendment(self):
        cli, run, output = self.prepare_failure_fixture("""
Path("inventory.py").write_text("DEFAULT = 'json'\\n")
changed = {"method": "item/completed", "params": {"threadId": "thread-1", "turnId": "turn-1",
    "item": {"type": "commandExecution", "id": "change", "status": "completed"}}}
completed = {"method": "turn/completed", "params": {"threadId": "thread-1",
    "turn": {"id": "turn-1", "status": "completed", "error": None}}}
sys.stdout.buffer.write((json.dumps(changed) + "\\n" + json.dumps(completed) + "\\n").encode())
sys.stdout.buffer.flush()
sys.stdin.buffer.read()
""")
        result = cli(*run)
        self.assertNotEqual(result.returncode, 0)
        attempt = output / "attempt"
        outcome_raw = (attempt / "outcome.json").read_bytes()
        outcome = json.loads(outcome_raw)
        self.assertEqual(outcome["status"], "incomplete")
        self.assertFalse(outcome["amendment_rpc_accepted"])
        self.assertEqual(outcome["semantic_success"], "not-assessed")
        self.assertIn("turn ended without an accepted amendment", outcome["error"])
        sent_raw = (attempt / "collector-sent.jsonl").read_bytes()
        sent = [json.loads(line) for line in sent_raw.splitlines()]
        self.assertEqual([item["method"] for item in sent].count("turn/start"), 1)
        self.assertEqual([item["method"] for item in sent].count("turn/steer"), 1)
        received = [json.loads(line) for line in (attempt / "collector-stdout.log").read_bytes().splitlines()]
        self.assertEqual(received[-1]["method"], "turn/completed")
        self.assertNotEqual(cli(*run).returncode, 0)
        self.assertEqual((attempt / "outcome.json").read_bytes(), outcome_raw)
        self.assertEqual((attempt / "collector-sent.jsonl").read_bytes(), sent_raw)

    def test_rejected_steering_retains_error_and_does_not_start_another_turn(self):
        cli, run, output = self.prepare_failure_fixture("""
Path("inventory.py").write_text("DEFAULT = 'json'\\n")
emit({"method": "item/completed", "params": {"threadId": "thread-1", "turnId": "turn-1",
    "item": {"type": "commandExecution", "id": "change", "status": "completed"}}})
steer = receive()
emit({"id": steer["id"], "error": {"code": -32000, "message": "turn is no longer active"}})
sys.stdin.buffer.read()
""")
        self.assertNotEqual(cli(*run).returncode, 0)
        attempt = output / "attempt"
        outcome = json.loads((attempt / "outcome.json").read_bytes())
        self.assertEqual(outcome["status"], "incomplete")
        self.assertFalse(outcome["amendment_rpc_accepted"])
        sent = [json.loads(line) for line in (attempt / "collector-sent.jsonl").read_bytes().splitlines()]
        self.assertEqual([item["method"] for item in sent],
                         ["initialize", "initialized", "thread/start", "turn/start", "turn/steer"])
        received = [json.loads(line) for line in (attempt / "collector-stdout.log").read_bytes().splitlines()]
        self.assertEqual(received[-1], {"id": 4, "error": {
            "code": -32000, "message": "turn is no longer active"}})
        rows = [json.loads(line) for line in (attempt / "receipts.jsonl").read_bytes().splitlines()]
        self.assertEqual(rows[-1]["message"], received[-1])
        self.assertFalse(any(row["kind"] == "amendment-rpc-accepted" for row in rows))

    def test_permission_request_remains_unanswered_and_retained(self):
        cli, run, output = self.prepare_failure_fixture("""
emit({"id": 99, "method": "item/commandExecution/requestApproval", "params": {
    "threadId": "thread-1", "turnId": "turn-1", "itemId": "edit", "reason": "fixture permission"}})
sys.stdin.buffer.read()
""")
        self.assertNotEqual(cli(*run).returncode, 0)
        attempt = output / "attempt"
        outcome = json.loads((attempt / "outcome.json").read_bytes())
        self.assertEqual(outcome["status"], "incomplete")
        self.assertIn("remains unanswered", outcome["error"])
        sent = [json.loads(line) for line in (attempt / "collector-sent.jsonl").read_bytes().splitlines()]
        self.assertEqual([item["method"] for item in sent],
                         ["initialize", "initialized", "thread/start", "turn/start"])
        self.assertFalse(any(item.get("id") == 99 for item in sent))
        rows = [json.loads(line) for line in (attempt / "receipts.jsonl").read_bytes().splitlines()]
        request = rows[-1]["message"]
        self.assertEqual(request["id"], 99)
        self.assertEqual(request["method"], "item/commandExecution/requestApproval")
        self.assertIsNone(outcome["trigger_observation_sequence"])

    def test_profile_drift_is_recorded_before_launch_and_preserves_failed_attempt(self):
        cli, run, output = self.prepare_failure_fixture("raise AssertionError('must not launch')\n")
        profile = output.parent / "profile.json"
        profile.write_bytes(profile.read_bytes() + b" ")
        self.assertNotEqual(cli(*run).returncode, 0)
        attempt = output / "attempt"
        outcome_raw = (attempt / "outcome.json").read_bytes()
        outcome = json.loads(outcome_raw)
        self.assertEqual(outcome["status"], "incomplete")
        self.assertIn("identity differs:", outcome["error"])
        self.assertIn("profile.json", outcome["error"])
        self.assertIsNone(outcome["thread_id"])
        self.assertFalse((attempt / "collector-sent.jsonl").exists())
        self.assertFalse((attempt / "collector-process.json").exists())
        self.assertNotEqual(cli(*run).returncode, 0)
        self.assertEqual((attempt / "outcome.json").read_bytes(), outcome_raw)

    def test_native_profile_is_refused_before_preparation(self):
        cli, _, output = self.prepare_failure_fixture("raise AssertionError('must not launch')\n")
        profile_path = output.parent / "profile.json"
        profile = json.loads(profile_path.read_bytes())
        profile["kind"] = "native-app-server"
        profile_path.write_bytes(encoded(profile))
        packet = output.parent / "packet"
        rejected = output.parent / "native-rejected"
        result = cli(COLLECTOR, "prepare", "--seed-package", packet,
                     "--seed-receipt-sha256", sha((packet / "receipt.json").read_bytes()),
                     "--profile", profile_path, "--profile-sha256", sha(profile_path.read_bytes()),
                     "--implementation", "inventory.py", "--output", rejected)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"native is unqualified", result.stderr)
        self.assertFalse(rejected.exists())
        self.assertFalse((output / "attempt").exists())

    def test_native_shaped_fake_version_mismatch_refuses_task_and_retains_attempt(self):
        cli, _, legacy_output = self.prepare_failure_fixture("sys.stdin.buffer.read()\n")
        base = legacy_output.parent
        fixture = base / "fake.py"
        fixture.write_text(r'''import json
import sys

initial = json.loads(sys.stdin.buffer.readline())
assert initial["method"] == "initialize", initial
sys.stdout.buffer.write((json.dumps({
    "id": initial["id"], "result": {"userAgent": "synthetic-native/other"}
}) + "\n").encode())
sys.stdout.buffer.flush()
sys.stdin.buffer.read()
''')
        profile_path = base / "profile.json"
        profile = json.loads(profile_path.read_bytes())
        profile["kind"] = "cooperative-native-app-server-fake/v1"
        profile["fixture_sha256"] = sha(fixture.read_bytes())
        profile["app_server_profile"] = {
            "schema": "compatibility-native-protocol-profile/v1",
            "version": "synthetic-native/expected"}
        profile_path.write_bytes(encoded(profile))
        packet, output = base / "packet", base / "native-shaped-observation"
        prepared = cli(COLLECTOR, "prepare", "--seed-package", packet,
                       "--seed-receipt-sha256", sha((packet / "receipt.json").read_bytes()),
                       "--profile", profile_path, "--profile-sha256", sha(profile_path.read_bytes()),
                       "--implementation", "inventory.py", "--output", output)
        self.assertEqual(prepared.returncode, 0, prepared.stderr.decode())
        run = (COLLECTOR, "run", "--manifest", output / "manifest.json",
               "--expected-sha256", sha((output / "manifest.json").read_bytes()))
        result = cli(*run)
        self.assertNotEqual(result.returncode, 0, result.stdout.decode())
        attempt = output / "attempt"
        outcome = json.loads((attempt / "outcome.json").read_bytes())
        self.assertEqual(outcome["status"], "incomplete")
        self.assertIsNone(outcome["turn_id"])
        self.assertIn("version", outcome["error"])
        self.assertIn("synthetic-native/expected", outcome["error"])
        self.assertIn("synthetic-native/other", outcome["error"])
        sent = [json.loads(line) for line in
                (attempt / "collector-sent.jsonl").read_bytes().splitlines()]
        self.assertEqual(sent[0]["method"], "initialize")
        self.assertFalse(any(message["method"] == "turn/start" for message in sent))
        received = [json.loads(line) for line in
                    (attempt / "collector-stdout.log").read_bytes().splitlines()]
        self.assertEqual(received[0], {"id": sent[0]["id"], "result": {
            "userAgent": "synthetic-native/other"}})

    def test_native_shaped_fake_catalog_ending_controls_effort_check(self):
        for cursor_present, cursor in ((True, None), (False, None), (True, "next-page")):
            with self.subTest(cursor_present=cursor_present, cursor=cursor):
                cli, _, legacy_output = self.prepare_failure_fixture("sys.stdin.buffer.read()\n")
                base = legacy_output.parent
                catalog = {"data": [{
                    "id": "synthetic-sol", "model": "gpt-6.1-sol",
                    "displayName": "Synthetic Sol", "description": "Synthetic catalog only",
                    "hidden": False, "isDefault": True, "defaultReasoningEffort": "low",
                    "supportedReasoningEfforts": [
                        {"reasoningEffort": "low", "description": "Synthetic low effort"}],
                }], "nextCursor": None}
                if cursor_present:
                    catalog["nextCursor"] = cursor
                else:
                    del catalog["nextCursor"]
                initialize = {"userAgent": "synthetic-native/expected",
                              "codexHome": "/synthetic/codex",
                              "platformFamily": "unix", "platformOs": "linux"}
                fixture = base / "fake.py"
                fixture.write_text("INITIALIZE = " + repr(initialize) + "\n"
                                   + "CATALOG = " + repr(catalog) + "\n" + r'''
import json
import sys

def receive(method):
    message = json.loads(sys.stdin.buffer.readline())
    assert message["method"] == method, message
    return message

def emit(value):
    sys.stdout.buffer.write((json.dumps(value) + "\n").encode())
    sys.stdout.buffer.flush()

first = receive("initialize")
emit({"id": first["id"], "result": INITIALIZE})
initialized = receive("initialized")
assert "id" not in initialized, initialized
listing = receive("model/list")
assert listing["params"].get("cursor") is None, listing
assert listing["params"].get("includeHidden") is True, listing
emit({"id": listing["id"], "result": CATALOG})
# Stay alive until the collector closes its owned process.
sys.stdin.buffer.read()
''')
                profile_path = base / "profile.json"
                profile = json.loads(profile_path.read_bytes())
                profile["kind"] = "cooperative-native-app-server-fake/v1"
                profile["fixture_sha256"] = sha(fixture.read_bytes())
                profile["app_server_profile"] = {
                    "schema": "compatibility-native-protocol-profile/v1",
                    "version": "synthetic-native/expected",
                    "model": "gpt-6.1-sol", "effort": "medium"}
                profile_path.write_bytes(encoded(profile))
                packet, output = base / "packet", base / "unsupported-effort-observation"
                prepared = cli(COLLECTOR, "prepare", "--seed-package", packet,
                               "--seed-receipt-sha256", sha((packet / "receipt.json").read_bytes()),
                               "--profile", profile_path, "--profile-sha256", sha(profile_path.read_bytes()),
                               "--implementation", "inventory.py", "--output", output)
                self.assertEqual(prepared.returncode, 0, prepared.stderr.decode())
                result = cli(COLLECTOR, "run", "--manifest", output / "manifest.json",
                             "--expected-sha256", sha((output / "manifest.json").read_bytes()))
                self.assertNotEqual(result.returncode, 0, result.stdout.decode())
                attempt = output / "attempt"
                outcome = json.loads((attempt / "outcome.json").read_bytes())
                self.assertEqual(outcome["status"], "incomplete")
                self.assertIsNone(outcome["thread_id"])
                self.assertIsNone(outcome["turn_id"])
                self.assertFalse(outcome["amendment_rpc_accepted"])
                self.assertEqual(outcome["semantic_success"], "not-assessed")
                self.assertIsNone(outcome["trigger_observation_sequence"])
                if cursor is not None:
                    self.assertIn("paging", outcome["error"])
                    self.assertNotIn("effort unavailable", outcome["error"])
                else:
                    self.assertIn("effort", outcome["error"])
                    self.assertIn("gpt-6.1-sol", outcome["error"])
                    self.assertIn("medium", outcome["error"])
                    self.assertIn("low", outcome["error"])
                sent = [json.loads(line) for line in
                        (attempt / "collector-sent.jsonl").read_bytes().splitlines()]
                self.assertEqual([message["method"] for message in sent],
                                 ["initialize", "initialized", "model/list"])
                self.assertIsNone(sent[2]["params"].get("cursor"))
                self.assertTrue(sent[2]["params"]["includeHidden"])
                received = [json.loads(line) for line in
                            (attempt / "collector-stdout.log").read_bytes().splitlines()]
                self.assertEqual(received, [
                    {"id": sent[0]["id"], "result": initialize},
                    {"id": sent[2]["id"], "result": catalog}])
                rows = [json.loads(line) for line in
                        (attempt / "receipts.jsonl").read_bytes().splitlines()]
                retained = [row for row in rows if row["kind"] == "received"]
                self.assertEqual([row["message"] for row in retained], received)
                inbound = (attempt / "collector-stdout.log").read_bytes()
                for row in retained:
                    reference = row["wire"]
                    self.assertEqual(reference["file"], "collector-stdout.log")
                    raw = inbound[reference["offset"]:reference["offset"] + reference["bytes"]]
                    self.assertEqual(sha(raw), reference["sha256"])
                    self.assertEqual(json.loads(raw), row["message"])


    def test_amends_once_after_first_implementation_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            seed = base / "seed"
            seed.mkdir()
            initial = {"inventory.py": b"DEFAULT = 'text'\n",
                       "tests.py": b"# ordinary tests\n"}
            for name, raw in initial.items():
                (seed / name).write_bytes(raw)
            (seed / "inventory.py").chmod(0o755)
            entries = [{"path": name, "sha256": sha(raw),
                        "executable": name == "inventory.py"}
                       for name, raw in sorted(initial.items())]
            requests = []
            for index, name in enumerate(("01-add-json.md", "02-preserve-default.md")):
                raw = (HERE / "requests" / name).read_bytes()
                target = base / str(index)
                target.write_bytes(raw)
                requests.append({"path": target.name, "sha256": sha(raw)})
            spec = {"version": 1, "seed": {"path": "seed", "files": entries,
                    "identity": sha(encoded(entries))}, "requests": requests,
                    "observation_cases": [], "constructed_candidates": []}
            (base / "spec.json").write_bytes(encoded(spec))
            packet, output = base / "packet", base / "observation"

            def cli(*args, success=True):
                result = subprocess.run([sys.executable, "-B", *map(str, args)],
                                        capture_output=True, timeout=15)
                if success:
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                else:
                    self.assertNotEqual(result.returncode, 0)
                return result

            cli(HERE / "prepare_seed.py", "--spec", base / "spec.json",
                "--output", packet)
            fixture = base / "fake.py"
            # This barrier uses the public evidence package, not a fake RPC.
            fixture.write_text(
                "OUTPUT = " + repr(str(output)) + "\n" + r'''
import json
from pathlib import Path
import sys
import time

def receive(method):
    message = json.loads(sys.stdin.buffer.readline())
    assert message["method"] == method, message
    return message

def emit(value):
    sys.stdout.buffer.write((json.dumps(value, separators=(",", ":")) + "\n").encode())
    sys.stdout.buffer.flush()

def tool(ident):
    emit({"method": "item/completed", "params": {
        "threadId": "thread-1", "turnId": "turn-1",
        "item": {"type": "commandExecution", "id": ident, "status": "completed"}}})

first = receive("initialize")
emit({"id": first["id"], "result": {}})
receive("initialized")
thread = receive("thread/start")
emit({"id": thread["id"], "result": {"thread": {"id": "thread-1"}}})
task = receive("turn/start")
assert task["params"]["threadId"] == "thread-1"
emit({"id": task["id"], "result": {"turn": {"id": "turn-1"}}})
Path("tests.py").write_bytes(b"# test-only change\n")
tool("tests-only")
deadline = time.monotonic() + 5
while True:
    journal = Path(OUTPUT, "attempt", "receipts.jsonl")
    rows = [json.loads(line) for line in journal.read_bytes().splitlines()]
    if any(row["kind"] == "tool-completed" and
           row["item"]["id"] == "tests-only" for row in rows):
        break
    assert time.monotonic() < deadline, "test observation was not retained"
    time.sleep(0.01)
Path("inventory.py").write_bytes(b"DEFAULT = 'json'\n")
tool("implementation-1")
steer = receive("turn/steer")
assert steer["params"]["threadId"] == "thread-1"
assert steer["params"]["expectedTurnId"] == "turn-1"
emit({"id": steer["id"], "result": {"turnId": "turn-1"}})
tool("implementation-1")
Path("inventory.py").write_bytes(b"DEFAULT = 'text'\nJSON = True\n")
tool("implementation-2")
emit({"method": "turn/completed", "params": {
    "threadId": "thread-1", "turn": {"id": "turn-1", "status": "completed", "error": None}}})
# Stay alive for the collector's normal owned-process shutdown.
sys.stdin.buffer.read()
''')
            profile = {"kind": "cooperative-python-fake/v1",
                       "command": [sys.executable, "-I", "-S", "-u", str(fixture)],
                       "python_sha256": sha(Path(sys.executable).read_bytes()),
                       "fixture_sha256": sha(fixture.read_bytes())}
            profile_path = base / "profile.json"
            profile_path.write_bytes(encoded(profile))
            prepare = (COLLECTOR, "prepare", "--seed-package", packet,
                       "--seed-receipt-sha256", sha((packet / "receipt.json").read_bytes()),
                       "--profile", profile_path, "--profile-sha256",
                       sha(profile_path.read_bytes()), "--implementation", "inventory.py",
                       "--output", output)
            cli(*prepare)
            self.assertEqual((output / "project" / "inventory.py").stat().st_mode & 0o7777, 0o755)
            manifest_raw = (output / "manifest.json").read_bytes()
            manifest = json.loads(manifest_raw)
            self.assertEqual(manifest["seed_receipt_sha256"],
                             sha((packet / "receipt.json").read_bytes()))
            self.assertEqual(manifest["seed_identity"], spec["seed"]["identity"])
            self.assertEqual(manifest["profile_sha256"], sha(profile_path.read_bytes()))
            self.assertEqual(manifest["request_sha256"], [r["sha256"] for r in requests])
            self.assertFalse(manifest["native_execution_authorized"])
            self.assertEqual(manifest["profile_qualification"], "cooperative-fake-only")
            cli(*prepare, success=False)
            self.assertEqual((output / "manifest.json").read_bytes(), manifest_raw)
            run = (COLLECTOR, "run", "--manifest", output / "manifest.json",
                   "--expected-sha256", sha(manifest_raw))
            cli(*run)
            attempt = output / "attempt"
            sent_raw = (attempt / "collector-sent.jsonl").read_bytes()
            inbound = (attempt / "collector-stdout.log").read_bytes()
            sent = [json.loads(line) for line in sent_raw.splitlines()]
            self.assertEqual([m["method"] for m in sent],
                             ["initialize", "initialized", "thread/start", "turn/start", "turn/steer"])
            for message, index in ((sent[3], 0), (sent[4], 1)):
                self.assertEqual(message["params"]["input"], [{"type": "text",
                    "text": (packet / "requests" / f"{index:04d}").read_bytes().decode("utf-8"),
                    "text_elements": []}])
            rows_raw = (attempt / "receipts.jsonl").read_bytes()
            rows = [json.loads(line) for line in rows_raw.splitlines()]
            self.assertEqual([r["sequence"] for r in rows], list(range(len(rows))))
            scans = [r for r in rows if r["kind"] == "tool-completed"]
            self.assertEqual([r["item"]["id"] for r in scans],
                             ["tests-only", "implementation-1", "implementation-1", "implementation-2"])
            self.assertEqual(scans[0]["changed"], {})
            trigger, = [r for r in rows if r["kind"] == "amendment-trigger"]
            self.assertEqual(trigger["observation_sequence"], scans[1]["sequence"])
            self.assertEqual(scans[1]["changed"], {"inventory.py": {
                "before": sha(initial["inventory.py"]), "after": sha(b"DEFAULT = 'json'\n")}})
            self.assertEqual(scans[1]["item_sha256"], sha(encoded(scans[1]["item"])))
            accepted, = [r for r in rows if r["kind"] == "amendment-rpc-accepted"]
            self.assertGreater(accepted["sequence"], trigger["sequence"])
            self.assertEqual(accepted["returned_turn_id"], "turn-1")
            for row in rows:
                if "wire" in row:
                    reference = row["wire"]
                    raw = sent_raw if reference["file"] == "collector-sent.jsonl" else inbound
                    part = raw[reference["offset"]:reference["offset"] + reference["bytes"]]
                    self.assertEqual(sha(part), reference["sha256"])
                    self.assertEqual(json.loads(part), row["message"])
            outcome_raw = (attempt / "outcome.json").read_bytes()
            outcome = json.loads(outcome_raw)
            self.assertEqual(outcome["status"], "fake-observation-completed")
            self.assertEqual((outcome["thread_id"], outcome["turn_id"]), ("thread-1", "turn-1"))
            self.assertTrue(outcome["amendment_rpc_accepted"])
            self.assertEqual(outcome["semantic_success"], "not-assessed")
            self.assertEqual(outcome["trigger_observation_sequence"], scans[1]["sequence"])
            cli(*run, success=False)
            self.assertEqual((attempt / "outcome.json").read_bytes(), outcome_raw)
            self.assertEqual((attempt / "receipts.jsonl").read_bytes(), rows_raw)


if __name__ == "__main__":
    unittest.main()
