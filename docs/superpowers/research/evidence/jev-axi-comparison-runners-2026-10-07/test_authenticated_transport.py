import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import unittest


RUNNER = Path(__file__).with_name("comparison_runner.py")
CREDENTIAL = (
    "pk_test_DO_NOT_USE_authentication_transport_regression_"
    "7d4f9b831e6a42c0b75e1d892f34ac68"
)
INPUT = b"The supplied source directly supports the claim."

EXPECTED_PAYLOAD = (
    b'{"model": "gpt-6-luna", "input": "The supplied source directly supports the claim.", '
    b'"questions": [{"type": "choice", "name": "claim_relation", "instructions": '
    b'"Considering only the supplied sources, what relation does the designated assertion have '
    b'to their evidence? Respect the assertion\'s scope and any explicit qualifications in the '
    b'supplied evidence. Do not decide global truth or recommend an action.\\n\\nAssess '
    b'evidential warrant, including when the assertion says that reports establish a fact: a '
    b'derivative assertion adds no independent warrant beyond its supplied cited basis and '
    b'qualifications. A statement that a fact is unestablished limits warrant; it does not, by '
    b'itself, establish an incompatible event or state of affairs. Conflicting independent '
    b'factual accounts that the supplied context cannot resolve remain `unresolved`.", '
    b'"choices": [{"value": "supported", "description": "The supplied evidence warrants the '
    b'complete assertion at its stated scope."}, {"value": "contradicted", "description": "A '
    b'supplied source explicitly states an incompatible fact, and the supplied sources do not '
    b'conflict about it."}, {"value": "unsupported_extension", "description": "The assertion '
    b'claims more than the supplied evidence establishes, without a demonstrated incompatible '
    b'fact."}, {"value": "unresolved", "description": "Missing referents, conflicting sources, '
    b'or insufficiently interpretable context prevent choosing the other relations."}]}]}'
)

SUCCESS_RESPONSE = json.dumps(
    {
        "model": "gpt-6-luna",
        "answers": [
            {
                "type": "choice",
                "name": "claim_relation",
                "choice": "supported",
                "confidence": 0.7,
                "probabilities": [
                    {"value": "supported", "probability": 0.7},
                    {"value": "contradicted", "probability": 0.1},
                    {"value": "unsupported_extension", "probability": 0.1},
                    {"value": "unresolved", "probability": 0.1},
                ],
            }
        ],
        "usage": {"input_tokens": 100},
    },
    separators=(",", ":"),
).encode("ascii")


def child_environment():
    names = (
        "PATH",
        "SYSTEMROOT",
        "WINDIR",
        "COMSPEC",
        "PATHEXT",
        "TMPDIR",
        "TMP",
        "TEMP",
    )
    environment = {name: os.environ[name] for name in names if name in os.environ}
    environment["PYTHONIOENCODING"] = "utf-8"
    return environment


class RecordingServer(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False


class RecordingHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        request = {
            "method": self.command,
            "path": self.path,
            "authorization": self.headers.get_all("Authorization") or [],
            "content_type": self.headers.get_all("Content-Type") or [],
            "body": self.rfile.read(length),
        }
        with self.server.requests_lock:
            self.server.requests.append(request)

        response_body = getattr(self.server, "response_body", SUCCESS_RESPONSE)
        request_id = getattr(self.server, "request_id", "synthetic-request-0001")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_body)))
        self.send_header("x-request-id", request_id)
        self.end_headers()

        headers_sent = getattr(self.server, "response_headers_sent", None)
        if headers_sent is not None:
            headers_sent.set()
        body_gate = getattr(self.server, "response_body_gate", None)
        if body_gate is not None:
            body_gate.wait()
        try:
            self.wfile.write(response_body)
        except OSError:
            pass

    def log_message(self, format, *args):
        pass


