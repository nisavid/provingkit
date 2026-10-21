"""Public CLI checks for the synthetic startup collector."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
COLLECTOR = HERE / "startup_collector.py"


class StartupCollectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="startup-collector-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.source = self.project / "input.txt"
        self.source.write_bytes(b"original input\n")
        self.spec = self.root / "spec.json"
        self.package = self.root / "package"
        self.spec.write_text(json.dumps({
            "schema": 1,
            "command": [sys.executable, "-c", "pass"],
            "cwd": str(self.project),
            "sources": [str(self.source)],
            "expected_initialize": {
                "userAgent": "synthetic/1", "codexHome": str(self.root),
                "platformFamily": "unix", "platformOs": "linux",
            },
        }))

    def cli(self, *args):
        return subprocess.run(
            [sys.executable, str(COLLECTOR), *map(str, args)],
            capture_output=True, text=True, timeout=10,
        )

    def test_preparation_preserves_specification_and_binds_inputs(self):
        result = self.cli("prepare", "--spec", self.spec, "--output", self.package)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.package / "spec.json").read_bytes(), self.spec.read_bytes())
        manifest = json.loads((self.package / "manifest.json").read_text())
        self.assertEqual(manifest["schema"], 1)
        source = next(item for item in manifest["inputs"] if item["path"] == str(self.source))
        self.assertEqual(source["bytes"], 15)
        self.assertEqual(source["sha256"], hashlib.sha256(b"original input\n").hexdigest())
        self.assertIn(str(Path(sys.executable).resolve()), [i["path"] for i in manifest["inputs"]])
        self.assertIn(str(COLLECTOR), [i["path"] for i in manifest["inputs"]])

    def test_trace_stream_is_bound_collected_and_joined_with_startup_outcome(self):
        server = self.project / "traced_server.py"
        spec = json.loads(self.spec.read_text())
        server.write_text(
            "import json, os, signal, sys\n"
            "signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))\n"
            "trace = int(sys.argv[1])\n"
            "os.write(trace, b'openat(7, \"config\", O_RDONLY) = -1 ENOENT (missing)\\n+++ exited with 0 +++\\n')\n"
            "os.close(trace)\n"
            "sys.stdin.readline()\n"
            f"print(json.dumps({{'id': 1, 'result': {spec['expected_initialize']!r}}}), flush=True)\n"
            "sys.stdin.read()\n"
        )
        spec["command"] = [sys.executable, str(server), "{trace_fd}"]
        spec["sources"].append(str(server))
        spec["trace"] = {"binding": "strace-source-subset/v1"}
        self.spec.write_text(json.dumps(spec))
        self.assertEqual(self.cli("prepare", "--spec", self.spec, "--output", self.package).returncode, 0)
        manifest = json.loads((self.package / "manifest.json").read_text())
        self.assertIn(str(HERE / "trace_adapter.py"), [i["path"] for i in manifest["inputs"]])
        attempt = self.root / "attempt"
        result = self.cli("run", "--package", self.package, "--output", attempt)
        self.assertEqual(result.returncode, 0, result.stderr)
        outcome = json.loads((attempt / "outcome.json").read_text())
        trace = [json.loads(line) for line in (attempt / "trace.jsonl").read_text().splitlines()]
        self.assertEqual(outcome["trace"]["status"], "complete")
        self.assertEqual(outcome["trace"]["reason"], "eof")
        self.assertEqual(outcome["trace"]["sha256"], hashlib.sha256((attempt / "trace.jsonl").read_bytes()).hexdigest())
        self.assertEqual(trace[1]["operands"]["path"]["hex"], "636f6e666967")
        self.assertEqual(outcome["descendant_closure"], "unknown")
        self.assertEqual(outcome["diagnostic_qualification"], "not_established")

    def test_unrecognized_trace_prevents_a_successful_diagnostic_even_with_metadata(self):
        server = self.project / "unsupported_trace.py"
        spec = json.loads(self.spec.read_text())
        server.write_text(
            "import json, os, signal, sys\n"
            "signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))\n"
            "os.write(int(sys.argv[1]), b'UNPROJECTED_PRIVATE_TEXT\\n')\n"
            "os.close(int(sys.argv[1]))\n"
            "sys.stdin.readline()\n"
            f"print(json.dumps({{'id': 1, 'result': {spec['expected_initialize']!r}}}), flush=True)\n"
            "sys.stdin.read()\n"
        )
        spec.update(command=[sys.executable, str(server), "{trace_fd}"],
                    trace={"binding": "strace-source-subset/v1"})
        spec["sources"].append(str(server))
        self.spec.write_text(json.dumps(spec))
        self.assertEqual(self.cli("prepare", "--spec", self.spec, "--output", self.package).returncode, 0)
        attempt = self.root / "attempt"
        result = self.cli("run", "--package", self.package, "--output", attempt)
        self.assertEqual(result.returncode, 2)
        outcome = json.loads((attempt / "outcome.json").read_text())
        self.assertEqual(outcome["reason"], "trace_incomplete")
        self.assertEqual(outcome["initialize"], spec["expected_initialize"])
        self.assertEqual(outcome["trace"]["reason"], "unsupported_shape")
        self.assertNotIn(b"UNPROJECTED_PRIVATE_TEXT", (attempt / "trace.jsonl").read_bytes())

    def test_startup_sends_only_initialize_and_retains_metadata(self):
        server = self.project / "fake_server.py"
        expected = json.loads(self.spec.read_text())["expected_initialize"]
        server.write_text(
            "import json, signal, sys\n"
            "signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))\n"
            "request = json.loads(sys.stdin.readline())\n"
            "assert request == {'id': 1, 'method': 'initialize', 'params': "
            "{'clientInfo': {'name': 'compatibility-native-preparation', 'version': '2'}, "
            "'capabilities': {'experimentalApi': True}}}\n"
            f"print(json.dumps({{'id': 1, 'result': {expected!r}}}), flush=True)\n"
            "assert sys.stdin.read() == ''\n"
        )
        spec = json.loads(self.spec.read_text())
        spec["command"] = [sys.executable, str(server)]
        spec["sources"].append(str(server))
        self.spec.write_text(json.dumps(spec))
        prepared = self.cli("prepare", "--spec", self.spec, "--output", self.package)
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        attempt = self.root / "attempt"
        result = self.cli("run", "--package", self.package, "--output", attempt)
        self.assertEqual(result.returncode, 0, result.stderr)
        outcome = json.loads((attempt / "outcome.json").read_text())
        self.assertEqual(outcome["initialize"], expected)
        self.assertEqual(outcome["reason"], "initialized")
        self.assertIsInstance(outcome["direct_child_returncode"], int)
        self.assertEqual(outcome["descendant_closure"], "unknown")
        sent = [json.loads(line) for line in (attempt / "sent.jsonl").read_text().splitlines()]
        self.assertEqual([row["method"] for row in sent], ["initialize"])
        self.assertFalse(any(path.name.endswith(".log") for path in attempt.iterdir()))

    def test_unicode_metadata_preserves_terminal_outcome_within_control_budget(self):
        spec = json.loads(self.spec.read_text())
        spec["expected_initialize"]["userAgent"] = "é" * 30000
        expected = spec["expected_initialize"]
        reply = (json.dumps({"id": 1, "result": expected}) + "\n").encode()
        self.assertGreater(len(reply), 64 * 1024)
        self.assertLess(len(reply), 256 * 1024)
        server = self.project / "unicode_server.py"
        server.write_text(
            "import json, os, signal, sys\n"
            "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            "os.write(int(sys.argv[1]), b'+++ exited with 0 +++\\n')\n"
            "os.close(int(sys.argv[1]))\n"
            "sys.stdin.readline()\n"
            f"print(json.dumps({{'id': 1, 'result': {expected!r}}}), flush=True)\n"
            "sys.stdin.read()\n"
        )
        spec.update(command=[sys.executable, str(server), "{trace_fd}"],
                    trace={"binding": "strace-source-subset/v1"})
        spec["sources"].append(str(server))
        self.spec.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        self.assertLess(self.spec.stat().st_size, 64 * 1024)
        prepared = self.cli("prepare", "--spec", self.spec, "--output", self.package)
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        attempt = self.root / "attempt"
        result = self.cli("run", "--package", self.package, "--output", attempt)
        self.assertTrue((attempt / "outcome.json").is_file(), result.stderr)
        outcome = json.loads((attempt / "outcome.json").read_text())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(outcome["initialize"], expected)
        self.assertEqual(outcome["reason"], "initialized")
        self.assertEqual(outcome["direct_child_returncode"], 0)
        self.assertEqual(outcome["pipe_eof"], {"stdout": True, "stderr": True})
        self.assertEqual(outcome["stdout_bytes"], len(reply))
        self.assertEqual(outcome["stderr_bytes"], 0)
        self.assertEqual(outcome["package_manifest_sha256"],
                         hashlib.sha256((self.package / "manifest.json").read_bytes()).hexdigest())
        self.assertEqual(outcome["trace"]["status"], "complete")
        self.assertEqual(outcome["descendant_closure"], "unknown")
        self.assertEqual(outcome["diagnostic_qualification"], "not_established")
        self.assertLessEqual((attempt / "outcome.json").stat().st_size, 96 * 1024)
        control_bytes = sum((attempt / name).stat().st_size for name in
                            ("spec.json", "manifest.json", "sent.jsonl", "outcome.json"))
        self.assertLessEqual(control_bytes, 256 * 1024)

    def test_changed_input_is_preserved_as_a_refusal_before_request_delivery(self):
        prepared = self.cli("prepare", "--spec", self.spec, "--output", self.package)
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        self.source.write_text("changed input\n")
        attempt = self.root / "attempt"
        result = self.cli("run", "--package", self.package, "--output", attempt)
        self.assertEqual(result.returncode, 2)
        outcome = json.loads((attempt / "outcome.json").read_text())
        self.assertEqual(outcome["reason"], "input_changed")
        self.assertFalse(outcome["launched"])
        self.assertFalse((attempt / "sent.jsonl").exists())

    def test_output_limit_stops_collection_and_preserves_an_incomplete_result(self):
        server = self.project / "noisy_server.py"
        server.write_text("import sys\nsys.stderr.write('diagnostic-data-' * 512)\nsys.stderr.flush()\n")
        spec = json.loads(self.spec.read_text())
        spec["command"] = [sys.executable, str(server)]
        spec["sources"].append(str(server))
        spec["limits"] = {"pipe_bytes": 512}
        self.spec.write_text(json.dumps(spec))
        self.assertEqual(self.cli("prepare", "--spec", self.spec, "--output", self.package).returncode, 0)
        attempt = self.root / "attempt"
        result = self.cli("run", "--package", self.package, "--output", attempt)
        self.assertEqual(result.returncode, 2)
        outcome = json.loads((attempt / "outcome.json").read_text())
        self.assertEqual(outcome["reason"], "pipe_limit")
        self.assertEqual(outcome["stdout_bytes"] + outcome["stderr_bytes"], 512)
        self.assertIsInstance(outcome["direct_child_returncode"], int)
        self.assertNotIn("diagnostic-data", (attempt / "outcome.json").read_text())

    def test_preparation_refuses_limits_above_the_reviewed_envelope(self):
        spec = json.loads(self.spec.read_text())
        spec["limits"] = {"startup_seconds": 31}
        self.spec.write_text(json.dumps(spec))
        result = self.cli("prepare", "--spec", self.spec, "--output", self.package)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.package.exists())

    def test_preparation_refuses_ambiguous_commands_and_undeclared_fields(self):
        original = json.loads(self.spec.read_text())
        changes = [{"command": []}, {"command": ["python", "-c", "pass"]},
                   {"command": "python"}, {"cwd": "."}, {"sources": ["input.txt"]},
                   {"sourcez": []}]
        for n, change in enumerate(changes):
            with self.subTest(change=change):
                self.spec.write_text(json.dumps({**original, **change}))
                destination = self.root / f"invalid-{n}"
                result = self.cli("prepare", "--spec", self.spec, "--output", destination)
                self.assertEqual(result.returncode, 2)
                self.assertFalse(destination.exists())

    def test_response_emitted_during_shutdown_does_not_turn_timeout_into_success(self):
        server = self.project / "late_server.py"
        spec = json.loads(self.spec.read_text())
        expected = spec["expected_initialize"]
        server.write_text(
            "import json, signal, sys, time\n"
            "def stopped(*_):\n"
            f" print(json.dumps({{'id': 1, 'result': {expected!r}}}), flush=True)\n"
            " sys.exit(0)\n"
            "signal.signal(signal.SIGTERM, stopped)\n"
            "sys.stdin.readline()\n"
            "time.sleep(3)\n"
        )
        spec["command"] = [sys.executable, str(server)]
        spec["sources"].append(str(server))
        spec["limits"] = {"startup_seconds": 0.2, "term_seconds": 0.5, "kill_seconds": 0.5}
        self.spec.write_text(json.dumps(spec))
        self.assertEqual(self.cli("prepare", "--spec", self.spec, "--output", self.package).returncode, 0)
        attempt = self.root / "attempt"
        result = self.cli("run", "--package", self.package, "--output", attempt)
        self.assertEqual(result.returncode, 2)
        outcome = json.loads((attempt / "outcome.json").read_text())
        self.assertEqual(outcome["reason"], "startup_timeout")
        self.assertIsInstance(outcome["direct_child_returncode"], int)
        self.assertLess(outcome["elapsed_seconds"], 1.5)

    def test_shutdown_reaches_cooperative_group_child_after_direct_child_exits(self):
        server = self.project / "forked_server.py"
        spec = json.loads(self.spec.read_text())
        server.write_text(
            "import json, os, signal, sys, time\n"
            "parent = os.getpid()\n"
            "if os.fork(): os._exit(0)\n"
            "def stop(*_):\n"
            " sys.stderr.write('terminated\\n'); sys.stderr.flush(); sys.exit(0)\n"
            "signal.signal(signal.SIGTERM, stop)\n"
            "while os.getppid() == parent: time.sleep(0.001)\n"
            "sys.stdin.readline()\n"
            f"print(json.dumps({{'id': 1, 'result': {spec['expected_initialize']!r}}}), flush=True)\n"
            "time.sleep(2)\n"
        )
        spec["command"] = [sys.executable, str(server)]
        spec["sources"].append(str(server))
        spec["limits"] = {"startup_seconds": 1, "term_seconds": 0.2, "kill_seconds": 0.2}
        self.spec.write_text(json.dumps(spec))
        self.assertEqual(self.cli("prepare", "--spec", self.spec, "--output", self.package).returncode, 0)
        attempt = self.root / "attempt"
        result = self.cli("run", "--package", self.package, "--output", attempt)
        self.assertEqual(result.returncode, 0, result.stderr)
        outcome = json.loads((attempt / "outcome.json").read_text())
        self.assertEqual(outcome["stderr_bytes"], 11)
        self.assertEqual(outcome["pipe_eof"], {"stdout": True, "stderr": True})
        self.assertEqual(outcome["direct_child_returncode"], 0)
        self.assertEqual(outcome["descendant_closure"], "unknown")

    def test_existing_preparation_and_attempt_records_are_never_overwritten(self):
        self.assertEqual(self.cli("prepare", "--spec", self.spec, "--output", self.package).returncode, 0)
        preserved = {path.name: path.read_bytes() for path in self.package.iterdir()}
        self.assertEqual(self.cli("prepare", "--spec", self.spec, "--output", self.package).returncode, 2)
        self.assertEqual({path.name: path.read_bytes() for path in self.package.iterdir()}, preserved)
        attempt = self.root / "attempt"
        attempt.mkdir()
        (attempt / "outcome.json").write_bytes(b"preserved previous attempt\n")
        self.assertEqual(self.cli("run", "--package", self.package, "--output", attempt).returncode, 2)
        self.assertEqual((attempt / "outcome.json").read_bytes(), b"preserved previous attempt\n")
        self.assertEqual([path.name for path in attempt.iterdir()], ["outcome.json"])

    def test_boolean_response_id_is_not_the_requested_integer_id(self):
        server = self.project / "wrong_identity.py"
        spec = json.loads(self.spec.read_text())
        server.write_text(
            "import json, sys\nsys.stdin.readline()\n"
            f"print(json.dumps({{'id': True, 'result': {spec['expected_initialize']!r}}}), flush=True)\n"
        )
        spec["command"] = [sys.executable, str(server)]
        spec["sources"].append(str(server))
        self.spec.write_text(json.dumps(spec))
        self.assertEqual(self.cli("prepare", "--spec", self.spec, "--output", self.package).returncode, 0)
        attempt = self.root / "attempt"
        result = self.cli("run", "--package", self.package, "--output", attempt)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads((attempt / "outcome.json").read_text())["reason"], "response_mismatch")

    def test_launch_failure_retains_an_attempt_without_claiming_request_delivery(self):
        cwd = self.root / "empty-cwd"
        cwd.mkdir()
        spec = json.loads(self.spec.read_text())
        spec["cwd"] = str(cwd)
        self.spec.write_text(json.dumps(spec))
        self.assertEqual(self.cli("prepare", "--spec", self.spec, "--output", self.package).returncode, 0)
        cwd.rmdir()
        attempt = self.root / "attempt"
        result = self.cli("run", "--package", self.package, "--output", attempt)
        self.assertEqual(result.returncode, 2)
        outcome = json.loads((attempt / "outcome.json").read_text())
        self.assertEqual(outcome["reason"], "launch_error")
        self.assertFalse(outcome["launched"])
        self.assertFalse((attempt / "sent.jsonl").exists())

    def test_retargeted_executable_link_is_refused_even_when_bytes_match(self):
        first = self.root / "first"
        second = self.root / "second"
        for target in (first, second):
            target.write_text("#!/bin/sh\nexit 0\n")
            target.chmod(0o700)
        link = self.root / "launcher"
        link.symlink_to(first)
        spec = json.loads(self.spec.read_text())
        spec["command"] = [str(link)]
        self.spec.write_text(json.dumps(spec))
        self.assertEqual(self.cli("prepare", "--spec", self.spec, "--output", self.package).returncode, 0)
        link.unlink()
        link.symlink_to(second)
        attempt = self.root / "attempt"
        result = self.cli("run", "--package", self.package, "--output", attempt)
        self.assertEqual(result.returncode, 2)
        outcome = json.loads((attempt / "outcome.json").read_text())
        self.assertEqual(outcome["reason"], "input_changed")
        self.assertFalse(outcome["launched"])

    def test_incomplete_attempt_keeps_the_prepared_identity_records(self):
        self.assertEqual(self.cli("prepare", "--spec", self.spec, "--output", self.package).returncode, 0)
        attempt = self.root / "attempt"
        self.assertEqual(self.cli("run", "--package", self.package, "--output", attempt).returncode, 2)
        self.assertEqual((attempt / "spec.json").read_bytes(), (self.package / "spec.json").read_bytes())
        self.assertEqual((attempt / "manifest.json").read_bytes(), (self.package / "manifest.json").read_bytes())
        outcome = json.loads((attempt / "outcome.json").read_text())
        self.assertEqual(outcome["package_manifest_sha256"], hashlib.sha256((self.package / "manifest.json").read_bytes()).hexdigest())

    def test_preparation_allows_only_the_four_initialize_metadata_fields(self):
        spec = json.loads(self.spec.read_text())
        spec["expected_initialize"]["configuration"] = "unrelated fixture field"
        self.spec.write_text(json.dumps(spec))
        result = self.cli("prepare", "--spec", self.spec, "--output", self.package)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.package.exists())

    def test_oversized_specification_is_refused_before_package_creation(self):
        self.spec.write_bytes(b" " * (256 * 1024) + self.spec.read_bytes())
        result = self.cli("prepare", "--spec", self.spec, "--output", self.package)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.package.exists())

    def test_unknown_specification_revision_is_refused(self):
        spec = json.loads(self.spec.read_text())
        spec["schema"] = 2
        self.spec.write_text(json.dumps(spec))
        self.assertEqual(self.cli("prepare", "--spec", self.spec, "--output", self.package).returncode, 2)
        self.assertFalse(self.package.exists())

    def test_incomplete_and_unexpected_protocol_records_stay_incomplete(self):
        original = json.loads(self.spec.read_text())
        valid = json.dumps({"id": 1, "result": original["expected_initialize"]}).encode() + b"\n"
        cases = [
            (b"not-json\n", "malformed_response", {}),
            (b'{"method":"unexpected"}\n', "response_mismatch", {}),
            (b'{"id":1,"error":{"code":-1}}\n', "response_mismatch", {}),
            (b'{"id":1,"result":{}}\n', "response_mismatch", {}),
            (b'{"id":1', "premature_eof", {}),
            (valid + valid, "unsolicited_response", {}),
            (b"x" * 300 + b"\n", "message_limit", {"message_bytes": 64}),
        ]
        for index, (payload, reason, limits) in enumerate(cases):
            with self.subTest(reason=reason, index=index):
                server = self.project / f"protocol-{index}.py"
                server.write_text("import sys\nsys.stdin.readline()\n" +
                                  f"sys.stdout.buffer.write({payload!r})\nsys.stdout.flush()\n")
                spec = dict(original, command=[sys.executable, str(server)],
                            sources=[str(self.source), str(server)], limits=limits)
                self.spec.write_text(json.dumps(spec))
                package = self.root / f"package-{index}"
                attempt = self.root / f"attempt-{index}"
                self.assertEqual(self.cli("prepare", "--spec", self.spec, "--output", package).returncode, 0)
                self.assertEqual(self.cli("run", "--package", package, "--output", attempt).returncode, 2)
                self.assertEqual(json.loads((attempt / "outcome.json").read_text())["reason"], reason)


    def test_nested_non_rpc_reply_keeps_a_failed_attempt_and_child_outcome(self):
        spec = json.loads(self.spec.read_text())
        server = self.project / "nested_reply.py"
        server.write_text("import sys\nsys.stdin.readline()\nprint('[' * 1500 + '0' + ']' * 1500, flush=True)\n")
        spec["command"] = [sys.executable, str(server)]
        spec["sources"].append(str(server))
        self.spec.write_text(json.dumps(spec))
        self.assertEqual(self.cli("prepare", "--spec", self.spec, "--output", self.package).returncode, 0)
        attempt = self.root / "attempt"
        result = self.cli("run", "--package", self.package, "--output", attempt)
        self.assertEqual(result.returncode, 2)
        outcome = json.loads((attempt / "outcome.json").read_text())
        self.assertEqual(outcome["reason"], "response_mismatch")
        self.assertIsInstance(outcome["direct_child_returncode"], int)


if __name__ == "__main__":
    unittest.main()
