from __future__ import annotations

import json
import subprocess
import sys
import tempfile
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
        elif method == "model/list":
            result = {{"data": [
                {{"id": "unrelated", "model": "unrelated", "supportedReasoningEfforts": [{{"reasoningEffort": "high", "description": ""}}]}},
                {{"id": "daybreak", "model": "gpt-daybreak-blue-latest", "supportedReasoningEfforts": [{{"reasoningEffort": "high", "description": ""}}], "availableAccessPrograms": {{"cyber": ["daybreakBlue"]}}}}
            ]}}
        elif method == "account/rateLimits/read":
            result = {{
                "accountId": "private-account-id",
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
        if method == "model/list" and os.environ.get("FAKE_RPC_ERROR"):
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

    def test_incomplete_informational_metadata_invalidates_the_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            catalog = Path(temporary) / "bindings.md"
            incomplete = catalog_binding("one", "/synthetic/one", "one").replace(
                "  harmless_probe: synthetic observation\n", ""
            )
            catalog.write_text(incomplete, encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(CATALOG), "inspect", "--catalog", str(catalog)],
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
            (selected / "auth.json").write_text(
                json.dumps({"tokens": {"account_id": "synthetic-selected"}}),
                encoding="utf-8",
            )
            sibling_auth = sibling / "auth.json"
            sibling_auth.write_text("sibling sentinel", encoding="utf-8")
            poison_catalog = poison_home / ".agents" / "daybreak-account-bindings.md"
            poison_catalog.parent.mkdir()
            poison_catalog.write_text("ambient catalog sentinel", encoding="utf-8")
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
                env={
                    **BASE_ENV,
                    "HOME": str(poison_home),
                    "FAKE_LOG": str(log),
                },
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            sibling_after = sibling_auth.read_text(encoding="utf-8")
            catalog_after = poison_catalog.read_text(encoding="utf-8")
            fake_observation = json.loads(log.read_text().splitlines()[0])

        output = json.loads(result.stdout)
        self.assertEqual(output["operation"], "status-refresh")
        self.assertEqual(output["selector"], "gpt-daybreak-blue-latest/high")
        self.assertTrue(output["binding_matches"])
        self.assertTrue(output["authenticated"])
        self.assertTrue(output["ordinary_usage_allowed"])
        self.assertEqual(output["capacity"]["primary"]["used_percent"], 12)
        self.assertEqual(fake_observation, {"codex_home": str(selected)})
        self.assertEqual(sibling_after, "sibling sentinel")
        self.assertEqual(catalog_after, "ambient catalog sentinel")
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
            workspace = root / "probe-workspace"
            workspace.mkdir()
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
                env={**BASE_ENV, "FAKE_LOG": str(log)},
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertFalse(log.exists())

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
