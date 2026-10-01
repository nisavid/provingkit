from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_ROOT = REPO_ROOT / "plugins/rolecasting/skills/choosing-agent-models/scripts"
CATALOG = SCRIPT_ROOT / "daybreak_catalog.py"
ACCOUNT = SCRIPT_ROOT / "daybreak_account.py"
BASE_ENV = {"LC_ALL": "C", "PYTHONDONTWRITEBYTECODE": "1"}

sys.path.insert(0, str(SCRIPT_ROOT))
import daybreak_account as daybreak_account_module  # noqa: E402

sys.path.pop(0)


FAKE_CODEX = r"""#!{python}
import json
import os
import signal
import sys
import time

log_path = os.environ["FAKE_LOG"]
requests = []
with open(log_path, "w", encoding="utf-8") as log:
    def terminated(_signal, _frame):
        log.write(json.dumps({{"terminated": True}}) + "\n")
        log.flush()
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, terminated)
    observation = {{"codex_home": os.environ.get("CODEX_HOME")}}
    if os.environ.get("FAKE_OBSERVE_RESOLVED_CODEX_HOME"):
        observation["resolved_codex_home"] = os.path.abspath(
            os.environ["CODEX_HOME"]
        )
    json.dump(observation, log)
    log.write("\n")
    log.flush()
    transport_case = os.environ.get("FAKE_TRANSPORT_CASE")
    if transport_case == "early-exit":
        raise SystemExit(0)
    if transport_case == "closed-stdin":
        sys.stdin.close()
        time.sleep(0.1)
        raise SystemExit(0)
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
            elif cursor_mode == "write-stall" and model_page == 1:
                result["nextCursor"] = "x" * 900000
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
        if method == "initialize" and os.environ.get("FAKE_RPC_DUPLICATE_KEY"):
            sys.stdout.write('{{"id":1,"result":{{}},"result":{{"private_duplicate":"provider-duplicate-secret"}}}}\n')
            sys.stdout.flush()
            continue
        if method == "initialize" and os.environ.get("FAKE_RPC_NONFINITE"):
            sys.stdout.write('{{"id":1,"result":{{"private_number":NaN}}}}\n')
            sys.stdout.flush()
            continue
        if method == "initialize" and os.environ.get("FAKE_RPC_OVERSIZED_INTEGER"):
            sys.stdout.write(
                '{{"id":1,"result":{{"private_number":'
                + "9" * 5000
                + '}}}}\n'
            )
            sys.stdout.flush()
            continue
        if method == "initialize" and transport_case == "oversized-line":
            sys.stdout.write("x" * (1048576 + 1) + "\n")
            sys.stdout.flush()
            continue
        if method == "initialize" and transport_case == "oversized-no-newline":
            sys.stdout.write("x" * (1048576 + 1))
            sys.stdout.flush()
            signal.pause()
        if method == "initialize" and transport_case == "maximum-valid-frame":
            response["padding"] = ""
            compact = json.dumps(response, separators=(",", ":"))
            response["padding"] = "x" * (1048576 - len(compact))
            sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
            sys.stdout.flush()
            continue
        if method == "initialize" and transport_case == "notification-flood":
            for number in range(129):
                sys.stdout.write(json.dumps({{"method": "synthetic/event", "params": {{"number": number}}}}) + "\n")
            sys.stdout.flush()
        if transport_case == "legitimate-notifications":
            for number in range(4):
                sys.stdout.write(json.dumps({{"method": "synthetic/event", "params": {{"number": number}}}}) + "\n")
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
        if (
            method == "model/list"
            and os.environ.get("FAKE_MODEL_CURSOR_MODE") == "write-stall"
            and model_page == 1
        ):
            signal.pause()
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


def run_fake_status(
    root: Path,
    *,
    extra_env: dict[str, str] | None = None,
    auth_content: str | None = None,
    timeout: float = 5,
) -> tuple[subprocess.CompletedProcess[str], Path]:
    selected = root / "selected"
    selected.mkdir()
    (selected / "auth.json").write_text(
        auth_content
        if auth_content is not None
        else json.dumps({"tokens": {"account_id": "synthetic-selected"}}),
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
        timeout=timeout,
        env={**BASE_ENV, "FAKE_LOG": str(log), **(extra_env or {})},
    )
    return result, log


class DaybreakTransportUnitTests(unittest.TestCase):
    def test_pipe_and_selector_os_errors_map_to_fixed_diagnostics(self) -> None:
        with mock.patch.object(
            daybreak_account_module.selectors,
            "DefaultSelector",
            side_effect=OSError("private-selector-setup-detail"),
        ):
            with self.assertRaises(daybreak_account_module.AccountError) as caught:
                daybreak_account_module.RpcClient(
                    SimpleNamespace(
                        stdout=SimpleNamespace(),
                        stdin=SimpleNamespace(),
                    )
                )
        self.assertEqual(
            caught.exception.public_diagnostic(),
            "DA008: provider transport setup failed",
        )

        class BrokenInput:
            def fileno(self) -> int:
                return 123

        writer = object.__new__(daybreak_account_module.RpcClient)
        writer.process = SimpleNamespace(stdin=BrokenInput())
        writer.write_selector = mock.Mock()
        writer.write_selector.select.return_value = [object()]
        with mock.patch.object(
            daybreak_account_module.os,
            "write",
            side_effect=BrokenPipeError("private-pipe-detail"),
        ):
            with self.assertRaises(daybreak_account_module.AccountError) as caught:
                writer.send({"method": "synthetic"})
        self.assertEqual(
            caught.exception.public_diagnostic(),
            "DA009: provider transport write failed",
        )

        reader = object.__new__(daybreak_account_module.RpcClient)
        reader.buffer = b""
        reader.selector = mock.Mock()
        reader.selector.select.side_effect = OSError("private-selector-detail")
        reader.process = SimpleNamespace(stdout=SimpleNamespace(fileno=lambda: 0))
        with self.assertRaises(daybreak_account_module.AccountError) as caught:
            reader.read_message(time.monotonic() + 1)
        self.assertEqual(
            caught.exception.public_diagnostic(),
            "DA010: provider transport read failed",
        )

        reader.selector.select.side_effect = None
        reader.selector.select.return_value = [object()]
        with mock.patch.object(
            daybreak_account_module.os,
            "read",
            side_effect=OSError("private-read-detail"),
        ):
            with self.assertRaises(daybreak_account_module.AccountError) as caught:
                reader.read_message(time.monotonic() + 1)
        self.assertEqual(
            caught.exception.public_diagnostic(),
            "DA010: provider transport read failed",
        )

    def test_teardown_os_errors_are_bounded(self) -> None:
        process = mock.Mock()
        process.poll.return_value = None
        process.terminate.side_effect = OSError("private-teardown-detail")

        self.assertFalse(daybreak_account_module.stop_server(process))

        client = mock.Mock()
        client.close.return_value = True

        def reply(method: str, _params: object) -> object:
            if method == "initialize":
                return {}
            if method == "account/read":
                return {
                    "account": {
                        "type": "chatgpt",
                        "email": None,
                        "planType": "pro",
                    },
                    "requiresOpenaiAuth": True,
                }
            if method == "account/rateLimits/read":
                return {
                    "accountId": "synthetic-selected",
                    "ordinaryUsageAllowed": True,
                    "rateLimits": {},
                    "rateLimitsByLimitId": {},
                }
            if method == "model/list":
                return {
                    "data": [
                        {
                            "model": "gpt-daybreak-blue-latest",
                            "supportedReasoningEfforts": [
                                {"reasoningEffort": "high"}
                            ],
                            "availableAccessPrograms": {
                                "cyber": ["daybreakBlue"]
                            },
                        }
                    ]
                }
            raise AssertionError(method)

        client.request.side_effect = reply
        with (
            mock.patch.object(
                daybreak_account_module, "start_server", return_value=process
            ),
            mock.patch.object(
                daybreak_account_module, "RpcClient", return_value=client
            ),
            mock.patch.object(
                daybreak_account_module, "stop_server", return_value=False
            ),
        ):
            with self.assertRaises(daybreak_account_module.AccountError) as caught:
                daybreak_account_module.status_refresh(
                    Path("/synthetic/codex"),
                    Path("/synthetic/home"),
                    "synthetic-selected",
                    "gpt-daybreak-blue-latest/high",
                    1800,
                )
        self.assertEqual(
            caught.exception.public_diagnostic(),
            "DA032: provider teardown failed",
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

    def test_catalog_failures_use_only_fixed_public_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            catalog = root / "private-looking-catalog-name.md"
            cases = (
                (
                    "unknown-field",
                    ["inspect", "--catalog", str(catalog)],
                    catalog_binding("one", "/synthetic/one", "one")
                    + "  private_field_name: private-field-value\n",
                    "DC003: catalog input invalid",
                ),
                (
                    "duplicate-field",
                    ["inspect", "--catalog", str(catalog)],
                    catalog_binding("one", "/synthetic/one", "one")
                    + "  codex_home: /private/duplicate/path\n",
                    "DC003: catalog input invalid",
                ),
                (
                    "missing-file",
                    ["inspect", "--catalog", str(root / "private-missing.md")],
                    None,
                    "DC002: catalog input unavailable",
                ),
                (
                    "invalid-cli-value",
                    [
                        "select",
                        "--catalog",
                        str(catalog),
                        "--position",
                        "private-cli-value",
                    ],
                    catalog_binding("one", "/synthetic/one", "one"),
                    "DC001: invalid command line",
                ),
                (
                    "nul-account-home",
                    ["inspect", "--catalog", str(catalog)],
                    catalog_binding("one", "/private/\0catalog-home", "one"),
                    "DC003: catalog input invalid",
                ),
            )
            for name, arguments, content, expected in cases:
                with self.subTest(name=name):
                    if content is None:
                        catalog.unlink(missing_ok=True)
                    else:
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
                    self.assertEqual(
                        result.stderr, f"daybreak-catalog {expected}\n"
                    )
                    for private_value in (
                        "private_field_name",
                        "private-field-value",
                        "/private/duplicate/path",
                        "private-looking-catalog-name",
                        "private-missing",
                        "private-cli-value",
                        "catalog-home",
                    ):
                        self.assertNotIn(private_value, result.stderr)


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
            (selected / "auth.json").write_text(
                json.dumps({"tokens": {"account_id": "synthetic-selected"}}),
                encoding="utf-8",
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
            sibling_writer_blocked = sibling_writer.poll() is None
            catalog_writer_blocked = catalog_writer.poll() is None
            stop_fifo_writer(sibling_writer)
            stop_fifo_writer(catalog_writer)
            transcript = [json.loads(line) for line in log.read_text().splitlines()]
            fake_observation = transcript[0]
            rpc_methods = [
                entry["method"] for entry in transcript if "method" in entry
            ]
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
        self.assertEqual(
            rpc_methods,
            [
                "initialize",
                "account/read",
                "account/rateLimits/read",
                "model/list",
            ],
        )
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

    def test_status_refresh_absolutizes_home_relative_selection_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inherited_home = root / "relative-home"
            selected = inherited_home / "selected"
            selected.mkdir(parents=True)
            (selected / "auth.json").write_text(
                json.dumps({"tokens": {"account_id": "synthetic-selected"}}),
                encoding="utf-8",
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
                cwd=root,
                env={
                    **BASE_ENV,
                    "HOME": "relative-home",
                    "FAKE_LOG": str(log),
                    "FAKE_OBSERVE_RESOLVED_CODEX_HOME": "1",
                },
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            transcript = [
                json.loads(line) for line in log.read_text().splitlines()
            ]

        self.assertEqual(
            transcript[0],
            {
                "codex_home": str(selected),
                "resolved_codex_home": str(selected),
            },
        )

    def test_unavailable_harmless_probe_fails_before_authentication_or_launch(self) -> None:
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

        self.assertEqual(
            result.stderr,
            "daybreak-account DA031: harmless probe unavailable in status-only increment\n",
        )

    def test_invalid_status_arguments_fail_before_authentication_access(self) -> None:
        cases = (
            (
                "invalid-selector",
                "/synthetic/codex",
                "invalid selector",
                "1800",
                "DA033: invalid exact model selector",
            ),
            (
                "invalid-freshness",
                "/synthetic/codex",
                "gpt-daybreak-blue-latest/high",
                "0",
                "DA030: freshness interval invalid",
            ),
            (
                "relative-executable",
                "relative-codex",
                "gpt-daybreak-blue-latest/high",
                "1800",
                "DA006: invalid Codex executable",
            ),
        )
        for name, executable, selector, freshness, diagnostic in cases:
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    selected = root / "selected"
                    selected.mkdir()
                    auth_read = root / "status-auth-read"
                    auth_writer = start_observed_fifo(
                        selected / "auth.json",
                        auth_read,
                        json.dumps(
                            {"tokens": {"account_id": "synthetic-selected"}}
                        ),
                    )
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
                            executable,
                            "--model",
                            selector,
                            "--freshness-seconds",
                            freshness,
                        ],
                        input=json.dumps(selection),
                        text=True,
                        capture_output=True,
                        check=False,
                        timeout=2,
                        env=BASE_ENV,
                    )

                    time.sleep(0.05)
                    auth_writer_blocked = auth_writer.poll() is None
                    stop_fifo_writer(auth_writer)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, "")
                    self.assertEqual(
                        result.stderr, f"daybreak-account {diagnostic}\n"
                    )
                    self.assertTrue(auth_writer_blocked)
                    self.assertFalse(auth_read.exists())

    def test_status_rejects_fifo_auth_without_waiting_for_a_writer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            selected = root / "selected"
            selected.mkdir()
            os.mkfifo(selected / "auth.json")
            executable = root / "fake-codex"
            log = root / "fake.log"
            write_fake_codex(executable)
            selection = {
                "schema": "rolecasting-daybreak-account-selection-v1",
                "account_home": str(selected),
                "authenticated_account_id": "synthetic-selected",
            }
            process = subprocess.Popen(
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
                text=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**BASE_ENV, "FAKE_LOG": str(log)},
            )
            try:
                stdout, stderr = process.communicate(
                    input=json.dumps(selection), timeout=2
                )
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate(timeout=2)
                self.fail("status refresh blocked opening nonregular authentication")

            self.assertNotEqual(process.returncode, 0)
            self.assertEqual(stdout, "")
            self.assertEqual(
                stderr,
                "daybreak-account DA003: selected authentication unavailable\n",
            )
            self.assertFalse(log.exists())

    def test_status_rejects_authentication_above_explicit_byte_ceiling(self) -> None:
        valid = json.dumps(
            {"tokens": {"account_id": "synthetic-selected"}},
            separators=(",", ":"),
        )
        oversized = valid + " " * (1_048_577 - len(valid.encode("utf-8")))
        with tempfile.TemporaryDirectory() as temporary:
            result, log = run_fake_status(
                Path(temporary), auth_content=oversized
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertEqual(
                result.stderr,
                "daybreak-account DA004: selected authentication malformed\n",
            )
            self.assertFalse(log.exists())

    def test_status_accepts_auth_symlink_to_regular_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            selected = root / "selected"
            selected.mkdir()
            auth_target = root / "regular-auth.json"
            auth_target.write_text(
                json.dumps({"tokens": {"account_id": "synthetic-selected"}}),
                encoding="utf-8",
            )
            (selected / "auth.json").symlink_to(auth_target)
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
                env={**BASE_ENV, "FAKE_LOG": str(log)},
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                json.loads(result.stdout)["operation"], "status-refresh"
            )
            self.assertTrue(log.exists())

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
                "missing": ("", "DA002: invalid selection input"),
                "array": (json.dumps([valid]), "DA002: invalid selection input"),
                "multiple": (
                    json.dumps(valid) + json.dumps(valid),
                    "DA002: invalid selection input",
                ),
                "non-finite": (
                    '{"schema":"rolecasting-daybreak-account-selection-v1",'
                    f'"account_home":"{selected}",'
                    '"authenticated_account_id":NaN}',
                    "DA002: invalid selection input",
                ),
                "duplicate-key": (
                    (
                        '{"schema":"rolecasting-daybreak-account-selection-v1",'
                        f'"account_home":"{selected}","account_home":"{selected}",'
                        '"authenticated_account_id":"synthetic-selected"}'
                    ),
                    "DA002: invalid selection input",
                ),
                "unknown-field": (
                    json.dumps({**valid, "private_field_name": "private-value"}),
                    "DA002: invalid selection input",
                ),
                "nul-account-home": (
                    json.dumps(
                        {**valid, "account_home": "/private/\0selected-home"}
                    ),
                    "DA002: invalid selection input",
                ),
                "binding-mismatch": (
                    json.dumps(
                        {**valid, "authenticated_account_id": "different-account"}
                    ),
                    "DA005: selected authentication does not match selection",
                ),
            }
            for name, (selection, diagnostic) in cases.items():
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
                    self.assertEqual(
                        result.stderr, f"daybreak-account {diagnostic}\n"
                    )
                    self.assertNotIn("private_field_name", result.stderr)
                    self.assertNotIn("private-value", result.stderr)
                    self.assertNotIn("selected-home", result.stderr)
                    self.assertNotIn(str(selected), result.stderr)
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
        self.assertIn("DA004: selected authentication malformed", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn("provider-auth-secret", result.stderr)
        self.assertFalse(log.exists())

    def test_oversized_integer_authentication_fails_without_traceback_or_launch(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result, log = run_fake_status(
                Path(temporary),
                auth_content='{"tokens":{"account_id":' + "9" * 5000 + "}}",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertEqual(
                result.stderr,
                "daybreak-account DA004: selected authentication malformed\n",
            )
            self.assertNotIn("Traceback", result.stderr)
            self.assertFalse(log.exists())

    def test_noncanonical_authentication_json_fails_before_launch(self) -> None:
        cases = (
            '{"tokens":{"account_id":"synthetic-selected"},'
            '"tokens":{"account_id":"private-duplicate-secret"}}',
            '{"tokens":{"account_id":NaN}}',
        )
        for content in cases:
            with self.subTest(content=content):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    selected = root / "selected"
                    selected.mkdir()
                    (selected / "auth.json").write_text(content, encoding="utf-8")
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
                self.assertEqual(
                    result.stderr,
                    "daybreak-account DA004: selected authentication malformed\n",
                )
                self.assertNotIn("private-duplicate-secret", result.stderr)
                self.assertFalse(log.exists())

    def test_account_input_failures_use_only_fixed_public_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            selected = root / "private-selected-path"
            selected.mkdir()
            (selected / "auth.json").write_text(
                json.dumps({"tokens": {"account_id": "synthetic-selected"}}),
                encoding="utf-8",
            )
            selection = json.dumps(
                {
                    "schema": "rolecasting-daybreak-account-selection-v1",
                    "account_home": str(selected),
                    "authenticated_account_id": "synthetic-selected",
                }
            )
            cases = (
                (
                    [
                        "status-refresh",
                        "--selection-stdin",
                        "--codex",
                        "/private/codex",
                        "--model",
                        "gpt-daybreak-blue-latest/high",
                        "--freshness-seconds",
                        "private-cli-value",
                    ],
                    "DA001: invalid command line",
                ),
                (
                    [
                        "harmless-probe",
                        "--selection-stdin",
                        "--codex",
                        "private-codex-value",
                        "--model",
                        "gpt-daybreak-blue-latest/high",
                        "--workspace",
                        "/private/workspace",
                    ],
                    "DA006: invalid Codex executable",
                ),
                (
                    [
                        "harmless-probe",
                        "--selection-stdin",
                        "--codex",
                        "/private/codex",
                        "--model",
                        "private malformed selector",
                        "--workspace",
                        "/private/workspace",
                    ],
                    "DA033: invalid exact model selector",
                ),
            )
            for arguments, expected in cases:
                with self.subTest(expected=expected):
                    result = subprocess.run(
                        [sys.executable, str(ACCOUNT), *arguments],
                        input=selection,
                        text=True,
                        capture_output=True,
                        check=False,
                        env=BASE_ENV,
                    )

                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, "")
                    self.assertEqual(
                        result.stderr, f"daybreak-account {expected}\n"
                    )
                    for private_value in (
                        "private-selected-path",
                        "private-cli-value",
                        "private-codex-value",
                        "/private/codex",
                        "/private/workspace",
                        "private malformed selector",
                    ):
                        self.assertNotIn(private_value, result.stderr)

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
        self.assertIn("DA017: provider RPC failed", result.stderr)
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
        self.assertIn("DA029: provider capacity response invalid", result.stderr)
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
                self.assertIn("DA029: provider capacity response invalid", result.stderr)
                self.assertNotIn("provider-scalar-secret", result.stderr)
                self.assertEqual(transcript[-1], {"terminated": True})

    def test_status_rejects_malformed_rate_limit_envelopes(self) -> None:
        cases = {
            "missing-rate-limits": None,
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
                    "DA027: provider rate-limit response invalid",
                    result.stderr,
                )
                if secret is not None:
                    self.assertNotIn(secret, result.stderr)
                self.assertEqual(transcript[-1], {"terminated": True})

    def test_status_validates_provider_identity_and_usage_types(self) -> None:
        cases = {
            "bad-account-id": (
                "DA020: provider identity unavailable",
                "provider-account-secret",
            ),
            "bad-ordinary-usage": (
                "DA028: provider usage response invalid",
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
        self.assertIn("DA015: provider protocol message invalid", result.stderr)
        self.assertNotIn("provider-code-secret", result.stderr)
        self.assertNotIn("provider-secret-body", result.stderr)
        self.assertEqual(transcript[-1], {"terminated": True})

    def test_status_rejects_noncanonical_rpc_json_without_disclosure(self) -> None:
        for variable in ("FAKE_RPC_DUPLICATE_KEY", "FAKE_RPC_NONFINITE"):
            with self.subTest(variable=variable):
                with tempfile.TemporaryDirectory() as temporary:
                    result, log = run_fake_status(
                        Path(temporary), extra_env={variable: "1"}
                    )
                    transcript = [
                        json.loads(line) for line in log.read_text().splitlines()
                    ]

                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertEqual(
                    result.stderr,
                    "daybreak-account DA015: provider protocol message invalid\n",
                )
                self.assertNotIn("provider-duplicate-secret", result.stderr)
                self.assertEqual(transcript[-1], {"terminated": True})

    def test_status_rejects_oversized_integer_rpc_without_traceback_and_stops_process(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result, log = run_fake_status(
                Path(temporary),
                extra_env={"FAKE_RPC_OVERSIZED_INTEGER": "1"},
            )
            transcript = [
                json.loads(line) for line in log.read_text().splitlines()
            ]

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertEqual(
                result.stderr,
                "daybreak-account DA015: provider protocol message invalid\n",
            )
            self.assertNotIn("Traceback", result.stderr)
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
        self.assertIn("DA015: provider protocol message invalid", result.stderr)
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
            rpc_methods = [
                entry["method"] for entry in transcript if "method" in entry
            ]

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("DA021: provider identity does not match selection", result.stderr)
        self.assertNotIn("provider-other-account", result.stderr)
        self.assertNotIn("synthetic-selected", result.stderr)
        self.assertEqual(
            rpc_methods,
            ["initialize", "account/read", "account/rateLimits/read"],
        )
        self.assertEqual(transcript[-1], {"terminated": True})

    def test_status_transport_failures_are_bounded_and_non_disclosing(self) -> None:
        cases = {
            "early-exit": "DA011: provider transport closed",
            "closed-stdin": "DA011: provider transport closed",
            "oversized-line": "DA013: provider frame exceeds limit",
            "oversized-no-newline": "DA013: provider frame exceeds limit",
            "notification-flood": "DA014: provider message limit exceeded",
        }
        for transport_case, diagnostic in cases.items():
            with self.subTest(transport_case=transport_case):
                with tempfile.TemporaryDirectory() as temporary:
                    result, _log = run_fake_status(
                        Path(temporary),
                        extra_env={"FAKE_TRANSPORT_CASE": transport_case},
                    )

                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr, f"daybreak-account {diagnostic}\n")
                self.assertNotIn("Traceback", result.stderr)

    def test_status_bounds_provider_controlled_request_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            started = time.monotonic()
            result, log = run_fake_status(
                Path(temporary),
                extra_env={"FAKE_MODEL_CURSOR_MODE": "write-stall"},
                timeout=15,
            )
            elapsed = time.monotonic() - started
            transcript = [json.loads(line) for line in log.read_text().splitlines()]
            model_requests = [
                entry
                for entry in transcript
                if entry.get("method") == "model/list"
            ]

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertEqual(
            result.stderr,
            "daybreak-account DA009: provider transport write failed\n",
        )
        self.assertLess(elapsed, 14)
        self.assertEqual(len(model_requests), 1)
        self.assertEqual(transcript[-1], {"terminated": True})

    def test_status_discards_supported_notifications_without_accumulating(self) -> None:
        for transport_case in ("legitimate-notifications", "maximum-valid-frame"):
            with self.subTest(transport_case=transport_case):
                with tempfile.TemporaryDirectory() as temporary:
                    result, log = run_fake_status(
                        Path(temporary),
                        extra_env={"FAKE_TRANSPORT_CASE": transport_case},
                    )
                    transcript = [
                        json.loads(line) for line in log.read_text().splitlines()
                    ]

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    json.loads(result.stdout)["operation"], "status-refresh"
                )
                self.assertEqual(transcript[-1], {"terminated": True})

    def test_status_rejects_malformed_app_server_account_results(self) -> None:
        cases = {
            "missing-email": "DA018: provider account response invalid",
            "false-account": "DA019: provider is not authenticated with ChatGPT",
            "bad-plan": "DA018: provider account response invalid",
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
                self.assertIn("DA023: provider model pagination invalid", result.stderr)
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
        self.assertIn("DA022: provider model response invalid", result.stderr)
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
