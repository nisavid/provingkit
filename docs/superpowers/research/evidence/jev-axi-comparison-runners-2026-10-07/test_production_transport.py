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
INPUT = b"The supplied source directly supports the claim."
READY_CREDENTIAL = "pk_test_DO_NOT_USE_ready_transport_5914b85ab3694a59"
INVALID_CREDENTIAL = "pk_test invalid transport credential"
READY_SELECTOR = "PROVINGKIT_TEST_READY_API_KEY"
INVALID_SELECTOR = "PROVINGKIT_TEST_INVALID_API_KEY"

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
        "usage": {"input_tokens": 1},
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


def rates():
    return {"input": "0", "cached": "0", "write": "0", "output": "0"}


def claim_spec(source, conditions):
    return {
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
        "conditions": conditions,
        "limits": {
            "request_seconds": 3,
            "run_seconds": 8,
            "input_bytes": 1024,
            "request_bytes": 16384,
            "response_bytes": 16384,
            "requests_per_cell": 1,
        },
    }


class RecordingServer(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False


class RecordingHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        request = {
            "path": self.path,
            "authorization": self.headers.get_all("Authorization") or [],
            "content_type": self.headers.get_all("Content-Type") or [],
            "body": self.rfile.read(length),
        }
        with self.server.requests_lock:
            self.server.requests.append(request)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(SUCCESS_RESPONSE)))
        self.end_headers()
        self.wfile.write(SUCCESS_RESPONSE)

    def log_message(self, format, *args):
        pass


