from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_ROOT = REPO_ROOT / "plugins/rolecasting/skills/choosing-agent-models/scripts"
CATALOG = SCRIPT_ROOT / "daybreak_catalog.py"
ACCOUNT = SCRIPT_ROOT / "daybreak_account.py"
BASE_ENV = {"LC_ALL": "C", "PYTHONDONTWRITEBYTECODE": "1"}


FAKE_CODEX = r"""#!{python}
import json
import os
import signal
import sys

log_path = os.environ["FAKE_LOG"]
requests = []
with open(log_path, "w", encoding="utf-8") as log:
    def terminated(_signal, _frame):
        log.write(json.dumps({{"terminated": True}}) + "\n")
        log.flush()
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, terminated)
    json.dump({{"codex_home": os.environ.get("CODEX_HOME")}}, log)
    log.write("\n")
    log.flush()
    for line in sys.stdin:
        message = json.loads(line)
        if "id" not in message:
            continue
        requests.append(message)
        method = message["method"]
        if method == "initialize":
            result = {{}}
        elif method == "account/read":
            result = {{"account": {{"type": "chatgpt", "email": "private@example.invalid", "planType": "pro"}}, "requiresOpenaiAuth": True}}
            if os.environ.get("FAKE_ACCOUNT_READ_CASE") == "missing-email":
                result = {{"account": {{"type": "chatgpt", "planType": "pro"}}, "requiresOpenaiAuth": True}}
            elif os.environ.get("FAKE_ACCOUNT_READ_CASE") == "false-account":
                result = {{"account": False, "requiresOpenaiAuth": True}}
            elif os.environ.get("FAKE_ACCOUNT_READ_CASE") == "bad-plan":
                result = {{"account": {{"type": "chatgpt", "email": None, "planType": {{"secret": "provider-plan-secret"}}}}, "requiresOpenaiAuth": True}}
        elif method == "model/list":
            result = {{"data": [
                {{"id": "unrelated", "model": "unrelated", "supportedReasoningEfforts": [{{"reasoningEffort": "high", "description": ""}}]}},
                {{"id": "daybreak", "model": "gpt-daybreak-blue-latest", "supportedReasoningEfforts": [{{"reasoningEffort": "high", "description": ""}}], "availableAccessPrograms": {{"cyber": ["daybreakBlue"]}}}}
            ]}}
            model_page = sum(1 for request in requests if request["method"] == "model/list")
            cursor_mode = os.environ.get("FAKE_MODEL_CURSOR_MODE")
            if cursor_mode == "repeated" and model_page <= 2:
                result["nextCursor"] = "repeated-cursor"
            elif cursor_mode == "unique" and model_page <= 101:
                result["nextCursor"] = "cursor-" + str(model_page)
            if os.environ.get("FAKE_MODEL_CASE") == "bad-effort":
                result["data"][1]["supportedReasoningEfforts"][0]["reasoningEffort"] = {{"secret": "provider-effort-secret"}}
        elif method == "account/rateLimits/read":
            result = {{
                "accountId": "synthetic-selected",
                "ordinaryUsageAllowed": True,
                "rateLimits": {{"normalModelSlug": "unrelated", "primary": {{"usedPercent": 99}}}},
                "rateLimitsByLimitId": {{
                    "daybreak": {{
                        "normalModelSlug": "gpt-daybreak-blue-latest",
                        "primary": {{"usedPercent": 12, "resetsAt": 2000000000, "windowDurationMins": 300}},
                        "secondary": None,
                        "spendControlReached": False,
                        "rateLimitReachedType": None
                    }}
                }},
                "rawSecret": "must-not-escape"
            }}
        elif method == "thread/start":
            result = {{"thread": {{"id": "thread-synthetic"}}}}
        elif method == "turn/start":
            result = {{"turn": {{"id": "turn-synthetic", "status": "inProgress", "items": []}}}}
        else:
            result = {{}}
        if method == "account/rateLimits/read" and os.environ.get("FAKE_CAPACITY_SECRET"):
            result["rateLimitsByLimitId"]["daybreak"]["primary"]["usedPercent"] = {{"secret": "provider-capacity-secret"}}
        if method == "account/rateLimits/read":
            capacity_field = os.environ.get("FAKE_CAPACITY_FIELD")
            bucket = result["rateLimitsByLimitId"]["daybreak"]
            if capacity_field == "resets-at":
                bucket["primary"]["resetsAt"] = {{"secret": "provider-scalar-secret"}}
            elif capacity_field == "window-duration":
                bucket["primary"]["windowDurationMins"] = "provider-scalar-secret"
            elif capacity_field == "secondary":
                bucket["secondary"] = {{"usedPercent": "provider-scalar-secret"}}
            elif capacity_field == "spend-control":
                bucket["spendControlReached"] = "provider-scalar-secret"
            elif capacity_field == "reached-type":
                bucket["rateLimitReachedType"] = {{"secret": "provider-scalar-secret"}}
        if method == "account/rateLimits/read" and os.environ.get("FAKE_ACCOUNT_ID"):
            result["accountId"] = os.environ["FAKE_ACCOUNT_ID"]
        if method == "account/rateLimits/read":
            rate_case = os.environ.get("FAKE_RATE_CASE")
            if rate_case == "missing-rate-limits":
                del result["rateLimits"]
            elif rate_case == "bad-buckets":
                result["rateLimitsByLimitId"] = [{{"secret": "provider-bucket-secret"}}]
            elif rate_case == "bad-model-slug":
                result["rateLimitsByLimitId"]["daybreak"]["normalModelSlug"] = {{"secret": "provider-slug-secret"}}
            elif rate_case == "bad-account-id":
                result["accountId"] = {{"secret": "provider-account-secret"}}
            elif rate_case == "bad-ordinary-usage":
                result["ordinaryUsageAllowed"] = {{"secret": "provider-usage-secret"}}
        if method == "model/list" and os.environ.get("FAKE_RPC_STRUCTURED_CODE"):
            response = {{"id": message["id"], "error": {{"code": {{"secret": "provider-code-secret"}}, "message": "provider-secret-body"}}}}
        elif method == "model/list" and os.environ.get("FAKE_RPC_BAD_MESSAGE"):
            response = {{"id": message["id"], "error": {{"code": -32000, "message": {{"secret": "provider-message-secret"}}}}}}
        elif method == "model/list" and os.environ.get("FAKE_RPC_ERROR"):
            response = {{"id": message["id"], "error": {{"code": -32000, "message": "provider-secret-body"}}}}
        else:
            response = {{"id": message["id"], "result": result}}
        sys.stdout.write(json.dumps(response) + "\n")
        if method == "turn/start":
            sys.stdout.write(json.dumps({{
                "method": "turn/completed",
                "params": {{
                    "threadId": "thread-synthetic",
                    "turn": {{"id": "turn-synthetic", "status": "completed", "items": []}}
                }}
            }}) + "\n")
        sys.stdout.flush()
        log.write(json.dumps(message, sort_keys=True) + "\n")
        log.flush()
"""


