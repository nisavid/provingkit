import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import unittest
import venv


RUNNER = Path(__file__).with_name("comparison_runner.py")
FIRST_ENV = "PROVINGKIT_TEST_FIRST_RUNTIME_BOUNDARY"
SECOND_ENV = "PROVINGKIT_TEST_SECOND_RUNTIME_BOUNDARY"
COLLIDING_ENV = "PROVINGKIT_TEST_CLOSE_DELAY_MARKER"
FIRST_CREDENTIAL = "pk_test_DO_NOT_USE_first_runtime_boundary_7d4f9b831e6a42c0"
SECOND_CREDENTIAL = "pk_test_DO_NOT_USE_second_runtime_boundary_90210b6c37fd48bb"
COLLIDING_CREDENTIAL = "pk_test_DO_NOT_USE_close_delay_collision_48c72d99e81a4b30"
PROBE_ENVIRONMENT = (
    (FIRST_ENV, FIRST_CREDENTIAL),
    (SECOND_ENV, SECOND_CREDENTIAL),
    (COLLIDING_ENV, COLLIDING_CREDENTIAL),
)
INPUT = b"The supplied source directly supports the claim."
SUCCESS_RESPONSE = (
    b'{"model":"gpt-6-luna","answers":[{"type":"choice","name":"claim_relation",'
    b'"choice":"supported","confidence":0.7,"probabilities":['
    b'{"value":"supported","probability":0.7},'
    b'{"value":"contradicted","probability":0.1},'
    b'{"value":"unsupported_extension","probability":0.1},'
    b'{"value":"unresolved","probability":0.1}]}],"usage":{"input_tokens":1}}'
)
SHIM = f"""\
import http.client
import os

_PROBE_LIVENESS = "transport-child-startup-v1"
_ENVIRONMENT = (
    ({FIRST_ENV!r}, {FIRST_CREDENTIAL!r}),
    ({SECOND_ENV!r}, {SECOND_CREDENTIAL!r}),
    ({COLLIDING_ENV!r}, {COLLIDING_CREDENTIAL!r}),
)
_STARTUP = {{name: os.environ.get(name) for name, _ in _ENVIRONMENT}}
_original_request = http.client.HTTPConnection.request


def _state(name, expected):
    value = _STARTUP[name]
    if value is None:
        return "absent"
    return "match" if value == expected else "other"


def _request(self, method, url, body=None, headers=None, *, encode_chunked=False):
    request_headers = {{}} if headers is None else dict(headers)
    request_headers["X-Provingkit-Probe-Liveness"] = _PROBE_LIVENESS
    for index, (name, expected) in enumerate(_ENVIRONMENT, 1):
        request_headers[f"X-Provingkit-Startup-Credential-{{index}}"] = _state(
            name, expected
        )
    return _original_request(
        self, method, url, body=body, headers=request_headers, encode_chunked=encode_chunked
    )


http.client.HTTPConnection.request = _request
"""


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


def install_probe_python(root):
    venv.EnvBuilder(with_pip=False).create(root)
    executable = (
        root / "Scripts" / "python.exe"
        if os.name == "nt"
        else root / "bin" / "python"
    )
    discovery = subprocess.run(
        [str(executable), "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"],
        env=child_environment(),
        capture_output=True,
        text=True,
        timeout=20,
    )
    if discovery.returncode or not discovery.stdout.strip():
        raise RuntimeError(
            f"unable to locate probe site-packages:\n"
            f"stdout:\n{discovery.stdout}\nstderr:\n{discovery.stderr}"
        )
    purelib = Path(discovery.stdout.strip())
    (purelib / "sitecustomize.py").write_text(SHIM, encoding="utf-8")
    return executable


