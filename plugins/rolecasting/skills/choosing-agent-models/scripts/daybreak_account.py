"""Operate on one explicitly selected Daybreak account binding."""

from __future__ import annotations

import argparse
import datetime
import json
import os
import selectors
import subprocess
import sys
import time
from pathlib import Path

from daybreak_records import (
    RecordError,
    allowlisted_capacity,
    dump_json,
    load_selection,
    split_selector,
)

RPC_TIMEOUT_SECONDS = 10
MAX_MODEL_PAGES = 100
CHATGPT_PLAN_TYPES = {
    "free",
    "go",
    "plus",
    "pro",
    "prolite",
    "promax",
    "team",
    "self_serve_business_prolite",
    "self_serve_business_usage_based",
    "business",
    "ent26",
    "enterprise_cbp_automation",
    "enterprise_cbp_usage_based",
    "enterprise",
    "edu",
    "edu_plus",
    "edu_pro",
    "unknown",
}


class AccountError(RuntimeError):
    """A selected-account operation failed without authorizing fallback."""


class RpcClient:
    def __init__(self, process: subprocess.Popen[bytes]):
        self.process = process
        self.sequence = 0
        self.buffer = b""
        self.notifications: list[dict[str, object]] = []
        self.selector = selectors.DefaultSelector()
        assert process.stdout is not None
        self.selector.register(process.stdout, selectors.EVENT_READ)

    def close(self) -> None:
        self.selector.close()

    def send(self, message: dict[str, object]) -> None:
        assert self.process.stdin is not None
        self.process.stdin.write(dump_json(message).encode("utf-8"))
        self.process.stdin.flush()

    def request(self, method: str, params: object) -> object:
        self.sequence += 1
        request_id = self.sequence
        self.send({"id": request_id, "method": method, "params": params})
        deadline = time.monotonic() + RPC_TIMEOUT_SECONDS
        while True:
            message = self.read_message(deadline)
            if message.get("id") == request_id:
                if "error" in message:
                    error = message.get("error")
                    if not isinstance(error, dict) or not isinstance(
                        error.get("message"), str
                    ):
                        raise AccountError(
                            f"{method} returned RPC error with invalid payload"
                        )
                    code = error.get("code")
                    if type(code) is not int or not -(2**63) <= code < 2**63:
                        raise AccountError(
                            f"{method} returned RPC error with invalid code"
                        )
                    raise AccountError(f"{method} returned RPC error {code}")
                if "result" not in message:
                    raise AccountError(f"{method} returned no result")
                return message["result"]
            if "id" in message and "method" in message:
                raise AccountError("app server requested an unsupported client action")
            if "method" in message:
                self.notifications.append(message)

    def read_message(self, deadline: float) -> dict[str, object]:
        while b"\n" not in self.buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AccountError("app server response timed out")
            events = self.selector.select(timeout=remaining)
            if not events:
                raise AccountError("app server response timed out")
            assert self.process.stdout is not None
            chunk = os.read(self.process.stdout.fileno(), 65536)
            if not chunk:
                raise AccountError("app server terminated before completing")
            self.buffer += chunk
        line, self.buffer = self.buffer.split(b"\n", 1)
        try:
            message = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AccountError("app server returned malformed JSON") from error
        if not isinstance(message, dict):
            raise AccountError("app server returned a non-object message")
        return message


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Use one strict selection from stdin. The supplied Codex executable may "
            "read and write its selected CODEX_HOME and contact its provider."
        )
    )
    subparsers = parser.add_subparsers(dest="operation", required=True)
    status = subparsers.add_parser(
        "status-refresh",
        description=(
            "Expand only the selected ~/PATH, read its auth.json, and launch the "
            "trusted absolute Codex executable with the selected CODEX_HOME. The "
            "executable inherits the environment, may update selected-home state, "
            "and may contact its provider; no task thread or prompt is created."
        ),
    )
    status.add_argument("--selection-stdin", action="store_true", required=True)
    status.add_argument("--codex", type=Path, required=True)
    status.add_argument("--model", required=True)
    status.add_argument("--freshness-seconds", type=int, required=True)
    probe = subparsers.add_parser(
        "harmless-probe",
        description=(
            "Unavailable in this status-only helper: validate inputs, then fail "
            "before authentication access or Codex launch."
        ),
    )
    probe.add_argument("--selection-stdin", action="store_true", required=True)
    probe.add_argument("--codex", type=Path, required=True)
    probe.add_argument("--model", required=True)
    probe.add_argument("--workspace", type=Path, required=True)
    return parser


