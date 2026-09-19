"""Public-CLI tests for the Aeon Bell Codex status observation adapter.

Every test drives ``codex_status.py`` (and, where the contract crosses into
the engine, ``aeon_bell.py``) as a subprocess with a fake ``codex`` executable
on a controlled PATH. No live credentials, catalogs, or network are used.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parents[1]
SCRIPTS = REPOSITORY / "plugins" / "praxis" / "skills" / "aeon-bell" / "scripts"
ENGINE = SCRIPTS / "aeon_bell.py"
ADAPTER = SCRIPTS / "codex_status.py"

NOW = "2026-09-17T12:00:00+00:00"
LATER = "2026-09-17T12:16:00+00:00"
ACCOUNT_ID = "acct-SECRET-IDENTITY-0001"
OTHER_ACCOUNT_ID = "acct-SECRET-IDENTITY-0002"
ACCESS_TOKEN = "SECRET-ACCESS-TOKEN-VALUE"
SERVER_MARKER = "SERVER-SECRET-MARKER"
EXPECTED_ARGV = [
    "app-server",
    "--stdio",
    "-c",
    "mcp_servers={}",
    "-c",
    "features.plugins=false",
    "-c",
    "features.apps=false",
]

FAKE_CODEX = '''#!{python}
"""Fake Codex app-server for adapter tests. Records the protocol it sees."""
import json
import os
import sys
import time
from pathlib import Path

here = Path(__file__).resolve().parent
fixture = json.loads((here / "fixture.json").read_text(encoding="utf-8"))
calls_path = here / "calls.json"
record = {{
    "argv": sys.argv[1:],
    "pid": os.getpid(),
    "env_keys": sorted(os.environ),
    "codex_home": os.environ.get("CODEX_HOME"),
    "cwd": os.getcwd(),
    "cwd_entries": sorted(os.listdir(os.getcwd())),
    "messages": [],
}}


def save():
    calls_path.write_text(json.dumps(record), encoding="utf-8")


def emit(message):
    sys.stdout.write(json.dumps(message) + "\\n")
    sys.stdout.flush()


save()
pages_served = 0
for raw in sys.stdin:
    try:
        message = json.loads(raw)
    except ValueError:
        message = {{"malformed_client_line": True}}
    record["messages"].append(message)
    save()
    method = message.get("method")
    identifier = message.get("id")
    if identifier is None:
        continue
    behavior = fixture.get("behavior", {{}}).get(method)
    delay = fixture.get("delays", {{}}).get(method)
    if delay is not None:
        time.sleep(delay)
    rewrite = fixture.get("auth_rewrite")
    if rewrite and rewrite.get("at") == method:
        auth = Path(os.environ["CODEX_HOME"]) / "auth.json"
        document = json.loads(auth.read_text(encoding="utf-8"))
        document["tokens"]["account_id"] = rewrite["account_id"]
        auth.write_text(json.dumps(document), encoding="utf-8")
    for notification in fixture.get("notifications_before", {{}}).get(method, []):
        emit(notification)
    server_request = fixture.get("server_request_before", {{}}).get(method)
    if server_request:
        emit(server_request)
    if behavior == "hang":
        time.sleep(30)
        continue
    if behavior == "exit":
        raise SystemExit(3)
    if behavior == "malformed":
        sys.stdout.write("this is not json " + "{marker}" + "\\n")
        sys.stdout.flush()
        continue
    if behavior == "rpc-error":
        emit({{"id": identifier, "error": {{"code": -32000, "message": "{marker}"}}}})
        continue
    if behavior == "oversized":
        emit({{"id": identifier, "result": {{"pad": "x" * (2 * 1024 * 1024)}}}})
        continue
    response = fixture["responses"].get(method)
    if method == "model/list":
        if isinstance(response, dict) and "repeat" in response:
            page = response["repeat"]
        else:
            page = response[min(pages_served, len(response) - 1)]
        pages_served += 1
        response = page
    if response is None:
        emit({{"id": identifier, "error": {{"code": -32601, "message": "unknown"}}}})
        continue
    emit({{"id": identifier, "result": response}})
'''


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
        **kwargs,
    )


def engine(store: Path, *args: str, now: str = NOW) -> dict[str, Any]:
    result = run([str(ENGINE), *args, "--store", str(store), "--now", now])
    if result.returncode != 0:
        raise AssertionError(f"engine failed: {result.stderr}")
    return json.loads(result.stdout)


def quota_gate(revision: str, bucket: str = "weekly") -> dict[str, str]:
    return {
        "kind": "quota_recovery",
        "account": "acct-label",
        "route": "route-label",
        "bucket": bucket,
        "policy_revision": revision,
    }


def daybreak_gate(revision: str, model: str = "daybreak") -> dict[str, str]:
    return {
        "kind": "daybreak_status",
        "account": "acct-label",
        "route": "route-label",
        "model": model,
        "policy_revision": revision,
    }


def window(used: float, reset: int = 1789736000, minutes: int = 300) -> dict[str, Any]:
    return {"usedPercent": used, "resetsAt": reset, "windowDurationMins": minutes}


def window_without_reset(used: float, minutes: int = 300) -> dict[str, Any]:
    """A present, numeric window that advertises no usable reset time."""
    return {"usedPercent": used, "windowDurationMins": minutes}


# Unix seconds for the synthetic clock: NOW is 1789646400 (2026-09-17T12:00:00Z).
RESET_IN_2H = 1789653600  # 2026-09-17T14:00:00+00:00
RESET_IN_4H = 1789660800  # 2026-09-17T16:00:00+00:00
RESET_FAR = 1789800000  # 2026-09-19T06:40:00+00:00, well after the 360-minute ceiling


def rate_limits(primary: dict | None, secondary: dict | None) -> dict[str, Any]:
    limit: dict[str, Any] = {"limitId": "codex", "credits": {"balance": "999"}}
    if primary is not None:
        limit["primary"] = primary
    if secondary is not None:
        limit["secondary"] = secondary
    return {
        "rateLimits": {"primary": window(0), "secondary": window(0)},
        "rateLimitsByLimitId": {"codex": limit},
    }


def default_responses() -> dict[str, Any]:
    return {
        "initialize": {"userAgent": "fake-codex/0.0"},
        "account/read": {
            "account": {"type": "chatgpt", "email": SERVER_MARKER + "@example.test"},
            "requiresOpenaiAuth": False,
        },
        "model/list": [
            {"data": [{"model": "gpt-other"}], "nextCursor": "page-2"},
            {"data": [{"model": "gpt-daybreak-exact"}], "nextCursor": None},
        ],
        "account/rateLimits/read": rate_limits(
            window(40, minutes=300), window(70, minutes=10080)
        ),
    }


class AdapterHarness:
    """One isolated fake Codex environment, binding config, and engine store."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.codex_home = root / "codex-home"
        self.codex_home.mkdir()
        self.bin = root / "bin"
        self.bin.mkdir()
        self.store = root / "store"
        self.fixture = {"responses": default_responses()}
        fake = self.bin / "codex"
        fake.write_text(
            FAKE_CODEX.format(python=sys.executable, marker=SERVER_MARKER),
            encoding="utf-8",
        )
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        self.write_auth(ACCOUNT_ID)
        self.config = {
            "format": "praxis-aeon-bell-codex-binding",
            "version": 1,
            "account": "acct-label",
            "route": "route-label",
            "policy_revision": "policy-2026-09",
            "codex_home": str(self.codex_home),
            "expected_account_id": ACCOUNT_ID,
            "quota": {
                "weekly": {
                    "limit_id": "codex",
                    "windows": [
                        {"window": "primary", "duration_minutes": 300},
                        {"window": "secondary", "duration_minutes": 10080},
                    ],
                }
            },
            "models": {"daybreak": {"model": "gpt-daybreak-exact", "quota": "weekly"}},
        }

    def write_auth(self, account_id: str | None) -> None:
        document: dict[str, Any] = {
            "auth_mode": "chatgpt",
            "OPENAI_API_KEY": None,
            "tokens": {
                "id_token": "SECRET-ID-TOKEN",
                "access_token": ACCESS_TOKEN,
                "refresh_token": "SECRET-REFRESH-TOKEN",
            },
        }
        if account_id is not None:
            document["tokens"]["account_id"] = account_id
        (self.codex_home / "auth.json").write_text(
            json.dumps(document), encoding="utf-8"
        )

    def write_config(self, mode: int = 0o600) -> Path:
        path = self.root / "binding.json"
        path.write_text(json.dumps(self.config), encoding="utf-8")
        path.chmod(mode)
        return path

    def write_fixture(self) -> None:
        (self.bin / "fixture.json").write_text(
            json.dumps(self.fixture), encoding="utf-8"
        )

    def calls(self) -> dict[str, Any] | None:
        path = self.bin / "calls.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def methods(self) -> list[str]:
        calls = self.calls()
        return [] if calls is None else [m.get("method") for m in calls["messages"]]

    def describe(self) -> dict[str, Any]:
        result = self.adapter("describe")
        if result.returncode != 0:
            raise AssertionError(result.stderr)
        return json.loads(result.stdout)

    def revision(self) -> str:
        return self.describe()["policy_revision"]

    def adapter(
        self, *args: str, timeout: str = "10", now: str = NOW
    ) -> subprocess.CompletedProcess[str]:
        self.write_fixture()
        config = self.write_config()
        env = {
            "PATH": os.pathsep.join([str(self.bin), str(Path(sys.executable).parent)]),
            "HOME": str(self.root),
            "SECRET_ENV_VALUE": "must-not-leak",
            "CODEX_HOME": str(self.root / "ambient-wrong-home"),
        }
        extra: list[str] = []
        if args[0] == "observe":
            extra = ["--now", now, "--timeout-seconds", timeout]
        return run(
            [str(ADAPTER), args[0], "--binding", str(config), *args[1:], *extra],
            env=env,
            cwd=self.root,
        )

    def observe(
        self, requests_path: Path, *args: str, timeout: str = "10", now: str = NOW
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        result = self.adapter(
            "observe", "--requests", str(requests_path), *args, timeout=timeout, now=now
        )
        if result.returncode != 0:
            raise AssertionError(result.stderr)
        return result, json.loads(result.stdout)

    def register(self, gate: dict[str, str], task_id: str = "task-1") -> dict[str, Any]:
        return engine(
            self.store,
            "register",
            "--owner",
            "owner-a",
            "--host",
            "host-a",
            "--task-id",
            task_id,
            "--episode",
            "episode-1",
            "--gate-json",
            json.dumps(gate),
            "--continuation",
            "Resume the synthetic waiting work.",
        )

    def requests(self, now: str = NOW) -> Path:
        cycle = engine(self.store, "cycle", now=now)
        path = self.root / "cycle-output.json"
        path.write_text(json.dumps(cycle), encoding="utf-8")
        return path

    def cycle_with(self, report: dict[str, Any], now: str = NOW) -> dict[str, Any]:
        path = self.root / "cycle-input.json"
        path.write_text(json.dumps(report["cycle_input"]), encoding="utf-8")
        return engine(self.store, "cycle", "--input", str(path), now=now)


class CodexStatusAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.harness = AdapterHarness(Path(self.tempdir.name).resolve())

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def assert_redacted(self, *texts: str) -> None:
        for text in texts:
            for secret in (
                ACCOUNT_ID,
                OTHER_ACCOUNT_ID,
                ACCESS_TOKEN,
                SERVER_MARKER,
                "SECRET",
                str(self.harness.codex_home),
                "gpt-daybreak-exact",
            ):
                self.assertNotIn(secret, text)

    def gate_outcomes(self, report: dict[str, Any]) -> dict[str, tuple[str, str]]:
        return {g["gate_key"]: (g["outcome"], g["reason"]) for g in report["gates"]}

    # -- describe and binding revision ------------------------------------

    def test_describe_exposes_only_safe_labels_and_a_binding_bound_revision(self):
        described = self.harness.describe()
        self.assertEqual(described["account"], "acct-label")
        self.assertEqual(described["route"], "route-label")
        self.assertEqual(described["buckets"], ["weekly"])
        self.assertEqual(described["models"], ["daybreak"])
        self.assertTrue(described["policy_revision"].startswith("policy-2026-09+"))
        self.assert_redacted(json.dumps(described))
        first = described["policy_revision"]

        self.harness.config["expected_account_id"] = OTHER_ACCOUNT_ID
        self.assertNotEqual(self.harness.revision(), first)
        self.harness.config["expected_account_id"] = ACCOUNT_ID
        self.assertEqual(self.harness.revision(), first)
        self.assertIsNone(self.harness.calls(), "describe never launches codex")

    def test_binding_config_is_closed_private_and_explicit(self):
        cases = (
            ("command key", lambda c: c.update(codex_command=["evil"])),
            ("missing account id", lambda c: c.pop("expected_account_id")),
            ("relative home", lambda c: c.update(codex_home="relative/home")),
            ("unknown window", lambda c: c["quota"]["weekly"]["windows"].append(
                {"window": "tertiary"}
            )),
            ("unbound model quota", lambda c: c["models"].update(
                daybreak={"model": "gpt-daybreak-exact", "quota": "nope"}
            )),
        )
        for label, mutate in cases:
            with self.subTest(label=label):
                harness = AdapterHarness(Path(tempfile.mkdtemp(dir=self.tempdir.name)))
                mutate(harness.config)
                result = harness.adapter("describe")
                self.assertEqual(result.returncode, 2)
                self.assertIn("codex status: invalid-binding", result.stderr)
                self.assert_redacted(result.stderr, result.stdout)

        config = self.harness.write_config(mode=0o644)
        result = run([str(ADAPTER), "describe", "--binding", str(config)])
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid-binding", result.stderr)

    # -- protocol -----------------------------------------------------------

    def test_observe_uses_the_fixed_status_only_protocol_in_an_isolated_process(self):
        revision = self.harness.revision()
        self.harness.register(quota_gate(revision), "task-1")
        self.harness.register(daybreak_gate(revision), "task-2")
        self.harness.fixture["notifications_before"] = {
            "account/rateLimits/read": [
                {"method": "account/rateLimits/updated", "params": {"x": SERVER_MARKER}}
            ]
        }
        self.harness.fixture["server_request_before"] = {
            "model/list": {"id": "srv-1", "method": "item/tool/requestApproval", "params": {}}
        }
        result, report = self.harness.observe(self.harness.requests())

        calls = self.harness.calls()
        assert calls is not None
        self.assertEqual(calls["argv"], EXPECTED_ARGV)
        self.assertEqual(calls["codex_home"], str(self.harness.codex_home))
        self.assertNotIn("SECRET_ENV_VALUE", calls["env_keys"])
        self.assertEqual(calls["cwd_entries"], [])
        self.assertNotEqual(calls["cwd"], str(self.harness.root))
        self.assertFalse(Path(calls["cwd"]).exists(), "temporary cwd is removed")
        messages = calls["messages"]
        self.assertEqual(
            [m.get("method") for m in messages],
            [
                "initialize",
                "initialized",
                "account/read",
                "model/list",
                "model/list",
                "account/rateLimits/read",
            ],
        )
        self.assertEqual(
            messages[0]["params"]["capabilities"], {"experimentalApi": True}
        )
        self.assertEqual(
            set(messages[0]["params"]["clientInfo"]), {"name", "version"}
        )
        self.assertNotIn("id", messages[1])
        self.assertEqual(messages[2]["params"], {"refreshToken": False})
        self.assertEqual(
            messages[3]["params"], {"includeHidden": True, "limit": 100, "cursor": None}
        )
        self.assertEqual(messages[4]["params"]["cursor"], "page-2")
        self.assertEqual(messages[5]["params"], {})
        self.assertTrue(all("srv-1" != m.get("id") for m in messages))

        outcomes = self.gate_outcomes(report)
        self.assertEqual({o for o, _ in outcomes.values()}, {"observed"})
        self.assert_redacted(result.stdout, result.stderr)
        identity = report["bindings"][0]["identity"]
        self.assertEqual(identity["server_identity"], "unavailable")
        self.assertTrue(identity["local_metadata_matches"])
        self.assertEqual(report["bindings"][0]["policy_revision"], revision)

    def test_matching_account_yields_open_quota_and_available_daybreak(self):
        revision = self.harness.revision()
        quota = self.harness.register(quota_gate(revision), "task-1")
        daybreak = self.harness.register(daybreak_gate(revision), "task-2")
        _, report = self.harness.observe(self.harness.requests())

        observations = {o["gate_key"]: o for o in report["cycle_input"]["observations"]}
        quota_observation = observations[quota["gate_key"]]
        self.assertEqual(quota_observation["status"], "ok")
        # No required window is exhausted, so nothing blocks the bucket and there
        # is no expected opening to hint: the advertised window resets are not
        # a reset_at (they are neither capacity nor a scheduling hint here).
        self.assertEqual(
            quota_observation["buckets"],
            [{"name": "weekly", "remaining_percent": 30.0}],
        )
        self.assertNotIn("credits", quota_observation)
        self.assertNotIn("expires_at", quota_observation)
        daybreak_observation = observations[daybreak["gate_key"]]
        self.assertEqual(daybreak_observation["exposed_models"], ["daybreak"])
        self.assertEqual(daybreak_observation["capacity"], "available")

        cycle = self.harness.cycle_with(report)
        results = {i["gate_key"]: (i["result"], i["reason"]) for i in cycle["ingested_observations"]}
        self.assertEqual(results[quota["gate_key"]], ("open", "bucket-has-remaining-capacity"))
        self.assertEqual(results[daybreak["gate_key"]], ("open", "model-exposed-with-capacity"))
        self.assertEqual(cycle["observation_requests"], [])
        self.assertEqual(
            {s["reason"] for s in cycle["skipped"]}, {"task-unknown"}
        )

    def test_server_confirmed_identity_is_reported_and_mismatch_is_held(self):
        revision = self.harness.revision()
        self.harness.register(quota_gate(revision))
        self.harness.fixture["responses"]["account/read"]["account"]["accountId"] = ACCOUNT_ID
        _, report = self.harness.observe(self.harness.requests())
        self.assertEqual(report["bindings"][0]["identity"]["server_identity"], "confirmed")
        self.assertEqual({o for o, _ in self.gate_outcomes(report).values()}, {"observed"})

        self.harness.fixture["responses"]["account/read"]["account"]["accountId"] = OTHER_ACCOUNT_ID
        result, report = self.harness.observe(self.harness.requests())
        self.assertEqual(
            {v for v in self.gate_outcomes(report).values()},
            {("held", "held:account-mismatch")},
        )
        self.assertEqual(report["cycle_input"]["observations"][0]["status"], "error")
        self.assert_redacted(result.stdout)

    def test_expected_account_email_confirms_identity_and_a_mismatch_is_held(self):
        self.harness.config["expected_account_email"] = SERVER_MARKER + "@example.test"
        revision = self.harness.revision()
        self.harness.register(quota_gate(revision))
        result, report = self.harness.observe(self.harness.requests())
        identity = report["bindings"][0]["identity"]
        self.assertEqual(identity["status"], "verified")
        self.assertEqual(identity["server_identity"], "confirmed")
        self.assertEqual({o for o, _ in self.gate_outcomes(report).values()}, {"observed"})
        self.assert_redacted(result.stdout, result.stderr)
        self.assertNotIn("@example.test", result.stdout)

        self.harness.fixture["responses"]["account/read"]["account"]["email"] = (
            "someone-else@example.test"
        )
        result, report = self.harness.observe(self.harness.requests())
        self.assertEqual(
            list(self.gate_outcomes(report).values()), [("held", "held:account-mismatch")]
        )
        self.assertEqual(report["bindings"][0]["identity"]["status"], "held")
        self.assertEqual(report["cycle_input"]["observations"][0]["status"], "error")
        self.assertNotIn("someone-else", result.stdout)
        self.assert_redacted(result.stdout, result.stderr)

        # A server that exposes no email or id cannot confirm, and is not held for it.
        del self.harness.fixture["responses"]["account/read"]["account"]["email"]
        _, report = self.harness.observe(self.harness.requests())
        self.assertEqual(report["bindings"][0]["identity"]["server_identity"], "unavailable")
        self.assertEqual({o for o, _ in self.gate_outcomes(report).values()}, {"observed"})

    # -- identity gates -----------------------------------------------------

    def test_local_account_mismatch_is_held_without_launching_codex(self):
        revision = self.harness.revision()
        self.harness.register(quota_gate(revision))
        self.harness.write_auth(OTHER_ACCOUNT_ID)
        result, report = self.harness.observe(self.harness.requests())
        self.assertEqual(
            list(self.gate_outcomes(report).values()), [("held", "held:account-mismatch")]
        )
        self.assertIsNone(self.harness.calls())
        self.assertFalse(report["bindings"][0]["identity"]["local_metadata_matches"])
        self.assert_redacted(result.stdout, result.stderr)

        cycle = self.harness.cycle_with(report)
        self.assertEqual(cycle["ingested_observations"][0]["result"], "error")
        self.assertEqual(cycle["skipped"][0]["reason"], "gate-unobserved")

    def test_missing_or_unreadable_credentials_are_held(self):
        revision = self.harness.revision()
        self.harness.register(quota_gate(revision))
        (self.harness.codex_home / "auth.json").unlink()
        _, report = self.harness.observe(self.harness.requests())
        self.assertEqual(
            list(self.gate_outcomes(report).values()),
            [("held", "held:credentials-missing")],
        )
        self.assertIsNone(self.harness.calls())

        (self.harness.codex_home / "auth.json").write_text("{not json", encoding="utf-8")
        _, report = self.harness.observe(self.harness.requests())
        self.assertEqual(
            list(self.gate_outcomes(report).values()),
            [("held", "held:credentials-unreadable")],
        )

        self.harness.write_auth(None)
        _, report = self.harness.observe(self.harness.requests())
        self.assertEqual(
            list(self.gate_outcomes(report).values()),
            [("held", "held:credentials-missing")],
        )

    def test_identity_change_during_observation_is_held(self):
        revision = self.harness.revision()
        self.harness.register(quota_gate(revision))
        self.harness.fixture["auth_rewrite"] = {
            "at": "account/read",
            "account_id": OTHER_ACCOUNT_ID,
        }
        result, report = self.harness.observe(self.harness.requests())
        self.assertEqual(
            list(self.gate_outcomes(report).values()),
            [("held", "held:identity-changed")],
        )
        self.assertTrue(report["bindings"][0]["identity"]["changed_during_observation"])
        self.assert_redacted(result.stdout)

    def test_unauthenticated_or_non_chatgpt_server_account_is_held(self):
        revision = self.harness.revision()
        self.harness.register(quota_gate(revision))
        self.harness.fixture["responses"]["account/read"] = {"account": None}
        _, report = self.harness.observe(self.harness.requests())
        self.assertEqual(
            list(self.gate_outcomes(report).values()),
            [("held", "held:not-authenticated")],
        )
        self.harness.fixture["responses"]["account/read"] = {"account": {"type": "apiKey"}}
        _, report = self.harness.observe(self.harness.requests())
        self.assertEqual(
            list(self.gate_outcomes(report).values()),
            [("held", "held:account-type-unsupported")],
        )
        # Only an account whose type is exactly "chatgpt" passes: a missing,
        # non-string, or differently cased type is held rather than assumed.
        for account in (
            {"email": SERVER_MARKER + "@example.test"},
            {"type": None},
            {"type": ["chatgpt"]},
            {"type": "ChatGPT"},
        ):
            with self.subTest(account=sorted(account)):
                self.harness.fixture["responses"]["account/read"] = {"account": account}
                result, report = self.harness.observe(self.harness.requests())
                self.assertEqual(
                    list(self.gate_outcomes(report).values()),
                    [("held", "held:account-type-unsupported")],
                )
                self.assert_redacted(result.stdout, result.stderr)

    def test_policy_revision_or_label_mismatch_never_observes(self):
        stale = self.harness.register(quota_gate("policy-2026-09+stalebinding"), "task-1")
        foreign = self.harness.register(
            {**quota_gate(self.harness.revision()), "route": "other-route"}, "task-2"
        )
        _, report = self.harness.observe(self.harness.requests())
        outcomes = self.gate_outcomes(report)
        self.assertEqual(outcomes[stale["gate_key"]], ("held", "held:policy-revision-mismatch"))
        self.assertEqual(outcomes[foreign["gate_key"]], ("unhandled", "binding-labels-differ"))
        self.assertEqual(
            [o["gate_key"] for o in report["cycle_input"]["observations"]],
            [stale["gate_key"]],
        )
        self.assertIsNone(self.harness.calls())

    def test_unbound_bucket_or_model_label_is_held(self):
        revision = self.harness.revision()
        bucket = self.harness.register(quota_gate(revision, bucket="monthly"), "task-1")
        model = self.harness.register(daybreak_gate(revision, model="other"), "task-2")
        _, report = self.harness.observe(self.harness.requests())
        outcomes = self.gate_outcomes(report)
        self.assertEqual(outcomes[bucket["gate_key"]], ("held", "held:bucket-unbound"))
        self.assertEqual(outcomes[model["gate_key"]], ("held", "held:model-unbound"))

    # -- quota semantics ----------------------------------------------------

    def test_missing_limit_window_or_duration_is_held_not_silently_closed(self):
        # A binding that names a limit id, a required window, or a pinned
        # duration the server does not present is a binding-to-server mismatch:
        # the owner must act, so the gate is held (backs off, never opens, and
        # stands as a failing marker) rather than read as a quietly closed gate.
        revision = self.harness.revision()
        quota = self.harness.register(quota_gate(revision), "task-1")
        daybreak = self.harness.register(daybreak_gate(revision), "task-2")
        cases = (
            ("limit id absent", {"rateLimits": {"primary": window(0)}, "rateLimitsByLimitId": {}}),
            ("secondary window absent", rate_limits(window(10), None)),
            ("primary window absent", rate_limits(None, window(10, minutes=10080))),
            ("duration mismatch", rate_limits(window(10, minutes=60), window(10, minutes=10080))),
            ("used percent invalid", rate_limits(window("10"), window(10, minutes=10080))),
        )
        requests = self.harness.requests()
        # Each case is a later tick (the engine's evidence per gate is
        # monotonic, so an error stamped at an earlier or equal time would be
        # skipped rather than ingested).
        for minute, (label, limits) in enumerate(cases):
            with self.subTest(label=label):
                at = f"2026-09-17T12:{minute:02d}:00+00:00"
                self.harness.fixture["responses"]["account/rateLimits/read"] = limits
                result, report = self.harness.observe(requests, now=at)
                self.assertEqual(
                    set(self.gate_outcomes(report).values()),
                    {("held", "held:limit-window-missing")},
                )
                self.assertEqual(report["bindings"][0]["identity"]["status"], "verified")
                observations = {
                    o["gate_key"]: o for o in report["cycle_input"]["observations"]
                }
                for key in (quota["gate_key"], daybreak["gate_key"]):
                    self.assertEqual(
                        (observations[key]["status"], observations[key]["reason"]),
                        ("error", "held:limit-window-missing"),
                    )
                self.assert_redacted(result.stdout, result.stderr)
                cycle = self.harness.cycle_with(report, now=at)
                ingested = {i["gate_key"]: (i["result"], i["reason"]) for i in cycle["ingested_observations"]}
                self.assertEqual(
                    set(ingested.values()), {("error", "held:limit-window-missing")}
                )
                self.assertEqual(cycle["wake_proposals"], [])
                schedule = engine(self.harness.store, "inspect", now=at)["retry_schedule"]
                self.assertEqual(
                    {schedule[key]["last_reason"] for key in (quota["gate_key"], daybreak["gate_key"])},
                    {"held:limit-window-missing"},
                )
        # The hold takes the existing notice path: a failing marker on first
        # sight, with the owner's next action, and a quiet identical re-result.
        after = "2026-09-17T12:05:00+00:00"
        report_path = self.harness.root / "tick-report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")
        notice = engine(self.harness.store, "notice", "--adapter-report", str(report_path), now=after)
        self.assertTrue(notice["report"])
        failing = {n["gate_key"]: n for n in notice["new"] if n["family"] == "failing"}
        self.assertEqual(set(failing), {quota["gate_key"], daybreak["gate_key"]})
        for body in failing.values():
            self.assertEqual(body["reason"], "held:limit-window-missing")
            self.assertIn("fix the binding", body["next_action"])
        self.assertIn("held:limit-window-missing", notice["text"])
        engine(self.harness.store, "acknowledge", "--notice-id", notice["notice_id"], now=after)
        again = engine(self.harness.store, "notice", "--adapter-report", str(report_path), now=after)
        self.assertFalse(again["report"])

        self.harness.fixture["responses"]["account/rateLimits/read"] = {"rateLimits": {}}
        _, report = self.harness.observe(requests)
        self.assertEqual(
            set(self.gate_outcomes(report).values()),
            {("error", "error:rate-limits-shape")},
        )

    def test_missing_limit_holds_only_the_gates_bound_to_it(self):
        # One binding, two buckets: the server presents the weekly limit and
        # lacks the daily one. Only the gates bound to the missing limit are
        # held; the others on the same binding are observed as usual.
        self.harness.config["quota"]["daily"] = {
            "limit_id": "codex-daily",
            "windows": [{"window": "primary", "duration_minutes": 1440}],
        }
        self.harness.config["models"]["nightly"] = {"model": "gpt-daybreak-exact", "quota": "daily"}
        revision = self.harness.revision()
        weekly = self.harness.register(quota_gate(revision, bucket="weekly"), "task-1")
        daily = self.harness.register(quota_gate(revision, bucket="daily"), "task-2")
        nightly = self.harness.register(daybreak_gate(revision, model="nightly"), "task-3")
        result, report = self.harness.observe(self.harness.requests())
        outcomes = self.gate_outcomes(report)
        self.assertEqual(outcomes[weekly["gate_key"]], ("observed", "typed-observation"))
        self.assertEqual(outcomes[daily["gate_key"]], ("held", "held:limit-window-missing"))
        self.assertEqual(outcomes[nightly["gate_key"]], ("held", "held:limit-window-missing"))
        self.assertEqual(report["bindings"][0]["identity"]["status"], "verified")
        self.assertEqual(self.harness.methods().count("account/rateLimits/read"), 1)
        self.assert_redacted(result.stdout, result.stderr)
        cycle = self.harness.cycle_with(report)
        ingested = {i["gate_key"]: i["result"] for i in cycle["ingested_observations"]}
        self.assertEqual(ingested[weekly["gate_key"]], "open")
        self.assertEqual(ingested[daily["gate_key"]], "error")
        self.assertEqual(ingested[nightly["gate_key"]], "error")
        self.assertEqual(
            {(s["task_id"], s["reason"]) for s in cycle["skipped"]},
            {("task-1", "task-unknown"), ("task-2", "gate-unobserved"), ("task-3", "gate-unobserved")},
        )

    def test_any_exhausted_required_window_closes_the_bucket(self):
        revision = self.harness.revision()
        quota = self.harness.register(quota_gate(revision), "task-1")
        daybreak = self.harness.register(daybreak_gate(revision), "task-2")
        cases = (
            ("primary exhausted", window(100), window(20, minutes=10080), 0.0, "exhausted"),
            ("secondary exhausted", window(5), window(100, minutes=10080), 0.0, "exhausted"),
            ("both exhausted", window(100), window(100, minutes=10080), 0.0, "exhausted"),
            ("both remaining", window(99.5), window(1, minutes=10080), 0.5, "available"),
        )
        requests = self.harness.requests()
        # Each case is a later tick: the engine's anchor per gate is monotonic.
        for minute, (label, primary, secondary, remaining, capacity) in enumerate(cases):
            with self.subTest(label=label):
                at = f"2026-09-17T12:{minute:02d}:00+00:00"
                self.harness.fixture["responses"]["account/rateLimits/read"] = rate_limits(
                    primary, secondary
                )
                _, report = self.harness.observe(requests, now=at)
                observations = {
                    o["gate_key"]: o for o in report["cycle_input"]["observations"]
                }
                bucket = observations[quota["gate_key"]]["buckets"][0]
                self.assertEqual(bucket["remaining_percent"], remaining)
                self.assertEqual(observations[daybreak["gate_key"]]["capacity"], capacity)
                cycle = self.harness.cycle_with(report, now=at)
                results = {i["gate_key"]: i["result"] for i in cycle["ingested_observations"]}
                expected = "open" if remaining > 0 else "closed"
                self.assertEqual(results[quota["gate_key"]], expected)
                self.assertEqual(results[daybreak["gate_key"]], expected)

    def test_early_reset_is_requeried_at_the_planned_check_not_the_advertised_reset(self):
        revision = self.harness.revision()
        quota = self.harness.register(quota_gate(revision))
        far_reset = 1789800000  # 2026-09-19, well after LATER
        self.harness.fixture["responses"]["account/rateLimits/read"] = rate_limits(
            window(100, reset=far_reset), window(10, reset=far_reset, minutes=10080)
        )
        _, report = self.harness.observe(self.harness.requests())
        cycle = self.harness.cycle_with(report)
        ingested = cycle["ingested_observations"][0]
        self.assertEqual(ingested["result"], "closed")
        self.assertEqual(ingested["expires_at"], "2026-09-17T12:15:00+00:00")
        # The adapter's reset_at is a scheduling hint, not freshness: with the
        # reset days out the engine plans the 360-minute ceiling from NOW, so a
        # cycle at LATER requests nothing and the planned check does.
        self.assertEqual(cycle["schedule"]["next_check_at"], "2026-09-17T18:00:00+00:00")
        self.assertEqual(
            engine(self.harness.store, "cycle", now=LATER)["observation_requests"], []
        )
        requeried = engine(self.harness.store, "cycle", now="2026-09-17T18:00:00+00:00")
        self.assertEqual(
            [r["reason"] for r in requeried["observation_requests"]], ["stale"]
        )
        self.harness.fixture["responses"]["account/rateLimits/read"] = rate_limits(
            window(10, reset=far_reset), window(10, reset=far_reset, minutes=10080)
        )
        requests = self.harness.root / "cycle-output.json"
        requests.write_text(json.dumps(requeried), encoding="utf-8")
        _, report = self.harness.observe(requests)
        observation = report["cycle_input"]["observations"][0]
        self.assertEqual(observation["gate_key"], quota["gate_key"])
        self.assertEqual(observation["buckets"][0]["remaining_percent"], 90.0)

    def test_reset_hint_follows_the_windows_that_exhaust_the_bucket(self):
        # The bucket's expected opening depends on the windows that block it.
        # A non-exhausted weekly window resetting days out must not postpone
        # the hint from an exhausted 5-hour window resetting in two hours; when
        # several windows block, all of them must recover; and a blocking
        # window with no usable reset leaves the opening unknown rather than
        # borrowing another window's reset. The hint only plans the requery: it
        # never opens the gate.
        cases = (
            (
                "short window exhausted, long window has capacity",
                window(100, reset=RESET_IN_2H),
                window(20, reset=RESET_FAR, minutes=10080),
                "2026-09-17T14:00:00+00:00",
                ("reset-hint", "2026-09-17T12:30:00+00:00", 30),
            ),
            (
                "both windows exhausted: the later recovery is needed",
                window(100, reset=RESET_IN_2H),
                window(100, reset=RESET_IN_4H, minutes=10080),
                "2026-09-17T16:00:00+00:00",
                ("reset-hint", "2026-09-17T13:00:00+00:00", 60),
            ),
            (
                "exhausted short window advertises no reset",
                window_without_reset(100),
                window(20, reset=RESET_FAR, minutes=10080),
                None,
                ("no-estimate", "2026-09-17T13:00:00+00:00", 60),
            ),
            (
                "both exhausted, one reset unknown: no known opening",
                window(100, reset=RESET_IN_2H),
                window_without_reset(100, minutes=10080),
                None,
                ("no-estimate", "2026-09-17T13:00:00+00:00", 60),
            ),
        )
        for label, primary, secondary, reset_at, plan in cases:
            with self.subTest(label=label):
                harness = AdapterHarness(Path(tempfile.mkdtemp(dir=self.tempdir.name)).resolve())
                quota = harness.register(quota_gate(harness.revision()))
                harness.fixture["responses"]["account/rateLimits/read"] = rate_limits(
                    primary, secondary
                )
                result, report = harness.observe(harness.requests())
                self.assertEqual(
                    list(self.gate_outcomes(report).values()), [("observed", "typed-observation")]
                )
                [observation] = report["cycle_input"]["observations"]
                [bucket] = observation["buckets"]
                self.assertEqual(bucket["remaining_percent"], 0.0)
                self.assertEqual(bucket.get("reset_at"), reset_at)
                self.assert_redacted(result.stdout, result.stderr)
                cycle = harness.cycle_with(report)
                [ingested] = cycle["ingested_observations"]
                self.assertEqual((ingested["result"], ingested["reason"]), ("closed", "bucket-exhausted"))
                self.assertEqual(cycle["wake_proposals"], [])
                basis, next_check_at, delay = plan
                [gate] = cycle["schedule"]["gates"]
                self.assertEqual(gate["gate_key"], quota["gate_key"])
                self.assertEqual(gate["anchor"], NOW)
                self.assertEqual((gate["basis"], gate["estimate_at"]), (basis, reset_at))
                self.assertEqual(gate["interval_minutes"], delay)
                self.assertEqual(cycle["schedule"]["reason"], "gate-query")
                self.assertEqual(cycle["schedule"]["next_check_at"], next_check_at)
                self.assertEqual(cycle["schedule"]["delay_minutes"], delay)
                # A tick at the old fixed cadence requests nothing; the planned
                # check does. The hint is not capacity: even after the reset
                # has passed on the clock, only a new open observation admits.
                self.assertEqual(engine(harness.store, "cycle", now=LATER)["observation_requests"], [])
                planned = engine(harness.store, "cycle", now=next_check_at)
                self.assertEqual([r["reason"] for r in planned["observation_requests"]], ["stale"])
                states = harness.root / "task-states.json"
                states.write_text(
                    json.dumps({"observations": [], "task_states": [
                        {"host": "host-a", "task_id": "task-1", "status": "idle", "observed_at": "2026-09-17T16:01:00+00:00"}
                    ]}),
                    encoding="utf-8",
                )
                after_reset = engine(harness.store, "cycle", "--input", str(states), now="2026-09-17T16:01:00+00:00")
                self.assertEqual(after_reset["wake_proposals"], [])
                self.assertEqual([s["reason"] for s in after_reset["skipped"]], ["gate-observation-stale"])

    def test_daybreak_capacity_reset_hint_plans_the_requery_and_never_opens(self):
        # The bound bucket's reset already observed for the daybreak gate is
        # carried as the optional reset_at and drives the closed plan when
        # capacity is the closing cause. It never implies the model will be
        # exposed and never opens the gate.
        cases = (
            ("exhausted, model exposed", True, "capacity-exhausted", "reset-hint", "2026-09-17T12:30:00+00:00"),
            ("exhausted, model absent", False, "model-not-exposed", "no-estimate", "2026-09-17T13:00:00+00:00"),
        )
        for label, exposed, reason, basis, next_check_at in cases:
            with self.subTest(label=label):
                harness = AdapterHarness(Path(tempfile.mkdtemp(dir=self.tempdir.name)).resolve())
                daybreak = harness.register(daybreak_gate(harness.revision()))
                harness.fixture["responses"]["account/rateLimits/read"] = rate_limits(
                    window(100, reset=RESET_IN_2H), window(20, reset=RESET_FAR, minutes=10080)
                )
                if not exposed:
                    harness.fixture["responses"]["model/list"] = [
                        {"data": [{"model": "gpt-other"}], "nextCursor": None}
                    ]
                result, report = harness.observe(harness.requests())
                [observation] = report["cycle_input"]["observations"]
                self.assertEqual(observation["gate_key"], daybreak["gate_key"])
                self.assertEqual(observation["capacity"], "exhausted")
                self.assertEqual(observation["exposed_models"], ["daybreak"] if exposed else [])
                self.assertEqual(observation["reset_at"], "2026-09-17T14:00:00+00:00")
                self.assert_redacted(result.stdout, result.stderr)
                cycle = harness.cycle_with(report)
                [ingested] = cycle["ingested_observations"]
                self.assertEqual((ingested["result"], ingested["reason"]), ("closed", reason))
                self.assertEqual(cycle["wake_proposals"], [])
                [gate] = cycle["schedule"]["gates"]
                self.assertEqual(gate["basis"], basis)
                self.assertEqual(cycle["schedule"]["next_check_at"], next_check_at)
                self.assertEqual(engine(harness.store, "cycle", now=LATER)["observation_requests"], [])
                planned = engine(harness.store, "cycle", now=next_check_at)
                self.assertEqual([r["reason"] for r in planned["observation_requests"]], ["stale"])
        # With capacity available nothing blocks the bucket, so no hint is carried.
        harness = AdapterHarness(Path(tempfile.mkdtemp(dir=self.tempdir.name)).resolve())
        harness.register(daybreak_gate(harness.revision()))
        _, report = harness.observe(harness.requests())
        [observation] = report["cycle_input"]["observations"]
        self.assertEqual(observation["capacity"], "available")
        self.assertNotIn("reset_at", observation)
        self.assertEqual(
            harness.cycle_with(report)["ingested_observations"][0]["reason"],
            "model-exposed-with-capacity",
        )

    # -- model semantics ----------------------------------------------------

    def test_model_pagination_and_missing_model(self):
        revision = self.harness.revision()
        daybreak = self.harness.register(daybreak_gate(revision))
        requests = self.harness.requests()
        self.harness.fixture["responses"]["model/list"] = [
            {"data": [{"model": "a"}], "nextCursor": "p2"},
            {"data": [{"model": "b"}], "nextCursor": "p3"},
            {"data": [{"model": "gpt-daybreak-exact"}], "nextCursor": None},
        ]
        _, report = self.harness.observe(requests)
        self.assertEqual(self.harness.methods().count("model/list"), 3)
        observation = report["cycle_input"]["observations"][0]
        self.assertEqual(observation["exposed_models"], ["daybreak"])

        self.harness.fixture["responses"]["model/list"] = [
            {"data": [{"model": "gpt-daybreak-exact-preview"}], "nextCursor": None}
        ]
        _, report = self.harness.observe(requests)
        observation = report["cycle_input"]["observations"][0]
        self.assertEqual(observation["exposed_models"], [])
        cycle = self.harness.cycle_with(report)
        self.assertEqual(cycle["ingested_observations"][0]["reason"], "model-not-exposed")
        self.assertEqual(daybreak["gate_key"], observation["gate_key"])

        self.harness.fixture["responses"]["model/list"] = {
            "repeat": {"data": [{"model": "x"}], "nextCursor": "again"}
        }
        _, report = self.harness.observe(requests)
        self.assertEqual(
            list(self.gate_outcomes(report).values()),
            [("error", "error:model-list-unbounded")],
        )
        self.assertLessEqual(self.harness.methods().count("model/list"), 10)

    def test_quota_only_requests_skip_model_list(self):
        self.harness.register(quota_gate(self.harness.revision()))
        self.harness.observe(self.harness.requests())
        self.assertNotIn("model/list", self.harness.methods())

    # -- failures -----------------------------------------------------------

    def test_server_failures_are_generic_errors_and_stop_the_process(self):
        revision = self.harness.revision()
        self.harness.register(quota_gate(revision), "task-1")
        self.harness.register(daybreak_gate(revision), "task-2")
        cases = (
            ("malformed", "account/read", "error:malformed-response"),
            ("rpc-error", "account/rateLimits/read", "error:rpc-error"),
            ("exit", "initialize", "error:codex-exit"),
            ("oversized", "model/list", "error:malformed-response"),
            ("hang", "model/list", "error:codex-timeout"),
        )
        requests = self.harness.requests()
        # Each case is a later tick: the engine's evidence per gate is monotonic.
        for minute, (behavior, method, reason) in enumerate(cases):
            with self.subTest(behavior=behavior):
                at = f"2026-09-17T12:{minute:02d}:00+00:00"
                self.harness.fixture["behavior"] = {method: behavior}
                started = time.monotonic()
                result, report = self.harness.observe(requests, timeout="2", now=at)
                self.assertLess(time.monotonic() - started, 20)
                self.assertEqual(
                    set(self.gate_outcomes(report).values()), {("error", reason)}
                )
                calls = self.harness.calls()
                assert calls is not None
                self.assertFalse(Path(f"/proc/{calls['pid']}").exists() and _alive(calls["pid"]))
                self.assertFalse(Path(calls["cwd"]).exists())
                observations = report["cycle_input"]["observations"]
                self.assertEqual({o["status"] for o in observations}, {"error"})
                self.assertEqual({o["reason"] for o in observations}, {reason})
                self.assert_redacted(result.stdout, result.stderr)
                cycle = self.harness.cycle_with(report, now=at)
                self.assertEqual(
                    {i["result"] for i in cycle["ingested_observations"]}, {"error"}
                )

    def test_missing_codex_executable_is_a_generic_error(self):
        self.harness.register(quota_gate(self.harness.revision()))
        (self.harness.bin / "codex").unlink()
        result, report = self.harness.observe(self.harness.requests())
        self.assertEqual(
            list(self.gate_outcomes(report).values()),
            [("error", "error:codex-unavailable")],
        )
        self.assert_redacted(result.stdout, result.stderr)

    # -- cycle input plumbing ------------------------------------------------

    def test_task_states_and_output_file_produce_cycle_ready_input(self):
        revision = self.harness.revision()
        registration = self.harness.register(quota_gate(revision))
        states = self.harness.root / "task-states.json"
        states.write_text(
            json.dumps(
                [
                    {
                        "host": "host-a",
                        "task_id": "task-1",
                        "status": "idle",
                        "observed_at": NOW,
                    }
                ]
            ),
            encoding="utf-8",
        )
        output = self.harness.root / "input.json"
        _, report = self.harness.observe(
            self.harness.requests(), "--task-states", str(states), "--output", str(output)
        )
        written = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(written, report["cycle_input"])
        self.assertEqual(set(written), {"observations", "task_states"})
        cycle = engine(self.harness.store, "cycle", "--input", str(output))
        self.assertEqual(len(cycle["wake_proposals"]), 1)
        proposal = cycle["wake_proposals"][0]
        self.assertEqual(proposal["registration_id"], registration["registration_id"])
        [send] = [s for s in proposal["native_steps"] if s["step"] == "send"]
        self.assertIsNone(send["model_override"])

    def test_output_file_is_written_private_even_when_it_already_exists_wider(self):
        self.harness.register(quota_gate(self.harness.revision()))
        output = self.harness.root / "tick-input.json"
        requests = self.harness.requests()
        self.harness.observe(requests, "--output", str(output))
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
        # A leftover world-readable file at the same path is tightened, not reused.
        output.chmod(0o644)
        self.harness.observe(requests, "--output", str(output))
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
        self.assertEqual(
            set(json.loads(output.read_text(encoding="utf-8"))),
            {"observations", "task_states"},
        )

    def test_several_bindings_each_observe_their_own_labels_in_one_run(self):
        second = AdapterHarness(Path(tempfile.mkdtemp(dir=self.tempdir.name)).resolve())
        second.config["account"] = "acct-two"
        second.config["route"] = "route-two"
        second.config["expected_account_id"] = OTHER_ACCOUNT_ID
        second.write_auth(OTHER_ACCOUNT_ID)
        second.fixture["responses"]["account/rateLimits/read"] = rate_limits(
            window(100), window(0, minutes=10080)
        )
        second.write_fixture()
        second_config = second.write_config()
        first_gate = self.harness.register(quota_gate(self.harness.revision()), "task-1")
        second_gate = self.harness.register(
            {**quota_gate(second.revision()), "account": "acct-two", "route": "route-two"},
            "task-2",
        )
        stray = self.harness.register(
            {**quota_gate("x"), "account": "acct-three", "route": "route-three"}, "task-3"
        )
        # Both bindings resolve the same fake codex from PATH; each is still
        # verified against its own auth metadata and expected account id.
        _, report = self.harness.observe(
            self.harness.requests(), "--binding", str(second_config)
        )
        outcomes = self.gate_outcomes(report)
        self.assertEqual(outcomes[first_gate["gate_key"]], ("observed", "typed-observation"))
        self.assertEqual(outcomes[second_gate["gate_key"]], ("observed", "typed-observation"))
        self.assertEqual(outcomes[stray["gate_key"]], ("unhandled", "binding-labels-differ"))
        self.assertEqual(
            [(b["account"], b["identity"]["status"]) for b in report["bindings"]],
            [("acct-label", "verified"), ("acct-two", "verified")],
        )
        observed_keys = {o["gate_key"] for o in report["cycle_input"]["observations"]}
        self.assertEqual(observed_keys, {first_gate["gate_key"], second_gate["gate_key"]})

        duplicate = self.harness.adapter(
            "observe", "--requests", str(self.harness.requests()), "--binding",
            str(self.harness.root / "binding.json"),
        )
        self.assertEqual(duplicate.returncode, 2)
        self.assertIn("invalid-binding", duplicate.stderr)

    def test_worked_example_with_its_task_state_fixture_wakes_only_the_idle_task(self):
        # The engine-cli.md worked example: three tasks share one gate; the
        # monitor supplies t1 idle, t2 running, t3 completed before the observe
        # step.
        gate = quota_gate(self.harness.revision())
        for task in ("t1", "t2", "t3"):
            engine(
                self.harness.store, "register", "--owner", "me", "--host", "h1",
                "--task-id", task, "--episode", f"{task}-wait-1", "--gate-json",
                json.dumps(gate), "--continuation",
                f"Quota observed open; revalidate and resume {task}.",
            )
        plan = self.harness.requests()
        [request] = json.loads(plan.read_text(encoding="utf-8"))["observation_requests"]
        self.assertEqual(request["task_ids"], ["t1", "t2", "t3"])
        states = self.harness.root / "task-states.json"
        states.write_text(
            json.dumps(
                [
                    {"host": "h1", "task_id": task, "status": status, "observed_at": NOW}
                    for task, status in (("t1", "idle"), ("t2", "running"), ("t3", "completed"))
                ]
            ),
            encoding="utf-8",
        )
        output = self.harness.root / "tick-input.json"
        _, report = self.harness.observe(
            plan, "--task-states", str(states), "--output", str(output)
        )
        self.assertEqual(self.harness.methods().count("account/rateLimits/read"), 1)
        self.assertEqual(len(report["cycle_input"]["observations"]), 1)
        cycle = engine(self.harness.store, "cycle", "--input", str(output))
        [proposal] = cycle["wake_proposals"]
        self.assertEqual((proposal["host"], proposal["task_id"]), ("h1", "t1"))
        self.assertEqual(
            {(s["task_id"], s["reason"]) for s in cycle["skipped"]},
            {("t2", "task-running"), ("t3", "task-completed")},
        )

    def test_request_no_binding_owns_is_unhandled_and_requested_again_every_tick(self):
        # A mislabelled gate produces no observation and no backoff, so the engine
        # asks for it again at every tick with nothing in attention. The adapter
        # report is the only place it is named; the monitor reports it from there.
        stray = self.harness.register(
            {**quota_gate("x"), "account": "acct-three", "route": "route-three"}
        )
        _, report = self.harness.observe(self.harness.requests())
        self.assertEqual(
            report["gates"],
            [
                {
                    "gate_key": stray["gate_key"],
                    "kind": "quota_recovery",
                    "outcome": "unhandled",
                    "reason": "binding-labels-differ",
                }
            ],
        )
        self.assertEqual(report["cycle_input"]["observations"], [])
        self.assertIsNone(self.harness.calls())
        cycle = self.harness.cycle_with(report)
        self.assertEqual([r["reason"] for r in cycle["observation_requests"]], ["unobserved"])
        self.assertEqual([s["reason"] for s in cycle["skipped"]], ["gate-unobserved"])
        self.assertEqual(cycle["attention"], [])
        again = engine(self.harness.store, "cycle", now=LATER)
        self.assertEqual([r["reason"] for r in again["observation_requests"]], ["unobserved"])
        self.assertEqual(again["attention"], [])
        self.assertEqual(engine(self.harness.store, "inspect", now=LATER)["retry_schedule"], {})

    def test_empty_requests_are_a_successful_no_op_without_launching_codex(self):
        _, report = self.harness.observe(self.harness.requests())
        self.assertEqual(report["gates"], [])
        self.assertEqual(report["cycle_input"], {"observations": [], "task_states": []})
        self.assertIsNone(self.harness.calls())

    def test_requests_and_gate_keys_are_validated(self):
        bad = self.harness.root / "bad.json"
        bad.write_text(json.dumps({"observation_requests": [{"gate_key": "x"}]}), encoding="utf-8")
        result = self.harness.adapter("observe", "--requests", str(bad))
        self.assertEqual(result.returncode, 2)
        self.assertIn("codex status: invalid-requests", result.stderr)

        mismatched = self.harness.root / "mismatch.json"
        mismatched.write_text(
            json.dumps(
                {
                    "observation_requests": [
                        {"gate_key": "0" * 64, "gate": quota_gate(self.harness.revision())}
                    ]
                }
            ),
            encoding="utf-8",
        )
        _, report = self.harness.observe(mismatched)
        self.assertEqual(
            list(self.gate_outcomes(report).values()),
            [("held", "held:gate-key-mismatch")],
        )
        self.assertIsNone(self.harness.calls())

    def test_report_flag_writes_the_printed_report_privately_and_nothing_on_exit_2(self):
        self.harness.register(quota_gate(self.harness.revision()))
        requests = self.harness.requests()
        report_path = self.harness.root / "report.json"
        output = self.harness.root / "input.json"
        result, report = self.harness.observe(
            requests, "--output", str(output), "--report", str(report_path)
        )
        self.assertEqual(stat.S_IMODE(report_path.stat().st_mode), 0o600)
        written = report_path.read_text(encoding="utf-8")
        self.assertEqual(written, result.stdout)
        self.assertEqual(json.loads(written), report)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), report["cycle_input"])
        self.assert_redacted(written)
        # A wider leftover file at the report path is tightened, not reused.
        report_path.chmod(0o644)
        self.harness.observe(requests, "--report", str(report_path))
        self.assertEqual(stat.S_IMODE(report_path.stat().st_mode), 0o600)
        # Exit 2 prints nothing and writes nothing.
        report_path.unlink()
        output.unlink()
        self.harness.write_fixture()
        config = self.harness.write_config(mode=0o644)
        result = run(
            [str(ADAPTER), "observe", "--binding", str(config), "--requests", str(requests),
             "--output", str(output), "--report", str(report_path), "--now", NOW],
            env={"PATH": os.pathsep.join([str(self.harness.bin), str(Path(sys.executable).parent)]), "HOME": str(self.harness.root)},
            cwd=self.harness.root,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("codex status: invalid-binding", result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertFalse(report_path.exists())
        self.assertFalse(output.exists())

    def test_report_write_failure_is_exit_2_and_leaves_an_earlier_output_file(self):
        # The two files are written one after the other with no transaction:
        # --output lands first, then --report fails, and the run is exit 2
        # with nothing printed. The engine reads neither file on exit 2.
        self.harness.register(quota_gate(self.harness.revision()))
        requests = self.harness.requests()
        output = self.harness.root / "input.json"
        unwritable = self.harness.root / "report-dir"
        unwritable.mkdir()
        result = self.harness.adapter(
            "observe", "--requests", str(requests), "--output", str(output), "--report", str(unwritable)
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("codex status: output-io: output file is unwritable", result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertTrue(output.exists(), "the earlier output file remains")
        self.assertEqual(set(json.loads(output.read_text(encoding="utf-8"))), {"observations", "task_states"})
        # The reverse: an unwritable --output fails before --report is written.
        output.unlink()
        report_path = self.harness.root / "report.json"
        result = self.harness.adapter(
            "observe", "--requests", str(requests), "--output", str(unwritable), "--report", str(report_path)
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("codex status: output-io", result.stderr)
        self.assertFalse(report_path.exists())

    def test_directed_tick_argv_runs_the_adapter_and_its_artifacts_are_ingested(self):
        revision = self.harness.revision()
        registration = self.harness.register(quota_gate(revision))
        config = self.harness.write_config()
        self.harness.write_fixture()
        store = self.harness.store
        view = engine(store, "tick", "start", "--binding", str(config), "--heartbeat", "heartbeat-1")
        tick_id = view["tick"]["tick_id"]

        def submit(view: dict, result: dict) -> dict:
            return engine(
                store, "tick", "submit", "--tick-id", tick_id,
                "--action-id", view["pending_action"]["action_id"], "--result-json", json.dumps(result),
            )

        self.assertEqual(view["pending_action"]["kind"], "task_read")
        view = submit(view, {"status": "idle", "observed_at": NOW})
        observe = view["pending_action"]
        self.assertEqual((observe["kind"], observe["purpose"]), ("observe", "query"))
        argv = observe["arguments"]["argv"]
        self.assertEqual(argv[:3], ["python3", str(ADAPTER), "observe"])
        self.assertEqual(argv[-2:], ["--now", NOW])
        self.assertNotIn("--task-states", argv)
        directory = store / "ticks" / tick_id
        output_path = Path(argv[argv.index("--output") + 1])
        report_path = Path(argv[argv.index("--report") + 1])
        self.assertEqual(output_path.parent, directory)
        self.assertEqual(report_path.parent, directory)
        self.assertRegex(output_path.name, r"^input-[0-9a-f]{24}\.json$")
        self.assertRegex(report_path.name, r"^report-[0-9a-f]{24}\.json$")
        # The monitor runs exactly that argv.
        env = {
            "PATH": os.pathsep.join([str(self.harness.bin), str(Path(sys.executable).parent)]),
            "HOME": str(self.harness.root),
            "CODEX_HOME": str(self.harness.root / "ambient-wrong-home"),
        }
        completed = subprocess.run(
            argv, capture_output=True, text=True, check=False, timeout=60, env=env, cwd=self.harness.root
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(self.harness.calls()["codex_home"], str(self.harness.codex_home))
        for path in (directory / "plan.json", report_path, output_path):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600, path.name)
        self.assertEqual(json.loads(report_path.read_text(encoding="utf-8")), json.loads(completed.stdout))
        self.assert_redacted(completed.stdout, output_path.read_text(encoding="utf-8"))
        view = submit(view, {"exit_code": 0})
        key = registration["gate_key"]
        self.assertEqual(view["last_result"]["consequence"], "observation-ingested")
        self.assertEqual(view["tick"]["observe"]["answered_gate_keys"], [key])
        self.assertEqual(view["tick"]["observe"]["adapter_report"], {key: "observed"})
        # The open quota observation and the idle read admit the wake.
        pre = view["pending_action"]
        self.assertEqual((pre["kind"], pre["purpose"]), ("task_read", "pre-send"))
        view = submit(view, {"status": "idle", "observed_at": NOW})
        send = view["pending_action"]
        self.assertEqual(send["kind"], "send")
        self.assertIn("Resume the synthetic waiting work.", send["arguments"]["message"])
        self.assertIsNone(send["arguments"]["model_override"])
        self.assert_redacted(json.dumps(view))
        view = submit(view, {"outcome": "accepted"})
        self.assertEqual(view["pending_action"]["kind"], "emit")
        view = submit(view, {"emitted": True})
        heartbeat = view["pending_action"]
        self.assertEqual(heartbeat["kind"], "heartbeat_set")
        view = submit(view, {"applied": True, "next_run_at": heartbeat["arguments"]["target_at"]})
        self.assertEqual(view["tick"]["status"], "complete")
        self.assertFalse(directory.exists())
        self.assert_redacted(json.dumps(view))

    def test_monitor_takeover_ingests_only_the_active_observation_execution(self):
        revision = self.harness.revision()
        registration = self.harness.register(quota_gate(revision))
        config = self.harness.write_config()
        self.harness.fixture["delays"] = {"account/rateLimits/read": 1.0}
        self.harness.write_fixture()

        contender = AdapterHarness(
            Path(tempfile.mkdtemp(dir=self.tempdir.name)).resolve()
        )
        contender.fixture["behavior"] = {"account/rateLimits/read": "rpc-error"}
        contender.write_fixture()

        def engine_cli(*args: str) -> dict[str, Any]:
            result = run([str(ENGINE), *args])
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)

        def adapter_env(harness: AdapterHarness) -> dict[str, str]:
            return {
                "PATH": os.pathsep.join(
                    [str(harness.bin), str(Path(sys.executable).parent)]
                ),
                "HOME": str(harness.root),
            }

        bound = engine_cli(
            "monitor",
            "bind",
            "--store",
            str(self.harness.store),
            "--binding",
            str(config),
            "--heartbeat",
            "heartbeat-1",
        )
        first = engine_cli(
            "monitor", "enter", "--entry-ref", bound["entry_ref"], "--now", NOW
        )
        first = engine_cli(
            "monitor",
            "continue",
            "--continuation",
            first["continuation"],
            "--result-json",
            json.dumps({"status": "idle", "observed_at": NOW}),
            "--now",
            NOW,
        )
        self.assertEqual(first["action"]["kind"], "observe")

        stale_process = subprocess.Popen(
            first["action"]["arguments"]["argv"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=adapter_env(self.harness),
            cwd=self.harness.root,
        )
        try:
            deadline = time.monotonic() + 5
            methods: list[str] = []
            while "account/rateLimits/read" not in methods:
                self.assertLess(time.monotonic(), deadline, "stale adapter did not reach its delayed provider response")
                try:
                    methods = self.harness.methods()
                except json.JSONDecodeError:
                    methods = []
                time.sleep(0.01)

            active = engine_cli(
                "monitor", "enter", "--entry-ref", bound["entry_ref"], "--now", NOW
            )
            self.assertEqual(active["action"]["kind"], "observe")
            active_argv = active["action"]["arguments"]["argv"]

            active_process = subprocess.run(
                active_argv,
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
                env=adapter_env(contender),
                cwd=contender.root,
            )
            self.assertEqual(active_process.returncode, 0, active_process.stderr)
            stale_stdout, stale_stderr = stale_process.communicate(timeout=60)
            self.assertEqual(stale_process.returncode, 0, stale_stderr)
            self.assertNotEqual(
                json.loads(stale_stdout)["cycle_input"],
                json.loads(active_process.stdout)["cycle_input"],
                "the overlapping executions must produce divergent coherent results",
            )

            result = engine_cli(
                "monitor",
                "continue",
                "--continuation",
                active["continuation"],
                "--result-json",
                json.dumps({"exit_code": 0}),
                "--now",
                NOW,
            )
        finally:
            if stale_process.poll() is None:
                stale_process.kill()
            stale_process.communicate()

        self.assertNotEqual(
            (result.get("action") or {}).get("purpose"),
            "pre-send",
            "the stale OPEN observation must not admit a wake",
        )
        self.assertNotEqual(
            first["action"]["arguments"]["argv"],
            active_argv,
            "takeover must bind a fresh observation execution",
        )
        inspected = engine_cli(
            "inspect", "--store", str(self.harness.store), "--now", NOW
        )
        self.assertEqual(inspected["observations"], [])
        retry = inspected["retry_schedule"][registration["gate_key"]]
        self.assertEqual(retry["last_reason"], "error:rpc-error")

    def test_real_invalid_binding_field_set_line_takes_the_query_failed_path(self):
        # Review cycle 9, finding 1: the adapter's longest fixed failure line
        # (the invalid-binding field-set error) must be accepted verbatim by
        # `tick submit` as an exit-2 observe result and take the documented
        # query-failed path rather than trapping the action at invalid-result.
        revision = self.harness.revision()
        registration = self.harness.register(quota_gate(revision))
        store = self.harness.store
        # A synthetic invalid binding: one extra top-level field. load_binding
        # refuses it before any subprocess, so even with the fake codex on PATH
        # nothing is launched and no provider or account operation happens.
        self.harness.config["extra_top_level_field"] = True
        config = self.harness.write_config()
        self.harness.write_fixture()
        view = engine(store, "tick", "start", "--binding", str(config), "--heartbeat", "heartbeat-1")
        tick_id = view["tick"]["tick_id"]

        def submit(view: dict, result: dict) -> dict:
            return engine(
                store, "tick", "submit", "--tick-id", tick_id,
                "--action-id", view["pending_action"]["action_id"], "--result-json", json.dumps(result),
            )

        view = submit(view, {"status": "idle", "observed_at": NOW})
        observe = view["pending_action"]
        self.assertEqual((observe["kind"], observe["purpose"]), ("observe", "query"))
        # The monitor runs exactly the issued argv and captures the failure line.
        env = {
            "PATH": os.pathsep.join([str(self.harness.bin), str(Path(sys.executable).parent)]),
            "HOME": str(self.harness.root),
        }
        completed = subprocess.run(
            observe["arguments"]["argv"], capture_output=True, text=True, check=False,
            timeout=60, env=env, cwd=self.harness.root,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, "")
        self.assertIsNone(self.harness.calls(), "an invalid binding launches nothing")
        [line] = completed.stderr.splitlines()
        self.assertTrue(
            line.startswith("codex status: invalid-binding: binding config must have exactly the fields ["), line
        )
        self.assertTrue(line.endswith("plus optional ['expected_account_email']"), line)
        message = line.split(": ", 2)[2]
        # Execution evidence for the reviewer's count: the message is 201
        # characters and the whole line 232, past the former 200-character cap.
        self.assertEqual((len(line), len(message)), (232, 201))
        self.assert_redacted(line)
        # The verbatim line is submitted to the pending observe action.
        view = submit(view, {"exit_code": 2, "stderr_line": line})
        self.assertEqual(view["last_result"]["disposition"], "performed")
        self.assertEqual(view["last_result"]["consequence"], "query-failed")
        result = view["tick"]["observe"]
        self.assertEqual((result["exit_code"], result["failure_line"]), (2, line))
        self.assertEqual(result["unanswered_gate_keys"], [registration["gate_key"]])
        self.assertFalse(result["adapter_report_learned"])
        self.assertIsNone(result["adapter_report"])
        heartbeat = view["pending_action"]
        self.assertEqual(heartbeat["kind"], "heartbeat_set")
        self.assertEqual(heartbeat["arguments"]["rule"], "failed-observation-recovery")
        view = submit(view, {"applied": True, "next_run_at": heartbeat["arguments"]["target_at"]})
        emit = view["pending_action"]
        self.assertEqual((emit["kind"], emit["purpose"]), ("emit", "diagnostics"))
        self.assertEqual(emit["arguments"]["text"], f"step observe: {line}", "relayed untruncated")
        view = submit(view, {"emitted": True})
        self.assertEqual(view["tick"]["status"], "complete")
        self.assertFalse((store / "ticks" / tick_id).exists())
        self.assert_redacted(json.dumps(view))


if __name__ == "__main__":
    unittest.main()
