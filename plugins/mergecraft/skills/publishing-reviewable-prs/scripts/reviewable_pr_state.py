"""Shared exact-state operations for guarded PR publication."""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Literal

REPOSITORY_RE = re.compile(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+")
GITHUB_HOST = "github.com"
OID_RE = re.compile(r"[0-9a-f]{40}")
PR_URL_RE = re.compile(
    r"https://github\.com/(?P<repository>[^/]+/[^/]+)/pull/(?P<pr>[0-9]+)(?=\s|$)"
)
STORED_FIELDS = (
    "number,url,title,body,baseRefName,baseRefOid,headRefName,"
    "headRefOid,headRepository,headRepositoryOwner,isDraft,state"
)
READ_TIMEOUT_SECONDS = 30
MUTATION_TIMEOUT_SECONDS = 30
_ACTIVE_INTEGER_DIGIT_LIMIT = sys.get_int_max_str_digits()
_DEFAULT_INTEGER_DIGIT_LIMIT = sys.int_info.default_max_str_digits
# This is the supported Python runtime's conversion boundary, not a provider limit.
DECIMAL_IDENTIFIER_DIGIT_LIMIT = (
    min(_ACTIVE_INTEGER_DIGIT_LIMIT, _DEFAULT_INTEGER_DIGIT_LIMIT)
    if _ACTIVE_INTEGER_DIGIT_LIMIT
    else _DEFAULT_INTEGER_DIGIT_LIMIT
)
MAX_DECIMAL_JSON_INTEGER = 10**DECIMAL_IDENTIFIER_DIGIT_LIMIT - 1
MAX_RETAINED_JSON_DEPTH = 64
MAX_RETAINED_JSON_ITEMS = 100_000
READ_AUTHORITY_GUIDANCE = (
    "reuse existing read authority while it remains valid; obtain new authority "
    "only if the target or action is outside its scope"
)
MALFORMED_REST_PR_NODE = (
    "GitHub pull request pagination returned a malformed PR node"
)


class PublicationError(RuntimeError):
    """A PR publication operation could not reach a verified result."""


class StateReadError(PublicationError):
    """The current PR state could not be established."""


class MalformedRestPrNodeError(StateReadError):
    """A REST pull-request node failed structural admission."""

    def __init__(self) -> None:
        super().__init__(MALFORMED_REST_PR_NODE)


class LiveStateResponseError(StateReadError):
    """A live PR response failed safe, value-free admission."""

    def __init__(self, kind: Literal["incomplete", "malformed"]) -> None:
        self.kind = kind
        super().__init__(f"live PR response is {kind}")


class JsonReadError(StateReadError):
    """A JSON response failed one strict syntax requirement."""

    def __init__(
        self,
        kind: Literal["invalid", "duplicate-key", "non-finite"],
        message: str,
    ) -> None:
        self.kind = kind
        super().__init__(message)


class CommandReadError(StateReadError):
    """A read command failed with a value-free public diagnostic."""

    def __init__(
        self,
        *,
        return_code: int | None = None,
        timeout_seconds: int | None = None,
        malformed_output: bool = False,
        local_preparation_failed: bool = False,
        process_outcome_unknown: bool = False,
    ) -> None:
        self.return_code = return_code
        self.timeout_seconds = timeout_seconds
        self.malformed_output = malformed_output
        self.local_preparation_failed = local_preparation_failed
        self.process_outcome_unknown = process_outcome_unknown
        if local_preparation_failed:
            message = (
                "read command could not be prepared locally; no read command "
                "started; command inputs and preparation details were withheld "
                "because they may contain sensitive data; correct the local "
                "command inputs before retrying the read"
            )
        elif process_outcome_unknown:
            message = (
                "read command failed during process launch or communication; "
                "whether the read process started is unknown; command inputs, "
                "output, and failure details were withheld because they may "
                "contain sensitive data; verify the local CLI installation and "
                "execution environment before retrying the read"
            )
        elif timeout_seconds is not None:
            message = (
                f"read command timed out after {timeout_seconds} seconds; command "
                "output was withheld because it may contain sensitive data; verify "
                "connectivity and authentication before retrying the read"
            )
        elif return_code is not None:
            message = (
                f"read command rejected (return code {return_code}); command output "
                "was withheld because it may contain sensitive data; verify "
                "authentication, read access, repository identity, and CLI "
                "compatibility before retrying the read"
            )
        elif malformed_output:
            message = (
                "read command returned malformed successful output; strict UTF-8 "
                "was required and command output was withheld because it may "
                "contain sensitive data; verify CLI compatibility before retrying "
                "the read"
            )
        else:
            message = (
                "read command failed for an unclassified reason; command details "
                "were withheld because they may contain sensitive data"
            )
        super().__init__(message)


class CommandRejectedError(PublicationError):
    """A mutation command returned nonzero without exposing its output."""

    def __init__(self, return_code: int) -> None:
        self.return_code = return_code
        super().__init__(
            f"mutation command rejected (return code {return_code}); command output "
            "was withheld because it may contain sensitive data, so the rejection "
            "cause is unknown; verify authentication, write authority, repository "
            "policy, and CLI compatibility before any separately authorized attempt"
        )


class MutationPreparationError(PublicationError):
    """A mutation command failed local preparation before process invocation."""

    def __init__(self) -> None:
        super().__init__(
            "mutation command could not be prepared locally; no target mutation ran; "
            "command inputs and preparation details were withheld because they may "
            "contain sensitive data; correct the local command inputs before any "
            "separately authorized attempt"
        )


class MutationAmbiguousError(PublicationError):
    """A possible mutation timed out and must not be retried blindly."""

    def __init__(
        self,
        message: str,
        *,
        timeout_seconds: int | None = None,
        malformed_output: bool = False,
        process_outcome_unknown: bool = False,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.malformed_output = malformed_output
        self.process_outcome_unknown = process_outcome_unknown
        super().__init__(message)


def _exception_chain(error: BaseException) -> list[BaseException]:
    chain: list[BaseException] = []
    current: BaseException | None = error
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        chain.append(current)
        seen.add(id(current))
        current = current.__cause__
    return chain


def mutation_failure_diagnostic(error: PublicationError) -> str:
    """Return an actionable diagnostic derived only from approved safe fields."""

    chain = _exception_chain(error)
    for item in chain:
        if isinstance(item, MutationPreparationError):
            return str(item)
    for item in chain:
        if isinstance(item, CommandRejectedError):
            return str(item)
    for item in chain:
        if isinstance(item, MutationAmbiguousError) and item.malformed_output:
            return (
                "mutation command returned malformed successful output; strict "
                "UTF-8 was required and command output was withheld because it may "
                "contain sensitive data; mutation outcome is unknown; independently "
                "reread exact state and do not retry"
            )
    for item in chain:
        if (
            isinstance(item, MutationAmbiguousError)
            and item.timeout_seconds is not None
        ):
            return (
                "mutation outcome is unknown after a "
                f"{item.timeout_seconds}-second timeout; command output was withheld "
                "because it may contain sensitive data; independently reread exact "
                "state and do not retry"
            )
    if any(isinstance(item, MutationAmbiguousError) for item in chain):
        if any(
            isinstance(item, MutationAmbiguousError)
            and item.process_outcome_unknown
            for item in chain
        ):
            return (
                "mutation command failed during process launch or communication; "
                "whether the mutation process started is unknown and mutation "
                "outcome is unknown; command inputs, output, and failure details "
                "were withheld because they may contain sensitive data; "
                "independently reread exact state and do not retry"
            )
        return (
            "mutation outcome is unknown; command details were withheld because "
            "they may contain sensitive data; independently reread exact state and "
            "do not retry"
        )
    return (
        "mutation command failed for an unclassified reason; command details were "
        "withheld because they may contain sensitive data, so the cause is unknown; "
        "verify authentication, write authority, repository policy, and CLI "
        "compatibility before any separately authorized attempt"
    )


def read_failure_diagnostic(error: PublicationError) -> str:
    """Return a safe post-mutation reread diagnostic."""

    for item in _exception_chain(error):
        if isinstance(item, CommandReadError):
            if item.local_preparation_failed:
                return (
                    "post-mutation reread command could not be prepared locally; "
                    "no reread command started; command inputs and preparation "
                    "details were withheld because they may contain sensitive "
                    f"data; {READ_AUTHORITY_GUIDANCE}"
                )
            if item.process_outcome_unknown:
                return (
                    "post-mutation reread failed during process launch or "
                    "communication; whether the read process started is unknown; "
                    "command inputs, output, and failure details were withheld "
                    "because they may contain sensitive data; "
                    f"{READ_AUTHORITY_GUIDANCE}"
                )
            if item.timeout_seconds is not None:
                return (
                    "post-mutation reread timed out after "
                    f"{item.timeout_seconds} seconds; command output was withheld "
                    "because it may contain sensitive data; "
                    f"{READ_AUTHORITY_GUIDANCE}"
                )
            if item.malformed_output:
                return (
                    "post-mutation reread returned malformed successful output; "
                    "strict UTF-8 was required and command output was withheld "
                    "because it may contain sensitive data; "
                    f"{READ_AUTHORITY_GUIDANCE}"
                )
            if item.return_code is not None:
                return (
                    "post-mutation reread was rejected (return code "
                    f"{item.return_code}); command output was withheld because it "
                    "may contain sensitive data; verify authentication, read access, "
                    "repository identity, and CLI compatibility; "
                    f"{READ_AUTHORITY_GUIDANCE}"
                )
    response_failure = _response_failure_classification(error)
    if response_failure is not None:
        return (
            f"post-mutation reread returned {response_failure}; response content "
            "was withheld because it may contain sensitive data; "
            f"{READ_AUTHORITY_GUIDANCE}"
        )
    return (
        "post-mutation reread failed for an unclassified reason; details were "
        "withheld because they may contain sensitive data; "
        f"{READ_AUTHORITY_GUIDANCE}"
    )


def classified_read_failure(error: PublicationError, *, stage: str) -> str:
    """Return one value-free read classification for a caller-owned stage."""

    for item in _exception_chain(error):
        if not isinstance(item, CommandReadError):
            continue
        if item.local_preparation_failed:
            return (
                f"{stage} could not be prepared locally; no read command started; "
                "command inputs and preparation details were withheld because they "
                "may contain sensitive data"
            )
        if item.process_outcome_unknown:
            return (
                f"{stage} failed during process launch or communication; whether "
                "the read process started is unknown; command inputs, output, and "
                "failure details were withheld because they may contain sensitive "
                "data; verify the local CLI installation and execution environment"
            )
        if item.timeout_seconds is not None:
            return (
                f"{stage} timed out after {item.timeout_seconds} seconds; command "
                "output was withheld because it may contain sensitive data; verify "
                "connectivity and authentication"
            )
        if item.malformed_output:
            return (
                f"{stage} returned malformed successful output; strict UTF-8 was "
                "required and command output was withheld because it may contain "
                "sensitive data; verify CLI compatibility"
            )
        if item.return_code is not None:
            return (
                f"{stage} was rejected (return code {item.return_code}); command "
                "output was withheld because it may contain sensitive data; verify "
                "authentication, read access, repository identity, and CLI "
                "compatibility"
            )
    response_failure = _response_failure_classification(error)
    if response_failure is not None:
        return f"{stage} returned {response_failure}"
    return (
        f"{stage} failed for an unclassified reason; details were withheld because "
        "they may contain sensitive data"
    )


def _response_failure_classification(error: PublicationError) -> str | None:
    for item in _exception_chain(error):
        if isinstance(item, JsonReadError):
            return {
                "invalid": "invalid JSON",
                "duplicate-key": "JSON with duplicate object keys",
                "non-finite": "JSON with a non-finite value",
            }[item.kind]
        if isinstance(item, LiveStateResponseError):
            article = "an" if item.kind == "incomplete" else "a"
            return f"{article} {item.kind} response"
        if isinstance(item, MalformedRestPrNodeError):
            return "a malformed response"
    return None


@dataclass(frozen=True)
class ExpectedIdentity:
    repository: str
    pr_number: int
    base: str
    base_oid: str
    head: str
    head_oid: str
    head_owner: str
    head_repository: str

    @property
    def head_branch(self) -> str:
        return self.head.split(":", 1)[1]

    @property
    def url(self) -> str:
        return f"https://github.com/{self.repository}/pull/{self.pr_number}"


def _environment() -> dict[str, str]:
    environment = dict(os.environ)
    environment.pop("GH_HOST", None)
    environment.pop("GH_REPO", None)
    environment.update(
        {
            "GH_PROMPT_DISABLED": "1",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    return environment


def github_repository(repository: str) -> str:
    if REPOSITORY_RE.fullmatch(repository) is None:
        raise PublicationError("repository must be OWNER/REPO")
    return f"{GITHUB_HOST}/{repository}"


def run_read(
    arguments: list[str], *, input_text: str | None = None
) -> subprocess.CompletedProcess[str]:
    try:
        encoded_input = _prepare_command(arguments, input_text=input_text)
    except (TypeError, ValueError, UnicodeError) as error:
        raise CommandReadError(local_preparation_failed=True) from error
    try:
        result = subprocess.run(
            arguments,
            input=encoded_input,
            capture_output=True,
            text=False,
            check=False,
            timeout=READ_TIMEOUT_SECONDS,
            env=_environment(),
        )
    except subprocess.TimeoutExpired as error:
        raise CommandReadError(timeout_seconds=READ_TIMEOUT_SECONDS) from error
    except OSError as error:
        raise CommandReadError(process_outcome_unknown=True) from error
    if result.returncode:
        raise CommandReadError(return_code=result.returncode)
    try:
        stdout = _strict_utf8(result.stdout)
        stderr = _strict_utf8(result.stderr)
    except UnicodeDecodeError as error:
        raise CommandReadError(malformed_output=True) from error
    return subprocess.CompletedProcess(result.args, result.returncode, stdout, stderr)


def run_mutation(
    arguments: list[str], *, input_text: str | None = None
) -> subprocess.CompletedProcess[str]:
    try:
        encoded_input = _prepare_command(arguments, input_text=input_text)
    except (TypeError, ValueError, UnicodeError) as error:
        raise MutationPreparationError() from error
    try:
        result = subprocess.run(
            arguments,
            input=encoded_input,
            capture_output=True,
            text=False,
            check=False,
            timeout=MUTATION_TIMEOUT_SECONDS,
            env=_environment(),
        )
    except subprocess.TimeoutExpired as error:
        raise MutationAmbiguousError(
            "mutation command timed out after a possible mutation; command output "
            "was withheld because it may contain sensitive data; reread exact state "
            "and do not retry",
            timeout_seconds=MUTATION_TIMEOUT_SECONDS,
        ) from error
    except OSError as error:
        raise MutationAmbiguousError(
            "mutation command failed during process launch or communication; "
            "whether the mutation process started is unknown and mutation outcome "
            "is unknown; command inputs, output, and failure details were withheld "
            "because they may contain sensitive data; independently reread exact "
            "state and do not retry",
            process_outcome_unknown=True,
        ) from error
    if result.returncode:
        raise CommandRejectedError(result.returncode)
    try:
        stdout = _strict_utf8(result.stdout)
        stderr = _strict_utf8(result.stderr)
    except UnicodeDecodeError as error:
        raise MutationAmbiguousError(
            "mutation command returned malformed successful output; strict UTF-8 "
            "was required and command output was withheld because it may contain "
            "sensitive data; mutation outcome is unknown; independently reread "
            "exact state and do not retry",
            malformed_output=True,
        ) from error
    return subprocess.CompletedProcess(result.args, result.returncode, stdout, stderr)


def _prepare_command(arguments: list[str], *, input_text: str | None) -> bytes | None:
    """Validate local process inputs before any command can start."""

    for argument in arguments:
        if type(argument) is not str:
            raise TypeError("command argument is not exact text")
        os.fsencode(argument)
        if "\x00" in argument:
            raise ValueError("command argument contains a null byte")
    if input_text is None:
        return None
    if type(input_text) is not str:
        raise TypeError("command input is not exact text")
    return input_text.encode("utf-8")


def _strict_utf8(output: bytes | str) -> str:
    if isinstance(output, bytes):
        return output.decode("utf-8")
    return output


def parse_positive_decimal_identifier(value: str) -> int:
    """Parse one bounded ASCII-decimal provider identifier."""

    if (
        type(value) is not str
        or not value
        or len(value) > DECIMAL_IDENTIFIER_DIGIT_LIMIT
        or any(character < "0" or character > "9" for character in value)
    ):
        raise ValueError("provider identifier is not bounded ASCII decimal")
    parsed = int(value)
    if parsed <= 0:
        raise ValueError("provider identifier is not positive")
    return parsed


def _utf8_scalar(value: Any) -> str:
    if type(value) is not str:
        raise TypeError("required observation field is not a string")
    value.encode("utf-8")
    return value


def _parse_json_integer(value: str) -> int:
    digits = value[1:] if value.startswith("-") else value
    if len(digits) > DECIMAL_IDENTIFIER_DIGIT_LIMIT:
        raise ValueError("JSON integer exceeds the supported runtime digit limit")
    return int(value)


def _parse_json_float(value: str, source: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise JsonReadError(
            "non-finite",
            f"{source} contains non-finite JSON value",
        )
    return parsed


def _retained_json_copy(value: Any, *, require_utf8: bool = True) -> Any:
    """Return a detached, bounded copy of one strict JSON-compatible value."""

    item_count = 0

    def copy(item: Any, depth: int) -> Any:
        nonlocal item_count
        item_count += 1
        if item_count > MAX_RETAINED_JSON_ITEMS or depth > MAX_RETAINED_JSON_DEPTH:
            raise ValueError("retained JSON exceeds the supported structural boundary")
        if item is None or type(item) is bool:
            return item
        if type(item) is int:
            if abs(item) > MAX_DECIMAL_JSON_INTEGER:
                raise ValueError("JSON integer exceeds the supported runtime digit limit")
            return item
        if type(item) is float:
            if not math.isfinite(item):
                raise ValueError("retained JSON contains a non-finite number")
            return item
        if type(item) is str:
            if require_utf8:
                item.encode("utf-8")
            return item
        if type(item) is list:
            return [copy(child, depth + 1) for child in item]
        if type(item) is dict:
            result: dict[str, Any] = {}
            for key, child in item.items():
                if type(key) is not str:
                    raise TypeError("retained JSON object key is not a string")
                if require_utf8:
                    key.encode("utf-8")
                result[key] = copy(child, depth + 1)
            return result
        raise TypeError("retained value is not JSON-compatible")

    return copy(value, 0)


def strict_json(output: str, source: str) -> Any:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise JsonReadError(
                    "duplicate-key",
                    f"{source} contains duplicate JSON object keys",
                )
            value[key] = item
        return value

    def reject_constant(_: str) -> None:
        raise JsonReadError(
            "non-finite",
            f"{source} contains non-finite JSON value",
        )

    try:
        value = json.loads(
            output,
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
            parse_int=_parse_json_integer,
            parse_float=lambda item: _parse_json_float(item, source),
        )
        return _retained_json_copy(value, require_utf8=False)
    except (json.JSONDecodeError, RecursionError, TypeError, UnicodeError, ValueError) as error:
        raise JsonReadError(
            "invalid",
            f"{source} returned invalid JSON",
        ) from error


def validate_selected_specialists(value: Any) -> list[str]:
    """Capture one sorted, unique list of exact UTF-8 specialist names."""

    if type(value) is not list:
        raise PublicationError(
            "selected review specialists must be a sorted unique JSON array of "
            "non-empty strings"
        )
    try:
        captured = [_utf8_scalar(item) for item in value]
    except (TypeError, UnicodeEncodeError) as error:
        raise PublicationError(
            "selected review specialists must be a sorted unique JSON array of "
            "non-empty strings"
        ) from error
    if (
        not all(captured)
        or captured != sorted(captured)
        or len(captured) != len(set(captured))
    ):
        raise PublicationError(
            "selected review specialists must be a sorted unique JSON array of "
            "non-empty strings"
        )
    return captured


def parse_selected_specialists(output: str) -> list[str]:
    """Parse CLI specialist input without retaining or disclosing malformed data."""

    try:
        value = strict_json(output, "selected review specialists")
        return validate_selected_specialists(value)
    except (JsonReadError, PublicationError) as error:
        raise PublicationError(
            "selected review specialists must be a sorted unique JSON array of "
            "non-empty strings"
        ) from error


def validate_live_pr_observation(value: Any) -> dict[str, Any]:
    """Admit one complete live PR response without comparing exact identity."""

    try:
        admitted = _retained_json_copy(value)
    except (RecursionError, TypeError, UnicodeError, ValueError) as error:
        raise LiveStateResponseError("malformed") from error

    required = {
        "number",
        "url",
        "title",
        "body",
        "baseRefName",
        "baseRefOid",
        "headRefName",
        "headRefOid",
        "headRepository",
        "headRepositoryOwner",
        "isDraft",
        "state",
    }
    if type(admitted) is not dict:
        raise LiveStateResponseError("malformed")
    if not required.issubset(admitted):
        raise LiveStateResponseError("incomplete")

    head_repository = admitted["headRepository"]
    head_owner = admitted["headRepositoryOwner"]
    if type(head_repository) is not dict or type(head_owner) is not dict:
        raise LiveStateResponseError("malformed")
    if "login" not in head_owner:
        raise LiveStateResponseError("incomplete")
    has_repository_parts = {"owner", "name"}.issubset(head_repository)
    if "nameWithOwner" not in head_repository and not has_repository_parts:
        raise LiveStateResponseError("incomplete")
    if (
        "nameWithOwner" in head_repository
        and type(head_repository["nameWithOwner"]) is not str
        and not has_repository_parts
    ):
        raise LiveStateResponseError("malformed")

    url = admitted["url"]
    url_match = PR_URL_RE.fullmatch(url) if type(url) is str else None
    try:
        url_number = (
            parse_positive_decimal_identifier(url_match.group("pr"))
            if url_match is not None
            else None
        )
        required_strings = {
            field: _utf8_scalar(admitted[field])
            for field in (
                "url",
                "title",
                "body",
                "baseRefName",
                "baseRefOid",
                "headRefName",
                "headRefOid",
                "state",
            )
        }
        owner_login = _utf8_scalar(head_owner["login"])
        if type(head_repository.get("nameWithOwner")) is str:
            _utf8_scalar(head_repository["nameWithOwner"])
        else:
            repository_owner = head_repository["owner"]
            if type(repository_owner) is dict:
                repository_owner = repository_owner.get("login")
            _utf8_scalar(repository_owner)
            _utf8_scalar(head_repository["name"])
        repository_name = _utf8_scalar(_head_repository_name(admitted))
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise LiveStateResponseError("malformed") from error
    if (
        type(admitted["number"]) is not int
        or admitted["number"] <= 0
        or url_match is None
        or REPOSITORY_RE.fullmatch(url_match.group("repository")) is None
        or url_number is None
        or admitted["number"] != url_number
        or not required_strings["baseRefName"]
        or OID_RE.fullmatch(required_strings["baseRefOid"]) is None
        or not required_strings["headRefName"]
        or OID_RE.fullmatch(required_strings["headRefOid"]) is None
        or not owner_login
        or REPOSITORY_RE.fullmatch(repository_name) is None
        or type(admitted["isDraft"]) is not bool
        or required_strings["state"] not in {"OPEN", "CLOSED", "MERGED"}
    ):
        raise LiveStateResponseError("malformed")
    return admitted


def stored_pr(repository: str, pr_number: int) -> dict[str, Any]:
    try:
        result = run_read(
            [
                "gh",
                "-R",
                github_repository(repository),
                "pr",
                "view",
                str(pr_number),
                "--json",
                STORED_FIELDS,
            ]
        )
    except PublicationError as error:
        raise StateReadError(f"cannot read PR state: {error}") from error
    return validate_live_pr_observation(strict_json(result.stdout, "gh pr view"))


def open_prs(repository: str, base: str, head: str) -> list[dict[str, Any]]:
    try:
        result = run_read(
            [
                "gh",
                "api",
                "--hostname",
                GITHUB_HOST,
                "--method",
                "GET",
                "--paginate",
                "--slurp",
                f"repos/{repository}/pulls",
                "-f",
                "state=open",
                "-f",
                f"base={base}",
                "-f",
                f"head={head}",
                "-f",
                "per_page=100",
            ]
        )
    except PublicationError as error:
        raise StateReadError(f"cannot list matching PRs: {error}") from error
    value = strict_json(result.stdout, "GitHub pull request pagination")
    if not isinstance(value, list) or not all(isinstance(page, list) for page in value):
        raise StateReadError(
            "GitHub pull request pagination returned an unexpected value"
        )
    return [
        _stored_from_rest_pr(item, repository)
        for page in value
        for item in _validated_rest_page(page)
    ]


def _validated_rest_page(page: list[Any]) -> list[dict[str, Any]]:
    if not all(isinstance(item, dict) and item for item in page):
        raise MalformedRestPrNodeError
    return page


def _rest_body(value: Any) -> str:
    if value is None:
        return ""
    if type(value) is not str:
        raise TypeError("REST pull request body is not exact text or null")
    return value


def _stored_from_rest_pr(item: dict[str, Any], repository: str) -> dict[str, Any]:
    try:
        base = item["base"]
        head = item["head"]
        base_repository = base["repo"]
        head_repository = head["repo"]
        head_owner = head_repository["owner"]["login"]
        head_repository_name = head_repository["full_name"]
        stored = {
            "number": item["number"],
            "title": item["title"],
            "body": _rest_body(item["body"]),
            "baseRefName": base["ref"],
            "baseRefOid": base["sha"],
            "headRefName": head["ref"],
            "headRefOid": head["sha"],
            "headRepository": {"nameWithOwner": head_repository_name},
            "headRepositoryOwner": {"login": head_owner},
            "isDraft": item["draft"],
            "state": item["state"].upper(),
        }
    except (KeyError, TypeError, AttributeError) as error:
        raise MalformedRestPrNodeError from error

    if (
        not isinstance(base_repository, dict)
        or base_repository.get("full_name") != repository
    ):
        raise StateReadError(
            "GitHub pull request pagination drifted to another repository"
        )
    required_strings = (
        "title",
        "baseRefName",
        "baseRefOid",
        "headRefName",
        "headRefOid",
        "state",
    )
    if (
        type(stored["number"]) is not int
        or stored["number"] <= 0
        or not isinstance(stored["isDraft"], bool)
        or not isinstance(head_owner, str)
        or not head_owner
        or not isinstance(head_repository_name, str)
        or REPOSITORY_RE.fullmatch(head_repository_name) is None
        or any(
            not isinstance(stored[field], str) or not stored[field]
            for field in required_strings
        )
        or not isinstance(stored["body"], str)
    ):
        raise MalformedRestPrNodeError
    try:
        stored["url"] = f"https://github.com/{repository}/pull/{stored['number']}"
        return validate_live_pr_observation(stored)
    except (LiveStateResponseError, ValueError) as error:
        raise MalformedRestPrNodeError from error


def _head_repository_name(stored: dict[str, Any]) -> str | None:
    repository = stored.get("headRepository")
    if not isinstance(repository, dict):
        return None
    name_with_owner = repository.get("nameWithOwner")
    if isinstance(name_with_owner, str):
        return name_with_owner
    owner = repository.get("owner")
    name = repository.get("name")
    if isinstance(owner, dict):
        owner = owner.get("login")
    if isinstance(owner, str) and isinstance(name, str):
        return f"{owner}/{name}"
    return None


def validate_identity_inputs(
    *,
    repository: str,
    pr_number: int | None,
    base: str,
    base_oid: str,
    head: str,
    head_oid: str,
    head_owner: str,
    head_repository: str,
) -> None:
    if REPOSITORY_RE.fullmatch(repository) is None:
        raise PublicationError("repository must use OWNER/REPO")
    if REPOSITORY_RE.fullmatch(head_repository) is None:
        raise PublicationError("head repository must use OWNER/REPO")
    if pr_number is not None and (type(pr_number) is not int or pr_number <= 0):
        raise PublicationError("PR number must be positive")
    if not base.strip():
        raise PublicationError("base must be non-empty")
    if ":" not in head or not all(part.strip() for part in head.split(":", 1)):
        raise PublicationError("head must use OWNER:BRANCH")
    if head.split(":", 1)[0] != head_owner:
        raise PublicationError("head owner must exactly match the OWNER in head")
    if head_repository.split("/", 1)[0] != head_owner:
        raise PublicationError("head repository owner must match head owner")
    if OID_RE.fullmatch(base_oid) is None:
        raise PublicationError("base OID must be a lowercase 40-digit hex OID")
    if OID_RE.fullmatch(head_oid) is None:
        raise PublicationError("head OID must be a lowercase 40-digit hex OID")


def head_base_matches(
    stored: dict[str, Any],
    *,
    base: str,
    head: str,
    head_owner: str,
    head_repository: str,
) -> bool:
    owner = stored.get("headRepositoryOwner")
    stored_owner = owner.get("login") if isinstance(owner, dict) else None
    return (
        stored.get("baseRefName") == base
        and stored.get("headRefName") == head.split(":", 1)[1]
        and stored_owner == head_owner
        and _head_repository_name(stored) == head_repository
        and stored.get("state") == "OPEN"
    )


def identity_matches(stored: dict[str, Any], expected: ExpectedIdentity) -> bool:
    return (
        type(expected.pr_number) is int
        and type(stored.get("number")) is int
        and stored.get("number") == expected.pr_number
        and stored.get("url") == expected.url
        and head_base_matches(
            stored,
            base=expected.base,
            head=expected.head,
            head_owner=expected.head_owner,
            head_repository=expected.head_repository,
        )
        and stored.get("baseRefOid") == expected.base_oid
        and stored.get("headRefOid") == expected.head_oid
    )


def state_matches(
    stored: dict[str, Any],
    expected: ExpectedIdentity,
    *,
    title: str,
    body: str,
    is_draft: bool,
) -> bool:
    return (
        identity_matches(stored, expected)
        and stored.get("title") == title
        and stored.get("body") == body
        and stored.get("isDraft") is is_draft
    )
