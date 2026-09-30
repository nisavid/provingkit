"""Operate on one explicitly selected Daybreak account binding."""

from __future__ import annotations

import argparse
import datetime
import os
import selectors
import stat
import subprocess
import sys
import time
from pathlib import Path

from daybreak_records import (
    RecordError,
    allowlisted_capacity,
    dump_json,
    load_selection,
    load_strict_json,
    split_selector,
)

RPC_TIMEOUT_SECONDS = 10
MAX_AUTH_BYTES = 1_048_576
AUTH_OPEN_FLAGS = os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0)
MAX_MODEL_PAGES = 100
MAX_RPC_FRAME_BYTES = 1_048_576
MAX_RPC_BUFFER_BYTES = MAX_RPC_FRAME_BYTES + 1
MAX_RPC_MESSAGES_PER_REQUEST = 128
RPC_READ_BYTES = 65_536
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

    MESSAGES = {
        "DA001": "invalid command line",
        "DA002": "invalid selection input",
        "DA003": "selected authentication unavailable",
        "DA004": "selected authentication malformed",
        "DA005": "selected authentication does not match selection",
        "DA006": "invalid Codex executable",
        "DA007": "Codex launch failed",
        "DA008": "provider transport setup failed",
        "DA009": "provider transport write failed",
        "DA010": "provider transport read failed",
        "DA011": "provider transport closed",
        "DA012": "provider response timed out",
        "DA013": "provider frame exceeds limit",
        "DA014": "provider message limit exceeded",
        "DA015": "provider protocol message invalid",
        "DA016": "provider requested unsupported client action",
        "DA017": "provider RPC failed",
        "DA018": "provider account response invalid",
        "DA019": "provider is not authenticated with ChatGPT",
        "DA020": "provider identity unavailable",
        "DA021": "provider identity does not match selection",
        "DA022": "provider model response invalid",
        "DA023": "provider model pagination invalid",
        "DA024": "exact model is not uniquely exposed",
        "DA025": "exact model effort is not exposed",
        "DA026": "exact model lacks Daybreak Blue access",
        "DA027": "provider rate-limit response invalid",
        "DA028": "provider usage response invalid",
        "DA029": "provider capacity response invalid",
        "DA030": "freshness interval invalid",
        "DA031": "harmless probe unavailable in status-only increment",
        "DA032": "provider teardown failed",
        "DA033": "invalid exact model selector",
        "DA034": "invalid probe workspace",
        "DA035": "status output failed",
    }

    def __init__(self, code: str):
        if code not in self.MESSAGES:
            raise ValueError("unknown account diagnostic code")
        self.code = code
        super().__init__(self.MESSAGES[code])

    def public_diagnostic(self) -> str:
        return f"{self.code}: {self.MESSAGES[self.code]}"


class FixedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise AccountError("DA001")


class RpcClient:
    def __init__(self, process: subprocess.Popen[bytes]):
        self.process = process
        self.sequence = 0
        self.buffer = b""
        assert process.stdout is not None
        try:
            self.selector = selectors.DefaultSelector()
            self.selector.register(process.stdout, selectors.EVENT_READ)
        except (OSError, UnicodeError, ValueError) as error:
            if hasattr(self, "selector"):
                try:
                    self.selector.close()
                except (OSError, ValueError):
                    pass
            raise AccountError("DA008") from error

    def close(self) -> bool:
        try:
            self.selector.close()
        except (OSError, ValueError):
            return False
        return True

    def send(self, message: dict[str, object]) -> None:
        assert self.process.stdin is not None
        try:
            self.process.stdin.write(dump_json(message).encode("utf-8"))
            self.process.stdin.flush()
        except (OSError, UnicodeError, ValueError) as error:
            raise AccountError("DA009") from error

    def request(self, method: str, params: object) -> object:
        self.sequence += 1
        request_id = self.sequence
        self.send({"id": request_id, "method": method, "params": params})
        deadline = time.monotonic() + RPC_TIMEOUT_SECONDS
        for _message_number in range(MAX_RPC_MESSAGES_PER_REQUEST):
            message = self.read_message(deadline)
            has_id = "id" in message
            has_method = "method" in message
            if has_method and not isinstance(message.get("method"), str):
                raise AccountError("DA015")
            if has_id and has_method:
                raise AccountError("DA016")
            if has_id and type(message.get("id")) is not int:
                raise AccountError("DA015")
            if message.get("id") == request_id:
                if ("error" in message) == ("result" in message):
                    raise AccountError("DA015")
                if "error" in message:
                    error = message.get("error")
                    if not isinstance(error, dict) or not isinstance(
                        error.get("message"), str
                    ):
                        raise AccountError("DA015")
                    code = error.get("code")
                    if type(code) is not int or not -(2**63) <= code < 2**63:
                        raise AccountError("DA015")
                    raise AccountError("DA017")
                if "result" not in message:
                    raise AccountError("DA015")
                return message["result"]
            if has_id:
                raise AccountError("DA015")
            if has_method:
                continue
            raise AccountError("DA015")
        raise AccountError("DA014")

    def read_message(self, deadline: float) -> dict[str, object]:
        while b"\n" not in self.buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AccountError("DA012")
            try:
                events = self.selector.select(timeout=remaining)
            except (OSError, ValueError) as error:
                raise AccountError("DA010") from error
            if not events:
                raise AccountError("DA012")
            assert self.process.stdout is not None
            available = MAX_RPC_BUFFER_BYTES - len(self.buffer)
            if available <= 0:
                raise AccountError("DA013")
            try:
                chunk = os.read(
                    self.process.stdout.fileno(), min(RPC_READ_BYTES, available)
                )
            except (OSError, ValueError) as error:
                raise AccountError("DA010") from error
            if not chunk:
                raise AccountError("DA011")
            self.buffer += chunk
            if b"\n" not in self.buffer and len(self.buffer) > MAX_RPC_FRAME_BYTES:
                raise AccountError("DA013")
        newline = self.buffer.index(b"\n")
        if newline > MAX_RPC_FRAME_BYTES:
            raise AccountError("DA013")
        line, self.buffer = self.buffer.split(b"\n", 1)
        try:
            message = load_strict_json(line)
        except (UnicodeDecodeError, RecordError) as error:
            raise AccountError("DA015") from error
        if not isinstance(message, dict):
            raise AccountError("DA015")
        return message