class AuthenticatedTransportTest(unittest.TestCase):
    def test_decisions_claim_uses_runtime_bearer_without_retaining_it(self):
        server = RecordingServer(("127.0.0.1", 0), RecordingHandler)
        server.requests = []
        server.requests_lock = threading.Lock()
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        try:
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = root / "claim.txt"
                spec_path = root / "spec.json"
                prepared = root / "prepared"
                run_output = root / "run"
                source.write_bytes(INPUT)

                spec = {
                    "version": 1,
                    "kind": "claim",
                    "cases": [
                        {
                            "id": "c01",
                            "status": "ready",
                            "input": {
                                "path": str(source),
                                "sha256": hashlib.sha256(INPUT).hexdigest(),
                            },
                        }
                    ],
                    "conditions": [
                        {
                            "id": "decisions_auth",
                            "adapter": "decisions",
                            "model": "gpt-6-luna",
                            "effort": None,
                            "endpoint": (
                                f"http://127.0.0.1:{server.server_address[1]}"
                                "/v1/decisions"
                            ),
                            "billing": "openai_api",
                            "auth_env": "PROVINGKIT_TEST_API_KEY",
                            "rates": {
                                "input": "2",
                                "cached": "0",
                                "write": "0",
                                "output": "0",
                            },
                        }
                    ],
                    "limits": {
                        "request_seconds": 3,
                        "run_seconds": 8,
                        "input_bytes": 1024,
                        "request_bytes": 16384,
                        "response_bytes": 16384,
                        "requests_per_cell": 1,
                    },
                }
                spec_path.write_text(json.dumps(spec), encoding="utf-8")

                prepare_environment = child_environment()
                self.assertNotIn("PROVINGKIT_TEST_API_KEY", prepare_environment)
                prepare = subprocess.run(
                    [
                        sys.executable,
                        str(RUNNER),
                        "prepare",
                        "--spec",
                        str(spec_path),
                        "--output",
                        str(prepared),
                    ],
                    cwd=root,
                    env=prepare_environment,
                    capture_output=True,
                    timeout=10,
                    check=False,
                )
                self.assertEqual(
                    prepare.returncode,
                    0,
                    prepare.stderr.decode("utf-8", errors="replace"),
                )
                manifest_digest = json.loads(prepare.stdout)["sha256"]

                run_environment = child_environment()
                run_environment["PROVINGKIT_TEST_API_KEY"] = CREDENTIAL
                execution = subprocess.run(
                    [
                        sys.executable,
                        str(RUNNER),
                        "run",
                        "--prepared",
                        str(prepared),
                        "--manifest-sha256",
                        manifest_digest,
                        "--output",
                        str(run_output),
                        "--local-http",
                    ],
                    cwd=root,
                    env=run_environment,
                    capture_output=True,
                    timeout=12,
                    check=False,
                )
                self.assertEqual(
                    execution.returncode,
                    0,
                    execution.stderr.decode("utf-8", errors="replace"),
                )

                with server.requests_lock:
                    requests = list(server.requests)
                self.assertEqual(len(requests), 1)
                observed = requests[0]
                self.assertEqual(observed["method"], "POST")
                self.assertEqual(observed["path"], "/v1/decisions")
                self.assertEqual(observed["content_type"], ["application/json"])

                manifest = json.loads((prepared / "manifest.json").read_bytes())
                self.assertEqual(
                    manifest["conditions"][0]["auth_env"],
                    "PROVINGKIT_TEST_API_KEY",
                )

                reservation_path = run_output / "request-0000.json"
                attempt_path = run_output / "attempt-0000.json"
                self.assertTrue(reservation_path.is_file())
                self.assertTrue(attempt_path.is_file())
                self.assertNotEqual(reservation_path, attempt_path)

                reservation = json.loads(reservation_path.read_bytes())
                attempt = json.loads(attempt_path.read_bytes())
                self.assertEqual(reservation["attempt_id"], attempt["attempt_id"])
                self.assertEqual(attempt["status"], "completed")
                self.assertIsNone(attempt["condition_error"])
                self.assertEqual(attempt["relation"], "supported")
                self.assertEqual(attempt["usage"], {"input_tokens": 100})
                self.assertEqual(attempt["valuation_status"], "known")
                self.assertEqual(attempt["api_rate_equivalent_usd"], "0.0002")

                summary = json.loads((run_output / "summary.json").read_bytes())
                self.assertEqual(len(summary["slots"]), 1)
                self.assertEqual(summary["slots"][0]["status"], "completed")
                accounting = summary["request_accounting"]
                self.assertEqual(accounting["attempts"], 1)
                self.assertEqual(
                    accounting["known_api_rate_equivalent_usd"], "0.0002"
                )
                self.assertEqual(accounting["unvalued_attempts"], 0)
                self.assertEqual(accounting["api_rate_equivalent_usd"], "0.0002")
                self.assertEqual(
                    accounting["input_tokens"],
                    {
                        "reported_sum": 100,
                        "unreported_attempts": 0,
                        "missing_attempts": 0,
                        "invalid_attempts": 0,
                    },
                )

                retained_body = (run_output / attempt["request_body"]).read_bytes()
                self.assertEqual(retained_body, EXPECTED_PAYLOAD)
                self.assertEqual(observed["body"], EXPECTED_PAYLOAD)
                self.assertEqual(observed["body"], retained_body)
                self.assertEqual(
                    attempt["payload_sha256"],
                    hashlib.sha256(EXPECTED_PAYLOAD).hexdigest(),
                )

                credential_bytes = CREDENTIAL.encode("ascii")
                for captured in (
                    prepare.stdout,
                    prepare.stderr,
                    execution.stdout,
                    execution.stderr,
                ):
                    self.assertNotIn(credential_bytes, captured)
                for artifact_root in (prepared, run_output):
                    for artifact in artifact_root.rglob("*"):
                        if artifact.is_file():
                            self.assertNotIn(
                                credential_bytes,
                                artifact.read_bytes(),
                                str(artifact.relative_to(artifact_root)),
                            )

                self.assertEqual(
                    observed["authorization"],
                    [f"Bearer {CREDENTIAL}"],
                )
        finally:
            server.shutdown()
            server.server_close()
            server_thread.join(2)

    def test_prepare_and_run_record_safe_reflection_evidence(self):
        safe_prefix = b'{"safe_prefix":true,"reflected_credential":"'
        body_response = safe_prefix + CREDENTIAL.encode("ascii") + b'"}'
        coverage_source = "The source is available."
        coverage_input = json.dumps(
            {
                "task": "Assess the supplied evidence coverage.",
                "ordinary": "Inspect the supplied source.",
                "deterministic": "Inspect the supplied source.",
                "sources": [
                    {
                        "id": "s01",
                        "path": "source.txt",
                        "content": coverage_source,
                        "sha256": hashlib.sha256(
                            coverage_source.encode("utf-8")
                        ).hexdigest(),
                    }
                ],
            },
            separators=(",", ":"),
        ).encode("utf-8")
        server = RecordingServer(("127.0.0.1", 0), RecordingHandler)
        server.requests = []
        server.requests_lock = threading.Lock()
        server_thread = threading.Thread(
            target=server.serve_forever, daemon=True
        )
        server_thread.start()

        try:
            cases = (
                ("claim", "body", body_response, "synthetic-request-0001", safe_prefix),
                ("claim", "header", SUCCESS_RESPONSE, CREDENTIAL, b""),
                ("coverage", "body", body_response, "synthetic-request-0001", safe_prefix),
                ("coverage", "header", SUCCESS_RESPONSE, CREDENTIAL, b""),
            )
            for kind, location, response_body, request_id, retained_response in cases:
                with self.subTest(kind=kind, location=location):
                    server.response_body = response_body
                    server.request_id = request_id
                    with server.requests_lock:
                        server.requests.clear()

                    with tempfile.TemporaryDirectory() as temporary:
                        root = Path(temporary)
                        source = root / (
                            "claim.txt" if kind == "claim" else "coverage.json"
                        )
                        spec_path = root / "spec.json"
                        prepared = root / "prepared"
                        run_output = root / "run"
                        input_data = INPUT if kind == "claim" else coverage_input
                        source.write_bytes(input_data)

                        spec = {
                            "version": 1,
                            "kind": kind,
                            **({"mode": "diagnostic"} if kind == "coverage" else {}),
                            "cases": [
                                {
                                    "id": "c01",
                                    "status": "ready",
                                    "input": {
                                        "path": str(source),
                                        "sha256": hashlib.sha256(input_data).hexdigest(),
                                    },
                                }
                            ],
                            "conditions": [
                                {
                                    "id": f"{kind}_auth",
                                    "adapter": "decisions" if kind == "claim" else "responses",
                                    "model": "gpt-6-luna",
                                    "effort": None if kind == "claim" else "low",
                                    "endpoint": (
                                        f"http://127.0.0.1:{server.server_address[1]}/v1/"
                                        + ("decisions" if kind == "claim" else "responses")
                                    ),
                                    "billing": "openai_api",
                                    "auth_env": "PROVINGKIT_TEST_API_KEY",
                                    **({"arm": "ordinary"} if kind == "coverage" else {}),
                                    "rates": {
                                        "input": "2",
                                        "cached": "0",
                                        "write": "0",
                                        "output": "0",
                                    },
                                }
                            ],
                            "limits": {
                                "request_seconds": 3,
                                "run_seconds": 8,
                                "input_bytes": 1024,
                                "request_bytes": 16384,
                                "response_bytes": 16384,
                                "requests_per_cell": 1 if kind == "claim" else 2,
                                **(
                                    {"cell_seconds": 6, "tool_operations": 2,
                                     "tool_result_bytes": 4096,
                                     "tool_total_bytes": 8192}
                                    if kind == "coverage"
                                    else {}
                                ),
                            },
                        }
                        spec_path.write_text(json.dumps(spec), encoding="utf-8")

                        prepare_environment = child_environment()
                        self.assertNotIn(
                            "PROVINGKIT_TEST_API_KEY", prepare_environment
                        )
                        prepare = subprocess.run(
                            [
                                sys.executable,
                                str(RUNNER),
                                "prepare",
                                "--spec",
                                str(spec_path),
                                "--output",
                                str(prepared),
                            ],
                            cwd=root,
                            env=prepare_environment,
                            capture_output=True,
                            timeout=10,
                            check=False,
                        )
                        self.assertEqual(
                            prepare.returncode,
                            0,
                            prepare.stderr.decode("utf-8", errors="replace"),
                        )
                        manifest_digest = json.loads(prepare.stdout)["sha256"]

                        run_environment = child_environment()
                        run_environment["PROVINGKIT_TEST_API_KEY"] = CREDENTIAL
                        execution = subprocess.run(
                            [
                                sys.executable,
                                str(RUNNER),
                                "run",
                                "--prepared",
                                str(prepared),
                                "--manifest-sha256",
                                manifest_digest,
                                "--output",
                                str(run_output),
                                "--local-http",
                            ],
                            cwd=root,
                            env=run_environment,
                            capture_output=True,
                            timeout=12,
                            check=False,
                        )
                        self.assertEqual(
                            execution.returncode,
                            0,
                            execution.stderr.decode("utf-8", errors="replace"),
                        )

                        with server.requests_lock:
                            requests = list(server.requests)
                        self.assertEqual(len(requests), 1)
                        observed = requests[0]
                        self.assertEqual(observed["method"], "POST")
                        self.assertEqual(
                            observed["path"],
                            "/v1/decisions" if kind == "claim" else "/v1/responses",
                        )
                        self.assertEqual(
                            observed["authorization"], [f"Bearer {CREDENTIAL}"]
                        )

                        attempt_paths = list(run_output.rglob("attempt-*.json"))
                        self.assertEqual(len(attempt_paths), 1)
                        attempt = json.loads(attempt_paths[0].read_bytes())
                        self.assertEqual(attempt["status"], "credential_reflection")
                        self.assertEqual(
                            attempt["transport_status"], "credential_reflection"
                        )
                        self.assertEqual(attempt["http_status"], 200)
                        self.assertTrue(
                            attempt["residual_provider_work_unknown"]
                        )
                        if kind == "claim":
                            self.assertTrue(attempt["response_truncated"])
                            self.assertIsNone(attempt["relation"])
                            self.assertNotIn("answer", attempt)
                        else:
                            self.assertNotIn("response_truncated", attempt)
                            self.assertNotIn("relation", attempt)
                            self.assertNotIn("answer", attempt)
                        self.assertIsNone(attempt["usage"])
                        self.assertEqual(attempt["usage_scope"], "unknown")
                        self.assertEqual(attempt["valuation_status"], "unknown")
                        self.assertIsNone(attempt["api_rate_equivalent_usd"])

                        retained_request = (
                            attempt_paths[0].parent / attempt["request_body"]
                        ).read_bytes()
                        self.assertEqual(observed["body"], retained_request)
                        self.assertEqual(
                            json.loads(retained_request), attempt["request"]
                        )
                        self.assertEqual(
                            (
                                attempt_paths[0].parent / attempt["response_body"]
                            ).read_bytes(),
                            retained_response,
                        )

                        summary = json.loads(
                            (run_output / "summary.json").read_bytes()
                        )
                        self.assertEqual(len(summary["slots"]), 1)
                        self.assertEqual(
                            summary["slots"][0]["status"],
                            "credential_reflection",
                        )
                        accounting = summary["request_accounting"]
                        self.assertEqual(accounting["attempts"], 1)
                        self.assertEqual(
                            accounting["known_api_rate_equivalent_usd"], "0"
                        )
                        self.assertEqual(accounting["unvalued_attempts"], 1)
                        self.assertEqual(
                            accounting["unknown_valuation_attempts"], 1
                        )
                        self.assertIsNone(
                            accounting["api_rate_equivalent_usd"]
                        )
                        missing_counter = {
                            "reported_sum": 0,
                            "unreported_attempts": 1,
                            "missing_attempts": 1,
                            "invalid_attempts": 0,
                        }
                        for counter in ("input_tokens", "output_tokens"):
                            self.assertEqual(accounting[counter], missing_counter)

                        if kind == "coverage":
                            cell_summary = json.loads(
                                (
                                    attempt_paths[0].parent / "summary.json"
                                ).read_bytes()
                            )
                            self.assertEqual(
                                cell_summary["status"], "credential_reflection"
                            )
                            self.assertIsNone(cell_summary["answer"])
                            self.assertEqual(cell_summary["requests"], 1)
                            self.assertEqual(cell_summary["tool_operations"], 0)
                            self.assertEqual(cell_summary["tool_prepared_bytes"], 0)
                            self.assertEqual(
                                cell_summary["tool_submission_attempted_bytes"], 0
                            )
                            self.assertIsNone(
                                cell_summary["provider_consumed_tool_bytes"]
                            )
                            self.assertEqual(
                                cell_summary["unsubmitted_tool_results"], []
                            )
                            self.assertIsNone(cell_summary["unsubmitted_reason"])
                            self.assertEqual(
                                list(attempt_paths[0].parent.glob("tools-*.json")),
                                [],
                            )

                        credential_bytes = CREDENTIAL.encode("ascii")
                        for captured in (
                            prepare.stdout,
                            prepare.stderr,
                            execution.stdout,
                            execution.stderr,
                        ):
                            self.assertNotIn(credential_bytes, captured)
                        for artifact_root in (prepared, run_output):
                            for artifact in artifact_root.rglob("*"):
                                if artifact.is_file():
                                    self.assertNotIn(
                                        credential_bytes,
                                        artifact.read_bytes(),
                                        str(artifact.relative_to(artifact_root)),
                                    )
        finally:
            server.shutdown()
            server.server_close()
            server_thread.join(2)

    def test_reflection_survives_deadline_expiry_without_changing_plain_timeout(self):
        server = RecordingServer(("127.0.0.1", 0), RecordingHandler)
        server.requests = []
        server.requests_lock = threading.Lock()
        server_thread = threading.Thread(
            target=server.serve_forever, daemon=True
        )
        server_thread.start()

        try:
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = root / "claim.txt"
                spec_path = root / "spec.json"
                prepared = root / "prepared"
                shim = root / "shim"
                source.write_bytes(INPUT)
                shim.mkdir()
                (shim / "sitecustomize.py").write_text(
                    """
import http.client
import os
import time

_marker = os.environ.get("PROVINGKIT_TEST_CLOSE_DELAY_MARKER")
_original_close = http.client.HTTPConnection.close

if _marker:
    def _test_only_delayed_close(connection):
        if connection.sock is not None:
            try:
                with open(_marker, "x", encoding="utf-8") as stream:
                    stream.write("test-only HTTPConnection.close delay entered\\n")
            except FileExistsError:
                pass
            while True:
                time.sleep(60)
        return _original_close(connection)

    http.client.HTTPConnection.close = _test_only_delayed_close
""".lstrip(),
                    encoding="utf-8",
                )

                spec = {
                    "version": 1,
                    "kind": "claim",
                    "cases": [
                        {
                            "id": "c01",
                            "status": "ready",
                            "input": {
                                "path": str(source),
                                "sha256": hashlib.sha256(INPUT).hexdigest(),
                            },
                        }
                    ],
                    "conditions": [
                        {
                            "id": "decisions_auth",
                            "adapter": "decisions",
                            "model": "gpt-6-luna",
                            "effort": None,
                            "endpoint": (
                                f"http://127.0.0.1:{server.server_address[1]}"
                                "/v1/decisions"
                            ),
                            "billing": "openai_api",
                            "auth_env": "PROVINGKIT_TEST_API_KEY",
                            "rates": {
                                "input": "2",
                                "cached": "0",
                                "write": "0",
                                "output": "0",
                            },
                        }
                    ],
                    "limits": {
                        "request_seconds": 2,
                        "run_seconds": 8,
                        "input_bytes": 1024,
                        "request_bytes": 16384,
                        "response_bytes": 16384,
                        "requests_per_cell": 1,
                    },
                }
                spec_path.write_text(json.dumps(spec), encoding="utf-8")

                prepare_environment = child_environment()
                self.assertNotIn(
                    "PROVINGKIT_TEST_API_KEY", prepare_environment
                )
                prepare = subprocess.run(
                    [
                        sys.executable,
                        str(RUNNER),
                        "prepare",
                        "--spec",
                        str(spec_path),
                        "--output",
                        str(prepared),
                    ],
                    cwd=root,
                    env=prepare_environment,
                    capture_output=True,
                    timeout=10,
                    check=False,
                )
                self.assertEqual(
                    prepare.returncode,
                    0,
                    prepare.stderr.decode("utf-8", errors="replace"),
                )
                manifest_digest = json.loads(prepare.stdout)["sha256"]

                cases = (
                    (
                        "observed_reflection_with_test_cleanup_delay",
                        CREDENTIAL,
                        "credential_reflection",
                        True,
                    ),
                    (
                        "deadline_without_observed_reflection",
                        "synthetic-request-0001",
                        "timeout",
                        False,
                    ),
                )
                for name, request_id, expected_status, delay_close in cases:
                    with self.subTest(case=name):
                        run_output = root / f"run-{name}"
                        close_delay_marker = root / f"{name}.marker"
                        headers_sent = threading.Event()
                        body_gate = threading.Event()
                        server.response_body = SUCCESS_RESPONSE
                        server.request_id = request_id
                        server.response_headers_sent = headers_sent
                        server.response_body_gate = body_gate
                        with server.requests_lock:
                            server.requests.clear()

                        run_environment = child_environment()
                        run_environment["PYTHONPATH"] = str(shim)
                        run_environment["PROVINGKIT_TEST_API_KEY"] = CREDENTIAL
                        if delay_close:
                            run_environment[
                                "PROVINGKIT_TEST_CLOSE_DELAY_MARKER"
                            ] = str(close_delay_marker)
                        try:
                            execution = subprocess.run(
                                [
                                    sys.executable,
                                    str(RUNNER),
                                    "run",
                                    "--prepared",
                                    str(prepared),
                                    "--manifest-sha256",
                                    manifest_digest,
                                    "--output",
                                    str(run_output),
                                    "--local-http",
                                ],
                                cwd=root,
                                env=run_environment,
                                capture_output=True,
                                timeout=12,
                                check=False,
                            )
                        finally:
                            body_gate.set()

                        self.assertEqual(
                            execution.returncode,
                            0,
                            execution.stderr.decode("utf-8", errors="replace"),
                        )
                        self.assertTrue(headers_sent.is_set())
                        if delay_close:
                            self.assertEqual(
                                close_delay_marker.read_text(encoding="utf-8"),
                                "test-only HTTPConnection.close delay entered\n",
                            )
                        else:
                            self.assertFalse(close_delay_marker.exists())

                        attempt_paths = list(
                            run_output.glob("attempt-*.json")
                        )
                        self.assertEqual(len(attempt_paths), 1)
                        attempt = json.loads(attempt_paths[0].read_bytes())
                        self.assertEqual(attempt["status"], expected_status)
                        self.assertEqual(
                            attempt["transport_status"], expected_status
                        )
                        self.assertIs(attempt["deadline_expired"], True)
                        self.assertTrue(attempt["response_truncated"])
                        self.assertTrue(
                            attempt["residual_provider_work_unknown"]
                        )
                        self.assertIsNone(attempt["relation"])
                        self.assertIsNone(attempt["raw_response"])
                        self.assertEqual(attempt["raw_events"], [])
                        self.assertIsNone(attempt["usage"])
                        self.assertEqual(attempt["usage_scope"], "unknown")
                        self.assertEqual(
                            attempt["valuation_status"], "unknown"
                        )
                        self.assertIsNone(
                            attempt["api_rate_equivalent_usd"]
                        )
                        self.assertEqual(
                            (
                                run_output / attempt["response_body"]
                            ).read_bytes(),
                            b"",
                        )

                        summary = json.loads(
                            (run_output / "summary.json").read_bytes()
                        )
                        self.assertEqual(len(summary["slots"]), 1)
                        self.assertEqual(
                            summary["slots"][0]["status"], expected_status
                        )
                        accounting = summary["request_accounting"]
                        self.assertEqual(accounting["attempts"], 1)
                        self.assertEqual(
                            accounting["unvalued_attempts"], 1
                        )
                        self.assertEqual(
                            accounting["unknown_valuation_attempts"], 1
                        )
                        self.assertIsNone(
                            accounting["api_rate_equivalent_usd"]
                        )

                        credential_bytes = CREDENTIAL.encode("ascii")
                        for captured in (
                            prepare.stdout,
                            prepare.stderr,
                            execution.stdout,
                            execution.stderr,
                        ):
                            self.assertNotIn(credential_bytes, captured)
                        for artifact_root in (prepared, run_output):
                            for artifact in artifact_root.rglob("*"):
                                if artifact.is_file():
                                    self.assertNotIn(
                                        credential_bytes,
                                        artifact.read_bytes(),
                                        str(
                                            artifact.relative_to(
                                                artifact_root
                                            )
                                        ),
                                    )
        finally:
            server.shutdown()
            server.server_close()
            server_thread.join(2)


if __name__ == "__main__":
    unittest.main()