def write_fake_codex(path: Path) -> None:
    path.write_text(FAKE_CODEX.format(python=sys.executable), encoding="utf-8")
    path.chmod(0o700)


def start_observed_fifo(path: Path, marker: Path, content: str) -> subprocess.Popen:
    os.mkfifo(path)
    ready = marker.with_name(marker.name + ".ready")
    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            (
                "import pathlib,sys; "
                "pathlib.Path(sys.argv[2] + '.ready').touch(); "
                "stream=open(sys.argv[1], 'w', encoding='utf-8'); "
                "stream.write(sys.argv[3]); stream.close(); "
                "pathlib.Path(sys.argv[2]).touch()"
            ),
            str(path),
            str(marker),
            content,
        ],
        env=BASE_ENV,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _attempt in range(200):
        if ready.exists():
            return process
        if process.poll() is not None:
            break
        time.sleep(0.005)
    stop_fifo_writer(process)
    raise AssertionError("FIFO observer did not become ready")


def stop_fifo_writer(process: subprocess.Popen) -> None:
    if process.poll() is None:
        process.terminate()
        process.wait(timeout=2)


def catalog_binding(label: str, account_home: str, account_id: str) -> str:
    return (
        f"- binding: {label}\n"
        f"  codex_home: {account_home}\n"
        f"  authenticated_account_id: {account_id}\n"
        "  account_classification: synthetic plan\n"
        "  authentication_observation: synthetic observation\n"
        "  configuration_topology: synthetic configuration\n"
        "  database_topology: synthetic database\n"
        "  usage_capacity: synthetic capacity\n"
        "  daybreak_selector: synthetic selector\n"
        "  harmless_probe: synthetic observation\n"
        "  task_data_authority: not implied by this binding\n"
    )