def build_parser() -> argparse.ArgumentParser:
    parser = FixedArgumentParser(
        prog="daybreak-account",
        description=(
            "Use one strict selection from stdin. The supplied Codex executable may "
            "read and write its selected CODEX_HOME and contact its provider."
        )
    )
    subparsers = parser.add_subparsers(
        dest="operation", required=True, parser_class=FixedArgumentParser
    )
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
    try:
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
                raise AccountError("DA002")
            account_home = Path.home() / relative
        elif not account_home.is_absolute():
            raise AccountError("DA002")
    except AccountError:
        raise
    except (OSError, UnicodeError, RecordError, RuntimeError, ValueError) as error:
        raise AccountError("DA002") from error
    return selection, account_home


def read_authentication(path: Path) -> bytes:
    descriptor: int | None = None
    try:
        descriptor = os.open(path, AUTH_OPEN_FLAGS)
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise AccountError("DA003")
        stream = os.fdopen(descriptor, "rb")
        descriptor = None
        with stream:
            content = stream.read(MAX_AUTH_BYTES + 1)
    except AccountError:
        raise
    except (OSError, UnicodeError, ValueError) as error:
        raise AccountError("DA003") from error
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
    if len(content) > MAX_AUTH_BYTES:
        raise AccountError("DA004")
    return content


def verify_binding(selection: dict[str, str], account_home: Path) -> None:
    content = read_authentication(account_home / "auth.json")
    try:
        auth = load_strict_json(content)
    except (UnicodeDecodeError, RecordError) as error:
        raise AccountError("DA004") from error
    if not isinstance(auth, dict) or not isinstance(auth.get("tokens"), dict):
        raise AccountError("DA004")
    observed = auth["tokens"].get("account_id")
    if not isinstance(observed, str):
        raise AccountError("DA004")
    if observed != selection["authenticated_account_id"]:
        raise AccountError("DA005")


def start_server(
    executable: Path, account_home: Path, cwd: Path
) -> subprocess.Popen[bytes]:
    if not executable.is_absolute():
        raise AccountError("DA006")
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
    except (OSError, UnicodeError, ValueError) as error:
        raise AccountError("DA007") from error