def load_selection_input() -> tuple[dict[str, str], Path]:
    selection = load_selection(sys.stdin.read())
    raw_home = selection["account_home"]
    account_home = Path(raw_home)
    if raw_home.startswith("~/"):
        relative = Path(raw_home[2:])
        if (
            relative.is_absolute()
            or not relative.parts
            or {".", ".."}.intersection(relative.parts)
        ):
            raise RecordError("selection account_home has invalid ~/PATH syntax")
        account_home = Path.home() / relative
    elif not account_home.is_absolute():
        raise RecordError(
            "selection account_home must be absolute or use ~/PATH syntax"
        )
    return selection, account_home


def verify_binding(selection: dict[str, str], account_home: Path) -> None:
    try:
        auth = json.loads((account_home / "auth.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AccountError("selected authentication record is unavailable") from error
    if not isinstance(auth, dict) or not isinstance(auth.get("tokens"), dict):
        raise AccountError("selected authentication record is malformed")
    observed = auth["tokens"].get("account_id")
    if not isinstance(observed, str):
        raise AccountError("selected authentication record is malformed")
    if observed != selection["authenticated_account_id"]:
        raise AccountError("selected binding does not match authentication state")


def start_server(
    executable: Path, account_home: Path, cwd: Path
) -> subprocess.Popen[bytes]:
    if not executable.is_absolute():
        raise AccountError("codex executable must be an absolute path")
    environment = dict(os.environ)
    environment["CODEX_HOME"] = str(account_home)
    try:
        return subprocess.Popen(
            [str(executable), "app-server", "--stdio"],
            cwd=cwd,
            env=environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except OSError as error:
        raise AccountError("supplied codex executable could not be launched") from error


def stop_server(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def initialize(client: RpcClient) -> None:
    client.request(
        "initialize",
        {
            "clientInfo": {"name": "rolecasting-daybreak", "version": "1"},
            "capabilities": {"experimentalApi": True},
        },
    )
    client.send({"method": "initialized"})


def exposed_model(client: RpcClient, model: str, effort: str) -> dict[str, object]:
    cursor: object = None
    seen_cursors: set[str] = set()
    matches: list[dict[str, object]] = []
    for _page_number in range(MAX_MODEL_PAGES):
        page = client.request(
            "model/list", {"includeHidden": True, "limit": 100, "cursor": cursor}
        )
        if not isinstance(page, dict) or not isinstance(page.get("data"), list):
            raise AccountError("model/list returned an invalid result")
        for candidate in page["data"]:
            if isinstance(candidate, dict) and candidate.get("model") == model:
                matches.append(candidate)
        cursor = page.get("nextCursor")
        if cursor is None:
            break
        if not isinstance(cursor, str) or not cursor or cursor in seen_cursors:
            raise AccountError("model/list pagination is invalid")
        seen_cursors.add(cursor)
    else:
        raise AccountError("model/list pagination is invalid")
    if len(matches) != 1:
        raise AccountError("exact model selector is not uniquely exposed")
    efforts = matches[0].get("supportedReasoningEfforts")
    if not isinstance(efforts, list):
        raise AccountError("model/list returned an invalid result")
    exposed_efforts = set()
    for item in efforts:
        if not isinstance(item, dict) or not isinstance(
            item.get("reasoningEffort"), str
        ):
            raise AccountError("model/list returned an invalid result")
        exposed_efforts.add(item["reasoningEffort"])
    if effort not in exposed_efforts:
        raise AccountError("exact model effort is not exposed")
    access = matches[0].get("availableAccessPrograms")
    cyber = access.get("cyber") if isinstance(access, dict) else None
    if not isinstance(cyber, list) or not all(
        isinstance(program, str) for program in cyber
    ):
        raise AccountError("model/list returned an invalid result")
    if "daybreakBlue" not in cyber:
        raise AccountError("exact model does not advertise Daybreak Blue access")
    return matches[0]


def validate_authenticated_account(account_result: object) -> None:
    if not isinstance(account_result, dict):
        raise AccountError("account/read returned an invalid result")
    requires_auth = account_result.get("requiresOpenaiAuth")
    if type(requires_auth) is not bool:
        raise AccountError("account/read returned an invalid result")
    account = account_result.get("account")
    if not isinstance(account, dict) or account.get("type") != "chatgpt":
        raise AccountError("selected app server is not authenticated with ChatGPT")
    if "email" not in account or "planType" not in account:
        raise AccountError("account/read returned an invalid result")
    email = account.get("email")
    plan_type = account.get("planType")
    if (email is not None and not isinstance(email, str)) or (
        not isinstance(plan_type, str) or plan_type not in CHATGPT_PLAN_TYPES
    ):
        raise AccountError("account/read returned an invalid result")


def selected_capacity(rate_result: object, model: str) -> dict[str, object] | None:
    if not isinstance(rate_result, dict) or not isinstance(
        rate_result.get("rateLimits"), dict
    ):
        raise AccountError("account/rateLimits/read returned an invalid result")
    buckets = rate_result.get("rateLimitsByLimitId")
    if buckets is not None and not isinstance(buckets, dict):
        raise AccountError("account/rateLimits/read returned an invalid result")
    matches = []
    if isinstance(buckets, dict):
        for value in buckets.values():
            if not isinstance(value, dict):
                raise AccountError("account/rateLimits/read returned an invalid result")
            slug = value.get("normalModelSlug")
            if slug is not None and not isinstance(slug, str):
                raise AccountError("account/rateLimits/read returned an invalid result")
            if slug == model:
                matches.append(value)
    if len(matches) > 1:
        raise AccountError("multiple capacity buckets match the exact model")
    return allowlisted_capacity(matches[0]) if matches else None


def status_refresh(
    executable: Path,
    account_home: Path,
    expected_account_id: str,
    selector: str,
    freshness_seconds: int,
) -> dict[str, object]:
    if freshness_seconds <= 0:
        raise AccountError("freshness-seconds must be positive")
    model, effort = split_selector(selector)
    process = start_server(executable, account_home, account_home)
    client = RpcClient(process)
    try:
        initialize(client)
        account_result = client.request("account/read", {"refreshToken": False})
        validate_authenticated_account(account_result)
        exposed_model(client, model, effort)
        rate_result = client.request(
            "account/rateLimits/read",
            {"excludeResetCreditDetails": True, "supportsLunaReserve": False},
        )
        if not isinstance(rate_result, dict):
            raise AccountError("account/rateLimits/read returned an invalid result")
        provider_account_id = rate_result.get("accountId")
        if not isinstance(provider_account_id, str):
            raise AccountError("provider account identity is unavailable")
        if provider_account_id != expected_account_id:
            raise AccountError("provider account does not match selected binding")
        ordinary = rate_result.get("ordinaryUsageAllowed")
        if ordinary is not None and not isinstance(ordinary, bool):
            raise AccountError("ordinaryUsageAllowed has an invalid type")
        return {
            "schema": "rolecasting-daybreak-status-v1",
            "operation": "status-refresh",
            "observed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "freshness_seconds": freshness_seconds,
            "binding_matches": True,
            "authenticated": True,
            "selector": selector,
            "selector_exposed": True,
            "ordinary_usage_allowed": ordinary,
            "capacity": selected_capacity(rate_result, model),
        }
    finally:
        client.close()
        stop_server(process)


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        selection, account_home = load_selection_input()
        if arguments.operation == "status-refresh":
            verify_binding(selection, account_home)
            result = status_refresh(
                arguments.codex,
                account_home,
                selection["authenticated_account_id"],
                arguments.model,
                arguments.freshness_seconds,
            )
        else:
            split_selector(arguments.model)
            if not arguments.codex.is_absolute():
                raise AccountError("codex executable must be an absolute path")
            if not arguments.workspace.is_absolute():
                raise AccountError("workspace must be an absolute path")
            raise AccountError(
                "supported Codex controls do not provide a closed-world task-tool "
                "deny; no Codex process was launched"
            )
    except (AccountError, RecordError) as error:
        print(f"daybreak_account: {error}", file=sys.stderr)
        return 1
    sys.stdout.write(dump_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