@unittest.skipUnless(sys.platform == "linux", "transport execution is Linux-only")
class ProductionTransportTest(unittest.TestCase):
    def run_cli(self, *arguments, environment, cwd):
        return subprocess.run(
            [sys.executable, str(RUNNER), *arguments],
            cwd=cwd,
            env=environment,
            capture_output=True,
            timeout=12,
            check=False,
        )

    def test_prepare_accepts_only_fixed_https_route_and_credential_bindings(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "claim.txt"
            source.write_bytes(INPUT)

            valid = (
                {
                    "id": "responses",
                    "adapter": "responses",
                    "model": "gpt-6-luna",
                    "effort": "low",
                    "endpoint": "https://api.openai.com/v1/responses",
                    "billing": "openai_api",
                    "auth_env": "OPENAI_API_KEY",
                    "rates": rates(),
                },
                {
                    "id": "decisions",
                    "adapter": "decisions",
                    "model": "gpt-6-luna",
                    "effort": None,
                    "endpoint": "https://api.openai.com/v1/decisions",
                    "billing": "openai_api",
                    "auth_env": "OPENAI_API_KEY",
                    "rates": rates(),
                },
                {
                    "id": "jev",
                    "adapter": "jev",
                    "model": "jev-1.13.0",
                    "effort": None,
                    "endpoint": "https://api.typesafe.ai/v1/systemone",
                    "billing": "typesafe_api",
                    "auth_env": "TYPESAFE_API_KEY",
                    "rates": rates(),
                },
            )
            environment = child_environment()
            for index, condition in enumerate(valid):
                with self.subTest(valid=condition["adapter"]):
                    spec_path = root / f"valid-{index}.json"
                    output = root / f"valid-{index}"
                    spec_path.write_text(
                        json.dumps(claim_spec(source, [condition])),
                        encoding="utf-8",
                    )
                    result = self.run_cli(
                        "prepare",
                        "--spec",
                        str(spec_path),
                        "--output",
                        str(output),
                        environment=environment,
                        cwd=root,
                    )
                    self.assertEqual(
                        result.returncode,
                        0,
                        result.stderr.decode("utf-8", errors="replace"),
                    )

            invalid = (
                dict(
                    valid[0],
                    id="wrong_host",
                    endpoint="https://api.openai.com.example.invalid/v1/responses",
                ),
                dict(
                    valid[0],
                    id="wrong_path",
                    endpoint="https://api.openai.com/v1/decisions",
                ),
                dict(
                    valid[1],
                    id="insecure_provider",
                    endpoint="http://api.openai.com/v1/decisions",
                ),
                dict(
                    valid[2],
                    id="wrong_credential",
                    auth_env="OPENAI_API_KEY",
                ),
            )
            for index, condition in enumerate(invalid):
                with self.subTest(invalid=condition["id"]):
                    spec_path = root / f"invalid-{index}.json"
                    output = root / f"invalid-{index}"
                    spec_path.write_text(
                        json.dumps(claim_spec(source, [condition])),
                        encoding="utf-8",
                    )
                    result = self.run_cli(
                        "prepare",
                        "--spec",
                        str(spec_path),
                        "--output",
                        str(output),
                        environment=environment,
                        cwd=root,
                    )
                    self.assertEqual(result.returncode, 2)
                    self.assertIn(
                        b"unsupported endpoint or credential selector binding",
                        result.stderr,
                    )
                    self.assertFalse(output.exists())

    def test_invalid_credential_is_condition_local_and_loopback_is_explicit(self):
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
                refused_output = root / "refused"
                run_output = root / "run"
                source.write_bytes(INPUT)
                endpoint = (
                    f"http://127.0.0.1:{server.server_port}/v1/decisions"
                )

                def condition(identity, selector):
                    return {
                        "id": identity,
                        "adapter": "decisions",
                        "model": "gpt-6-luna",
                        "effort": None,
                        "endpoint": endpoint,
                        "billing": "synthetic",
                        "auth_env": selector,
                        "rates": rates(),
                    }

                spec_path.write_text(
                    json.dumps(
                        claim_spec(
                            source,
                            [
                                condition("invalid", INVALID_SELECTOR),
                                condition("ready", READY_SELECTOR),
                            ],
                        )
                    ),
                    encoding="utf-8",
                )
                environment = child_environment()
                preparation = self.run_cli(
                    "prepare",
                    "--spec",
                    str(spec_path),
                    "--output",
                    str(prepared),
                    environment=environment,
                    cwd=root,
                )
                self.assertEqual(
                    preparation.returncode,
                    0,
                    preparation.stderr.decode("utf-8", errors="replace"),
                )
                manifest_digest = json.loads(preparation.stdout)["sha256"]

                environment[INVALID_SELECTOR] = INVALID_CREDENTIAL
                environment[READY_SELECTOR] = READY_CREDENTIAL
                refused = self.run_cli(
                    "run",
                    "--prepared",
                    str(prepared),
                    "--manifest-sha256",
                    manifest_digest,
                    "--output",
                    str(refused_output),
                    environment=environment,
                    cwd=root,
                )
                self.assertEqual(refused.returncode, 2)
                self.assertIn(
                    b"loopback HTTP requires --local-http",
                    refused.stderr,
                )
                self.assertFalse(refused_output.exists())
                self.assertEqual(server.requests, [])

                execution = self.run_cli(
                    "run",
                    "--prepared",
                    str(prepared),
                    "--manifest-sha256",
                    manifest_digest,
                    "--output",
                    str(run_output),
                    "--local-http",
                    environment=environment,
                    cwd=root,
                )
                self.assertEqual(
                    execution.returncode,
                    0,
                    execution.stderr.decode("utf-8", errors="replace"),
                )

                summary = json.loads((run_output / "summary.json").read_bytes())
                self.assertEqual(
                    summary["credential_preflight"],
                    [
                        {
                            "condition": "invalid",
                            "auth_env": INVALID_SELECTOR,
                            "status": "credential_invalid",
                            "submission_started": False,
                        },
                        {
                            "condition": "ready",
                            "auth_env": READY_SELECTOR,
                            "status": "ready",
                            "submission_started": False,
                        },
                    ],
                )
                self.assertEqual(
                    [
                        (slot["condition"], slot["status"], slot.get("reason"))
                        for slot in summary["slots"]
                    ],
                    [
                        ("invalid", "unattempted", "credential_invalid"),
                        ("ready", "completed", None),
                    ],
                )
                self.assertFalse((run_output / "request-0000.body").exists())
                self.assertFalse((run_output / "request-0000.json").exists())
                self.assertFalse((run_output / "response-0000.body").exists())
                self.assertFalse((run_output / "attempt-0000.json").exists())
                self.assertTrue((run_output / "attempt-0001.json").is_file())

                with server.requests_lock:
                    requests = list(server.requests)
                self.assertEqual(len(requests), 1)
                self.assertEqual(requests[0]["path"], "/v1/decisions")
                self.assertEqual(
                    requests[0]["authorization"],
                    [f"Bearer {READY_CREDENTIAL}"],
                )
                self.assertEqual(
                    requests[0]["content_type"],
                    ["application/json"],
                )

                secrets = (
                    INVALID_CREDENTIAL.encode("ascii"),
                    READY_CREDENTIAL.encode("ascii"),
                )
                for captured in (
                    preparation.stdout,
                    preparation.stderr,
                    refused.stdout,
                    refused.stderr,
                    execution.stdout,
                    execution.stderr,
                ):
                    for secret in secrets:
                        self.assertNotIn(secret, captured)
                for artifact_root in (prepared, run_output):
                    for artifact in artifact_root.rglob("*"):
                        if artifact.is_file():
                            content = artifact.read_bytes()
                            for secret in secrets:
                                self.assertNotIn(
                                    secret,
                                    content,
                                    str(artifact.relative_to(artifact_root)),
                                )
        finally:
            server.shutdown()
            server.server_close()
            server_thread.join(2)

    def test_production_mode_retains_missing_credentials_without_submissions(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "claim.txt"
            source.write_bytes(INPUT)
            conditions = [
                {"id": "responses", "adapter": "responses", "model": "gpt-6-luna",
                 "effort": "low", "endpoint": "https://api.openai.com/v1/responses",
                 "billing": "openai_api", "auth_env": "OPENAI_API_KEY", "rates": rates()},
                {"id": "jev", "adapter": "jev", "model": "jev-1.13.0", "effort": None,
                 "endpoint": "https://api.typesafe.ai/v1/systemone", "billing": "typesafe_api",
                 "auth_env": "TYPESAFE_API_KEY", "rates": rates()},
            ]
            spec = root / "spec.json"
            spec.write_text(json.dumps(claim_spec(source, conditions)))
            environment = child_environment()
            prepared = root / "prepared"
            result = self.run_cli("prepare", "--spec", str(spec), "--output", str(prepared),
                                  environment=environment, cwd=root)
            self.assertEqual(result.returncode, 0, result.stderr)
            digest = json.loads(result.stdout)["sha256"]
            refused = root / "refused"
            result = self.run_cli("run", "--prepared", str(prepared), "--manifest-sha256", digest,
                                  "--output", str(refused), "--local-http",
                                  environment=environment, cwd=root)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(refused.exists())
            output = root / "run"
            result = self.run_cli("run", "--prepared", str(prepared), "--manifest-sha256", digest,
                                  "--output", str(output), environment=environment, cwd=root)
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual([slot["reason"] for slot in summary["slots"]],
                             ["credential_missing", "credential_missing"])
            self.assertEqual(list(output.glob("attempt-*.json")), [])


if __name__ == "__main__":
    unittest.main()