def stop_server(process: subprocess.Popen[bytes]) -> bool:
    try:
        if process.poll() is not None:
            return True
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)
    except (OSError, ValueError, subprocess.SubprocessError):
        return False
    return True


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
    match: dict[str, object] | None = None
    match_count = 0
    for _page_number in range(MAX_MODEL_PAGES):
        page = client.request(
            "model/list", {"includeHidden": True, "limit": 100, "cursor": cursor}
        )
        if not isinstance(page, dict) or not isinstance(page.get("data"), list):
            raise AccountError("DA022")
        for candidate in page["data"]:
            if isinstance(candidate, dict) and candidate.get("model") == model:
                match_count += 1
                if match is None:
                    match = candidate
        cursor = page.get("nextCursor")
        if cursor is None:
            break
        if not isinstance(cursor, str) or not cursor or cursor in seen_cursors:
            raise AccountError("DA023")
        seen_cursors.add(cursor)
    else:
        raise AccountError("DA023")
    if match_count != 1 or match is None:
        raise AccountError("DA024")
    efforts = match.get("supportedReasoningEfforts")
    if not isinstance(efforts, list):
        raise AccountError("DA022")
    exposed_efforts = set()
    for item in efforts:
        if not isinstance(item, dict) or not isinstance(
            item.get("reasoningEffort"), str
        ):
            raise AccountError("DA022")
        exposed_efforts.add(item["reasoningEffort"])
    if effort not in exposed_efforts:
        raise AccountError("DA025")
    access = match.get("availableAccessPrograms")
    cyber = access.get("cyber") if isinstance(access, dict) else None
    if not isinstance(cyber, list) or not all(
        isinstance(program, str) for program in cyber
    ):
        raise AccountError("DA022")
    if "daybreakBlue" not in cyber:
        raise AccountError("DA026")
    return match


def validate_authenticated_account(account_result: object) -> None:
    if not isinstance(account_result, dict):
        raise AccountError("DA018")
    requires_auth = account_result.get("requiresOpenaiAuth")
    if type(requires_auth) is not bool:
        raise AccountError("DA018")
    account = account_result.get("account")
    if not isinstance(account, dict) or account.get("type") != "chatgpt":
        raise AccountError("DA019")
    if "email" not in account or "planType" not in account:
        raise AccountError("DA018")
    email = account.get("email")
    plan_type = account.get("planType")
    if (email is not None and not isinstance(email, str)) or (
        not isinstance(plan_type, str) or plan_type not in CHATGPT_PLAN_TYPES
    ):
        raise AccountError("DA018")


def selected_capacity(rate_result: object, model: str) -> dict[str, object] | None:
    if not isinstance(rate_result, dict) or not isinstance(
        rate_result.get("rateLimits"), dict
    ):
        raise AccountError("DA027")
    buckets = rate_result.get("rateLimitsByLimitId")
    if buckets is not None and not isinstance(buckets, dict):
        raise AccountError("DA027")
    matches = []
    if isinstance(buckets, dict):
        for value in buckets.values():
            if not isinstance(value, dict):
                raise AccountError("DA027")
            slug = value.get("normalModelSlug")
            if slug is not None and not isinstance(slug, str):
                raise AccountError("DA027")
            if slug == model:
                matches.append(value)
    if len(matches) > 1:
        raise AccountError("DA027")
    try:
        return allowlisted_capacity(matches[0]) if matches else None
    except RecordError as error:
        raise AccountError("DA029") from error


def status_refresh(
    executable: Path,
    account_home: Path,
    expected_account_id: str,
    selector: str,
    freshness_seconds: int,
) -> dict[str, object]:
    if freshness_seconds <= 0:
        raise AccountError("DA030")
    try:
        model, effort = split_selector(selector)
    except RecordError as error:
        raise AccountError("DA033") from error
    process = start_server(executable, account_home, account_home)
    client: RpcClient | None = None
    try:
        client = RpcClient(process)
        initialize(client)
        account_result = client.request("account/read", {"refreshToken": False})
        validate_authenticated_account(account_result)
        rate_result = client.request(
            "account/rateLimits/read",
            {"excludeResetCreditDetails": True, "supportsLunaReserve": False},
        )
        if not isinstance(rate_result, dict):
            raise AccountError("DA027")
        provider_account_id = rate_result.get("accountId")
        if not isinstance(provider_account_id, str):
            raise AccountError("DA020")
        if provider_account_id != expected_account_id:
            raise AccountError("DA021")
        exposed_model(client, model, effort)
        ordinary = rate_result.get("ordinaryUsageAllowed")
        if ordinary is not None and not isinstance(ordinary, bool):
            raise AccountError("DA028")
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
        close_ok = client.close() if client is not None else True
        stop_ok = stop_server(process)
        if not close_ok or not stop_ok:
            if sys.exc_info()[0] is None:
                raise AccountError("DA032")


def main(argv: list[str] | None = None) -> int:
    try:
        arguments = build_parser().parse_args(argv)
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
            try:
                split_selector(arguments.model)
            except RecordError as error:
                raise AccountError("DA033") from error
            if not arguments.codex.is_absolute():
                raise AccountError("DA006")
            if not arguments.workspace.is_absolute():
                raise AccountError("DA034")
            raise AccountError("DA031")
    except AccountError as error:
        print(f"daybreak-account {error.public_diagnostic()}", file=sys.stderr)
        return 1
    try:
        sys.stdout.write(dump_json(result))
        sys.stdout.flush()
    except (OSError, UnicodeError, ValueError):
        print(
            f"daybreak-account {AccountError('DA035').public_diagnostic()}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