class DaybreakCatalogTests(unittest.TestCase):
    def test_inspect_reports_only_positions_for_every_valid_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            catalog = root / "bindings.md"
            catalog.write_text(
                "# Synthetic bindings\n\nThese records are fixture inputs.\n\n"
                + catalog_binding(
                    "fixture-one", "~/synthetic/account-one", "synthetic-one"
                )
                + "\n"
                + catalog_binding(
                    "fixture-two", "~/synthetic/account-two", "synthetic-two"
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, str(CATALOG), "inspect", "--catalog", str(catalog)],
                text=True,
                capture_output=True,
                check=False,
                env=BASE_ENV,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            {
                "schema": "rolecasting-daybreak-catalog-inspection-v1",
                "binding_count": 2,
                "entries": [{"position": 1}, {"position": 2}],
            },
        )
        self.assertNotIn("synthetic-one", result.stdout)
        self.assertNotIn("account-one", result.stdout)

    def test_malformed_binding_blocks_and_invalid_positions_emit_no_record(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            catalog = root / "bindings.md"
            cases = (
                (
                    "malformed-second-binding",
                    catalog_binding("one", "/synthetic/one", "one")
                    + "\n- binding: two\n"
                    "  codex_home: /synthetic/two\n"
                    "  wrong_field: two\n",
                    ["inspect", "--catalog", str(catalog)],
                ),
                (
                    "position-outside-catalog",
                    catalog_binding("one", "/synthetic/one", "one"),
                    ["select", "--catalog", str(catalog), "--position", "2"],
                ),
                (
                    "home-relative-path-becomes-absolute",
                    catalog_binding("one", "~//synthetic/escape", "one"),
                    ["inspect", "--catalog", str(catalog)],
                ),
            )
            for name, content, arguments in cases:
                with self.subTest(name=name):
                    catalog.write_text(content, encoding="utf-8")
                    result = subprocess.run(
                        [sys.executable, str(CATALOG), *arguments],
                        text=True,
                        capture_output=True,
                        check=False,
                        env=BASE_ENV,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, "")

    def test_missing_or_unknown_informational_metadata_invalidates_catalog(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            catalog = Path(temporary) / "bindings.md"
            valid = catalog_binding("one", "/synthetic/one", "one")
            cases = {
                "missing": valid.replace(
                    "  harmless_probe: synthetic observation\n", ""
                ),
                "unknown": valid + "  future_metadata: unsupported\n",
            }
            for name, content in cases.items():
                with self.subTest(name=name):
                    catalog.write_text(content, encoding="utf-8")
                    result = subprocess.run(
                        [
                            sys.executable,
                            str(CATALOG),
                            "inspect",
                            "--catalog",
                            str(catalog),
                        ],
                        text=True,
                        capture_output=True,
                        check=False,
                        env=BASE_ENV,
                    )

                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, "")


class DaybreakAccountTests(unittest.TestCase):
    def test_status_refresh_uses_only_the_selected_home_and_redacts_results(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            selected = root / "selected"
            sibling = root / "sibling"
            poison_home = root
            selected.mkdir()
            sibling.mkdir()
            selected_read = root / "selected-auth-read"
            selected_writer = start_observed_fifo(
                selected / "auth.json",
                selected_read,
                json.dumps({"tokens": {"account_id": "synthetic-selected"}}),
            )
            sibling_auth = sibling / "auth.json"
            sibling_read = root / "sibling-auth-read"
            sibling_writer = start_observed_fifo(
                sibling_auth,
                sibling_read,
                json.dumps({"tokens": {"account_id": "synthetic-sibling"}}),
            )
            poison_catalog = poison_home / ".agents" / "daybreak-account-bindings.md"
            poison_catalog.parent.mkdir()
            catalog_read = root / "ambient-catalog-read"
            catalog_writer = start_observed_fifo(
                poison_catalog,
                catalog_read,
                "ambient catalog sentinel",
            )
            executable = root / "fake-codex"
            log = root / "fake.log"
            write_fake_codex(executable)
            selection = {
                "schema": "rolecasting-daybreak-account-selection-v1",
                "account_home": "~/selected",
                "authenticated_account_id": "synthetic-selected",
            }

            result = subprocess.run(
                [
                    sys.executable,
                    str(ACCOUNT),
                    "status-refresh",
                    "--selection-stdin",
                    "--codex",
                    str(executable),
                    "--model",
                    "gpt-daybreak-blue-latest/high",
                    "--freshness-seconds",
                    "1800",
                ],
                input=json.dumps(selection),
                text=True,
                capture_output=True,
                check=False,
                timeout=5,
                env={
                    **BASE_ENV,
                    "HOME": str(poison_home),
                    "FAKE_LOG": str(log),
                },
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(selected_writer.wait(timeout=2), 0)
            sibling_writer_blocked = sibling_writer.poll() is None
            catalog_writer_blocked = catalog_writer.poll() is None
            stop_fifo_writer(sibling_writer)
            stop_fifo_writer(catalog_writer)
            fake_observation = json.loads(log.read_text().splitlines()[0])
            selected_was_read = selected_read.exists()
            sibling_was_read = sibling_read.exists()
            catalog_was_read = catalog_read.exists()

        output = json.loads(result.stdout)
        self.assertEqual(output["operation"], "status-refresh")
        self.assertEqual(output["selector"], "gpt-daybreak-blue-latest/high")
        self.assertTrue(output["binding_matches"])
        self.assertTrue(output["authenticated"])
        self.assertTrue(output["ordinary_usage_allowed"])
        self.assertEqual(output["capacity"]["primary"]["used_percent"], 12)
        self.assertEqual(fake_observation, {"codex_home": str(selected)})
        self.assertTrue(selected_was_read)
        self.assertTrue(sibling_writer_blocked)
        self.assertFalse(sibling_was_read)
        self.assertTrue(catalog_writer_blocked)
        self.assertFalse(catalog_was_read)
        for forbidden in (
            "private@example.invalid",
            "private-account-id",
            "must-not-escape",
            "unrelated",
            str(selected),
            "synthetic-selected",
        ):
            self.assertNotIn(forbidden, result.stdout)

    def test_harmless_probe_fails_closed_without_tool_prevention_control(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            selected = root / "selected"
            selected.mkdir()
            workspace = root / "probe-workspace"
            workspace.mkdir()
            auth_read = root / "probe-auth-read"
            auth_writer = start_observed_fifo(
                selected / "auth.json",
                auth_read,
                json.dumps({"tokens": {"account_id": "synthetic-selected"}}),
            )
            executable = root / "fake-codex"
            log = root / "fake.log"
            write_fake_codex(executable)
            selection = {
                "schema": "rolecasting-daybreak-account-selection-v1",
                "account_home": str(selected),
                "authenticated_account_id": "synthetic-selected",
            }

            result = subprocess.run(
                [
                    sys.executable,
                    str(ACCOUNT),
                    "harmless-probe",
                    "--selection-stdin",
                    "--codex",
                    str(executable),
                    "--model",
                    "gpt-daybreak-blue-latest/high",
                    "--workspace",
                    str(workspace),
                ],
                input=json.dumps(selection),
                text=True,
                capture_output=True,
                check=False,
                timeout=5,
                env={**BASE_ENV, "FAKE_LOG": str(log)},
            )

            auth_writer_blocked = auth_writer.poll() is None
            stop_fifo_writer(auth_writer)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertFalse(log.exists())
            self.assertTrue(auth_writer_blocked)
            self.assertFalse(auth_read.exists())

        self.assertIn("do not provide a closed-world task-tool deny", result.stderr)
        self.assertIn("no Codex process was launched", result.stderr)

    def test_invalid_selection_and_binding_mismatch_never_launch_codex(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            selected = root / "selected"
            selected.mkdir()
            (selected / "auth.json").write_text(
                json.dumps({"tokens": {"account_id": "synthetic-selected"}}),
                encoding="utf-8",
            )
            executable = root / "fake-codex"
            write_fake_codex(executable)
            valid = {
                "schema": "rolecasting-daybreak-account-selection-v1",
                "account_home": str(selected),
                "authenticated_account_id": "synthetic-selected",
            }
            cases = {
                "missing": "",
                "array": json.dumps([valid]),
                "multiple": json.dumps(valid) + json.dumps(valid),
                "duplicate-key": (
                    '{"schema":"rolecasting-daybreak-account-selection-v1",'
                    f'"account_home":"{selected}","account_home":"{selected}",'
                    '"authenticated_account_id":"synthetic-selected"}'
                ),
                "unknown-field": json.dumps({**valid, "fallback": True}),
                "binding-mismatch": json.dumps(
                    {**valid, "authenticated_account_id": "different-account"}
                ),
            }
            for name, selection in cases.items():
                with self.subTest(name=name):
                    log = root / f"{name}.log"
                    result = subprocess.run(
                        [
                            sys.executable,
                            str(ACCOUNT),
                            "status-refresh",
                            "--selection-stdin",
                            "--codex",
                            str(executable),
                            "--model",
                            "gpt-daybreak-blue-latest/high",
                            "--freshness-seconds",
                            "1800",
                        ],
                        input=selection,
                        text=True,
                        capture_output=True,
                        check=False,
                        env={**BASE_ENV, "FAKE_LOG": str(log)},
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, "")
                    self.assertFalse(log.exists())

    def test_malformed_selected_authentication_fails_without_traceback_or_launch(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            selected = root / "selected"
            selected.mkdir()
            (selected / "auth.json").write_text(
                json.dumps({"tokens": "provider-auth-secret"}),
                encoding="utf-8",
            )
            executable = root / "fake-codex"
            log = root / "fake.log"
            write_fake_codex(executable)
            selection = {
                "schema": "rolecasting-daybreak-account-selection-v1",
                "account_home": str(selected),
                "authenticated_account_id": "synthetic-selected",
            }

            result = subprocess.run(
                [
                    sys.executable,
                    str(ACCOUNT),
                    "status-refresh",
                    "--selection-stdin",
                    "--codex",
                    str(executable),
                    "--model",
                    "gpt-daybreak-blue-latest/high",
                    "--freshness-seconds",
                    "1800",
                ],
                input=json.dumps(selection),
                text=True,
                capture_output=True,
                check=False,
                env={**BASE_ENV, "FAKE_LOG": str(log)},
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("selected authentication record is malformed", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn("provider-auth-secret", result.stderr)
        self.assertFalse(log.exists())

    def test_status_rpc_error_is_redacted_and_terminates_selected_process(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            selected = root / "selected"
            selected.mkdir()
            (selected / "auth.json").write_text(
                json.dumps({"tokens": {"account_id": "synthetic-selected"}}),
                encoding="utf-8",
            )
            executable = root / "fake-codex"
            log = root / "fake.log"
            write_fake_codex(executable)
            selection = {
                "schema": "rolecasting-daybreak-account-selection-v1",
                "account_home": str(selected),
                "authenticated_account_id": "synthetic-selected",
            }

            result = subprocess.run(
                [
                    sys.executable,
                    str(ACCOUNT),
                    "status-refresh",
                    "--selection-stdin",
                    "--codex",
                    str(executable),
                    "--model",
                    "gpt-daybreak-blue-latest/high",
                    "--freshness-seconds",
                    "1800",
                ],
                input=json.dumps(selection),
                text=True,
                capture_output=True,
                check=False,
                env={
                    **BASE_ENV,
                    "FAKE_LOG": str(log),
                    "FAKE_RPC_ERROR": "1",
                },
            )

            transcript = [json.loads(line) for line in log.read_text().splitlines()]

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("RPC error -32000", result.stderr)
        self.assertNotIn("provider-secret-body", result.stderr)
        self.assertEqual(transcript[-1], {"terminated": True})

    def test_status_rejects_malformed_capacity_without_echoing_provider_value(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            selected = root / "selected"
            selected.mkdir()
            (selected / "auth.json").write_text(
                json.dumps({"tokens": {"account_id": "synthetic-selected"}}),
                encoding="utf-8",
            )
            executable = root / "fake-codex"
            log = root / "fake.log"
            write_fake_codex(executable)
            selection = {
                "schema": "rolecasting-daybreak-account-selection-v1",
                "account_home": str(selected),
                "authenticated_account_id": "synthetic-selected",
            }

            result = subprocess.run(
                [
                    sys.executable,
                    str(ACCOUNT),
                    "status-refresh",
                    "--selection-stdin",
                    "--codex",
                    str(executable),
                    "--model",
                    "gpt-daybreak-blue-latest/high",
                    "--freshness-seconds",
                    "1800",
                ],
                input=json.dumps(selection),
                text=True,
                capture_output=True,
                check=False,
                env={
                    **BASE_ENV,
                    "FAKE_LOG": str(log),
                    "FAKE_CAPACITY_SECRET": "1",
                },
            )

            transcript = [json.loads(line) for line in log.read_text().splitlines()]

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("capacity response has an invalid type", result.stderr)
        self.assertNotIn("provider-capacity-secret", result.stderr)
        self.assertEqual(transcript[-1], {"terminated": True})

    def test_status_validates_each_allowlisted_capacity_field_type(self) -> None:
        for capacity_field in (
            "resets-at",
            "window-duration",
            "secondary",
            "spend-control",
            "reached-type",
        ):
            with self.subTest(capacity_field=capacity_field):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    selected = root / "selected"
                    selected.mkdir()
                    (selected / "auth.json").write_text(
                        json.dumps({"tokens": {"account_id": "synthetic-selected"}}),
                        encoding="utf-8",
                    )
                    executable = root / "fake-codex"
                    log = root / "fake.log"
                    write_fake_codex(executable)
                    selection = {
                        "schema": "rolecasting-daybreak-account-selection-v1",
                        "account_home": str(selected),
                        "authenticated_account_id": "synthetic-selected",
                    }

                    result = subprocess.run(
                        [
                            sys.executable,
                            str(ACCOUNT),
                            "status-refresh",
                            "--selection-stdin",
                            "--codex",
                            str(executable),
                            "--model",
                            "gpt-daybreak-blue-latest/high",
                            "--freshness-seconds",
                            "1800",
                        ],
                        input=json.dumps(selection),
                        text=True,
                        capture_output=True,
                        check=False,
                        env={
                            **BASE_ENV,
                            "FAKE_LOG": str(log),
                            "FAKE_CAPACITY_FIELD": capacity_field,
                        },
                    )

                    transcript = [
                        json.loads(line) for line in log.read_text().splitlines()
                    ]

                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertIn("capacity response has an invalid type", result.stderr)
                self.assertNotIn("provider-scalar-secret", result.stderr)
                self.assertEqual(transcript[-1], {"terminated": True})

    def test_status_rejects_malformed_rate_limit_envelopes(self) -> None:
        cases = {
            "missing-rate-limits": "provider",
            "bad-buckets": "provider-bucket-secret",
            "bad-model-slug": "provider-slug-secret",
        }
        for rate_case, secret in cases.items():
            with self.subTest(rate_case=rate_case):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    selected = root / "selected"
                    selected.mkdir()
                    (selected / "auth.json").write_text(
                        json.dumps({"tokens": {"account_id": "synthetic-selected"}}),
                        encoding="utf-8",
                    )
                    executable = root / "fake-codex"
                    log = root / "fake.log"
                    write_fake_codex(executable)
                    selection = {
                        "schema": "rolecasting-daybreak-account-selection-v1",
                        "account_home": str(selected),
                        "authenticated_account_id": "synthetic-selected",
                    }

                    result = subprocess.run(
                        [
                            sys.executable,
                            str(ACCOUNT),
                            "status-refresh",
                            "--selection-stdin",
                            "--codex",
                            str(executable),
                            "--model",
                            "gpt-daybreak-blue-latest/high",
                            "--freshness-seconds",
                            "1800",
                        ],
                        input=json.dumps(selection),
                        text=True,
                        capture_output=True,
                        check=False,
                        env={
                            **BASE_ENV,
                            "FAKE_LOG": str(log),
                            "FAKE_RATE_CASE": rate_case,
                        },
                    )

                    transcript = [
                        json.loads(line) for line in log.read_text().splitlines()
                    ]

                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertIn(
                    "account/rateLimits/read returned an invalid result",
                    result.stderr,
                )
                self.assertNotIn(secret, result.stderr)
                self.assertEqual(transcript[-1], {"terminated": True})

    def test_status_validates_provider_identity_and_usage_types(self) -> None:
        cases = {
            "bad-account-id": (
                "provider account identity is unavailable",
                "provider-account-secret",
            ),
            "bad-ordinary-usage": (
                "ordinaryUsageAllowed has an invalid type",
                "provider-usage-secret",
            ),
        }
        for rate_case, (diagnostic, secret) in cases.items():
            with self.subTest(rate_case=rate_case):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    selected = root / "selected"
                    selected.mkdir()
                    (selected / "auth.json").write_text(
                        json.dumps({"tokens": {"account_id": "synthetic-selected"}}),
                        encoding="utf-8",
                    )
                    executable = root / "fake-codex"
                    log = root / "fake.log"
                    write_fake_codex(executable)
                    selection = {
                        "schema": "rolecasting-daybreak-account-selection-v1",
                        "account_home": str(selected),
                        "authenticated_account_id": "synthetic-selected",
                    }

                    result = subprocess.run(
                        [
                            sys.executable,
                            str(ACCOUNT),
                            "status-refresh",
                            "--selection-stdin",
                            "--codex",
                            str(executable),
                            "--model",
                            "gpt-daybreak-blue-latest/high",
                            "--freshness-seconds",
                            "1800",
                        ],
                        input=json.dumps(selection),
                        text=True,
                        capture_output=True,
                        check=False,
                        env={
                            **BASE_ENV,
                            "FAKE_LOG": str(log),
                            "FAKE_RATE_CASE": rate_case,
                        },
                    )

                    transcript = [
                        json.loads(line) for line in log.read_text().splitlines()
                    ]

                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertIn(diagnostic, result.stderr)
                self.assertNotIn(secret, result.stderr)
                self.assertEqual(transcript[-1], {"terminated": True})

    def test_status_reduces_malformed_rpc_error_code_to_fixed_diagnostic(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            selected = root / "selected"
            selected.mkdir()
            (selected / "auth.json").write_text(
                json.dumps({"tokens": {"account_id": "synthetic-selected"}}),
                encoding="utf-8",
            )
            executable = root / "fake-codex"
            log = root / "fake.log"
            write_fake_codex(executable)
            selection = {
                "schema": "rolecasting-daybreak-account-selection-v1",
                "account_home": str(selected),
                "authenticated_account_id": "synthetic-selected",
            }

            result = subprocess.run(
                [
                    sys.executable,
                    str(ACCOUNT),
                    "status-refresh",
                    "--selection-stdin",
                    "--codex",
                    str(executable),
                    "--model",
                    "gpt-daybreak-blue-latest/high",
                    "--freshness-seconds",
                    "1800",
                ],
                input=json.dumps(selection),
                text=True,
                capture_output=True,
                check=False,
                env={
                    **BASE_ENV,
                    "FAKE_LOG": str(log),
                    "FAKE_RPC_STRUCTURED_CODE": "1",
                },
            )

            transcript = [json.loads(line) for line in log.read_text().splitlines()]

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("RPC error with invalid code", result.stderr)
        self.assertNotIn("provider-code-secret", result.stderr)
        self.assertNotIn("provider-secret-body", result.stderr)
        self.assertEqual(transcript[-1], {"terminated": True})

    def test_status_rejects_malformed_rpc_error_message(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            selected = root / "selected"
            selected.mkdir()
            (selected / "auth.json").write_text(
                json.dumps({"tokens": {"account_id": "synthetic-selected"}}),
                encoding="utf-8",
            )
            executable = root / "fake-codex"
            log = root / "fake.log"
            write_fake_codex(executable)
            selection = {
                "schema": "rolecasting-daybreak-account-selection-v1",
                "account_home": str(selected),
                "authenticated_account_id": "synthetic-selected",
            }

            result = subprocess.run(
                [
                    sys.executable,
                    str(ACCOUNT),
                    "status-refresh",
                    "--selection-stdin",
                    "--codex",
                    str(executable),
                    "--model",
                    "gpt-daybreak-blue-latest/high",
                    "--freshness-seconds",
                    "1800",
                ],
                input=json.dumps(selection),
                text=True,
                capture_output=True,
                check=False,
                env={
                    **BASE_ENV,
                    "FAKE_LOG": str(log),
                    "FAKE_RPC_BAD_MESSAGE": "1",
                },
            )

            transcript = [json.loads(line) for line in log.read_text().splitlines()]

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("RPC error with invalid payload", result.stderr)
        self.assertNotIn("provider-message-secret", result.stderr)
        self.assertEqual(transcript[-1], {"terminated": True})

    def test_status_rejects_provider_account_that_does_not_match_selection(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            selected = root / "selected"
            selected.mkdir()
            (selected / "auth.json").write_text(
                json.dumps({"tokens": {"account_id": "synthetic-selected"}}),
                encoding="utf-8",
            )
            executable = root / "fake-codex"
            log = root / "fake.log"
            write_fake_codex(executable)
            selection = {
                "schema": "rolecasting-daybreak-account-selection-v1",
                "account_home": str(selected),
                "authenticated_account_id": "synthetic-selected",
            }

            result = subprocess.run(
                [
                    sys.executable,
                    str(ACCOUNT),
                    "status-refresh",
                    "--selection-stdin",
                    "--codex",
                    str(executable),
                    "--model",
                    "gpt-daybreak-blue-latest/high",
                    "--freshness-seconds",
                    "1800",
                ],
                input=json.dumps(selection),
                text=True,
                capture_output=True,
                check=False,
                env={
                    **BASE_ENV,
                    "FAKE_LOG": str(log),
                    "FAKE_ACCOUNT_ID": "provider-other-account",
                },
            )

            transcript = [json.loads(line) for line in log.read_text().splitlines()]

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("provider account does not match selected binding", result.stderr)
        self.assertNotIn("provider-other-account", result.stderr)
        self.assertNotIn("synthetic-selected", result.stderr)
        self.assertEqual(transcript[-1], {"terminated": True})

    def test_status_rejects_malformed_app_server_account_results(self) -> None:
        cases = {
            "missing-email": "account/read returned an invalid result",
            "false-account": "selected app server is not authenticated with ChatGPT",
            "bad-plan": "account/read returned an invalid result",
        }
        for account_case, diagnostic in cases.items():
            with self.subTest(account_case=account_case):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    selected = root / "selected"
                    selected.mkdir()
                    (selected / "auth.json").write_text(
                        json.dumps({"tokens": {"account_id": "synthetic-selected"}}),
                        encoding="utf-8",
                    )
                    executable = root / "fake-codex"
                    log = root / "fake.log"
                    write_fake_codex(executable)
                    selection = {
                        "schema": "rolecasting-daybreak-account-selection-v1",
                        "account_home": str(selected),
                        "authenticated_account_id": "synthetic-selected",
                    }

                    result = subprocess.run(
                        [
                            sys.executable,
                            str(ACCOUNT),
                            "status-refresh",
                            "--selection-stdin",
                            "--codex",
                            str(executable),
                            "--model",
                            "gpt-daybreak-blue-latest/high",
                            "--freshness-seconds",
                            "1800",
                        ],
                        input=json.dumps(selection),
                        text=True,
                        capture_output=True,
                        check=False,
                        env={
                            **BASE_ENV,
                            "FAKE_LOG": str(log),
                            "FAKE_ACCOUNT_READ_CASE": account_case,
                        },
                    )

                    transcript = [
                        json.loads(line) for line in log.read_text().splitlines()
                    ]

                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertIn(diagnostic, result.stderr)
                self.assertNotIn("provider-plan-secret", result.stderr)
                self.assertEqual(transcript[-1], {"terminated": True})

    def test_status_bounds_repeated_and_excessive_model_pagination(self) -> None:
        for cursor_mode in ("repeated", "unique"):
            with self.subTest(cursor_mode=cursor_mode):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    selected = root / "selected"
                    selected.mkdir()
                    (selected / "auth.json").write_text(
                        json.dumps({"tokens": {"account_id": "synthetic-selected"}}),
                        encoding="utf-8",
                    )
                    executable = root / "fake-codex"
                    log = root / "fake.log"
                    write_fake_codex(executable)
                    selection = {
                        "schema": "rolecasting-daybreak-account-selection-v1",
                        "account_home": str(selected),
                        "authenticated_account_id": "synthetic-selected",
                    }

                    result = subprocess.run(
                        [
                            sys.executable,
                            str(ACCOUNT),
                            "status-refresh",
                            "--selection-stdin",
                            "--codex",
                            str(executable),
                            "--model",
                            "gpt-daybreak-blue-latest/high",
                            "--freshness-seconds",
                            "1800",
                        ],
                        input=json.dumps(selection),
                        text=True,
                        capture_output=True,
                        check=False,
                        timeout=5,
                        env={
                            **BASE_ENV,
                            "FAKE_LOG": str(log),
                            "FAKE_MODEL_CURSOR_MODE": cursor_mode,
                        },
                    )

                    transcript = [
                        json.loads(line) for line in log.read_text().splitlines()
                    ]

                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertIn("model/list pagination is invalid", result.stderr)
                self.assertEqual(transcript[-1], {"terminated": True})

    def test_status_rejects_malformed_model_fields_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            selected = root / "selected"
            selected.mkdir()
            (selected / "auth.json").write_text(
                json.dumps({"tokens": {"account_id": "synthetic-selected"}}),
                encoding="utf-8",
            )
            executable = root / "fake-codex"
            log = root / "fake.log"
            write_fake_codex(executable)
            selection = {
                "schema": "rolecasting-daybreak-account-selection-v1",
                "account_home": str(selected),
                "authenticated_account_id": "synthetic-selected",
            }

            result = subprocess.run(
                [
                    sys.executable,
                    str(ACCOUNT),
                    "status-refresh",
                    "--selection-stdin",
                    "--codex",
                    str(executable),
                    "--model",
                    "gpt-daybreak-blue-latest/high",
                    "--freshness-seconds",
                    "1800",
                ],
                input=json.dumps(selection),
                text=True,
                capture_output=True,
                check=False,
                env={
                    **BASE_ENV,
                    "FAKE_LOG": str(log),
                    "FAKE_MODEL_CASE": "bad-effort",
                },
            )

            transcript = [json.loads(line) for line in log.read_text().splitlines()]

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("model/list returned an invalid result", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn("provider-effort-secret", result.stderr)
        self.assertEqual(transcript[-1], {"terminated": True})

    def test_select_emits_only_the_explicit_one_based_position(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            catalog = Path(temporary) / "bindings.md"
            catalog.write_text(
                catalog_binding(
                    "fixture-one", "~/synthetic/account-one", "synthetic-one"
                )
                + "\n"
                + catalog_binding(
                    "fixture-two", "~/synthetic/account-two", "synthetic-two"
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(CATALOG),
                    "select",
                    "--catalog",
                    str(catalog),
                    "--position",
                    "2",
                ],
                text=True,
                capture_output=True,
                check=False,
                env=BASE_ENV,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            {
                "schema": "rolecasting-daybreak-account-selection-v1",
                "account_home": "~/synthetic/account-two",
                "authenticated_account_id": "synthetic-two",
            },
        )


if __name__ == "__main__":
    unittest.main()