class RecordingServer(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False


class RecordingHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        request = {
            "authorization": self.headers.get_all("Authorization") or [],
            "probe_liveness": self.headers.get_all("X-Provingkit-Probe-Liveness") or [],
            "startup_credential_1": (
                self.headers.get_all("X-Provingkit-Startup-Credential-1") or []
            ),
            "startup_credential_2": (
                self.headers.get_all("X-Provingkit-Startup-Credential-2") or []
            ),
            "startup_credential_3": (
                self.headers.get_all("X-Provingkit-Startup-Credential-3") or []
            ),
            "body": self.rfile.read(length),
        }
        with self.server.requests_lock:
            self.server.requests.append(request)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(SUCCESS_RESPONSE)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(SUCCESS_RESPONSE)

    def log_message(self, format, *args):
        pass


class TransportChildEnvironmentTest(unittest.TestCase):
    def run_cli(self, *arguments, environment, python_executable):
        result = subprocess.run(
            [str(python_executable), str(RUNNER), *arguments],
            cwd=RUNNER.parent,
            env=environment,
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        return result

    def _assert_transport_children(
        self, first_env, first_credential, second_env, second_credential
    ):
        server = RecordingServer(("127.0.0.1", 0), RecordingHandler)
        server.requests = []
        server.requests_lock = threading.Lock()
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                probe_python = install_probe_python(root / "probe-python")
                input_path = root / "input.txt"
                input_path.write_bytes(INPUT)
                spec_path = root / "spec.json"
                spec = {
                    "version": 1,
                    "kind": "claim",
                    "cases": [
                        {
                            "id": "c01",
                            "status": "ready",
                            "input": {
                                "path": str(input_path),
                                "sha256": hashlib.sha256(INPUT).hexdigest(),
                            },
                        }
                    ],
                    "conditions": [
                        {
                            "id": "first",
                            "adapter": "decisions",
                            "model": "gpt-6-luna",
                            "effort": None,
                            "endpoint": (
                                f"http://127.0.0.1:{server.server_port}/v1/decisions"
                            ),
                            "billing": "synthetic",
                            "auth_env": first_env,
                            "rates": {
                                "input": "0",
                                "cached": "0",
                                "write": "0",
                                "output": "0",
                            },
                        },
                        {
                            "id": "second",
                            "adapter": "decisions",
                            "model": "gpt-6-luna",
                            "effort": None,
                            "endpoint": (
                                f"http://127.0.0.1:{server.server_port}/v1/decisions"
                            ),
                            "billing": "synthetic",
                            "auth_env": second_env,
                            "rates": {
                                "input": "0",
                                "cached": "0",
                                "write": "0",
                                "output": "0",
                            },
                        }
                    ],
                    "limits": {
                        "request_seconds": 5,
                        "run_seconds": 10,
                        "input_bytes": 1024,
                        "request_bytes": 65536,
                        "response_bytes": 65536,
                        "requests_per_cell": 1,
                    },
                }
                spec_path.write_text(json.dumps(spec), encoding="utf-8")
                environment = child_environment()
                environment[first_env] = first_credential
                environment[second_env] = second_credential

                prepared = root / "prepared"
                preparation = self.run_cli(
                    "prepare",
                    "--spec",
                    str(spec_path),
                    "--output",
                    str(prepared),
                    environment=environment,
                    python_executable=probe_python,
                )
                manifest = json.loads(preparation.stdout)
                output = root / "run"
                self.run_cli(
                    "run",
                    "--prepared",
                    str(prepared),
                    "--manifest-sha256",
                    manifest["sha256"],
                    "--output",
                    str(output),
                    "--local-http",
                    environment=environment,
                    python_executable=probe_python,
                )

                summary = json.loads((output / "summary.json").read_text())
                attempts = [
                    json.loads((output / f"attempt-{index:04d}.json").read_text())
                    for index in range(2)
                ]
                self.assertEqual(
                    [(slot["condition"], slot["status"]) for slot in summary["slots"]],
                    [("first", "completed"), ("second", "completed")],
                )
                self.assertEqual(
                    [
                        (
                            attempt["condition"],
                            attempt["status"],
                            attempt["transport_status"],
                        )
                        for attempt in attempts
                    ],
                    [
                        ("first", "completed", "received"),
                        ("second", "completed", "received"),
                    ],
                )
                self.assertEqual(len(server.requests), 2)
                requests = {
                    request["authorization"][0]: request
                    for request in server.requests
                    if len(request["authorization"]) == 1
                }
                self.assertEqual(
                    set(requests),
                    {
                        "Bearer " + first_credential,
                        "Bearer " + second_credential,
                    },
                )
                for selected_env, selected_credential in (
                    (first_env, first_credential),
                    (second_env, second_credential),
                ):
                    request = requests["Bearer " + selected_credential]
                    self.assertEqual(
                        request["probe_liveness"],
                        ["transport-child-startup-v1"],
                        "the transport-child startup probe did not run",
                    )
                    expected_states = tuple(
                        ["match"] if name == selected_env else ["absent"]
                        for name, _ in PROBE_ENVIRONMENT
                    )
                    self.assertEqual(
                        (
                            request["startup_credential_1"],
                            request["startup_credential_2"],
                            request["startup_credential_3"],
                        ),
                        expected_states,
                        "the child startup environment did not contain only its selected credential",
                    )
        finally:
            server.shutdown()
            server.server_close()
            server_thread.join()

    def test_each_transport_child_receives_its_selected_credential_and_not_its_peer(self):
        scenarios = (
            (
                "noncolliding",
                FIRST_ENV,
                FIRST_CREDENTIAL,
                SECOND_ENV,
                SECOND_CREDENTIAL,
            ),
            (
                "runtime_allowlist_collision",
                FIRST_ENV,
                FIRST_CREDENTIAL,
                COLLIDING_ENV,
                COLLIDING_CREDENTIAL,
            ),
        )
        for scenario, *selector_pair in scenarios:
            with self.subTest(scenario=scenario):
                self._assert_transport_children(*selector_pair)


if __name__ == "__main__":
    unittest.main()
